"""P4 match+action tables."""

import copy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from pyp4 import expr
from pyp4.packet import Bus
from pyp4.trace import get_logger, Trace

logger = get_logger(__name__)


class Conditional:
    """A BM conditional table.

    BM represents conditional statements as a "conditional" objects on the same level as tables.

    Parameters
    ----------
    process_name
        The name of the process running the P4 program.
    bm_conditional
        Conditional definition in BM JSON format.

    """

    @Trace(logger)
    def __init__(self, process_name: str, bm_conditional: Dict):
        self.__process_name = process_name
        self.__bm_conditional = bm_conditional
        self.__expression = bm_conditional["expression"]
        self.logger = None

    @property
    def name(self) -> str:
        """Name of the conditional."""
        return self.__bm_conditional["name"]

    @property
    def process_name(self) -> str:
        """Name of the process running the P4 program this conditional belongs to."""
        return self.__process_name

    @Trace(logger)
    def apply(self, bus: Bus) -> Optional[str]:
        """Evaluate the conditional on the given bus.

        Parameters
        ----------
        bus
            The metadata + headers bus.

        Returns
        -------
        :
            The name of the next table.

        """
        self.logger.debug(
            f"{self.name}-"
            f"\"{self.__bm_conditional.get('source_info', {}).get('source_fragment', '')}\""
        )
        result = expr.rval(bus, self.__expression, None)
        assert result is not None
        self.logger.debug(f"rval={result}")
        return (
            self.__bm_conditional["true_next"] if result else
            self.__bm_conditional["false_next"]
        )


@dataclass
class _ActionRun:
    """Information about action to run."""
    action_id: int
    action_name: str
    action_data: list


@dataclass
class _ApplyResult:
    """Result of table.apply."""
    hit: bool
    action_run: _ActionRun


