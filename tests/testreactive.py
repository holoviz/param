import asyncio
import gc
import math
import operator
import re
import time
import weakref

import param
import pytest

from param.parameterized import Skip
from param.reactive import bind, rx
from typing import Any, Callable

from .utils import async_wait_until

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

NUMPY_UFUNCS = ("min", "max")

@pytest.fixture(scope='module')
def series():
    np = pytest.importorskip("numpy")
    pd = pytest.importorskip("pandas")
    return pd.Series(np.arange(5.0), name='A')

@pytest.fixture(scope='module')
def df():
    pd = pytest.importorskip("pandas")
    return pd._testing.makeMixedDataFrame()

class Parameters(param.Parameterized):

    string = param.String(default="string")

    integer = param.Integer(default=7)

    number = param.Number(default=3.14)

    function = param.Callable()

    boolean = param.Boolean(default=False)

    parameter = param.Parameter(allow_refs=False)

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
    assert op(rx(1)).rx.value == op(1)
    assert op(rx(0)).rx.value == op(0)

@pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
def test_reactive_logic_binary_ops_reverse(op):
    assert op(True, rx(True)).rx.value == op(True, True)
    assert op(True, rx(False)).rx.value == op(True, False)
    assert op(False, rx(True)).rx.value == op(False, True)
    assert op(False, rx(False)).rx.value == op(False, False)

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_getitem_dict(lazy):
    assert rx({'A': 1}, lazy=lazy)['A'].rx.value == 1
    assert rx({'A': 1, 'B': 2}, lazy=lazy)['B'].rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_getitem_list(lazy):
    assert rx([1, 2, 3], lazy=lazy)[1].rx.value == 2
    assert rx([1, 2, 3], lazy=lazy)[2].rx.value == 3

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_getitem_list_with_slice(lazy):
    i = rx(1, lazy=lazy)
    j = rx(5, lazy=lazy)
    lst = list(range(10))
    lstx = rx(lst)
    sx = lstx[i: j]
    assert sx.rx.value == lst[i.rx.value: j.rx.value]
    i.rx.value = 2
    assert sx.rx.value == lst[i.rx.value: j.rx.value]

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_getitem_numpy_with_tuple(lazy):
    np = pytest.importorskip("numpy")
    i = rx(0)
    j = rx(1)
    arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    arrx = rx(arr, lazy=lazy)
    selx = arrx[i, j]
    assert selx.rx.value == arr[i.rx.value, j.rx.value]
    i.rx.value = 1
    assert selx.rx.value == arr[i.rx.value, j.rx.value]

