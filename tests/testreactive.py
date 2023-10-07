import math
import operator
import os
import unittest

try:
    import numpy as np
except ImportError:
    if os.getenv('PARAM_TEST_NUMPY','0') == '1':
        raise ImportError("PARAM_TEST_NUMPY=1 but numpy not available.")
    else:
        raise unittest.SkipTest("numpy not available")

try:
    import pandas as pd
except ImportError:
    if os.getenv('PARAM_TEST_PANDAS','0') == '1':
        raise ImportError("PARAM_TEST_PANDAS=1 but pandas not available.")
    else:
        raise unittest.SkipTest("pandas not available")

import param
import pytest

from param.reactive import bind, rx

NUMERIC_BINARY_OPERATORS = (
    operator.add, divmod, operator.floordiv, operator.mod, operator.mul,
    operator.pow, operator.sub, operator.truediv,
)
LOGIC_BINARY_OPERATORS = (
    operator.and_, operator.or_, operator.xor
)

NUMERIC_UNARY_OPERATORS = (
    abs, math.ceil, math.floor, math.trunc, operator.neg, operator.pos, round
)

COMPARISON_OPERATORS = (
    operator.eq, operator.ge, operator.gt, operator.le, operator.lt, operator.ne,
)

LOGIC_UNARY_OPERATORS = (operator.inv,)

NUMPY_UFUNCS = (np.min, np.max)

@pytest.fixture(scope='module')
def series():
    return pd.Series(np.arange(5.0), name='A')

@pytest.fixture(scope='module')
def df():
    return pd._testing.makeMixedDataFrame()

class Parameters(param.Parameterized):

    string = param.String(default="string")

    integer = param.Integer(default=7)

    number = param.Number(default=3.14)

    function = param.Callable()

    boolean = param.Boolean(default=False)

    event = param.Event()

    @param.depends('integer')
    def multiply_integer(self):
        return self.integer * 2

@pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
def test_reactive_numeric_binary_ops(op):
    assert op(rx(1), 2).rx.value == op(1, 2)
    assert op(rx(2), 2).rx.value == op(2, 2)

@pytest.mark.parametrize('op', COMPARISON_OPERATORS)
def test_reactive_numeric_comparison_ops(op):
    assert op(rx(1), 2).rx.value == op(1, 2)
    assert op(rx(2), 1).rx.value == op(2, 1)

@pytest.mark.parametrize('op', NUMERIC_UNARY_OPERATORS)
def test_reactive_numeric_unary_ops(op):
    assert op(rx(1)).rx.value == op(1)
    assert op(rx(-1)).rx.value == op(-1)
    assert op(rx(3.142)).rx.value == op(3.142)

@pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
def test_reactive_numeric_binary_ops_reverse(op):
    assert op(2, rx(1)).rx.value == op(2, 1)
    assert op(2, rx(2)).rx.value == op(2, 2)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops(op):
    assert op(rx(True), True).rx.value == op(True, True)
    assert op(rx(True), False).rx.value == op(True, False)
    assert op(rx(False), True).rx.value == op(False, True)
    assert op(rx(False), False).rx.value == op(False, False)

@pytest.mark.parametrize('op', LOGIC_UNARY_OPERATORS)
def test_reactive_logic_unary_ops(op):
    assert op(rx(True)).rx.value == op(True)
    assert op(rx(False)).rx.value == op(False)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops_reverse(op):
    assert op(True, rx(True)).rx.value == op(True, True)
    assert op(True, rx(False)).rx.value == op(True, False)
    assert op(False, rx(True)).rx.value == op(False, True)
    assert op(False, rx(False)).rx.value == op(False, False)

def test_reactive_getitem_dict():
    assert rx({'A': 1})['A'].rx.value == 1
    assert rx({'A': 1, 'B': 2})['B'].rx.value == 2

def test_reactive_getitem_list():
    assert rx([1, 2, 3])[1].rx.value == 2
    assert rx([1, 2, 3])[2].rx.value == 3

@pytest.mark.parametrize('ufunc', NUMPY_UFUNCS)
def test_numpy_ufunc(ufunc):
    l = [1, 2, 3]
    assert ufunc(rx(l)).rx.value == ufunc(l)
    array = np.ndarray([1, 2, 3])
    assert ufunc(rx(array)).rx.value == ufunc(array)

def test_reactive_set_new_value():
    i = rx(1)
    assert i.rx.value == 1
    i.rx.value = 2
    assert i.rx.value == 2

def test_reactive_increment_value():
    i = rx(1)
    assert i.rx.value == 1
    i.rx.value += 2
    assert i.rx.value == 3

def test_reactive_multiply_value_inplace():
    i = rx(3)
    assert i.rx.value == 3
    i.rx.value *= 2
    assert i.rx.value == 6

def test_reactive_pipeline_set_new_value():
    i = rx(1)
    j = i + 2
    assert j.rx.value == 3
    i.rx.value = 2
    assert j.rx.value == 4

