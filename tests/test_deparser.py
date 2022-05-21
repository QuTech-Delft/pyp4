"""Unit test P4 deparsers."""

import pytest

from pyp4 import PacketIO
from pyp4.packet import BinaryPacket, FixedInt, HeaderStack


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


@pytest.fixture()
def deparser(process):
    return process.deparsers["deparser"]


def test_valid(deparser, bus):
    bus.packet.add_header("act")
    bus.packet.add_header("test")

    bus.packet["act"]["action_id"].val = 2
    bus.packet["test"]["value"].val = 0xaa

    bus.packet.unparsed = HeaderStack(b"payload")

    header_stack = deparser.process(bus.packet)
    assert len(header_stack) == 2
    assert header_stack.payload == b"payload"

    hdr = header_stack.pop()
    hdr["action_id"] == FixedInt(2, 32)

    hdr = header_stack.pop()
    hdr["value"] == FixedInt(0xaa, 8)

    assert len(header_stack) == 0


def test_invalid(deparser, bus):
    bus.packet.add_header("act")
    bus.packet.add_header("test")

    bus.packet["act"]["action_id"].val = 2
    bus.packet["test"]["value"].val = 0xaa

    bus.packet["act"].set_invalid()

    bus.packet.unparsed = HeaderStack(b"payload")

    header_stack = deparser.process(bus.packet)
    assert len(header_stack) == 1
    assert header_stack.payload == b"payload"

    hdr = header_stack.pop()
    hdr["value"] == FixedInt(0xaa, 8)

    assert len(header_stack) == 0


def test_unparsed(deparser, bus, process):
    bus.packet.add_header("act")
    bus.packet["act"]["action_id"].val = 2

    hdr = process.header("test")
    hdr["value"].val = 0xaa
    bus.packet.unparsed = HeaderStack(b"payload")
    bus.packet.unparsed.push(hdr)

    header_stack = deparser.process(bus.packet)
    assert len(header_stack) == 2
    assert header_stack.payload == b"payload"

    hdr = header_stack.pop()
    hdr["action_id"] == FixedInt(2, 32)
    assert len(header_stack) == 1

    hdr = header_stack.pop()
    hdr["value"] == FixedInt(0xaa, 8)
    assert len(header_stack) == 0


def test_missing(deparser, bus):
    bus.packet.add_header("act")
    bus.packet["act"]["action_id"].val = 2
    bus.packet.unparsed = HeaderStack()

    header_stack = deparser.process(bus.packet)
    assert len(header_stack) == 1

    hdr = header_stack.pop()
    hdr["action_id"] == FixedInt(2, 32)

    assert len(header_stack) == 0


def test_binary_deparser(MockProcess, program):
    process = MockProcess(__name__, program, packet_io=PacketIO.BINARY)
    deparser = process.deparsers["deparser"]
    bus = process.bus()

    bus.packet.add_header("act")
    bus.packet.add_header("test")

    payload_packet = BinaryPacket()
    payload_packet.extend(bytes([0x0a, 0x1b, 0x2c, 0x4d, 0x5e, 0x6f]))
    _ = payload_packet.get_next(2)
    bus.packet.unparsed = payload_packet

    bus.packet["act"]["action_id"].val = 2
    bus.packet["test"]["value"].val = 0xaa

    binary_packet = deparser.process(bus.packet)

    assert binary_packet[:bus.packet["act"].bytelen] == bus.packet["act"].to_bytes()
    assert binary_packet[
        bus.packet["act"].bytelen:(bus.packet["act"].bytelen + bus.packet["test"].bytelen)
    ] == bus.packet["test"].to_bytes()
    assert binary_packet[
        (bus.packet["act"].bytelen + bus.packet["test"].bytelen):
    ] == bytes([0x2c, 0x4d, 0x5e, 0x6f])