@pytest.mark.parametrize('ufunc', NUMPY_UFUNCS)
def test_numpy_ufunc(ufunc):
    np = pytest.importorskip("numpy")
    ufunc = getattr(np, ufunc)
    l = [1, 2, 3]
    assert ufunc(rx(l)).rx.value == ufunc(l)
    array = np.ndarray([1, 2, 3])
    assert ufunc(rx(array)).rx.value == ufunc(array)

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_empty_construct(lazy):
    i = rx(lazy=lazy)
    assert i.rx.value is None
    i.rx.value = 2
    assert i.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_set_new_value_assignment(lazy):
    i = rx(1, lazy=lazy)
    assert i.rx.value == 1
    i.rx.value = 2
    assert i.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_set_new_value_method(lazy):
    i = rx(1, lazy=lazy)
    assert i.rx.value == 1
    i.rx.set(2)
    assert i.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_increment_value(lazy):
    i = rx(1, lazy=lazy)
    assert i.rx.value == 1
    i.rx.value += 2
    assert i.rx.value == 3

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_multiply_value_inplace(lazy):
    i = rx(3, lazy=lazy)
    assert i.rx.value == 3
    i.rx.value *= 2
    assert i.rx.value == 6

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_pipeline_set_new_value(lazy):
    i = rx(1, lazy=lazy)
    j = i + 2
    assert j.rx.value == 3
    i.rx.value = 2
    assert j.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_reflect_param_value(lazy):
    P = Parameters(integer=1)
    i = rx(P.param.integer, lazy=lazy)
    assert i.rx.value == 1
    P.integer = 2
    assert i.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_skip_value(lazy):
    P = Parameters(integer=1)

    def skip_values(v):
        if v > 2:
            raise Skip()
        else:
            return v+1

    i = rx(P.param.integer, lazy=lazy).rx.pipe(skip_values)
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 3
    P.integer = 3
    assert i.rx.value == 3

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_skip_value_return(lazy):
    P = Parameters(integer=1)

    def skip_values(v):
        if v > 2:
            return Skip
        else:
            return v+1

    i = rx(P.param.integer, lazy=lazy).rx.pipe(skip_values)
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 3
    P.integer = 3
    assert i.rx.value == 3

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_pipeline_reflect_param_value(lazy):
    P = Parameters(integer=1)
    i = rx(P.param.integer, lazy=lazy) + 2
    assert i.rx.value == 3
    P.integer = 2
    assert i.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_reactive_reflect_other_rx(lazy):
    i = rx(1, lazy=lazy)
    j = rx(i, lazy=lazy)
    assert j.rx.value == 1
    i.rx.value = 2
    assert j.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_pipeline_reflect_other_reactive_expr(lazy):
    i = rx(1, lazy=lazy)
    j = i + 2
    k = rx(j, lazy=lazy)
    assert k.rx.value == 3
    i.rx.value = 2
    assert k.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_reflect_bound_method(lazy):
    P = Parameters(integer=1)
    i = rx(P.multiply_integer, lazy=lazy)
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_pipeline_reflect_bound_method(lazy):
    P = Parameters(integer=1)
    i = rx(P.multiply_integer, lazy=lazy) + 2
    assert i.rx.value == 4
    P.integer = 2
    assert i.rx.value == 6

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_reflect_bound_function(lazy):
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer), lazy=lazy)
    assert i.rx.value == 2
    P.integer = 2
    assert i.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_pipeline_reflect_bound_function(lazy):
    P = Parameters(integer=1)
    i = rx(bind(lambda v: v * 2, P.param.integer), lazy=lazy) + 2
    assert i.rx.value == 4
    P.integer = 2
    assert i.rx.value == 6

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_dataframe_method_chain(dataframe, lazy):
    pd = pytest.importorskip("pandas")
    dfi = rx(dataframe, lazy=lazy).groupby('str')[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_dataframe_attribute_chain(dataframe, lazy):
    np = pytest.importorskip("numpy")
    array = rx(dataframe).str.values.rx.value
    np.testing.assert_array_equal(array, dataframe.str.values)

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_dataframe_param_value_method_chain(dataframe, lazy):
    pd = pytest.importorskip("pandas")
    P = Parameters(string='str')
    dfi = rx(dataframe, lazy=lazy).groupby(P.param.string)[['float']].mean().reset_index()
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())
    P.string = 'int'
    pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('int')[['float']].mean().reset_index())

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_len(lazy):
    i = rx([1, 2, 3], lazy=lazy)
    l = i.rx.len()
    assert l.rx.value == 3
    i.rx.value = [1, 2]
    assert l.rx.value == 2

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_bool(lazy):
    i = rx(1, lazy=lazy)
    b = i.rx.bool()
    assert b.rx.value is True
    i.rx.value = 0
    assert b.rx.value is False

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_not_(lazy):
    i = rx(1, lazy=lazy)
    b = i.rx.not_()
    assert b.rx.value is False
    i.rx.value = 0
    assert b.rx.value is True

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_and_(lazy):
    i = rx('', lazy=lazy)
    b = i.rx.and_('foo')
    assert b.rx.value == ''
    i.rx.value = 'bar'
    assert b.rx.value == 'foo'

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_or_(lazy):
    i = rx('', lazy=lazy)
    b = i.rx.or_('')
    assert b.rx.value == ''
    i.rx.value = 'foo'
    assert b.rx.value == 'foo'

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_map(lazy):
    i = rx(range(3), lazy=lazy)
    b = i.rx.map(lambda x: x*2)
    assert b.rx.value == [0, 2, 4]
    i.rx.value = range(1, 4)
    assert b.rx.value == [2, 4, 6]

@pytest.mark.parametrize('lazy', [False, True])
async def test_reactive_async_map(lazy):
    i = rx(range(3), lazy=lazy)
    async def mul(x):
        await asyncio.sleep(0.05)
        return x*2
    b = i.rx.map(mul)
    assert b.rx.value is param.Undefined
    await async_wait_until(lambda: b.rx.value == [0, 2, 4])
    i.rx.value = range(1, 4)
    assert b.rx.value == [0, 2, 4]
    await async_wait_until(lambda: b.rx.value == [2, 4, 6])
    assert b.rx.value == [2, 4, 6]

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_map_args(lazy):
    i = rx(range(3), lazy=lazy)
    j = rx(2, lazy=lazy)
    b = i.rx.map(lambda x, m: x*m, j)
    assert b.rx.value == [0, 2, 4]
    j.rx.value = 3
    assert b.rx.value == [0, 3, 6]

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_iter(lazy):
    i = rx(('a', 'b'), lazy=lazy)
    if lazy: i.rx.value
    a, b = i
    assert a.rx.value == 'a'
    assert b.rx.value == 'b'
    i.rx.value = ('b', 'a')
    assert a.rx.value == 'b'
    assert b.rx.value == 'a'

def test_reactive_iter_lazy_fails():
    i = rx(('a', 'b'), lazy=True)
    with pytest.raises(RuntimeError):
        a, b = i

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_multi_iter(lazy):
    i = rx(('a', 'b'), lazy=lazy)
    if lazy: i.rx.value
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

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_is(lazy):
    i = rx(None, lazy=lazy)
    is_ = i.rx.is_(None)
    assert is_.rx.value
    i.rx.value = False
    assert not is_.rx.value

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_in(lazy):
    i = rx(2, lazy=lazy)
    in_ = i.rx.in_([1, 2, 3])
    assert in_.rx.value
    i.rx.value = 4
    assert not in_.rx.value

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_is_not(lazy):
    i = rx(None, lazy=lazy)
    is_ = i.rx.is_not(None)
    assert not is_.rx.value
    i.rx.value = False
    assert is_.rx.value

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_where_expr(lazy):
    p = Parameters()
    r = rx(p.param.boolean, lazy=lazy).rx.where('A', 'B')
    assert r.rx.value == 'B'
    p.boolean = True
    assert r.rx.value == 'A'

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_where_expr_refs(lazy):
    p = Parameters()
    results = []
    r = rx(p.param.boolean, lazy=lazy).rx.where(p.param.string, p.param.number)
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

