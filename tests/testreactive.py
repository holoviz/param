import math
import operator

import numpy as np
import pandas as pd
import param
import pytest

from param.depends import bind
from param.reactive import reactive

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

    @param.depends('integer')
    def multiply_integer(self):
        return self.integer * 2

@pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
def test_reactive_numeric_binary_ops(op):
    assert op(reactive(1), 2).eval() == op(1, 2)
    assert op(reactive(2), 2).eval() == op(2, 2)

@pytest.mark.parametrize('op', COMPARISON_OPERATORS)
def test_reactive_numeric_comparison_ops(op):
    assert op(reactive(1), 2).eval() == op(1, 2)
    assert op(reactive(2), 1).eval() == op(2, 1)

@pytest.mark.parametrize('op', NUMERIC_UNARY_OPERATORS)
def test_reactive_numeric_unary_ops(op):
    assert op(reactive(1)).eval() == op(1)
    assert op(reactive(-1)).eval() == op(-1)
    assert op(reactive(3.142)).eval() == op(3.142)

@pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
def test_reactive_numeric_binary_ops_reverse(op):
    assert op(2, reactive(1)).eval() == op(2, 1)
    assert op(2, reactive(2)).eval() == op(2, 2)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops(op):
    assert op(reactive(True), True).eval() == op(True, True)
    assert op(reactive(True), False).eval() == op(True, False)
    assert op(reactive(False), True).eval() == op(False, True)
    assert op(reactive(False), False).eval() == op(False, False)

@pytest.mark.parametrize('op', LOGIC_UNARY_OPERATORS)
def test_reactive_logic_unary_ops(op):
    assert op(reactive(True)).eval() == op(True)
    assert op(reactive(False)).eval() == op(False)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops_reverse(op):
    assert op(True, reactive(True)).eval() == op(True, True)
    assert op(True, reactive(False)).eval() == op(True, False)
    assert op(False, reactive(True)).eval() == op(False, True)
    assert op(False, reactive(False)).eval() == op(False, False)

def test_reactive_getitem_dict():
    assert reactive({'A': 1})['A'].eval() == 1
    assert reactive({'A': 1, 'B': 2})['B'].eval() == 2

def test_reactive_getitem_list():
    assert reactive([1, 2, 3])[1].eval() == 2
    assert reactive([1, 2, 3])[2].eval() == 3

@pytest.mark.parametrize('ufunc', NUMPY_UFUNCS)
def test_numpy_ufunc(ufunc):
    l = [1, 2, 3]
    assert ufunc(reactive(l)).eval() == ufunc(l)
    array = np.ndarray([1, 2, 3])
    assert ufunc(reactive(array)).eval() == ufunc(array)

def test_reactive_set_new_value():
    i = reactive(1)
    assert i.eval() == 1
    i.set(2)
    assert i.eval() == 2

def test_reactive_pipeline_set_new_value():
    i = reactive(1) + 2
    assert i.eval() == 3
    i.set(2)
    assert i.eval() == 4

def test_reactive_reactivelect_param_value():
    P = Parameters(integer=1)
    i = reactive(P.param.integer)
    assert i.eval() == 1
    P.integer = 2
    assert i.eval() == 2

def test_reactive_pipeline_reactivelect_param_value():
    P = Parameters(integer=1)
    i = reactive(P.param.integer) + 2
    assert i.eval() == 3
    P.integer = 2
    assert i.eval() == 4

def test_reactive_reactivelect_other_reactive():
    i = reactive(1)
    j = reactive(i)
    assert j.eval() == 1
    i.set(2)
    assert j.eval() == 2

def test_reactive_pipeline_reactivelect_other_reactive():
    i = reactive(1) + 2
    j = reactive(i)
    assert j.eval() == 3
    i.set(2)
    assert i.eval() == 4

def test_reactive_reactivelect_bound_method():
    P = Parameters(integer=1)
    i = reactive(P.multiply_integer)
    assert i.eval() == 2
    P.integer = 2
    assert i.eval() == 4

def test_reactive_pipeline_reactivelect_bound_method():
    P = Parameters(integer=1)
    i = reactive(P.multiply_integer) + 2
    assert i.eval() == 4
    P.integer = 2
    assert i.eval() == 6

def test_reactive_reactivelect_bound_function():
    P = Parameters(integer=1)
    i = reactive(bind(lambda v: v * 2, P.param.integer))
    assert i.eval() == 2
    P.integer = 2
    assert i.eval() == 4

def test_reactive_pipeline_reactivelect_bound_function():
    P = Parameters(integer=1)
    i = reactive(bind(lambda v: v * 2, P.param.integer)) + 2
    assert i.eval() == 4
    P.integer = 2
    assert i.eval() == 6

def test_reactive_dataframe_method_chain(dataframe):
    dfi = reactive(dataframe).groupby('str')[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.eval(), dataframe.groupby('str')[['float']].mean().reset_index())

def test_reactive_dataframe_attribute_chain(dataframe):
    array = reactive(dataframe).str.values.eval()
    np.testing.assert_array_equal(array, dataframe.str.values)

def test_reactive_dataframe_param_value_method_chain(dataframe):
    P = Parameters(string='str')
    dfi = reactive(dataframe).groupby(P.param.string)[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.eval(), dataframe.groupby('str')[['float']].mean().reset_index())
    P.string = 'int'
    pd.testing.assert_frame_equal(dfi.eval(), dataframe.groupby('int')[['float']].mean().reset_index())

def test_reactive_len():
    i = reactive([1, 2, 3])
    l = i.len()
    assert l.eval() == 3
    i.set([1, 2])
    assert l == 2

def test_reactive_bool():
    i = reactive(1)
    b = i.bool_()
    assert b.eval() is True
    i.set(0)
    assert b.eval() is False

def test_reactive_iter():
    i = reactive(('a', 'b'))
    a, b = i
    assert a.eval() == 'a'
    assert b.eval() == 'b'
    i.set(('b', 'a'))
    assert a.eval() == 'b'
    assert b.eval() == 'a'

def test_reactive_is():
    i = reactive(None)
    is_ = i.is_(None)
    assert is_.eval()
    i.set(False)
    assert not is_.eval()
