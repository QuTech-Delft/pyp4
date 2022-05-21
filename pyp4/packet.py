"""Structures representing packets."""

from copy import deepcopy
from functools import reduce


class FixedInt:
    """A fixed-size unsigned integer.

    Parameters
    ----------
    value : `int`
        Initial value.
    bitwidth : `int`
        The fixed bitwidth.

    """

    def __init__(self, value, bitwidth):
        self.__bitwidth = bitwidth
        self.__bytewidth = int((bitwidth + 7) / 8)
        self.__byteint = ((self.__bytewidth * 8) == self.__bitwidth)

        self.__mask = (1 << self.__bitwidth) - 1
        self.__value = None

        self.val = value

    def __repr__(self):
        return f"0x{self.val:X}"

    def __eq__(self, other):
        # pylint:disable=protected-access
        return (
            (self.__bitwidth == other.__bitwidth) and
            (self.__mask == other.__mask) and
            (self.__value == other.__value)
        )

    def __int__(self):
        return self.__value

    @property
    def bitwidth(self):
        """`int`: The bitwidth of the fixed-size integer."""
        return self.__bitwidth

    @property
    def bytewidth(self):
        """`int`: The bytewidth of the fixed-size integer."""
        return self.__bytewidth

    @property
    def byteint(self):
        """`bool`: True if the bitwidth is a multiple of an 8-bit byte."""
        return self.__byteint

    def set_max_val(self):
        """Set the internal value to the maximum possible value."""
        self.__value = self.__mask

    def is_max_val(self):
        """`bool`: True if the value stored is equal to maximum possible value."""
        return self.__value == self.__mask

    @property
    def val(self):
        """`int`: The integer value of the fixed-size integer."""
        return self.__value

    @val.setter
    def val(self, value):
        assert isinstance(value, int)
        assert value == (value & self.__mask)
        self.__value = value

    def from_bytes(self, binary):
        """Set the value to the value provided in the encoded binary.

        Parameters
        ----------
        binary : `bytearray` or `bytes`
            The binary representation of the value.

        """
        assert self.__byteint
        assert len(binary) >= self.__bytewidth
        self.__value = int.from_bytes(binary[:self.__bytewidth], byteorder="big", signed=False)

    def to_bytes(self):
        """Return the value as encoded binary.

        Returns
        -------
        `bytes`
            The binary encoded value.

        """
        assert self.__byteint
        return self.__value.to_bytes(self.__bytewidth, byteorder="big", signed=False)


class Header:
    """A packet header.

    A `pyp4.packet.Header` acts like read-only a dictionary of {field_name -> field_value}. The
    individual fields can be accessed as if `pyp4.packet.Header` was such a dictionary, e.g.
    header["field"]. However, it is not possible to add or remove headers after construction and
    whilst it is possible modify the `pyp4.packet.FixedInt` value, changing its bitwidth is not.

    Parameters
    ----------
    fields : list of 3-tuples of (str, int, bool)
         List of header types defined by the 3-tuple (name, bitwidth, signed).

    """

    def __init__(self, fields):
        self.__fields = {name: FixedInt(0, bitwidth) for name, bitwidth, _ in fields}

        bitlen = reduce(
            lambda width, next_fixed_int: width + next_fixed_int.bitwidth,
            self.__fields.values(),
            0,
        )
        self.__bytelen = int(bitlen / 8)
        self.__byteheader = ((self.__bytelen * 8) == bitlen)

        self.__valid = True

    def __repr__(self):
        return repr({**self.__fields, "valid": self.__valid})

    def __len__(self):
        return len(self.__fields)

    def __contains__(self, name):
        return name in self.__fields

    def __getitem__(self, name):
        return self.__fields[name]

    def as_dict(self):
        """`dict`: The header in dict format."""
        return {name: field.val for name, field in self.__fields.items()}

    @property
    def valid(self):
        """`bool`: True if the header is valid."""
        return self.__valid

    @property
    def bytelen(self):
        """`int`: The length of the header in bytes."""
        assert self.__byteheader
        return self.__bytelen

    def set_valid(self):
        """Set the header to status to valid."""
        self.__valid = True

    def set_invalid(self):
        """Set the header status to invalid."""
        self.__valid = False

    def from_bytes(self, binary):
        """Set the field values to the values decoded from the provided binary.

        Parameters
        ----------
        binary : `bytearray` or `bytes`
            The binary representation of the value.

        """
        start = 0
        end = 0
        for field in self.__fields.values():
            assert field.byteint
            end += int(field.bytewidth)
            field.from_bytes(binary[start:end])
            start = end

    def to_bytes(self):
        """Return the value as encoded binary.

        Returns
        -------
        `bytearray`
            The binary encoded header.

        """
        binary = bytearray()
        for field in self.__fields.values():
            binary += field.to_bytes()
        return binary


class HeaderStack:
    """A packet represented as a payload with a stack of headers.

    Parameters
    ----------
    payload : `Any`, optional
        The packet payload.

    """

    def __init__(self, payload=None):
        self.__stack = []
        self.__payload = payload

    def __repr__(self):
        repr_str = [f"payload: {str(self.__payload)}"]
        for header in self.__stack:
            repr_str.append(str(header))
        repr_str.reverse()
        return "{ " + ", ".join(repr_str) + " }"

    def __len__(self):
        return len(self.__stack)

    @property
    def payload(self):
        """`Any`: The payload."""
        return self.__payload

    @payload.setter
    def payload(self, payload):
        self.__payload = payload

    def push(self, header):
        """Push a header on top of the packet.

        Parameters
        ----------
        header : `pyp4.packet.Header`
            The header to push.

        """
        self.__stack.append(header)

    def pop(self):
        """Pop and return the top header of the packet.

        Returns
        -------
        `pyp4.packet.Header`
            The header that was on top of the packet.

        """
        return self.__stack.pop()