@pytest.mark.filterwarnings("ignore::UserWarning")
def test_reactive_watch_lazy_on_set_input():
    string = rx('string', lazy=True)
    new_string = string + '!'
    items = []
    new_string.rx.watch(items.append)
    string.rx.value = 'new string'
    assert items == ['new string!']

async def test_reactive_watch_async_on_event():
    p = Parameters()
    event = rx(p.param.event)
    items = []
    event.rx.watch(items.append)
    p.param.trigger('event')
    await async_wait_until(lambda: items == [True])

@pytest.mark.filterwarnings("ignore::UserWarning")
async def test_reactive_watch_lazy_async_on_event():
    p = Parameters()
    event = rx(p.param.event, lazy=True)
    items = []
    event.rx.watch(items.append)
    p.param.trigger('event')
    await async_wait_until(lambda: items == [True])

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_set_value_non_root_raises(lazy):
    rx_val = rx(1, lazy=lazy) + 1
    with pytest.raises(AttributeError):
        rx_val.rx.value = 3

@pytest.mark.parametrize(('input', 'op', 'expected'), [
    ('bob', lambda _rx: _rx.title(), 'Bob'),
    ('bob', lambda _rx: _rx.rx.map(str.upper), [*'BOB']),
])
def test_reactive_clone_evaluates_once_lazy(input: str, op: Callable[[rx], Any], expected: Any):
    fcalls = 0
    def debug_call_count(value):
        nonlocal fcalls
        fcalls += 1
        return value

    base = rx(input, lazy=True).rx.pipe(debug_call_count)

    assert fcalls == 0
    result = op(base)
    assert fcalls == 0

    assert result.rx.value == expected
    assert fcalls == 1

@pytest.mark.parametrize(('input', 'op', 'expected'), [
    ('bob', lambda _rx: _rx.title(), 'Bob'),
    ('bob', lambda _rx: _rx.rx.map(str.upper), [*'BOB']),
])
def test_reactive_clone_evaluates_once_eager(input: str, op: Callable[[rx], Any], expected: Any):
    fcalls = 0
    def debug_call_count(value):
        nonlocal fcalls
        fcalls += 1
        return value

    base = rx(input, lazy=False).rx.pipe(debug_call_count)

    assert fcalls == 0
    result = op(base)
    assert fcalls == 1

    assert result.rx.value == expected
    assert fcalls == 1


@pytest.mark.parametrize(('inputs', 'op', 'expecteds', 'lazy'), [
    (['alice', 'bob', 'charlie'], lambda _rx: _rx.title(), ['Alice', 'Bob', 'Charlie'], [True, False]),
    (['alice', 'bob', 'charlie'], lambda _rx: _rx.rx.map(str.upper), [[*'ALICE'], [*'BOB'], [*'CHARLIE']], [True, False]),
])
def test_reactive_clone_reevaluates(inputs: list[str], op: Callable[[rx], Any], expecteds: list[Any], lazy: bool):
    fcalls = 0
    def debug_call_count(value):
        nonlocal fcalls
        fcalls += 1
        return value

    base = rx(inputs[0], lazy=lazy)
    transformed = op(base.rx.pipe(debug_call_count))
    assert transformed.rx.value == expecteds[0]
    assert fcalls == 1

    for prev_fcalls, (input, expect) in enumerate(zip(inputs[1:], expecteds[1:]), start=fcalls):
        base.rx.value = input
        assert transformed.rx.value == expect
        assert fcalls == (prev_fcalls + 1)

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_when(lazy):
    p = Parameters(integer=3)
    integer = rx(p.param.integer, lazy=lazy).rx.when(p.param.event)
    assert integer.rx.value == 3
    p.integer = 4
    assert integer.rx.value == 3
    p.param.trigger('event')
    assert integer.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_when_initial(lazy):
    p = Parameters(integer=3)
    integer = rx(p.param.integer, lazy=lazy).rx.when(p.param.event, initial=None)
    assert integer.rx.value is None
    p.integer = 4
    assert integer.rx.value is None
    p.param.trigger('event')
    assert integer.rx.value == 4

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_resolve(lazy):
    p = Parameters(integer=3)
    p2 = Parameters(parameter=p.param.integer)

    prx = rx(p2.param.parameter, lazy=lazy)
    assert prx.rx.value is p.param.integer

    resolved_prx = prx.rx.resolve()
    assert resolved_prx.rx.value == 3

    changes = []
    resolved_prx.rx.watch(changes.append)

    # Test changing referenced value
    p.integer = 4
    assert resolved_prx.rx.value == 4
    assert changes == [4]

    # Test changing reference itself
    p2.parameter = p.param.number
    assert resolved_prx.rx.value == 3.14
    assert changes == [4, 3.14]

    # Ensure no updates triggered when old reference is updated
    p.integer = 5
    assert resolved_prx.rx.value == 3.14
    assert changes == [4, 3.14]

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_resolve_nested(lazy):
    p = Parameters(integer=3)
    p2 = Parameters(parameter=[p.param.integer])

    prx = rx(p2.param.parameter, lazy=lazy)
    assert prx.rx.value == [p.param.integer]

    resolved_prx = prx.rx.resolve(nested=True)
    assert resolved_prx.rx.value == [3]

    changes = []
    resolved_prx.rx.watch(changes.append)

    # Test changing referenced value
    p.integer = 4
    assert resolved_prx.rx.value == [4]
    assert changes == [[4]]

    # Test changing reference itself
    p2.parameter = [p.param.number]
    assert resolved_prx.rx.value == [3.14]
    assert changes == [[4], [3.14]]

    # Ensure no updates triggered when old reference is updated
    p.integer = 5
    assert resolved_prx.rx.value == [3.14]
    assert changes == [[4], [3.14]]