def test_reactive_reflect_param_value():
    P = Parameters(integer=1)
    i = rx(P.param.integer)
    assert i.rx.value == 1
    P.integer = 2
    assert i.rx.value == 2

def test_reactive_pipeline_reflect_param_value():
    P = Parameters(integer=1)
    i = rx(P.param.integer) + 2
    assert i.rx.value == 3
    P.integer = 2
    assert i.rx.value == 4

def test_reactive_reactive_reflect_other_rx():
    i = rx(1)
    j = rx(i)
    assert j.rx.value == 1
    i.rx.value = 2
    assert j.rx.value == 2

def test_reactive_pipeline_reflect_other_reactive_expr():
    i = rx(1)
    j = i + 2
    k = rx(j)
    assert k.rx.value == 3
    i.rx.value = 2
    assert k.rx.value == 4

def test_reactive_reflect_bound_method():
    P = Parameters(integer=1)
    i = rx(P.multiply_integer)
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 4

def test_reactive_pipeline_reflect_bound_method():
    P = Parameters(integer=1)
    i = rx(P.multiply_integer) + 2
    assert i.rx.value == 4
    P.integer = 2
    assert i.rx.value == 6

def test_reactive_reflect_bound_function():
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer))
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 4

def test_reactive_pipeline_reflect_bound_function():
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer)) + 2
    assert i.rx.value == 4
    P.integer = 2
    assert i.rx.value == 6

def test_reactive_dataframe_method_chain(dataframe):
    dfi = rx(dataframe).groupby('str')[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())

def test_reactive_dataframe_attribute_chain(dataframe):
    array = rx(dataframe).str.values.rx.value
    np.testing.assert_array_equal(array, dataframe.str.values)

def test_reactive_dataframe_param_value_method_chain(dataframe):
    P = Parameters(string='str')
    dfi = rx(dataframe).groupby(P.param.string)[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())
    P.string = 'int'
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('int')[['float']].mean().reset_index())

def test_reactive_len():
    i = rx([1, 2, 3])
    l = i.rx.len()
    assert l.rx.value == 3
    i.rx.value = [1, 2]
    assert l == 2

def test_reactive_bool():
    i = rx(1)
    b = i.rx.bool()
    assert b.rx.value is True
    i.rx.value = 0
    assert b.rx.value is False

def test_reactive_iter():
    i = rx(('a', 'b'))
    a, b = i
    assert a.rx.value == 'a'
    assert b.rx.value == 'b'
    i.rx.value = ('b', 'a')
    assert a.rx.value == 'b'
    assert b.rx.value == 'a'

def test_reactive_multi_iter():
    i = rx(('a', 'b'))
    a1, b1 = i
    a2, b2 = i
    assert a1.rx.value == 'a'
    assert b1.rx.value == 'b'
    assert a2.rx.value == 'a'
    assert b2.rx.value == 'b'
    i.rx.value = ('b', 'a')
    assert a1.rx.value == 'b'
    assert b1.rx.value == 'a'
    assert a2.rx.value == 'b'
    assert b2.rx.value == 'a'

def test_reactive_is():
    i = rx(None)
    is_ = i.rx.is_(None)
    assert is_.rx.value
    i.rx.value = False
    assert not is_.rx.value

def test_reactive_in():
    i = rx(2)
    in_ = i.rx.in_([1, 2, 3])
    assert in_.rx.value
    i.rx.value = 4
    assert not in_.rx.value

def test_reactive_is_not():
    i = rx(None)
    is_ = i.rx.is_not(None)
    assert not is_.rx.value
    i.rx.value = False
    assert is_.rx.value

def test_reactive_where_expr():
    p = Parameters()
    r = p.param.boolean.rx.where('A', 'B')
    assert r.rx.value == 'B'
    p.boolean = True
    assert r.rx.value == 'A'

def test_reactive_where_expr_refs():
    p = Parameters()
    results = []
    r = p.param.boolean.rx.where(p.param.string, p.param.number)
    r.rx.watch(results.append)
    assert r.rx.value == 3.14
    p.boolean = True
    assert results == ['string']
    p.string = 'foo'
    assert results == ['string', 'foo']
    p.number = 2.1
    assert results == ['string', 'foo']
    p.boolean = False
    assert results == ['string', 'foo', 2.1]

def test_reactive_watch_on_set_input():
    string = rx('string')
    new_string = string + '!'
    items = []
    new_string.rx.watch(items.append)
    string.rx.value = 'new string'
    assert items == ['new string!']

def test_reactive_set_value_non_root_raises():
    rx_val = rx(1) + 1
    with pytest.raises(AttributeError):
        rx_val.rx.value = 3

def test_reactive_clone_evaluates_once():
    namex = rx('bob')

    items = []
    def debug(value):
        items.append(value)
        return value

    assert namex.rx.pipe(debug).title().rx.value == 'Bob'
    assert len(items) == 1
