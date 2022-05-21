"""Package wide definitions for PyP4."""

from enum import auto, Enum


class PacketIO(Enum):
    """Encoding/decoding type for packets."""
    BINARY = auto()
    STACK = auto()
