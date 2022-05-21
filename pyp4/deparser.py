"""P4 deparsers."""

from abc import ABC, abstractmethod

from pyp4 import PacketIO
from pyp4.packet import HeaderStack
from pyp4.trace import get_logger, Trace

logger = get_logger(__name__)


class Deparser:
    """A P4 deparser.

    Parameters
    ----------
    process_name : `str`
        The name of the process running the P4 program.
    bm_deparser : dict
        Deparser definition in  BM JSON format.
    packet_io : `pyp4.PacketIO`
        External packet representation type.

    """

    @Trace(logger)
    def __init__(self, process_name, bm_deparser, packet_io=PacketIO.BINARY):
        self.__process_name = process_name
        self.__bm_deparser = bm_deparser
        self.__emitter = None
        self.logger = None

        if packet_io == PacketIO.BINARY:
            self.__emitter = BinaryEmitter()
        else:
            assert packet_io == PacketIO.STACK
            self.__emitter = StackEmitter()

    @property
    def name(self):
        """`str`: Name of the deparser."""
        return self.__bm_deparser["name"]

    @property
    def process_name(self):
        """`str`: Name of the process running the P4 program this deparser belongs to."""
        return self.__process_name

    @Trace(logger)
    def process(self, packet):
        """Deparse a packet.

        Parameters
        ----------
        packet : `pyp4.packet.Packet`
            The packet to deparse

        Returns
        -------
        `<PacketIO specific PacketClass>`
            The output packet.

        """
        self.__emitter.reset(packet)

        for header_name in self.__bm_deparser["order"]:
            if self.__emitter.emit(header_name):
                self.logger.debug(f"header={header_name}")

        return self.__emitter.finalise()


class Emitter(ABC):
    """A deparse emitter."""

    def __init__(self):
        self.__packet = None
        self.__packet_out = None

    @property
    def _packet(self):
        return self.__packet

    @property
    def _packet_out(self):
        return self.__packet_out

    @_packet_out.setter
    def _packet_out(self, packet_out):
        self.__packet_out = packet_out

    def reset(self, packet):
        """Reset the emitter with a new packet to deparse.

        Parameters
        ----------
        packet : `pyp4.packet.Packet`
            The packet to deparse.

        """
        self.__packet = packet
        self._reset()

    @abstractmethod
    def _reset(self):
        raise NotImplementedError

    def emit(self, header_name):
        """Emit a header.

        The emitter stores the header internally until :py:meth:`pyp4.deparser.Emitter.finalise` is
        called at which point the fully deparsed packet can be retrieved.

        Parameters
        ----------
        header_name : `str`
            The name of the header to emit.

        Returns
        -------
        `bool`
            True if the header was valid and emitted. Otherwise, False.

        """
        if self.__packet.is_valid(header_name):
            self._emit(header_name)
            return True
        return False

    @abstractmethod
    def _emit(self, header_name):
        raise NotImplementedError

    def finalise(self):
        """Finalise and return the deparsed packet.

        This will reset the emitter.

        Returns
        -------
        `<PacketIO specific PacketClass>`
             The deparsed packet.

        """
        self._finalise()
        packet_out = self.__packet_out

        self.reset(None)
        return packet_out

    @abstractmethod
    def _finalise(self):
        raise NotImplementedError


class StackEmitter(Emitter):
    """A header stack deparse emitter."""

    def _reset(self):
        self._packet_out = []

    def _emit(self, header_name):
        self._packet_out.append(self._packet[header_name])

    def _finalise(self):
        packet_out = self._packet.unparsed if self._packet.unparsed is not None else HeaderStack()
        while self._packet_out:
            packet_out.push(self._packet_out.pop())
        self._packet_out = packet_out


class BinaryEmitter(Emitter):
    """A binary deparse emitter."""

    def _reset(self):
        self._packet_out = bytearray()

    def _emit(self, header_name):
        self._packet_out.extend(self._packet[header_name].to_bytes())

    def _finalise(self):
        self._packet_out.extend(self._packet.unparsed.get_remaining())
