"""Unit tests for P4 expression evaluation."""

import pytest


@pytest.fixture(scope="module")
def program_file_name():
    return "tests/p4/expressions.json"


def check_operator(bus, action, in32a=None, in32b=None, in8=None, in1=None, out32=None, out1=None,
                   runtime_data=None):
    bus.packet.add_header("expr")
    header = bus.packet["expr"]

    # op-code encoding is in tests/p4/expression.p4 table operations
    header["in32a"].val = in32a or 0
    header["in32b"].val = in32b or 0
    header["in8"].val = in8 or 0
    header["in1"].val = in1 or 0
    header["out32"].val = 0
    header["out1"].val = 0
    header["padding"].val = 0

    action.process(bus, runtime_data)

    assert (out32 is None) or (int(header["out32"]) == out32)
    assert (out1 is None) or (int(header["out1"]) == out1)


def test_extern(v1model_actions, bus):
    bus.metadata["standard_metadata"]["egress_spec"].val = 1
    check_operator(bus, v1model_actions["MyIngress.act_drop"])
    assert bus.metadata["standard_metadata"]["egress_spec"].is_max_val()


def test_add(actions, bus):
    # 789 + 456 = 1245
    check_operator(bus, actions["MyIngress.act_add"], in32a=789, in32b=456, out32=1245)


def test_subtract(actions, bus):
    # 789 - 456 = 333
    check_operator(bus, actions["MyIngress.act_subtract"], in32a=789, in32b=456, out32=333)


def test_multiply(actions, bus):
    # 762 * 976 = 743712
    check_operator(bus, actions["MyIngress.act_multiply"], in32a=762, in32b=976, out32=743712)


def test_left_shift(actions, bus):
    # 0b101 << 3 = 0b101000
    check_operator(bus, actions["MyIngress.act_left_shift"], in32a=0b101, in8=3, out32=0b101000)


def test_right_shift(actions, bus):
    # 0b101011 >> 3 = 0b101
    check_operator(bus, actions["MyIngress.act_right_shift"], in32a=0b101011, in8=3, out32=0b101)


def test_is_equal(actions, bus):
    # 123 == 123: true
    check_operator(bus, actions["MyIngress.act_is_equal"], in32a=123, in32b=123, out1=1)
    # 123 == 456: false
    check_operator(bus, actions["MyIngress.act_is_equal"], in32a=123, in32b=456, out1=0)


def test_is_not_equal(actions, bus):
    # 123 != 123: false
    check_operator(bus, actions["MyIngress.act_is_not_equal"], in32a=123, in32b=123, out1=0)
    # 123 != 456: true
    check_operator(bus, actions["MyIngress.act_is_not_equal"], in32a=123, in32b=456, out1=1)


def test_is_greater_than(actions, bus):
    # 88888 > 77777: true
    check_operator(bus, actions["MyIngress.act_is_greater_than"], in32a=88888, in32b=77777, out1=1)
    # 88888 > 88888: false
    check_operator(bus, actions["MyIngress.act_is_greater_than"], in32a=88888, in32b=88888, out1=0)
    # 88888 > 99999: false
    check_operator(bus, actions["MyIngress.act_is_greater_than"], in32a=88888, in32b=99999, out1=0)


def test_is_greater_than_or_equal(actions, bus):
    # 88888 >= 77777: true
    check_operator(
        bus, actions["MyIngress.act_is_greater_than_or_equal"], in32a=88888, in32b=77777, out1=1
    )
    # 88888 >= 88888: true
    check_operator(
        bus, actions["MyIngress.act_is_greater_than_or_equal"], in32a=88888, in32b=88888, out1=1
    )
    # 88888 >= 99999: false
    check_operator(
        bus, actions["MyIngress.act_is_greater_than_or_equal"], in32a=88888, in32b=99999, out1=0
    )


def test_is_less_than(actions, bus):
    # 88888 < 77777: false
    check_operator(bus, actions["MyIngress.act_is_less_than"], in32a=88888, in32b=77777, out1=0)
    # 88888 < 88888: false
    check_operator(bus, actions["MyIngress.act_is_less_than"], in32a=88888, in32b=88888, out1=0)
    # 88888 < 99999: true
    check_operator(bus, actions["MyIngress.act_is_less_than"], in32a=88888, in32b=99999, out1=1)


def test_is_less_than_or_equal(actions, bus):
    # 88888 <= 77777: false
    check_operator(
        bus, actions["MyIngress.act_is_less_than_or_equal"], in32a=88888, in32b=77777, out1=0
    )
    # 88888 <= 88888: true
    check_operator(
        bus, actions["MyIngress.act_is_less_than_or_equal"], in32a=88888, in32b=88888, out1=1
    )
    # 88888 <= 99999: true
    check_operator(
        bus, actions["MyIngress.act_is_less_than_or_equal"], in32a=88888, in32b=99999, out1=1
    )


