"""Unit test PyP4 packet representations."""

import pytest

from pyp4.packet import BinaryPacket, Bus, FixedInt, Header, Packet, HeaderStack


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


@pytest.fixture(scope="module")
def header_defs(program):
    return {hdr["name"]: hdr for hdr in program["headers"]}


@pytest.fixture(scope="module")
def header_types(program):
    return {hdr_t["name"]: hdr_t for hdr_t in program["header_types"]}


def test_fixed_int():
    fixed_int = FixedInt(0xae, 32)
    assert fixed_int.val == 0xae
    assert int(fixed_int) == 0xae
    assert fixed_int.bitwidth == 32
    assert fixed_int == FixedInt(0xae, 32)
    assert fixed_int != FixedInt(0xbf, 32)
    assert fixed_int != FixedInt(0xae, 64)
    assert isinstance(repr(fixed_int), str) and (int(repr(fixed_int), 0) == 0xae)
    assert fixed_int.to_bytes() == bytes([0x00, 0x00, 0x00, 0xae])
    fixed_int.from_bytes(bytes([0x00, 0xae, 0x00, 0xfe]))
    assert fixed_int.val == 0xae00fe


def test_header():
    header = Header([["field_1", 32, False], ["field_2", 64, False], ["field_3", 32, False]])
    assert header.valid
    assert len(header) == 3

    assert "field_1" in header
    header["field_1"].val = 1
    assert header["field_1"].val == 1
    assert header["field_1"].bitwidth == 32

    assert "field_2" in header
    header["field_2"].val = 2
    assert header["field_2"].val == 2
    assert header["field_2"].bitwidth == 64

    assert "field_3" in header
    header["field_3"].val = 3
    assert header["field_3"].val == 3
    assert header["field_3"].bitwidth == 32

    header.set_invalid()
    assert not header.valid

    header.set_valid()
    assert header.valid

    assert isinstance(repr(header), str)

    assert header.bytelen == 16
    assert header.to_bytes() == bytes(
        [0x00, 0x00, 0x00, 0x01] +
        [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02] +
        [0x00, 0x00, 0x00, 0x03]
    )
    header.from_bytes(bytes(
        [0x00, 0xaa, 0x00, 0x01] +
        [0x00, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02] +
        [0x00, 0xcc, 0x00, 0x03]
    ))
    assert header["field_1"].val == 0xaa0001
    assert header["field_1"].bitwidth == 32
    assert header["field_2"].val == 0xbb000000000002
    assert header["field_2"].bitwidth == 64
    assert header["field_3"].val == 0xcc0003
    assert header["field_3"].bitwidth == 32


def test_header_stack():
    header = Header([("field", 128, False)])
    header["field"].val = 0xae

    header_stack = HeaderStack()
    assert len(header_stack) == 0

    header_stack.payload = b"payload"

    header_stack.push(header)
    assert len(header_stack) == 1

    assert isinstance(repr(header_stack), str)

    header = header_stack.pop()
    assert len(header_stack) == 0
    assert "field" in header
    assert header["field"].val == 0xae

    assert header_stack.payload == b"payload"


def test_binary_packet():
    binary_packet = BinaryPacket()

    header_1 = Header([("field_1", 128, False), ("field_2", 64, False)])
    header_1["field_1"].val = 0xae
    header_1["field_2"].val = 0xea
    binary_packet.extend(header_1.to_bytes())

    header_2 = Header([("field_3", 64, False), ("field_4", 128, False)])
    header_2["field_3"].val = 0xaa00ae
    header_2["field_4"].val = 0xaa00ea
    binary_packet.extend(header_2.to_bytes())

    binary_packet.extend(bytes([0x2c, 0x3d, 0x4e, 0x5f]))

    header_1.from_bytes(binary_packet.get_next(header_1.bytelen))
    assert "field_1" in header_1
    assert "field_2" in header_1
    assert header_1["field_1"].val == 0xae
    assert header_1["field_2"].val == 0xea

    header_2.from_bytes(binary_packet.get_next(header_2.bytelen))
    assert "field_3" in header_2
    assert "field_4" in header_2
    assert header_2["field_3"].val == 0xaa00ae
    assert header_2["field_4"].val == 0xaa00ea

    assert binary_packet.get_remaining() == bytes([0x2c, 0x3d, 0x4e, 0x5f])

    with pytest.raises(ValueError):
        binary_packet.get_next(1)

    binary_packet.reset()
    header_1.from_bytes(binary_packet.get_next(header_1.bytelen))
    assert "field_1" in header_1
    assert "field_2" in header_1
    assert header_1["field_1"].val == 0xae
    assert header_1["field_2"].val == 0xea


def test_packet(header_types, header_defs):
    packet = Packet(header_types, header_defs, b"payload")

    assert not packet.is_valid("act")
    assert not packet.is_valid("test")
    assert packet.unparsed == b"payload"

    packet.unparsed = b"payload2"

    packet.add_header("act")
    assert "act" in packet
    assert packet.is_valid("act")

    packet["act"].set_invalid()
    assert not packet.is_valid("act")

    packet.add_header("act")
    assert packet.is_valid("act")

    packet["test"] = Header(header_types[header_defs["test"]["header_type"]]["fields"])
    assert "test" in packet
    assert packet.is_valid("test")

    assert isinstance(repr(packet), str)

    packet.clear()

    assert "act" not in packet
    assert "test" not in packet
    assert packet.unparsed == b"payload2"

    assert not packet.is_valid("act")
    assert not packet.is_valid("test")


def test_bus(process, header_types, header_defs):
    packet = Packet(header_types, header_defs)
    packet.add_header("act")
    packet["act"]["action_id"].val = 0xab

    bus = Bus(process.metadata(), packet)

    assert bus.get_hdr("standard_metadata") is not None
    assert bus.metadata["standard_metadata"] is bus.get_hdr("standard_metadata")
    assert bus.get_hdr("scalars") is not None
    assert bus.get_hdr("act") == bus.packet["act"]
    assert bus.get_hdr("act")["action_id"].val == 0xab
    assert isinstance(repr(bus), str)

    bus_clone = bus.clone()
    bus_clone.packet["act"]["action_id"].val = 0xbf

    assert bus.get_hdr("act")["action_id"].val == 0xab
