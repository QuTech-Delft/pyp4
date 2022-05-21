"""Unit test P4 actions."""

import pytest


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/basic.json"


def test_add_header(actions, bus):
    actions["MyIngress.act_add_header"].process(bus, [])
    assert bus.packet["test"].valid


def test_remove_header(actions, bus):
    bus.packet.add_header("test")
    actions["MyIngress.act_remove_header"].process(bus, [])
    assert not bus.packet["test"].valid


def test_assign(actions, bus):
    bus.packet.add_header("test")
    bus.packet["test"]["value"].val = 0x00
    actions["MyIngress.act_assign"].process(bus, [])
    assert bus.packet["test"].valid
    assert int(bus.packet["test"]["value"]) == 0xaa


def test_extern(v1model_actions, bus):
    bus.metadata["standard_metadata"]["egress_spec"].val = 0x01
    v1model_actions["MyIngress.act_extern"].process(bus, [])
    assert bus.metadata["standard_metadata"]["egress_spec"].is_max_val()


def test_extern_keyword(v1model_actions, bus):
    bus.packet.add_header("test")
    bus.packet["test"]["value"].val = 0x00
    with pytest.raises(AssertionError):
        v1model_actions["MyIngress.act_extern_keyword"].process(bus, [])

    bus.packet["test"]["value"].val = 0xaa
    v1model_actions["MyIngress.act_extern_keyword"].process(bus, [])
    assert int(bus.packet["test"]["value"]) == 0xbb
