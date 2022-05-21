"""P4 parsers."""

from abc import ABC, abstractmethod

from pyp4 import expr, PacketIO
from pyp4.trace import get_logger, Trace

logger = get_logger(__name__)


class Parser:
    """A P4 parser.

    Parameters
    ----------
    process_name : `str`
        The name of the process running the P4 program.
    bm_parser : dict
        Parser definition in BM JSON format.
    packet_io : `pyp4.PacketIO`
        External packet representation type.

    """

    @Trace(logger)
    def __init__(
            self,
            process_name,
            bm_parser,
            packet_io=PacketIO.BINARY,
    ):
        # pylint: disable=too-many-arguments
        # reason: all arguments are required during initialisation
        self.__process_name = process_name
        self.__bm_parser = bm_parser
        self.__collector = None
        self.logger = None

        if packet_io == PacketIO.BINARY:
            self.__collector = BinaryCollector()
        else:
            assert packet_io == PacketIO.STACK
            self.__collector = StackCollector()

        # The ParseState class is the actual work horse of the parser.
        self.__states = {
            parse_state["name"]: ParseState(self.__process_name, parse_state)
            for parse_state in self.__bm_parser["parse_states"]
        }

    @property
    def name(self):
        """`str`: Name of the parser."""
        return self.__bm_parser["name"]

    @property
    def process_name(self):
        """`str`: Name of the process running the P4 program this parser belongs to."""
        return self.__process_name

    @Trace(logger)
    def process(self, bus, packet_in):
        """Parse incoming packet.

        Parameters
        ----------
        bus : `pyp4.packet.Bus`
            The metadata + headers bus.
        packet_in : `<PacketIO specific PacketClass>`
            The input packet.

        """

        self.__collector.reset(bus, packet_in)

        state = self.__bm_parser["init_state"]
        while state is not None:
            self.logger.debug(f"state-{state}")
            state = self.__states[state].process(self.__collector)

        self.__collector.finalise()


class ParseState:
    """A parser state.

    Parameters
    ----------
    process_name : `str`
        The name of the process that will be running the P4 program.
    bm_parse_state : dict
        Parse state definition in BM JSON format.

    """

    @Trace(logger)
    def __init__(self, process_name, bm_parse_state):
        self.__process_name = process_name
        self.__bm_parse_state = bm_parse_state
        self.logger = None

    @property
    def name(self):
        """`str`: Name of the parse state."""
        return self.__bm_parse_state["name"]

    @property
    def process_name(self):
        """`str`: Name of the process running the P4 program this parse state belongs to."""
        return self.__process_name

    @Trace(logger)
    def process(self, collector):
        """Process parser state for incoming packet.

        Parameters
        ----------
        collector : `pyp4.parser.Collector`
            Parse collector.

        Returns
        -------
        `str`
            The name of the next state.

        """
        for op in self.__bm_parse_state["parser_ops"]:
            self.logger.debug(f"op-{op['op']}")
            if op["op"] == "extract":
                header_name = collector.extract(op["parameters"])
                self.logger.debug(f"header={header_name}")
            else:
                # Eventually all operations should be supported
                raise NotImplementedError

        transition_key = None
        if self.__bm_parse_state["transition_key"]:
            # More than one key is legal, but not sure what that means
            assert len(self.__bm_parse_state["transition_key"]) == 1
            transition_key = self.__bm_parse_state["transition_key"][0]
            transition_key_val = expr.rval(collector.bus, transition_key, None)

        for transition in self.__bm_parse_state["transitions"]:
            if transition["type"] == "default":
                return transition["next_state"]

            rval = expr.rval(collector.bus, transition, None)
            if transition_key_val == rval:
                return transition["next_state"]

        # Should not get here
        raise AssertionError


class Collector(ABC):
    """A parse collector."""

    def __init__(self):
        self.__packet_in = None
        self.__bus = None

    def reset(self, bus, packet_in):
        """Reset the collector with a new input packet and bus.

        Parameters
        ----------
        bus : `pyp4.packet.Bus`
            The metadata + headers bus for an empty packet.
        packet_in : `<PacketIO specific PacketClass>`
            The input packet.

        """
        self.__bus = bus
        self.__packet_in = packet_in

    @property
    def _packet_in(self):
        return self.__packet_in

    @property
    def bus(self):
        """`pyp4.packet.Bus`: The bus that the collector is using."""
        return self.__bus

    def extract(self, parameters):
        """Extract a packet header.

        The collector stores the header internally until :py:meth:`pyp4.parser.Collector.finalise`
        is called at which point the fully parsed packet can be retrieved.

        Parameters
        ----------
        parameters : dict
            The parse operation parameters in BM JSON format.

        Returns
        -------
        `str`
            The name of extracted header.

        """
        assert self.__packet_in
        assert len(parameters) == 1
        header_name = parameters[0]["value"]
        self._extract(header_name)
        return header_name

    @abstractmethod
    def _extract(self, header_name):
        raise NotImplementedError

    def finalise(self):
        """Finalise the parsed packet.

        This will reset the collector.

        """
        self.bus.packet.unparsed = self.__packet_in
        self.reset(None, None)


class StackCollector(Collector):
    """A parse collector for header stack packets."""

    def _extract(self, header_name):
        self.bus.packet[header_name] = self._packet_in.pop()


class BinaryCollector(Collector):
    """A parse collector for binary packets."""

    def _extract(self, header_name):
        self.bus.packet.add_header(header_name)
        header = self.bus.packet[header_name]
        header.from_bytes(self._packet_in.get_next(header.bytelen))
