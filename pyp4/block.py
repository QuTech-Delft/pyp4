"""P4-programmable blocks."""

from pyp4.table import Conditional, Table
from pyp4.trace import get_logger, Trace

logger = get_logger(__name__)


class Block:
    """A P4-programmable block.

    Parameters
    ----------
    process_name : `str`
        The name of the process running the P4 program.
    bm_block : dict
        Block definition in BM JSON format.
    actions : dict of {`int` -> `pyp4.action.Action`}
        The dictionary of actions keyed on the action ID.

    """

    @Trace(logger)
    def __init__(self, process_name, bm_block, actions):
        self.__process_name = process_name
        self.__bm_block = bm_block
        self.__actions = actions
        self.logger = None

        # Mappings required for tables.
        action_id_to_name = {act_id: act.name for act_id, act in self.__actions.items()}
        action_name_to_id = {act.name: act_id for act_id, act in self.__actions.items()}

        # Separate tables and conditionals as that's what BM does
        self.__tables = {
            tab["name"]: Table(self.__process_name, tab, action_id_to_name, action_name_to_id)
            for tab in self.__bm_block["tables"]
        }
        self.__conditionals = {
            cond["name"]: Conditional(self.__process_name, cond)
            for cond in self.__bm_block["conditionals"]
        }

    @property
    def name(self):
        """`str`: Name of the block."""
        return self.__bm_block["name"]

    @property
    def process_name(self):
        """`str`: Name of the process running the P4 program this block belongs to."""
        return self.__process_name

    @property
    def tables(self):
        """dict of {`str` -> `pyp4.table.Table`}: The tables in this block keyed on the table name.

        """
        return self.__tables

    def __conditional(self, conditional, bus):
        # pylint:disable=no-self-use
        """Apply a conditional.

        Parameters
        ----------
        conditional : `pyp4.table.Conditional`
            Conditional definition in BM JSON format.
        bus : `pyp4.packet.Bus`
            The metadata + headers bus.

        Returns
        -------
        `str`, optional
            The name of the next table.

        """
        return conditional.apply(bus)

    def __table(self, table, bus):
        """Apply a table.

        Parameters
        ----------
        table : `pyp4.table.Table`
            The table definition in BM JSON format.
        bus : `pyp4.packet.Bus`
            The metadata + headers bus.

        Returns
        -------
        `str`, optional
            The name of the next table.

        """
        apply_result = table.apply(bus)
        action_id = apply_result.action_run.action_id
        action_data = apply_result.action_run.action_data
        action = self.__actions[action_id]
        assert action.name == apply_result.action_run.action_name
        action.process(bus, action_data)
        return table.next_table(apply_result)

    @Trace(logger)
    def process(self, bus):
        """Process the block.

        Parameters
        ----------
        bus : `pyp4.packet.Bus`
            The metadata + headers bus.

        """
        self.logger.debug(f"metadata={bus.metadata}")
        self.logger.debug(f"packet={bus.packet}")

        next_table = self.__bm_block["init_table"]

        while next_table is not None:
            self.logger.debug(f"next_table={next_table}")
            if next_table in self.__tables:
                next_table = self.__table(self.__tables[next_table], bus)
            else:
                assert next_table in self.__conditionals
                next_table = self.__conditional(self.__conditionals[next_table], bus)

        self.logger.debug(f"next_table={next_table}")