@pytest.mark.parametrize('lazy', [False, True])
def test_reactive_resolve_recursive(lazy):
    p = Parameters(integer=3)
    p2 = Parameters(parameter=p.param.integer)
    p3 = Parameters(parameter=p2.param.parameter)

    prx = rx(p3.param.parameter, lazy=lazy).rx()
    assert prx.rx.value is p2.param.parameter

    resolved_prx = prx.rx.resolve(recursive=True)
    assert resolved_prx.rx.value == 3

    changes = []
    resolved_prx.rx.watch(changes.append)

    # Test changing referenced value
    p.integer = 4
    assert resolved_prx.rx.value == 4
    assert changes == [4]

    # Test changing recursive reference
    p2.parameter = p.param.number
    assert resolved_prx.rx.value == 3.14
    assert changes == [4, 3.14]

    # Ensure no updates triggered when old reference is updated
    p.integer = 5
    assert resolved_prx.rx.value == 3.14
    assert changes == [4, 3.14]

    # Test changing reference itself
    p3.parameter = p.param.string
    assert resolved_prx.rx.value == 'string'
    assert changes == [4, 3.14, 'string']

@pytest.mark.parametrize('lazy', [False, True])
async def test_reactive_async_func(lazy):
    async def async_func():
        await asyncio.sleep(0.02)
        return 2

    async_rx = rx(async_func, lazy=lazy) + 2
    assert async_rx.rx.value is param.Undefined
    await async_wait_until(lambda: async_rx.rx.value == 4)

@pytest.mark.parametrize('lazy', [False, True])
async def test_reactive_pipe_async_func(lazy):
    async def async_func(value):
        await asyncio.sleep(0.02)
        return value+2

    async_rx = rx(0, lazy=lazy).rx.pipe(async_func)
    assert async_rx.rx.value is param.Undefined
    await async_wait_until(lambda: async_rx.rx.value == 2)

async def test_reactive_gen():
    def gen():
        yield 1
        time.sleep(0.05)
        yield 2

    rxgen = rx(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 2)