class Table:
    """A P4 match+action table."""

    @Trace(logger)
    def __init__(self, process_name: str, bm_table: Dict, action_id_to_name, action_name_to_id):
        """
        Parameters
        ----------
        process_name : `str`
            The name of the process running the P4 program.
        bm_table : dict
            Table definition in BM JSON format.
        action_id_to_name : dict of {`int` -> `str`}
            Map of action IDs to their names.
        action_name_to_id : dict of {`str` -> `int`}
            Map of action names to their IDs.

        """
        self.__process_name = process_name
        self.__bm_table = bm_table
        self.__entries = {}
        self.__next_handle = 0
        self.__action_id_to_name = action_id_to_name
        self.__action_name_to_id = action_name_to_id
        self.logger = None

        self.__insert_const_entries()

    @property
    def name(self) -> str:
        """Name of the table."""
        return self.__bm_table["name"]

    @property
    def process_name(self) -> str:
        """Name of the process running the P4 program this table belongs to."""
        return self.__process_name

    def reset(self) -> None:
        """Reset the table contents to their original state. Const entries will not be removed.

        """
        self.logger.debug(f"{self.logger.name}.reset")

        self.__entries.clear()
        self.__next_handle = 0

        self.__insert_const_entries()

    def __insert_const_entries(self):
        if "entries" not in self.__bm_table:
            return

        for entry in self.__bm_table["entries"]:
            self.__entries[self.__next_handle] = copy.deepcopy(entry)
            self.__entries[self.__next_handle]["const"] = True
            self.__next_handle += 1

    @Trace(logger)
    def apply(self, bus: Bus) -> _ApplyResult:
        """Get the action for the provided packet.

        Parameters
        ----------
        bus
            The metadata+headers bus.

        Returns
        -------
        :
            The apply result which indicates if it was a hit or miss and the action to run.

        """
        self.logger.debug(
            f"{self.name}-\"{self.__bm_table.get('source_info', {}).get('source_fragment', '')}\""
        )
        key_value = self.__extract_key_value_from_bus(bus)
        apply_result = self.__lookup_key_value(key_value)
        self.logger.debug(
            f"key={key_value} => "
            f"hit={apply_result.hit}; "
            f"action_name={self.__action_id_to_name[apply_result.action_run.action_id]}; "
            f"action_data={apply_result.action_run.action_data}"
        )
        return apply_result

    def insert_entry(
            self,
            key: Union[int, Tuple[int, int], List[Union[int, Tuple[int, int]]]],
            action_name: str,
            action_data: List[Union[str, int]],
    ) -> int:
        """Insert a new entry into the table.

        Parameters
        ----------
        key
            The match key(s) for this entry. If the key entry's type in the table definition is
            ``exact`` the key must be a single integer. If the key type is ``lpm`` the key is a
            tuple of (key, prefix length). If the key type is ``ternary`` the key is a tuple of
            (key, mask). If the key type is ``range`` the key is a tuple of (start, end).
        action_name
            The name of the action to execute on a hit.
        action_data
            The data to pass to the action on a hit.

        Returns
        -------
        :
            The handle to the entry which can be used to refer to this entry later.

        """
        self.logger.debug(
            f"{self.logger.name}.insert_entry-"
            f"key={key}; action_name={action_name}; action_data={action_data}"
        )

        if not isinstance(key, list):
            key = [key]

        if len(key) != len(self.__bm_table["key"]):
            raise ValueError(
                f"Length of key {key} does not match expected length {len(self.__bm_table['key'])}"
            )

        match_key = []
        for entry_key, table_key in zip(key, self.__bm_table["key"]):
            if table_key["match_type"] == "exact":
                match_key.append({
                        "match_type": "exact",
                        "key": hex(entry_key),
                    })
            elif table_key["match_type"] == "lpm":
                if not (isinstance(entry_key, tuple) and len(entry_key) == 2):
                    raise ValueError
                match_key.append({
                    "match_type": "lpm",
                    "key": hex(entry_key[0]),
                    "prefix_length": int(entry_key[1]),
                })
            elif table_key["match_type"] == "range":
                if not (isinstance(entry_key, tuple) and len(entry_key) == 2):
                    raise ValueError
                match_key.append({
                    "match_type": "range",
                    "start": hex(entry_key[0]),
                    "end": hex(entry_key[1]),
                })
            else:
                # assert table_key["match_type"] == "ternary"
                raise NotImplementedError

        assert match_key
        new_entry = {
            "match_key": match_key,
            "action_entry": {
                "action_id": self.__action_name_to_id[action_name],
                "action_data": [hex(item) for item in action_data],
            },
            "priority": 1,
            "const": False,
        }

        for tab_entry in self.__entries.values():
            assert new_entry["match_key"] != tab_entry["match_key"]

        entry_handle = self.__next_handle
        self.__next_handle += 1

        self.__entries[entry_handle] = new_entry

        self.logger.debug(f"{self.logger.name}.insert_entry-entry_handle={entry_handle}")
        return entry_handle

    def remove_entry(self, entry_handle: int) -> None:
        """Remove an entry from the table.

        Parameters
        ----------
        entry_handle
            The table entry handle returned by insert_entry.

        """
        self.logger.debug(f"{self.logger.name}.remove_entry-entry_handle={entry_handle}")

        entry = self.__entries.pop(entry_handle, None)
        if entry is not None and entry["const"]:
            # The user is NEVER given const entry handles so the user cannot know that this handle
            # actually belongs to any entry. Therefore, we reinsert the entry and return without
            # removing anything like we would normally do for an invalid handle.
            self.__entries[entry_handle] = entry

    def __extract_key_value_from_bus(self, bus: Bus) -> List[Dict]:
        key_value = []
        for key_elem in self.__bm_table["key"]:
            [header_name, field_name] = key_elem["target"]
            field = bus.get_hdr(header_name)[field_name]
            key_elem_value = {}
            key_elem_value["match_type"] = key_elem["match_type"]
            key_elem_value["value"] = field
            key_value.append(key_elem_value)
        return key_value

    def __lookup_key_value(self, key_value: List[Dict]) -> _ApplyResult:
        # Do a brute-force lookup, checking each entry. In general, simulated soft-switch tables are
        # small and performance is not critical. If performance was more important, we could have
        # represented the table in a more optimized way, e.g. a Patricia tree for LPM tables.
        # pylint:disable=unsubscriptable-object
        best_entry = None
        for entry in self.__entries.values():
            if Table.__key_value_matches_entry(key_value, entry):
                if ((best_entry is None) or (entry["priority"] < best_entry["priority"])):
                    best_entry = entry

        if best_entry:
            action_id = best_entry["action_entry"]["action_id"]
            action_data = best_entry["action_entry"]["action_data"]
        else:
            # We could not find any matching entry; return the default action.
            action_id = self.__bm_table["default_entry"]["action_id"]
            action_data = self.__bm_table["default_entry"]["action_data"]

        return _ApplyResult(hit=(best_entry is not None),
                            action_run=_ActionRun(
                                action_id=action_id,
                                action_name=self.__action_id_to_name[action_id],
                                action_data=action_data,
                            ))

    @staticmethod
    def __key_value_matches_entry(key_value: List[Dict], entry: Dict) -> bool:
        match_key = entry["match_key"]
        assert len(key_value) == len(match_key)
        for key_value_elem, match_elem in zip(key_value, match_key):
            if not Table.__key_elem_matches_entry(key_value_elem, match_elem):
                return False
        return True

    @staticmethod
    def __key_elem_matches_entry(key_value_elem: Dict, match_elem: Dict) -> bool:
        assert key_value_elem["match_type"] == match_elem["match_type"]
        match_type = key_value_elem["match_type"]
        if match_type == "exact":
            return Table.__exact_key_elem_matches_entry(key_value_elem, match_elem)
        if match_type == "lpm":
            return Table.__lpm_key_elem_matches_entry(key_value_elem, match_elem)
        if match_type == "range":
            return Table.__range_key_elem_matches_entry(key_value_elem, match_elem)
        raise NotImplementedError

    @staticmethod
    def __exact_key_elem_matches_entry(key_elem: Dict, match_elem: Dict) -> bool:
        field_value = key_elem["value"].val
        match_value = int(match_elem["key"], 16)
        return field_value == match_value

    @staticmethod
    def __lpm_key_elem_matches_entry(key_elem: Dict, match_elem: Dict) -> bool:
        field = key_elem["value"]
        field_len = field.bitwidth
        prefix_len = match_elem["prefix_length"]
        mask = Table.__prefix_to_mask(field_len, prefix_len)
        field_value = field.val & mask
        match_value = int(match_elem["key"], 16)
        return field_value == match_value

    @staticmethod
    def __range_key_elem_matches_entry(key_elem: Dict, match_elem: Dict) -> bool:
        field_value = key_elem["value"].val
        start_value = int(match_elem["start"], 16)
        end_value = int(match_elem["end"], 16)
        return start_value <= field_value <= end_value

    @staticmethod
    def __prefix_to_mask(field_len: int, prefix_len: int) -> int:
        """Convert a prefix length into a mask (which requires knowing the field length).

        """
        assert prefix_len <= field_len
        leading_ones = prefix_len
        mask = (1 << leading_ones) - 1
        trailing_zeros = field_len - prefix_len
        mask <<= trailing_zeros
        return mask

    def next_table(self, apply_result: _ApplyResult) -> str:
        """Determine the next table following the given action for this table.

        Parameters
        ----------
        apply_result
            The result from running table.apply which we want to follow up.

        Returns
        -------
        :
            The next table name.

        """
        next_tables = self.__bm_table["next_tables"]
        if "__HIT__" in next_tables:
            # The next table is predicated on a hit/miss instead.
            assert "__MISS__" in next_tables
            assert len(next_tables) == 2
            return next_tables["__HIT__" if apply_result.hit else "__MISS__"]
        # There is a "base_default_next" entry, but it seems the compiler now explicitly populates
        # the entire "next_tables" dictionary.
        return next_tables[apply_result.action_run.action_name]