class BinaryPacket:
    """A packet in binary.

    """

    def __init__(self):
        self.__bytes = bytearray()
        self.__ptr = 0

    def extend(self, binary):
        """Extend the packet.

        Parameters
        ----------
        binary : `bytearray` or `bytes`
            The binary to add to the end of the packet.
        """
        self.__bytes += binary

    def reset(self):
        """Reset the internal packet pointer."""
        self.__ptr = 0

    def get_next(self, bytewidth):
        """Get the next bytes of the packet from the start of the internal pointer.

        This moves the internal packet pointer the same number of bytes.

        Parameters
        ----------
        bytewidth : `int`
            The number of bytes to extract.

        """
        start = self.__ptr
        end = self.__ptr + bytewidth
        if end > len(self.__bytes):
            raise ValueError
        self.__ptr = end
        return self.__bytes[start:end]

    def get_remaining(self):
        """Get the remaining bytes of the packet from the start of the internal pointer.

        This moves the internal packet pointer to the end of the packet.

        """
        return self.get_next(len(self.__bytes) - self.__ptr)


class Packet:
    """An internal representation of a packet.

    This is an internal representation of a packet. It will check for correct packet structure based
    on the running P4 program. It is also unordered and stores headers by name (as defined in P4
    program) rather than the order they were placed on the original packet.

    Parameters
    ----------
    header_types : dict
        Dictionary of header types keyed on the header type name.
    header_defs : dict
        Dictionary of header definitions ("headers" in BM JSON) keyed on the header name.
    payload : `Any`, optional
        The packet payload.

    """

    def __init__(self, header_types, header_defs, unparsed=None):
        self.__header_types = header_types
        self.__header_defs = header_defs

        self.__headers = {}
        self.__unparsed = unparsed

        for name in header_defs:
            self.add_header(name)
            self.__headers[name].set_invalid()

    def __repr__(self):
        return repr({**self.__headers, "unparsed": repr(self.__unparsed)})

    def __contains__(self, name):
        return name in self.__headers

    def __getitem__(self, name):
        return self.__headers[name]

    def __setitem__(self, name, header):
        # Header must be one defined in BM JSON.
        assert name in self.__header_defs

        # Find header type and field list to verify provided header.
        header_type = self.__header_defs[name]["header_type"]
        header_fields = self.__header_types[header_type]["fields"]

        # We will copy the entire header to ensure the PyP4 internals do not have to worry about
        # whether they're dealing with a copy or reference.
        header_copy = Header(header_fields)

        # Check that the provided header matches the definition from BM.
        assert len(header) == len(header_fields)
        for field in header_fields:
            field_name = field[0]
            field_bitwidth = field[1]

            field_value = header[field_name]
            mask = (1 << field_bitwidth) - 1

            # We verify both, that the value is indeed legal and that the FixedInt struct agrees as
            # to the number of bits.
            assert (field_value.val & mask) == field_value.val
            assert field_value.bitwidth == field_bitwidth

            # And create a copy
            header_copy[field_name].val = field_value.val
            assert header_copy[field_name].bitwidth == field_value.bitwidth

        self.__headers[name] = header_copy

    @property
    def unparsed(self):
        """`<process specific PacketClass>`: The unparsed part of the input packet."""
        return self.__unparsed

    @unparsed.setter
    def unparsed(self, unparsed):
        self.__unparsed = unparsed

    def add_header(self, name):
        """Add a zero-initialised, pre-defined header to the packet based on its name.

        The header definition is taken from the BM JSON configuration.

        Parameters
        ----------
        name : `str`
            The name of the header

        """
        # Header must be one defined in BM JSON.
        assert name in self.__header_defs

        # If the header is already in the packet, just set it to valid
        if name in self.__headers:
            self.__headers[name].set_valid()
            return

        # Find header type and field list to verify provided header.
        header_type = self.__header_defs[name]["header_type"]
        header_fields = self.__header_types[header_type]["fields"]

        # Create a zero header
        self.__headers[name] = Header(header_fields)

    def is_valid(self, name):
        """Check if particular header is valid.

        Parameters
        ----------
        name : `str`
            The name of the header to check.

        Returns
        -------
        `bool`
            Whether the header has its valid flag set.

        """
        hdr = self.__headers.get(name)
        return hdr.valid if hdr is not None else False

    def clear(self):
        """Clear the packet of all headers."""
        self.__headers.clear()


class Bus:
    """The metadata + headers bus.

    Parameters
    ----------
    metadata : `dict` of {`str` -> `pyp4.packet.Header`}
        Architecture defined metadata mapped by name.
    packet : `pyp4.packet.Packet`
        The internal packet representation.

    """

    def __init__(self, metadata, packet):
        self.__metadata = metadata
        self.__packet = packet

    def __repr__(self):
        """Create a string representation of  Bus."""
        return repr({**self.__metadata, "packet": self.__packet})

    def clone(self):
        """`pyp4.packet.Bus`: A clone of the bus."""
        return deepcopy(self)

    @property
    def metadata(self):
        """`dict`: Dictionary of all the metadata blocks."""
        return self.__metadata

    @property
    def packet(self):
        """`pyp4.packet.Packet`: The packet itself."""
        return self.__packet

    def get_hdr(self, name):
        """Get a metadata/header.

        Parameters
        ----------
        name : `str`
            The name of the metadata/header.

        Returns
        -------
        `pyp4.packet.Header`
            The metadata/header.

        """
        hdr = self.__metadata.get(name)
        return hdr if hdr is not None else self.__packet[name]