async def test_reactive_lazy_gen():
    """
    Ensure that while the generator emits the changed value the rx expression
    does not update until the new value is requested.
    """
    def gen():
        yield 1
        time.sleep(0.05)
        yield 2

    rxgen = rx(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await asyncio.sleep(0.1)
    assert rxgen._current_ == 1
    await async_wait_until(lambda: rxgen.rx.value == 2)

async def test_reactive_gen_pipe():
    def gen(val):
        yield val+1
        time.sleep(0.1)
        yield val+2

    rxv = rx(0)
    rxgen = rxv.rx.pipe(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 2)
    rxv.rx.value = 2
    await async_wait_until(lambda: rxgen.rx.value == 3, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 4)

async def test_reactive_lazy_gen_pipe():
    def gen(val):
        yield val+1
        time.sleep(0.05)
        yield val+2

    rxv = rx(0)
    rxgen = rxv.rx.pipe(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await async_wait_until(lambda: rxgen._current_ == 2)
    assert rxgen.rx.value == 2

    rxv.rx.value = 2
    assert rxgen._current_ == 2
    rxgen.rx.value
    await async_wait_until(lambda: rxgen.rx.value == 3, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 4)

async def test_reactive_gen_with_dep():
    def gen(i):
        yield i+1
        time.sleep(0.1)
        yield i+2

    irx = rx(0)
    rxgen = rx(bind(gen, irx))
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    irx.rx.value = 3
    await async_wait_until(lambda: rxgen.rx.value == 4, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 5)

async def test_reactive_gen_pipe_with_dep():
    def gen(value, i):
        yield value+i+1
        time.sleep(0.1)
        yield value+i+2

    irx = rx(0)
    rxv = rx(0)
    rxgen = rxv.rx.pipe(bind(gen, irx))
    rxgen.rx.watch()
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    irx.rx.value = 3
    await async_wait_until(lambda: rxgen.rx.value == 4, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 5)
    rxv.rx.value = 5
    await async_wait_until(lambda: rxgen.rx.value == 9, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 10)

async def test_reactive_async_gen():
    async def gen():
        yield 1
        await asyncio.sleep(0.05)
        yield 2

    rxgen = rx(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 2)

async def test_reactive_lazy_async_gen():
    """
    Ensure that while the generator emits the changed value the rx expression
    does not update until the new value is requested.
    """
    async def gen():
        yield 1
        await asyncio.sleep(0.05)
        yield 2

    rxgen = rx(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await asyncio.sleep(0.1)
    assert rxgen._current_ == 1
    assert rxgen.rx.value == 2

async def test_reactive_async_gen_pipe():
    async def gen(value):
        yield value + 1
        await asyncio.sleep(0.05)
        yield value + 2

    rxgen = rx(0).rx.pipe(gen)
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 2)

async def test_reactive_async_gen_with_dep():
    async def gen(i):
        yield i+1
        await asyncio.sleep(0.1)
        yield i+2

    irx = rx(0)
    rxgen = rx(bind(gen, irx))
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    irx.rx.value = 3
    await asyncio.sleep(0.05)
    irx.rx.value = 4
    await async_wait_until(lambda: rxgen.rx.value == 5, interval=10)

async def test_reactive_async_gen_pipe_with_dep():
    async def gen(value, i):
        yield value+i+1
        await asyncio.sleep(0.05)
        yield value+i+2

    irx = rx(0)
    rxv = rx(0)
    rxgen = rxv.rx.pipe(bind(gen, i=irx))
    rxgen.rx.watch()
    assert rxgen.rx.value is param.Undefined
    await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
    irx.rx.value = 3
    await asyncio.sleep(0.04)
    irx.rx.value = 4
    await async_wait_until(lambda: rxgen.rx.value == 5, interval=10)
    rxv.rx.value = 5
    await async_wait_until(lambda: rxgen.rx.value == 10, interval=10)
    await async_wait_until(lambda: rxgen.rx.value == 11)

async def mul_slowly(value):
    await asyncio.sleep(0.02)
    return value*2

async def test_reactive_async_watcher_not_notified_while_awaiting():
    irx = rx(1)
    async_rx = irx.rx.pipe(mul_slowly)
    items = []
    async_rx.rx.watch(items.append)
    assert async_rx.rx.value is param.Undefined
    await async_wait_until(lambda: items == [2])
    irx.rx.value = 2

    # The awaited value has not resolved yet, so the watcher must not be
    # notified with the value computed from the previous input.
    assert items == [2]

    await async_wait_until(lambda: items == [2, 4])

async def test_reactive_async_downstream_watcher_not_notified_while_awaiting():
    irx = rx(1)
    downstream = irx.rx.pipe(mul_slowly) + 10
    items = []
    downstream.rx.watch(items.append)
    assert downstream.rx.value is param.Undefined
    await async_wait_until(lambda: items == [12])
    irx.rx.value = 2
    assert items == [12]
    await async_wait_until(lambda: items == [12, 14])

async def test_reactive_async_downstream_not_computed_while_awaiting():
    computed = []
    def add(value):
        computed.append(value)
        return value+10

    irx = rx(1)
    downstream = irx.rx.pipe(mul_slowly).rx.pipe(add)
    downstream.rx.watch()
    downstream.rx.value
    await async_wait_until(lambda: computed == [2])
    irx.rx.value = 2

    # The downstream operation must not be applied to the superseded value.
    assert computed == [2]

    await async_wait_until(lambda: computed == [2, 4])

async def test_reactive_async_rapid_updates_notify_once():
    irx = rx(1)
    async_rx = irx.rx.pipe(mul_slowly)
    items = []
    async_rx.rx.watch(items.append)
    async_rx.rx.value
    await async_wait_until(lambda: items == [2])
    for value in (2, 3, 4):
        irx.rx.value = value
    await async_wait_until(lambda: items == [2, 8])
    assert items == [2, 8]

def test_reactive_skip_value_does_not_notify_watcher():
    P = Parameters(integer=1)

    def skip_values(v):
        if v > 2:
            raise Skip
        return v+1

    i = rx(P.param.integer).rx.pipe(skip_values)
    items = []
    i.rx.watch(items.append)
    P.integer = 2
    assert items == [3]

    # The operation skipped, so the watcher must not be notified with the
    # value computed from the previous input.
    P.integer = 3
    assert items == [3]
    assert i.rx.value == 3

async def test_reactive_async_ref_not_synced_while_awaiting():
    class Ref(param.Parameterized):
        value = param.Integer(default=0, allow_refs=True)

    irx = rx(1)
    p = Ref(value=irx.rx.pipe(mul_slowly))
    await async_wait_until(lambda: p.value == 2)
    irx.rx.value = 2
    assert p.value == 2
    await async_wait_until(lambda: p.value == 4)

async def test_reactive_async_superseded_updates_not_computed():
    started, finished = [], []

    async def mul(value):
        started.append(value)
        await asyncio.sleep(0.02)
        finished.append(value)
        return value*2

    irx = rx(1)
    async_rx = irx.rx.pipe(mul)
    items = []
    async_rx.rx.watch(items.append)
    async_rx.rx.value
    await async_wait_until(lambda: items == [2])
    assert started == [1]

    # The updates arrive without yielding to the event loop, so the tasks they
    # schedule have not started by the time the next one supersedes them.
    for value in (2, 3, 4, 5):
        irx.rx.value = value

    await async_wait_until(lambda: items == [2, 10])

    # Only the final update was computed; the superseded coroutines were closed
    # before their bodies began.
    assert started == [1, 5]
    assert finished == [1, 5]

async def test_reactive_async_gen_superseded_updates_not_computed():
    started = []

    async def gen(value):
        started.append(value)
        yield value*2

    irx = rx(1)
    async_rx = irx.rx.pipe(gen)
    async_rx.rx.watch()
    async_rx.rx.value
    await async_wait_until(lambda: async_rx.rx.value == 2)
    assert started == [1]

    for value in (2, 3, 4, 5):
        irx.rx.value = value

    await async_wait_until(lambda: async_rx.rx.value == 10)

    # A superseded async generator is closed before it is first iterated, so
    # its body never runs.
    assert started == [1, 5]

async def test_reactive_async_running_task_is_cancelled():
    cancelled = []

    async def mul(value):
        try:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            cancelled.append(value)
            raise
        return value*2

    irx = rx(1)
    async_rx = irx.rx.pipe(mul)
    async_rx.rx.watch()
    async_rx.rx.value

    # Yield to the event loop so the body is actually suspended on its await;
    # a task in that state cannot be skipped, it has to be cancelled.
    await asyncio.sleep(0.01)
    irx.rx.value = 2

    await async_wait_until(lambda: async_rx.rx.value == 4)
    assert cancelled == [1]

@pytest.mark.parametrize('lazy', [False, True])
async def test_async_shared_rx_superseded_updates_computed_once(lazy):
    call_count = 0

    class Model(param.Parameterized):
        a = param.Number(1.0)

    model = Model()

    async def expensive_compute(a):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return {"x": a + 1, "y": a * 2}

    shared = rx(model.param.a, lazy=lazy).rx.pipe(expensive_compute)
    x_rx = shared.rx.pipe(lambda d: d["x"])
    y_rx = shared.rx.pipe(lambda d: d["y"])

    x_rx.rx.value
    y_rx.rx.value
    await async_wait_until(lambda: call_count == 1)

    for value in (2.0, 3.0, 4.0):
        model.a = value

    x_rx.rx.value
    y_rx.rx.value
    await async_wait_until(
        lambda: x_rx.rx.value == 5 and y_rx.rx.value == 8
    )

    # The branches resolve through the shared node rather than recomputing, and
    # the superseded updates are not computed at all.
    assert call_count == 2

async def test_reactive_async_error_raised_on_read():
    async def mul(value):
        await asyncio.sleep(0.01)
        if value == 2:
            raise RuntimeError('boom')
        return 10 * value

    irx = rx(1)
    async_rx = irx.rx.pipe(mul)
    async_rx.rx.value
    await async_wait_until(lambda: async_rx.rx.value == 10)

    irx.rx.value = 2
    async_rx.rx.value

    # The failed operation must settle the node and store the error, so it is
    # re-raised on every read instead of leaving the node awaiting forever.
    await async_wait_until(lambda: async_rx._error_state is not None)
    assert not async_rx._awaiting
    with pytest.raises(RuntimeError, match='boom'):
        async_rx.rx.value

    # A new input clears the error and the pipeline recovers.
    irx.rx.value = 3
    async_rx.rx.value
    await async_wait_until(lambda: async_rx.rx.value == 30)

async def test_reactive_async_error_propagates_downstream():
    async def mul(value):
        await asyncio.sleep(0.01)
        raise RuntimeError('boom')

    irx = rx(1)
    downstream = irx.rx.pipe(mul) + 10
    downstream.rx.value
    await async_wait_until(lambda: downstream._prev._error_state is not None)
    with pytest.raises(RuntimeError, match='boom'):
        downstream.rx.value

async def test_reactive_async_error_propagates_to_shared_branches():
    async def compute(value):
        await asyncio.sleep(0.01)
        raise RuntimeError('boom')

    shared = rx(1).rx.pipe(compute)
    x_rx = shared.rx.pipe(lambda d: d['x'])
    y_rx = shared.rx.pipe(lambda d: d['y'])

    x_rx.rx.value
    y_rx.rx.value
    await async_wait_until(lambda: not shared._awaiting)
    for branch in (x_rx, y_rx):
        with pytest.raises(RuntimeError, match='boom'):
            branch.rx.value

async def test_reactive_async_gen_error_ends_stream():
    async def gen(value):
        for i in range(3):
            await asyncio.sleep(0.01)
            if i == 2:
                raise RuntimeError('boom')
            yield value+i

    async_rx = rx(1).rx.pipe(gen)
    async_rx.rx.value
    await async_wait_until(lambda: async_rx._error_state is not None)

    # The raise ends the generator's stream and is reported on the next read.
    assert not async_rx._awaiting
    with pytest.raises(RuntimeError, match='boom'):
        async_rx.rx.value

async def test_reactive_gen_error_ends_stream():
    def gen(value):
        yield value
        raise RuntimeError('boom')

    async_rx = rx(1).rx.pipe(gen)
    async_rx.rx.value
    await async_wait_until(lambda: async_rx._error_state is not None)
    assert not async_rx._awaiting
    with pytest.raises(RuntimeError, match='boom'):
        async_rx.rx.value

async def test_reactive_async_superseded_error_not_recorded():
    async def mul(value):
        await asyncio.sleep(0.02)
        if value == 2:
            raise RuntimeError('boom')
        return value*2

    irx = rx(1)
    async_rx = irx.rx.pipe(mul)
    async_rx.rx.value
    await async_wait_until(lambda: async_rx.rx.value == 2)

    irx.rx.value = 2
    async_rx.rx.value
    # Yield to the event loop so the failing task is suspended on its await and
    # is superseded while in flight.
    await asyncio.sleep(0.01)
    irx.rx.value = 3
    async_rx.rx.value

    # The error belongs to a superseded input, so it must not poison the node.
    await async_wait_until(lambda: async_rx.rx.value == 6)
    assert async_rx._error_state is None
async def _pair(value):
    await asyncio.sleep(0.02)
    return (value * 2, value * 3)

async def test_async_shared_rx_branch_after_settling_resolves():
    irx = rx(1)
    node = irx.rx.pipe(_pair)
    node.rx.value
    await async_wait_until(lambda: node.rx.value == (2, 3))

    # The branch mirrors a node that has already settled, so it must resolve
    # on its first read rather than being stranded on Undefined.
    first = node[0]
    assert first.rx.value == 2

    irx.rx.value = 3
    await async_wait_until(lambda: first.rx.value == 6)

async def test_async_shared_rx_branch_while_awaiting_resolves():
    irx = rx(1)
    node = irx.rx.pipe(_pair)
    node.rx.value

    first = node[0]
    assert first.rx.value is param.Undefined
    await async_wait_until(lambda: first.rx.value == 2)

async def test_async_shared_rx_branch_before_resolving_resolves():
    irx = rx(1)
    node = irx.rx.pipe(_pair)
    first, second = node[0], node[1]

    assert first.rx.value is param.Undefined
    await async_wait_until(lambda: first.rx.value == 2)

    # The shared node has settled by now, so the sibling branch resolves on
    # its first read.
    assert second.rx.value == 3

async def test_async_shared_rx_branch_computed_once():
    call_count = 0

    async def count_pair(value):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return (value * 2, value * 3)

    irx = rx(1)
    node = irx.rx.pipe(count_pair)
    first, second = node[0], node[1]

    # Request the value for both nodes
    first.rx.value
    second.rx.value
    await async_wait_until(lambda: first.rx.value == 2 and second.rx.value == 3)

    # The branches resolve through the shared node rather than recomputing.
    assert call_count == 1

    irx.rx.value = 3
    await async_wait_until(lambda: first.rx.value == 6 and second.rx.value == 9)
    assert call_count == 2

async def test_async_shared_rx_branch_notifies_watcher():
    irx = rx(1)
    node = irx.rx.pipe(_pair)
    node.rx.value
    await async_wait_until(lambda: node.rx.value == (2, 3))

    items = []
    first = node[0]
    assert first.rx.value == 2
    first.rx.watch(items.append)

    irx.rx.value = 3
    await async_wait_until(lambda: items == [6])
    assert items == [6]

async def test_async_gen_shared_rx_branch_resolves():
    async def gen(value):
        for i in range(3):
            await asyncio.sleep(0.02)
            yield (value + i, i)

    irx = rx(1)
    node = irx.rx.pipe(gen)
    node.rx.value
    await async_wait_until(lambda: node.rx.value == (3, 2))

    # A branch of a generator node adopts the value the generator settled on.
    first = node[0]
    assert first.rx.value == 3

@pytest.mark.parametrize('lazy', [False, True])
def test_root_invalidation(lazy):
    arx = rx('a', lazy=lazy)
    brx = rx('b', lazy=lazy)

    computed = []
    def debug(value, info):
        computed.append(info)
        return value

    expr = arx.title().rx.pipe(debug, '1') + brx.title().rx.pipe(debug, '2')

    assert expr.rx.value == 'AB'
    assert computed == ['1', '2']

    brx.rx.value = 'c'

    assert expr.rx.value == 'AC'
    assert computed == ['1', '2', '2']

    arx.rx.value = 'd'
    assert expr.rx.value == 'DC'
    assert computed == ['1', '2', '2', '1']


def test_ensure_ref_can_update_by_watcher_of_same_parameter():
    # https://github.com/holoviz/param/pull/929

    class W(param.Parameterized):
        value = param.String()


    class T(param.Parameterized):
        lst = param.List(allow_refs=True, allow_None=True)

        @param.depends("lst", watch=True)
        def test(self):
            lst = self.lst or range(5)
            items = [W(value=str(i)) for i in lst]
            with param.discard_events(self):
                self.lst = param.rx(items).rx.resolve()
            self.items = items

    def transform(obj):
        if isinstance(obj, W):
            return obj.param.value
        return obj


    param.reactive.register_reference_transform(transform)

    t = T()
    t.lst = list("ABCDE")
    t.items[1].value = "TEST"
    assert t.lst[1] == "TEST"

def test_reactive_callback_resolve_accessor():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"name": ["Bill", "Bob"]})
    dfx = rx(df)
    out = dfx["name"].str._callback()
    assert type(out) is type(df["name"].str)
    assert out._name == df["name"].str._name


