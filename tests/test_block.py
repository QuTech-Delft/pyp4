"""Unit test P4 blocks."""

import pytest


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


@pytest.fixture()
def blocks(process):
    return process.blocks


def test_tables(blocks):
    assert "MyIngress.operations" in blocks["ingress"].tables


def test_ingress(blocks, bus):
    bus.packet.add_header("act")

    bus.packet["act"]["action_id"].val = 0
    blocks["ingress"].process(bus)
    assert bus.packet["test"].valid

    bus.packet["act"]["action_id"].val = 2
    bus.packet["test"]["value"].val = 0x00
    blocks["ingress"].process(bus)
    assert int(bus.packet["test"]["value"]) == 0xaa

    bus.packet["act"]["action_id"].val = 1
    blocks["ingress"].process(bus)
    assert not bus.packet["test"].valid


def test_false_next(blocks, bus):
    blocks["ingress"].process(bus)
    assert "act" not in bus.packet or not bus.packet["act"].valid
