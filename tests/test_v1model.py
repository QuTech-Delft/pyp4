"""Unit tests for V1Model processor features."""

import pytest

from pyp4.packet import HeaderStack
from pyp4.processors.v1model import V1ModelPortMeta

from tests.mock_device import MockV1ModelDevice


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/v1model.json"


@pytest.fixture()
def device(program):
    return MockV1ModelDevice(program)


def test_registers(process, device):
    header = process.header("ping")
    header["count"].val = 100
    ping = HeaderStack()
    ping.push(header)

    (_, ping), = device.processor.input(device.port_in_meta(0), ping)
    header = ping.pop()
    assert header["count"].val == 1

    ping.push(header)
    for _ in range(5):
        (_, ping), = device.processor.input(device.port_in_meta(0), ping)

    header = ping.pop()
    assert header["count"].val == 6


def test_ingress_tables(process, device):
    device.processor.table("ingress", "MyIngress.tbl_ping").insert_entry(
        key=100,
        action_name="MyIngress.drop",
        action_data=[],
    )

    header = process.header("ping")
    header["count"].val = 100
    ping = HeaderStack()
    ping.push(header)

    assert not device.processor.input(device.port_in_meta(0), ping)


def test_assert(process, device):
    header = process.header("ping")
    header["count"].val = 2001
    ping = HeaderStack()
    ping.push(header)

    with pytest.raises(AssertionError):
        device.processor.input(device.port_in_meta(0), ping)


def test_assume(process, device):
    ping = HeaderStack()

    with pytest.raises(AssertionError):
        device.processor.input(device.port_in_meta(0), ping)


def test_log_msg(process, device, capfd):
    header = process.header("ping")
    header["count"].val = 126
    ping = HeaderStack()
    ping.push(header)

    device.processor.input(device.port_in_meta(0), ping)
    out, _ = capfd.readouterr()
    assert out == "hdr.ping.count = 0x7E\n"


def test_egress_tables(process, device):
    device.processor.table("ingress", "MyIngress.tbl_ping").insert_entry(
        key=100,
        action_name="MyIngress.drop",
        action_data=[],
    )

    device.processor.table("egress", "MyEgress.tbl_ping").insert_entry(
        key=1,
        action_name="MyEgress.drop",
        action_data=[],
    )

    header = process.header("ping")
    header["count"].val = 0
    ping = HeaderStack()
    ping.push(header)

    # First ping will miss both tables
    (_, ping), = device.processor.input(device.port_in_meta(0), ping)
    header = ping.pop()
    assert header["count"].val == 1

    # The count is now 1, it will hit the egress table entry
    ping.push(header)
    assert not device.processor.input(device.port_in_meta(0), ping)


def test_missing_metadata(process, device):
    with pytest.raises(ValueError):
        device.processor.input(
            V1ModelPortMeta(standard_metadata={"egress_port": 5}),
            HeaderStack(),
        )
