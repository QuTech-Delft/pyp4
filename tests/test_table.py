"""Unit tests for P4 tables."""

import pytest

from pyp4.table import Conditional, Table
from pyp4.processor import Processor


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/complex.json"


@pytest.fixture(scope="module")
def conditionals(program):
    # Process does not provide direct access to the conditionals so we read them ourselves.
    return {
        cond["name"]: Conditional(__name__, cond)
        for cond in program["pipelines"][0]["conditionals"]
    }


@pytest.fixture()
def tables(process):
    yield process.blocks["ingress"].tables
    for tab in process.blocks["ingress"].tables.values():
        tab.reset()


@pytest.fixture()
def ethernet_fib(tables):
    return tables["ProcessIngress.ethernet_fib"]


@pytest.fixture()
def ethernet_ethertype_fib(tables):
    return tables["ProcessIngress.ethernet_ethertype_fib"]


@pytest.fixture()
def ethernet_ipv4_fib(tables):
    return tables["ProcessIngress.process_ingress_ipv4.ethernet_ipv4_fib"]


@pytest.fixture()
def ipv4_fib(tables):
    return tables["ProcessIngress.process_ingress_ipv4.ipv4_fib"]


@pytest.fixture()
def ttl_tbl(tables):
    return tables["ProcessIngress.process_ingress_ipv4.ttl_tbl"]


def test_processor_access(process, ethernet_fib, ipv4_fib):
    # Derive a mock class as Processor is abstract.
    class MockProcessor(Processor):
        def input(self, *args, **kwargs):
            raise AssertionError
    processor = MockProcessor(None).load(process)
    assert ethernet_fib is processor.table("ingress", "ProcessIngress.ethernet_fib")
    assert ipv4_fib is processor.table("ingress", "ProcessIngress.process_ingress_ipv4.ipv4_fib")
    with pytest.raises(ValueError):
        processor.table("not-ingress", "ProcessIngress.ethernet_fib")
    with pytest.raises(ValueError):
        processor.table("ingress", "ProcessIngress.made_up_fib")


def test_conditionals(conditionals, bus):
    bus.packet.add_header("ethernet")
    assert conditionals["node_2"].apply(bus) == "ProcessIngress.ethernet_fib"
    assert conditionals["node_6"].apply(bus) is None

    bus.packet.add_header("ipv4")
    assert conditionals["node_6"].apply(bus) == \
        "ProcessIngress.process_ingress_ipv4.ethernet_ipv4_fib"

    bus.get_hdr("scalars")["goto_ipv4_0"].val = 0
    assert conditionals["node_5"].apply(bus) == "tbl_complex174"

    bus.get_hdr("scalars")["goto_ipv4_0"].val = 1
    assert conditionals["node_5"].apply(bus) == "node_6"


def test_next_table(ethernet_fib, ipv4_fib):
    assert ethernet_fib.next_table(
        Table.ApplyResult(hit=True,
                          action_run=Table.ActionRun(
                              action_id=0,
                              action_name="ProcessIngress.act_hit",
                              action_data=[],
                          ))
    ) == "node_5"
    assert ethernet_fib.next_table(
        Table.ApplyResult(hit=False,
                          action_run=Table.ActionRun(
                              action_id=0,
                              action_name="ProcessIngress.act_miss",
                              action_data=[],
                          ))
    ) == "ProcessIngress.ethernet_ethertype_fib"
    assert ipv4_fib.next_table(
        Table.ApplyResult(hit=True,
                          action_run=Table.ActionRun(
                              action_id=0,
                              action_name="ProcessIngress.process_ingress_ipv4.act_hit",
                              action_data=[],
                          ))
    ) == "ProcessIngress.process_ingress_ipv4.ttl_tbl"
    assert ipv4_fib.next_table(
        Table.ApplyResult(hit=False,
                          action_run=Table.ActionRun(
                              action_id=0,
                              action_name="NoAction",
                              action_data=[],
                          ))
    ) == "tbl_process_ingress_ipv4_act_miss"


def test_exact_miss(ethernet_fib, bus):
    ethernet_fib.insert_entry(
        key=0x554433221100,
        action_name="ProcessIngress.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ethernet")
    bus.packet["ethernet"]["dst_addr"].val = 0x001122334455

    apply_result = ethernet_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_miss"


def test_exact_hit(ethernet_fib, bus):
    ethernet_fib.insert_entry(
        key=0x001122334455,
        action_name="ProcessIngress.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ethernet")
    bus.packet["ethernet"]["dst_addr"].val = 0x001122334455

    apply_result = ethernet_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_hit"


def test_remove_entry(ethernet_fib, bus):
    entry_handle = ethernet_fib.insert_entry(
        key=0x001122334455,
        action_name="ProcessIngress.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ethernet")
    bus.packet["ethernet"]["dst_addr"].val = 0x001122334455

    ethernet_fib.remove_entry(entry_handle + 100)

    apply_result = ethernet_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_hit"

    ethernet_fib.remove_entry(entry_handle)

    apply_result = ethernet_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_miss"


