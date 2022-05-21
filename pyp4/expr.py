"""Parse and evaluate expressions from BM AST format."""

from collections import namedtuple
from enum import Enum, auto


__ExprDispatch = namedtuple("__ExprDispatch", "function can_be_lval")  # pylint:disable=invalid-name
__OperDispatch = namedtuple("__OperDispatch", "function nr_args")  # pylint:disable=invalid-name


class __ExprContext(Enum):  # pylint:disable=invalid-name
    LVAL = auto()
    RVAL = auto()
    PARAM = auto()


def __evaluate(bus, expr, runtime_data, expr_context=__ExprContext.RVAL):
    if runtime_data is None:
        runtime_data = []
    if "op" in expr:
        dispatch = OPER_DISPATCHES.get(expr["op"])
        __check_nr_args(expr, dispatch.nr_args)
        return dispatch.function(bus, expr, runtime_data)

    assert "type" in expr
    dispatch = EXPR_DISPATCHES.get(expr["type"], __ExprDispatch(__expr_value, False))
    is_lval = (
        True if expr_context == __ExprContext.LVAL else
        False if expr_context == __ExprContext.RVAL else
        dispatch.can_be_lval
    )
    assert dispatch.can_be_lval or not is_lval
    return dispatch.function(bus, expr, runtime_data, is_lval)


def __check_nr_args(expr, nr_args):
    assert nr_args in [1, 2, 3]
    assert expr["right"] is not None
    if nr_args >= 2:
        assert expr["left"] is not None
    else:
        assert expr["left"] is None
    if nr_args >= 3:
        assert expr["cond"] is not None
    else:
        assert ("cond" not in expr) or (expr["cond"] is None)


def lval(bus, expr, runtime_data):
    """Evaluate an lvalue expression in the BM AST format.

    Parameters
    ----------
    bus : `pyp4.packet.Bus`
        The metadata + headers bus.
    expr : dict
        The expression in BM AST format.
    runtime_data : list of `str`
        The runtime data provided during execution.

    Returns
    -------
    `int` or `bool`
        The result of the expression.

    """
    return __evaluate(bus, expr, runtime_data, __ExprContext.LVAL)


def rval(bus, expr, runtime_data):
    """Evaluate an rvalue expression in the BM AST format.

    Parameters
    ----------
    bus : `pyp4.packet.Bus`
        The metadata + headers bus.
    expr : dict
        The expression in BM AST format.
    runtime_data : list of `str`
        The runtime data provided during execution.

    Returns
    -------
    `int` or `bool`
        The result of the expression.

    """
    return __evaluate(bus, expr, runtime_data, __ExprContext.RVAL)


def param(bus, expr, runtime_data):
    """Evaluate a parameter expression in the BM AST format.

    Parameters
    ----------
    bus : `pyp4.packet.Bus`
        The metadata + headers bus.
    expr : dict
        The expression in BM AST format.
    runtime_data : list of `str`
        The runtime data provided during execution.

    Returns
    -------
    `int` or `bool`
        The result of the expression.

    """
    return __evaluate(bus, expr, runtime_data, __ExprContext.PARAM)


def __coerce_to_bool(value):
    # The BMv2 compiler does not apply d2b to all possible bool fields for some reason. However,
    # those fields should still be 0/1. Note that in Python bools are a subtype of int.
    assert value in (0, 1)
    return bool(value)


def __expr_expression(bus, expr, runtime_data, is_lval):
    return __evaluate(bus, expr["value"], runtime_data, is_lval)


def __expr_field(bus, expr, _runtime_data, is_lval):
    (header_instance_name, field_member_name) = expr["value"]
    if is_lval:
        header = bus.get_hdr(header_instance_name)
        return header[field_member_name]
    else:
        if field_member_name == "$valid$":
            return bus.packet.is_valid(header_instance_name)
        else:
            header = bus.get_hdr(header_instance_name)
            return header[field_member_name].val


def __expr_hexstr(_bus, expr, _runtime_data, _is_lval):
    return int(expr["value"], 0)


def __expr_header(bus, expr, _runtime_data, _is_lval):
    value = expr["value"]
    return bus.get_hdr(value)


def __expr_bool(_bus, expr, _runtime_data, _is_lval):
    value = expr["value"]
    value = __coerce_to_bool(value)
    return value


def __expr_string(_bus, expr, _runtime_data, _is_lval):
    value = expr["value"]
    assert isinstance(value, str)
    return value


def __expr_header_stack(_bus, _expr, _runtime_data, _is_lval):
    # TODO
    raise NotImplementedError


def __expr_stack_field(_bus, _expr, _runtime_data, _is_lval):
    # TODO
    raise NotImplementedError


def __expr_runtime_data(_bus, expr, runtime_data, _is_lval):
    index = expr["value"]
    value_str = runtime_data[index]
    value = int(value_str, 16)
    return value


def __expr_parameters_vector(bus, expr, runtime_data, is_lval):
    return tuple(__evaluate(bus, value, runtime_data, is_lval) for value in expr["value"])


def __expr_value(_bus, expr, _runtime_data, _is_lval):
    assert expr["type"] in ["meter_array", "counter_array", "register_array"]
    return expr["value"]


