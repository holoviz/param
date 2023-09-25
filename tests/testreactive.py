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
    assert op(rx(1), 2).rx.resolve() == op(1, 2)
    assert op(rx(2), 2).rx.resolve() == op(2, 2)

@pytest.mark.parametrize('op', COMPARISON_OPERATORS)
def test_reactive_numeric_comparison_ops(op):
    assert op(rx(1), 2).rx.resolve() == op(1, 2)
    assert op(rx(2), 1).rx.resolve() == op(2, 1)

@pytest.mark.parametrize('op', NUMERIC_UNARY_OPERATORS)
def test_reactive_numeric_unary_ops(op):
    assert op(rx(1)).rx.resolve() == op(1)
    assert op(rx(-1)).rx.resolve() == op(-1)
    assert op(rx(3.142)).rx.resolve() == op(3.142)

@pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
def test_reactive_numeric_binary_ops_reverse(op):
    assert op(2, rx(1)).rx.resolve() == op(2, 1)
    assert op(2, rx(2)).rx.resolve() == op(2, 2)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops(op):
    assert op(rx(True), True).rx.resolve() == op(True, True)
    assert op(rx(True), False).rx.resolve() == op(True, False)
    assert op(rx(False), True).rx.resolve() == op(False, True)
    assert op(rx(False), False).rx.resolve() == op(False, False)

@pytest.mark.parametrize('op', LOGIC_UNARY_OPERATORS)
def test_reactive_logic_unary_ops(op):
    assert op(rx(True)).rx.resolve() == op(True)
    assert op(rx(False)).rx.resolve() == op(False)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops_reverse(op):
    assert op(True, rx(True)).rx.resolve() == op(True, True)
    assert op(True, rx(False)).rx.resolve() == op(True, False)
    assert op(False, rx(True)).rx.resolve() == op(False, True)
    assert op(False, rx(False)).rx.resolve() == op(False, False)

def test_reactive_getitem_dict():
    assert rx({'A': 1})['A'].rx.resolve() == 1
    assert rx({'A': 1, 'B': 2})['B'].rx.resolve() == 2

def test_reactive_getitem_list():
    assert rx([1, 2, 3])[1].rx.resolve() == 2
    assert rx([1, 2, 3])[2].rx.resolve() == 3

@pytest.mark.parametrize('ufunc', NUMPY_UFUNCS)
def test_numpy_ufunc(ufunc):
    l = [1, 2, 3]
    assert ufunc(rx(l)).rx.resolve() == ufunc(l)
    array = np.ndarray([1, 2, 3])
    assert ufunc(rx(array)).rx.resolve() == ufunc(array)

def test_reactive_set_new_value():
    i = rx(1)
    assert i.rx.resolve() == 1
    i.rx.set_input(2)
    assert i.rx.resolve() == 2

def test_reactive_pipeline_set_new_value():
    i = rx(1) + 2
    assert i.rx.resolve() == 3
    i.rx.set_input(2)
    assert i.rx.resolve() == 4

def test_reactive_reflect_param_value():
    P = Parameters(integer=1)
    i = rx(P.param.integer)
    assert i.rx.resolve() == 1
    P.integer = 2
    assert i.rx.resolve() == 2

def test_reactive_pipeline_reflect_param_value():
    P = Parameters(integer=1)
    i = rx(P.param.integer) + 2
    assert i.rx.resolve() == 3
    P.integer = 2
    assert i.rx.resolve() == 4

def test_reactive_reactive_reflect_other_rx():
    i = rx(1)
    j = rx(i)
    assert j.rx.resolve() == 1
    i.rx.set_input(2)
    assert j.rx.resolve() == 2

def test_reactive_pipeline_reflect_other_reactive_expr():
    i = rx(1) + 2
    j = rx(i)
    assert j.rx.resolve() == 3
    i.rx.set_input(2)
    assert i.rx.resolve() == 4