def test_reactive_dunder_len_error():
    with pytest.raises(
        TypeError,
        match=re.escape(
            'len(<rx_obj>) is not supported. Use `<rx_obj>.rx.len()` to '
            'obtain the length as a reactive expression, or '
            '`len(<rx_obj>.rx.value)` to obtain the length of the underlying '
            'expression value.'
        )
    ):
        len(rx([1, 2]))


def test_reactive_dunder_bool():
    assert bool(rx([1, 2]))


def test_reactive_set_value_attributeerror():
    x = rx(1)
    with pytest.raises(AttributeError, match="'rx' has no attribute 'value'"):
        x.value = 1

def test_reactive_get_value_attributeerror():
    x = rx(1)
    with pytest.raises(AttributeError, match="'rx' object has no attribute 'value'"):
        x.value

def test_reactive_lazy_get_value_attributeerror():
    x = rx(1, lazy=True)
    xv = x.value
    with pytest.raises(AttributeError, match="'int' object has no attribute 'value'"):
        xv.rx.value

@pytest.mark.parametrize('lazy', [False, True])
def test_shared_rx_only_triggers_once(lazy):
    call_count = 0

    class Model(param.Parameterized):
        a = param.Number(1.0)

    model = Model()

    def expensive_compute(a):
        nonlocal call_count
        call_count += 1
        return {"x": a + 1, "y": a * 2}

    shared = rx(expensive_compute, lazy=lazy)(model.param.a)

    x_rx = shared.rx.pipe(lambda d: d["x"])
    y_rx = shared.rx.pipe(lambda d: d["y"])

    x_rx.rx.value
    y_rx.rx.value

    assert call_count == 1

    model.a = 2.0

    x_rx.rx.value
    y_rx.rx.value

    assert call_count == 2