def test_logical_and(actions, bus):
    # Note: in32a<10: true, in32b>=10: false, ditto for in32b
    # false and false: false
    check_operator(bus, actions["MyIngress.act_logical_and"], in32a=11, in32b=11, out1=0)
    # false and true: false
    check_operator(bus, actions["MyIngress.act_logical_and"], in32a=11, in32b=1, out1=0)
    # true and false: false
    check_operator(bus, actions["MyIngress.act_logical_and"], in32a=1, in32b=11, out1=0)
    # true and true: true
    check_operator(bus, actions["MyIngress.act_logical_and"], in32a=1, in32b=1, out1=1)


def test_logical_or(actions, bus):
    # Note: in32a<10: true, in32b>=10: false, ditto for in32b
    # false or false: false
    check_operator(bus, actions["MyIngress.act_logical_or"], in32a=11, in32b=11, out1=0)
    # false or true: true
    check_operator(bus, actions["MyIngress.act_logical_or"], in32a=11, in32b=1, out1=1)
    # true or false: true
    check_operator(bus, actions["MyIngress.act_logical_or"], in32a=1, in32b=11, out1=1)
    # true or true: true
    check_operator(bus, actions["MyIngress.act_logical_or"], in32a=1, in32b=1, out1=1)


def test_logical_not(actions, bus):
    # Note: in32a<10: true, in32b>=10: false
    # not false: true
    check_operator(bus, actions["MyIngress.act_logical_not"], in32a=11, out1=1)
    # not true: false
    check_operator(bus, actions["MyIngress.act_logical_not"], in32a=1, out1=0)


def test_bitwise_and(actions, bus):
    # 110 & 011: 010
    check_operator(bus, actions["MyIngress.act_bitwise_and"], in32a=0b110, in32b=0b011, out32=0b010)


def test_bitwise_or(actions, bus):
    # 110 | 011: 111
    check_operator(bus, actions["MyIngress.act_bitwise_or"], in32a=0b110, in32b=0b011, out32=0b111)


def test_bitwise_xor(actions, bus):
    # 110 ^ 011: 101
    check_operator(bus, actions["MyIngress.act_bitwise_xor"], in32a=0b110, in32b=0b011, out32=0b101)


def test_bitwise_not(actions, bus):
    # ~ 110: 011
    check_operator(
        bus,
        actions["MyIngress.act_bitwise_not"],
        in32a=0b00000000000000000000000000000110,
        out32=0b11111111111111111111111111111001,
    )


def test_is_valid(actions, bus):
    # TODO: operator 19
    pass


def test_is_valid_union(actions, bus):
    # TODO: operator 20
    pass


def test_data_to_bool(actions, bus):
    # Out1 is set to true if the header is valid (i.e. always)
    check_operator(bus, actions["MyIngress.act_data_to_bool"], out1=1)


def test_bool_to_data(actions, bus):
    # false -> 0
    check_operator(bus, actions["MyIngress.act_bool_to_data"], in1=0, out1=0)
    # true -> 1
    check_operator(bus, actions["MyIngress.act_bool_to_data"], in1=1, out1=1)


def test_bool(actions, bus):
    # this test is here to just hit an artificial expression with a raw boolean - it always
    # evaluates to true and returns 1 in out1.
    check_operator(bus, actions["MyIngress.act_bool"], in1=0, out1=1)
    check_operator(bus, actions["MyIngress.act_bool"], in1=1, out1=1)


def test_two_comp_mod(actions, bus):
    # TODO: operator 24
    pass


def test_sat_cast(actions, bus):
    # TODO: operator 25
    pass


def test_usat_cast(actions, bus):
    # TODO: operator 26
    pass


def test_ternary(actions, bus):
    # TODO: operator 27
    pass


def test_deref_header_stack(actions, bus):
    # TODO: operator 28
    pass


def test_last_stack_index(actions, bus):
    # TODO: operator 29
    pass


def test_size_stack(actions, bus):
    # TODO: operator 30
    pass


def test_access_field(actions, bus):
    # TODO: operator 31
    pass


def test_dereference_union_stack(actions, bus):
    # TODO: operator 32
    pass


def test_access_union_header(actions, bus):
    # TODO: operator 33
    pass


def test_runtime_data(actions, bus):
    check_operator(bus, actions["MyIngress.act_runtime_data"], out32=0xae, runtime_data=["0xae"])


def test_value(v1model_actions, bus):
    check_operator(bus, v1model_actions["MyIngress.act_value"], out32=0xbe)


def test_log_msg(v1model_actions, bus, capfd):
    # This test hits the "string" and "parameters_vector" expression types. Currently, I only know
    # how to trigger these through log_msg so need to check stdout.
    in1 = 1
    in8 = 9
    check_operator(bus, v1model_actions["MyIngress.act_log_msg"], in1=in1, in8=in8)
    out, _ = capfd.readouterr()
    assert out == f"Hello, world! in1=0x{in1:X}; in8=0x{in8:X};\n"