def test_reactive_reflect_bound_method():
    P = Parameters(integer=1)
    i = rx(P.multiply_integer)
    assert i.rx.resolve() == 2
    P.integer = 2
    assert i.rx.resolve() == 4

def test_reactive_pipeline_reflect_bound_method():
    P = Parameters(integer=1)
    i = rx(P.multiply_integer) + 2
    assert i.rx.resolve() == 4
    P.integer = 2
    assert i.rx.resolve() == 6

def test_reactive_reflect_bound_function():
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer))
    assert i.rx.resolve() == 2
    P.integer = 2
    assert i.rx.resolve() == 4

def test_reactive_pipeline_reflect_bound_function():
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer)) + 2
    assert i.rx.resolve() == 4
    P.integer = 2
    assert i.rx.resolve() == 6

def test_reactive_dataframe_method_chain(dataframe):
    dfi = rx(dataframe).groupby('str')[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.resolve(), dataframe.groupby('str')[['float']].mean().reset_index())

def test_reactive_dataframe_attribute_chain(dataframe):
    array = rx(dataframe).str.values.rx.resolve()
    np.testing.assert_array_equal(array, dataframe.str.values)

def test_reactive_dataframe_param_value_method_chain(dataframe):
    P = Parameters(string='str')
    dfi = rx(dataframe).groupby(P.param.string)[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.resolve(), dataframe.groupby('str')[['float']].mean().reset_index())
    P.string = 'int'
    pd.testing.assert_frame_equal(dfi.rx.resolve(), dataframe.groupby('int')[['float']].mean().reset_index())

def test_reactive_len():
    i = rx([1, 2, 3])
    l = i.rx.len()
    assert l.rx.resolve() == 3
    i.rx.set_input([1, 2])
    assert l == 2

def test_reactive_bool():
    i = rx(1)
    b = i.rx.bool()
    assert b.rx.resolve() is True
    i.rx.set_input(0)
    assert b.rx.resolve() is False

def test_reactive_iter():
    i = rx(('a', 'b'))
    a, b = i
    assert a.rx.resolve() == 'a'
    assert b.rx.resolve() == 'b'
    i.rx.set_input(('b', 'a'))
    assert a.rx.resolve() == 'b'
    assert b.rx.resolve() == 'a'

def test_reactive_multi_iter():
    i = rx(('a', 'b'))
    a1, b1 = i
    a2, b2 = i
    assert a1.rx.resolve() == 'a'
    assert b1.rx.resolve() == 'b'
    assert a2.rx.resolve() == 'a'
    assert b2.rx.resolve() == 'b'
    i.rx.set_input(('b', 'a'))
    assert a1.rx.resolve() == 'b'
    assert b1.rx.resolve() == 'a'
    assert a2.rx.resolve() == 'b'
    assert b2.rx.resolve() == 'a'

def test_reactive_is():
    i = rx(None)
    is_ = i.rx.is_(None)
    assert is_.rx.resolve()
    i.rx.set_input(False)
    assert not is_.rx.resolve()

def test_reactive_in():
    i = rx(2)
    in_ = i.rx.in_([1, 2, 3])
    assert in_.rx.resolve()
    i.rx.set_input(4)
    assert not in_.rx.resolve()

def test_reactive_is_not():
    i = rx(None)
    is_ = i.rx.is_not(None)
    assert not is_.rx.resolve()
    i.rx.set_input(False)
    assert is_.rx.resolve()

def test_reactive_where_expr():
    p = Parameters()
    r = p.param.boolean.rx.where('A', 'B')
    assert r.rx.resolve() == 'B'
    p.boolean = True
    assert r.rx.resolve() == 'A'

def test_reactive_where_expr_refs():
    p = Parameters()
    results = []
    r = p.param.boolean.rx.where(p.param.string, p.param.number)
    r.rx.watch(results.append)
    assert r.rx.resolve() == 3.14
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
    string.rx.set_input('new string')
    assert items == ['new string!']