@pytest.mark.parametrize('lazy', [False, True])
async def test_async_shared_rx_only_triggers_once(lazy):
    call_count = 0

    class Model(param.Parameterized):
        a = param.Number(1.0)

    model = Model()

    async def expensive_compute(a):
        nonlocal call_count
        call_count += 1
        return {"x": a + 1, "y": a * 2}

    shared = rx(model.param.a, lazy=lazy).rx.pipe(expensive_compute)

    x_rx = shared.rx.pipe(lambda d: d["x"])
    y_rx = shared.rx.pipe(lambda d: d["y"])

    x_rx.rx.value
    y_rx.rx.value

    await async_wait_until(lambda: call_count == 1)

    model.a = 2.0

    x_rx.rx.value
    y_rx.rx.value

    await async_wait_until(lambda: call_count == 2)

    assert x_rx.rx.value == 3
    assert y_rx.rx.value == 4

    assert call_count == 2


def test_reactive_derived_node_is_garbage_collected():
    def watcher_count(source):
        watchers = source._internal_params[0].owner._param__private.watchers
        return sum(len(lst) for what in watchers.values() for lst in what.values())

    a = param.rx(1)
    baseline = watcher_count(a)
    assert baseline == 2

    b = a + 1
    assert b.rx.value == 2
    assert watcher_count(a) > baseline

    ref = weakref.ref(b)
    del b
    gc.collect()
    assert ref() is None
    assert watcher_count(a) == baseline

    c = a + 10
    a.rx.value = 5
    assert c.rx.value == 15
    assert watcher_count(a) > baseline