EXPR_DISPATCHES = {
    "expression": __ExprDispatch(__expr_expression, True),
    "field": __ExprDispatch(__expr_field, True),
    "hexstr": __ExprDispatch(__expr_hexstr, False),
    "header": __ExprDispatch(__expr_header, False),
    "bool": __ExprDispatch(__expr_bool, False),
    "string": __ExprDispatch(__expr_string, False),
    "header_stack": __ExprDispatch(__expr_header_stack, False),
    "stack_field": __ExprDispatch(__expr_stack_field, False),
    "runtime_data": __ExprDispatch(__expr_runtime_data, False),
    "local": __ExprDispatch(__expr_runtime_data, False),
    "parameters_vector": __ExprDispatch(__expr_parameters_vector, False),
}


def __oper_add(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value + right_value


def __oper_subtract(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value - right_value


def __oper_multiply(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value * right_value


def __oper_left_shift(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value << right_value


def __oper_right_shift(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value >> right_value


def __oper_is_equal(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value == right_value


def __oper_is_not_equal(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value != right_value


def __oper_is_greater_than(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value > right_value


def __oper_is_greater_than_or_equal(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value >= right_value


def __oper_is_less_than(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value < right_value


def __oper_is_less_than_or_equal(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value <= right_value


def __oper_logical_and(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    left_value = __coerce_to_bool(left_value)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    right_value = __coerce_to_bool(right_value)
    return left_value and right_value


def __oper_logical_or(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    left_value = __coerce_to_bool(left_value)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    right_value = __coerce_to_bool(right_value)
    return left_value or right_value


def __oper_logical_not(bus, expr, runtime_data):  # pragma: no cover
    # The compiler has gotten too clever. It is able to optimise most uses of logical not so it's
    # not easy to write a test to hit this code. Because it used to work, for prevention purposes,
    # and because it's simple it can stay without a test.
    value = __evaluate(bus, expr["right"], runtime_data)
    value = __coerce_to_bool(value)
    return not value


def __oper_bitwise_and(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value & right_value


def __oper_bitwise_or(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value | right_value


def __oper_bitwise_xor(bus, expr, runtime_data):
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value ^ right_value


def __oper_bitwise_not(bus, expr, runtime_data):
    value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(value, int)
    return ~value


def __oper_is_valid(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_is_valid_union(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_data_to_bool(bus, expr, runtime_data):
    value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(value, int)
    return bool(value)


def __oper_bool_to_data(bus, expr, runtime_data):
    value = __evaluate(bus, expr["right"], runtime_data)
    value = __coerce_to_bool(value)
    return int(value)


def __oper_two_comp_mod(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_sat_cast(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_usat_cast(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_ternary(bus, expr, runtime_data):
    cond_value = __evaluate(bus, expr["cond"], runtime_data)
    cond_value = __coerce_to_bool(cond_value)
    left_value = __evaluate(bus, expr["left"], runtime_data)
    assert isinstance(left_value, int)
    right_value = __evaluate(bus, expr["right"], runtime_data)
    assert isinstance(right_value, int)
    return left_value if cond_value else right_value


def __oper_deref_header_stack(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_last_stack_index(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_size_stack(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_access_field(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_dereference_union_stack(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


def __oper_access_union_header(_bus, _expr, _runtime_data):
    # TODO
    raise NotImplementedError


OPER_DISPATCHES = {
    "+": __OperDispatch(__oper_add, 2),
    "-": __OperDispatch(__oper_subtract, 2),
    "*": __OperDispatch(__oper_multiply, 2),
    "<<": __OperDispatch(__oper_left_shift, 2),
    ">>": __OperDispatch(__oper_right_shift, 2),
    "==": __OperDispatch(__oper_is_equal, 2),
    "!=": __OperDispatch(__oper_is_not_equal, 2),
    ">": __OperDispatch(__oper_is_greater_than, 2),
    ">=": __OperDispatch(__oper_is_greater_than_or_equal, 2),
    "<": __OperDispatch(__oper_is_less_than, 2),
    "<=": __OperDispatch(__oper_is_less_than_or_equal, 2),
    "and": __OperDispatch(__oper_logical_and, 2),
    "or": __OperDispatch(__oper_logical_or, 2),
    "not": __OperDispatch(__oper_logical_not, 1),
    "&": __OperDispatch(__oper_bitwise_and, 2),
    "|": __OperDispatch(__oper_bitwise_or, 2),
    "^": __OperDispatch(__oper_bitwise_xor, 2),
    "~": __OperDispatch(__oper_bitwise_not, 1),
    "valid": __OperDispatch(__oper_is_valid, 1),
    "valid_union": __OperDispatch(__oper_is_valid_union, 1),
    "d2b": __OperDispatch(__oper_data_to_bool, 1),
    "b2d": __OperDispatch(__oper_bool_to_data, 1),
    "two_comp_mod": __OperDispatch(__oper_two_comp_mod, 2),
    "sat_cast": __OperDispatch(__oper_sat_cast, 1),
    "usat_cast": __OperDispatch(__oper_usat_cast, 1),
    "?": __OperDispatch(__oper_ternary, 3),
    # TODO: check nr args in all of the following
    "dereference_header_stack": __OperDispatch(__oper_deref_header_stack, 1),
    "last_stack_index": __OperDispatch(__oper_last_stack_index, 1),
    "size_stack": __OperDispatch(__oper_size_stack, 1),
    "access_field": __OperDispatch(__oper_access_field, 1),
    "dereference_union_stack": __OperDispatch(__oper_dereference_union_stack, 1),
    "access_union_header": __OperDispatch(__oper_access_union_header, 1),
}
