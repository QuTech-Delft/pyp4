"""P4 process."""

from abc import ABC, abstractmethod
from itertools import filterfalse, tee
from typing import Any, Dict, List, Optional

from pyp4 import PacketIO
from pyp4.action import Action
from pyp4.deparser import Deparser
from pyp4.packet import Bus, Header, Packet
from pyp4.parser import Parser
from pyp4.block import Block


def _partition(pred, iterable):
    """Use a predicate to partition entries into false entries and true entries"""
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    it1, it2 = tee(iterable)
    return filterfalse(pred, it1), filter(pred, it2)


class Process(ABC):
    """A P4 process.

    A P4 process is an instance of a P4 program. PyP4 supports running P4 programs that were
    compiled into the Behavioral Model (BM) JSON format.

    This `pyp4.processor.Process` class is an abstract base class for P4 processes. A concrete
    process subclass must be provided for each P4 architecture.

    Parameters
    ----------
    name
        The process name.
    program
        The program to execute in the BM format.
    packet_io
        External packet representation type.
    extern : <processor specific ExternClass>, optional
        The processor's extern object for extern calls.

    """
    # pylint: disable=too-many-instance-attributes
    # Reason: this is the central class of PyP4 - it needs to hold a lot.

    # P4 spec only guarantees that individual extern calls are executed atomically. Multiple extern
    # operations do not have such a guarantee. Therefore, the P4 spec allows for an @atomic
    # annotation to indicate blocks that need to be executed atomically. However, it is not clear
    # how this is supported within BMv2 JSON (if at all).
    #
    # Note that this is not an issue for single threaded applications running this code since all
    # packets will be processed one by one anyway.

    # Make __init__ abstract to force derived classes to provide the extern.
    @abstractmethod
    def __init__(
            self,
            name: str,
            program: Dict,
            packet_io: PacketIO = PacketIO.BINARY,
            extern: Optional[Any] = None,
    ):
        self.__name = name

        # Validate the program.
        self._validate_program(program)

        # Load the struct definitions.
        struct_types = {struct_t["name"]: struct_t for struct_t in program["header_types"]}

        # Split the struct types and definitions into metadata and headers.
        headers, metadata = _partition(lambda hdr: hdr["metadata"], program["headers"])

        self.__header_defs = {hdr["name"]: hdr for hdr in headers}
        self.__header_types = {
            hdr["header_type"]: struct_types[hdr["header_type"]]
            for hdr in self.__header_defs.values()
        }

        self.__metadata_defs = {hdr["name"]: hdr for hdr in metadata}
        self.__metadata_types = {
            hdr["header_type"]: struct_types[hdr["header_type"]]
            for hdr in self.__metadata_defs.values()
        }

        # We only need to validate the packet headers for packet IO.
        self.__validate_packet_io(self.__header_types, packet_io)

        # Parsers.
        self.__parsers = {
            pars["name"]: Parser(self.name, pars, packet_io)
            for pars in program["parsers"]
        }

        # Actions.
        actions = {
            act["id"]: Action(self.name, act, extern)
            for act in program["actions"]
        }

        # Blocks (called pipelines in the JSON).
        self.__blocks = {
            block["name"]: Block(self.name, block, actions)
            for block in program["pipelines"]
        }

        # Deparsers.
        self.__deparsers = {
            depars["name"]: Deparser(self.name, depars, packet_io)
            for depars in program["deparsers"]
        }

        # Keep track of enums so that they can be used by name.
        self.__enums = {
            enum["name"]: {kv[0]: kv[1] for kv in enum["entries"]}
            for enum in program["enums"]
        }

    @property
    def name(self) -> str:
        """The name of the process."""
        return self.__name

    @staticmethod
    @abstractmethod
    def _validate_program(program: Dict) -> None:
        """Validate the program.

        Parameters
        ----------
        process
            The program to validate.

        """
        raise NotImplementedError

    @staticmethod
    def _validate_program_pipeline(
            program: Dict,
            parsers: List[str],
            blocks: List[str],
            deparsers: List[str],
    ) -> None:
        """Validate the program pipeline elements.

        Parameters
        ----------
        progam
            The program to validate.
        parsers
            List of parser names that the architecture requires the program to have.
        blocks
            List of block names that the architecture requires the program to have.
        deparser
            List of deparser names that the architecture requires the program to have.

        """
        Process.__validate_program_pipeline_element("parser", parsers, program)
        Process.__validate_program_pipeline_element("pipeline", blocks, program)
        Process.__validate_program_pipeline_element("deparser", deparsers, program)

    @staticmethod
    def __validate_program_pipeline_element(name: str, required: List[str], program: Dict) -> None:
        """Validate a particular element type (e.g. parser, block) of the program.

        Parameters
        ----------
        name
            The name of the element type.
        required
            List of element names that the architecture requires the program to have.
        progam
            The program to validate.

        """
        if f"{name}s" not in program:
            raise TypeError(f"Program is required to have {name}(s)")
        provided = [elem["name"] for elem in program[f"{name}s"]]

        if len(required) != len(provided):
            raise TypeError(f"Program must have {len(required)} {name}(s) : "
                            f"provided program has {len(provided)} {name}(s)")
        for elem in required:
            if elem not in provided:
                raise TypeError(f"Program must have a {name} called \"{elem}\" : "
                                f"Provided program has {provided}")

    @staticmethod
    def __validate_packet_io(header_types: Dict, packet_io: PacketIO):
        if packet_io == PacketIO.BINARY:
            # We do not support headers that do not divide nicely into 8-bit bytes.
            for hdr_t in header_types.values():
                invalid = filter(lambda field: (field[1] % 8) != 0, hdr_t["fields"])
                if next(invalid, None) is not None:
                    raise ValueError(
                        "Only bitwidths that are a multiple of 8 are supported for "
                        "non-metadata headers when using PacketIO.BINARY"
                    )
        else:
            assert packet_io == PacketIO.STACK
            # NO-OP: everything is okay

    def header(self, header_name: str, metadata: bool = False) -> Header:
        """Get a new instance of a header by its name.

        Parameters
        ----------
        header_name
            The name of the header.
        metadata : optional
            True if this is actually a metadata "header".

        Returns
        -------
        :
            A new instance of that header.

        """
        (defs, types) = ((self.__metadata_defs, self.__metadata_types) if metadata else
                         (self.__header_defs, self.__header_types))

        assert header_name in defs
        header_type = defs[header_name]["header_type"]
        assert header_type in types

        return Header(types[header_type]["fields"])

    def metadata(self) -> Dict[str, Header]:
        """Get a new instance of the program metadata dictionary.

        Returns
        -------
        :
            A dictionary of metadata str -> `~pyp4.packet.Header`.

        """
        return {name: self.header(name, True) for name in self.__metadata_defs}

    def packet(self) -> Packet:
        """Get a new instance of a packet.

        Returns
        -------
        :
            A new instance of the internal representation of a packet.

        """
        return Packet(self.__header_types, self.__header_defs)

    def bus(self) -> Bus:
        """Get a new instance of a bus.

        Returns
        -------
        :
            A new instance of the internal metadata + headers bus.

        """
        return Bus(self.metadata(), self.packet())

    @property
    def parsers(self) -> Dict[str, Parser]:
        """Process parsers keyed on their names."""
        return self.__parsers

    @property
    def blocks(self) -> Dict[str, Block]:
        """Process blocks keyed on their names."""
        return self.__blocks

    @property
    def deparsers(self) -> Dict[str, Deparser]:
        """Process deparsers keyed on their names."""
        return self.__deparsers

    @property
    def enums(self) -> Dict:
        """Program enums."""
        return self.__enums
