"""Unit test P4 parsers."""

import json
import pytest

from pyp4 import PacketIO
from pyp4.packet import BinaryPacket, HeaderStack


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


@pytest.fixture()
def packet():
    return HeaderStack()


@pytest.fixture()
def parser(process):
    return process.parsers["parser"]


def test_one_state(process, parser, bus, packet):
    header = process.header("act")
    header["action_id"].val = 0
    packet.push(header)

    packet.payload = b"payload"

    parser.process(bus, packet)

    assert ("act" in bus.packet) and bus.packet["act"].valid
    assert ("test" in bus.packet) and not bus.packet["test"].valid
    assert bus.packet.unparsed.payload == b"payload"


def test_unparsed(process, parser, bus, packet):
    header = process.header("test")
    header["value"].val = 0xae
    packet.push(header)

    header = process.header("act")
    header["action_id"].val = 0
    packet.push(header)

    packet.payload = b"payload"

    parser.process(bus, packet)

    assert ("act" in bus.packet) and bus.packet["act"].valid
    assert ("test" in bus.packet) and not bus.packet["test"].valid
    header = bus.packet.unparsed.pop()
    assert "value" in header
    assert header["value"].val == 0xae
    assert bus.packet.unparsed.payload == b"payload"


def test_two_state(process, parser, bus, packet):
    header = process.header("test")
    header["value"].val = 0xae
    packet.push(header)

    header = process.header("act")
    header["action_id"].val = 1
    packet.push(header)

    packet.payload = b"payload"

    parser.process(bus, packet)

    assert ("act" in bus.packet) and bus.packet["act"].valid
    assert ("test" in bus.packet) and (int(bus.packet["test"]["value"]) == 0xae)
    assert bus.packet.unparsed.payload == b"payload"


def test_binary_parser(MockProcess, program):
    # First check it will reject a process with non-byte bitwidths.
    with pytest.raises(ValueError):
        with open("tests/p4/expressions.json") as program_file:
            program_expr = json.load(program_file)
        _ = MockProcess(__name__, program_expr, packet_io=PacketIO.BINARY)

    process = MockProcess(__name__, program, packet_io=PacketIO.BINARY)
    parser = process.parsers["parser"]

    packet = BinaryPacket()
    header = process.header("act")
    header["action_id"].val = 0
    packet.extend(header.to_bytes())

    packet.extend(bytes([0x2c, 0x4d, 0x5e, 0x6f]))

    bus = process.bus()
    parser.process(bus, packet)

    assert ("act" in bus.packet) and bus.packet["act"].valid
    assert ("test" in bus.packet) and not bus.packet["test"].valid
    assert bus.packet.unparsed.get_remaining() == bytes([0x2c, 0x4d, 0x5e, 0x6f])

    packet = BinaryPacket()
    header = process.header("act")
    header["action_id"].val = 1
    packet.extend(header.to_bytes())

    header = process.header("test")
    header["value"].val = 0xae
    packet.extend(header.to_bytes())

    bus = process.bus()
    parser.process(bus, packet)

    assert ("act" in bus.packet) and bus.packet["act"].valid
    assert ("test" in bus.packet) and (int(bus.packet["test"]["value"]) == 0xae)