def _rx_from_closure():
    """Build an object holding an rx pipeline whose root function closes over it."""
    class Owner:
        pass

    owner = Owner()

    def compute(x):
        return x + len(repr(owner)) * 0

    owner.expr = param.rx(compute)(41)
    return owner


def _rx_from_bound_method():
    """Build an object holding an rx pipeline rooted in one of its own methods."""
    class Owner:
        def __init__(self):
            self.expr = param.rx(self._compute)(41)

        def _compute(self, x):
            return x

    return Owner()


@pytest.mark.parametrize('factory', [_rx_from_closure, _rx_from_bound_method])
def test_reactive_function_rooted_node_does_not_pin_its_owner(factory):
    # weakref.finalize holds its arguments until the referent is collected, so
    # the invalidation cleanup must not own a path back to the node it cleans up.
    owner = factory()
    assert owner.expr.rx.value == 41

    ref = weakref.ref(owner)
    del owner
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize('factory', [_rx_from_closure, _rx_from_bound_method])
def test_reactive_function_rooted_nodes_do_not_accumulate(factory):
    refs = []
    for _ in range(50):
        owner = factory()
        owner.expr.rx.value
        refs.append(weakref.ref(owner))
        del owner
    gc.collect()
    assert all(ref() is None for ref in refs)