def test_remove_const_entry(ipv4_fib, bus):
    # Insert an entry. Const entries will have handles less than this. This is valid for the current
    # implementation, but there is no other way to learn these values as they are intentionally not
    # exposed to the outside world.
    first_handle = ipv4_fib.insert_entry(
        key=(0x0b010200, 24),
        action_name="ProcessIngress.process_ingress_ipv4.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ipv4")
    bus.packet["ipv4"]["dst_addr"].val = 0x0a01ffff

    for handle in range(first_handle):
        ipv4_fib.remove_entry(handle)

    apply_result = ipv4_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.process_ingress_ipv4.act_hit"


def test_lpm_miss(ipv4_fib, bus):
    ipv4_fib.insert_entry(
        key=(0x0b010200, 24),
        action_name="ProcessIngress.process_ingress_ipv4.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ipv4")
    bus.packet["ipv4"]["dst_addr"].val = 0x0b010303

    apply_result = ipv4_fib.apply(bus)
    assert apply_result.action_run.action_name == "NoAction"


def test_lpm_hit(ipv4_fib, bus):
    ipv4_fib.insert_entry(
        key=(0x0b010200, 24),
        action_name="ProcessIngress.process_ingress_ipv4.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ipv4")
    bus.packet["ipv4"]["dst_addr"].val = 0x0b0102ff

    apply_result = ipv4_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.process_ingress_ipv4.act_hit"


def test_invalid_lpm_key(ipv4_fib):
    with pytest.raises(ValueError):
        ipv4_fib.insert_entry(
            key=0x0a010200,
            action_name="ProcessIngress.process_ingress_ipv4.act_hit",
            action_data=[0xae],
        )

    with pytest.raises(ValueError):
        ipv4_fib.insert_entry(
            key=(0x0a010200, 24, 3),
            action_name="ProcessIngress.process_ingress_ipv4.act_hit",
            action_data=[0xae],
        )


def test_range_miss(ttl_tbl, bus):
    ttl_tbl.insert_entry(
        key=(10, 20),
        action_name="ProcessIngress.process_ingress_ipv4.act_miss",
        action_data=[],
    )

    bus.packet.add_header("ipv4")
    bus.packet["ipv4"]["ttl"].val = 5

    apply_result = ttl_tbl.apply(bus)
    assert apply_result.action_run.action_name == "NoAction"


def test_range_hit(ttl_tbl, bus):
    ttl_tbl.insert_entry(
        key=(10, 20),
        action_name="ProcessIngress.process_ingress_ipv4.act_miss",
        action_data=[],
    )

    for ttl_val in [10, 15, 20]:
        bus.packet.add_header("ipv4")
        bus.packet["ipv4"]["ttl"].val = ttl_val

        apply_result = ttl_tbl.apply(bus)
        assert apply_result.action_run.action_name == "ProcessIngress.process_ingress_ipv4.act_miss"


def test_invalid_range_key(ttl_tbl):
    with pytest.raises(ValueError):
        ttl_tbl.insert_entry(
            key=10,
            action_name="ProcessIngress.process_ingress_ipv4.act_miss",
            action_data=[],
        )

    with pytest.raises(ValueError):
        ttl_tbl.insert_entry(
            key=(10, 20, 30),
            action_name="ProcessIngress.process_ingress_ipv4.act_miss",
            action_data=[],
        )


def test_length_two_key(ethernet_ethertype_fib, bus):
    ethernet_ethertype_fib.insert_entry(
        key=[0x001122334455, 0x800],
        action_name="ProcessIngress.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ethernet")
    bus.packet["ethernet"]["dst_addr"].val = 0x001122334455
    bus.packet["ethernet"]["ethertype"].val = 0x000

    apply_result = ethernet_ethertype_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_miss"

    bus.packet["ethernet"]["ethertype"].val = 0x800

    apply_result = ethernet_ethertype_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.act_hit"


def test_mixed_key(ethernet_ipv4_fib, bus):
    ethernet_ipv4_fib.insert_entry(
        key=[0x001122334455, (0x0a010200, 24)],
        action_name="ProcessIngress.process_ingress_ipv4.act_hit",
        action_data=[0xae],
    )

    bus.packet.add_header("ethernet")
    bus.packet.add_header("ipv4")
    bus.packet["ethernet"]["dst_addr"].val = 0x001122334455
    bus.packet["ipv4"]["dst_addr"].val = 0x0b010203

    apply_result = ethernet_ipv4_fib.apply(bus)
    assert apply_result.action_run.action_name == "NoAction"

    bus.packet["ipv4"]["dst_addr"].val = 0x0a010203

    apply_result = ethernet_ipv4_fib.apply(bus)
    assert apply_result.action_run.action_name == "ProcessIngress.process_ingress_ipv4.act_hit"


def test_incorrect_length_key(ethernet_fib, ethernet_ethertype_fib):
    with pytest.raises(ValueError):
        ethernet_fib.insert_entry(
            key=[0x001122334455, 0x800],
            action_name="ProcessIngress.act_hit",
            action_data=[0xae],
        )

    with pytest.raises(ValueError):
        ethernet_ethertype_fib.insert_entry(
            key=0x001122334455,
            action_name="ProcessIngress.act_hit",
            action_data=[0xae],
        )

    with pytest.raises(ValueError):
        ethernet_ethertype_fib.insert_entry(
            key=[0x001122334455, 0x800, 0x801],
            action_name="ProcessIngress.act_hit",
            action_data=[0xae],
        )
