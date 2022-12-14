"""Package wide definitions for PyP4."""

from enum import auto, Enum


class PacketIO(Enum):
    """Encoding/decoding type for packets."""
    BINARY = auto()
    """Encode/decode packets in binary as `~pyp4.packet.BinaryPacket` objects."""
    STACK = auto()
    """Encode/decode packets as `~pyp4.packet.HeaderStack` objects."""
