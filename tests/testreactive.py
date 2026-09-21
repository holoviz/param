import asyncio
import contextlib
import gc
import math
import operator
import re
import time
import weakref

import param
import pytest

from param.parameterized import Comparator, Skip, batch
from param.reactive import Collected, bind, collect, current_node, rx
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

class TestOperators:
    """Arithmetic, comparison, and logical operator overloads."""

    @pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
    def test_reactive_numeric_binary_ops(self, op):
        assert op(rx(1), 2).rx.value == op(1, 2)
        assert op(rx(2), 2).rx.value == op(2, 2)

    @pytest.mark.parametrize('op', COMPARISON_OPERATORS)
    def test_reactive_numeric_comparison_ops(self, op):
        assert op(rx(1), 2).rx.value == op(1, 2)
        assert op(rx(2), 1).rx.value == op(2, 1)

    @pytest.mark.parametrize('op', NUMERIC_UNARY_OPERATORS)
    def test_reactive_numeric_unary_ops(self, op):
        assert op(rx(1)).rx.value == op(1)
        assert op(rx(-1)).rx.value == op(-1)
        assert op(rx(3.142)).rx.value == op(3.142)

    @pytest.mark.parametrize('op', NUMERIC_BINARY_OPERATORS)
    def test_reactive_numeric_binary_ops_reverse(self, op):
        assert op(2, rx(1)).rx.value == op(2, 1)
        assert op(2, rx(2)).rx.value == op(2, 2)

    @pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
    def test_reactive_logic_binary_ops(self, op):
        assert op(rx(True), True).rx.value == op(True, True)
        assert op(rx(True), False).rx.value == op(True, False)
        assert op(rx(False), True).rx.value == op(False, True)
        assert op(rx(False), False).rx.value == op(False, False)

    @pytest.mark.parametrize('op', LOGIC_UNARY_OPERATORS)
    def test_reactive_logic_unary_ops(self, op):
        assert op(rx(1)).rx.value == op(1)
        assert op(rx(0)).rx.value == op(0)

    @pytest.mark.parametrize('op', LOGIC_BINARY_OPERATORS)
    def test_reactive_logic_binary_ops_reverse(self, op):
        assert op(True, rx(True)).rx.value == op(True, True)
        assert op(True, rx(False)).rx.value == op(True, False)
        assert op(False, rx(True)).rx.value == op(False, True)
        assert op(False, rx(False)).rx.value == op(False, False)

class TestIndexingAndUfuncs:
    """``__getitem__`` and numpy ufunc support."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_getitem_dict(self, lazy):
        assert rx({'A': 1}, lazy=lazy)['A'].rx.value == 1
        assert rx({'A': 1, 'B': 2}, lazy=lazy)['B'].rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_getitem_list(self, lazy):
        assert rx([1, 2, 3], lazy=lazy)[1].rx.value == 2
        assert rx([1, 2, 3], lazy=lazy)[2].rx.value == 3

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_getitem_list_with_slice(self, lazy):
        i = rx(1, lazy=lazy)
        j = rx(5, lazy=lazy)
        lst = list(range(10))
        lstx = rx(lst)
        sx = lstx[i: j]
        assert sx.rx.value == lst[i.rx.value: j.rx.value]
        i.rx.value = 2
        assert sx.rx.value == lst[i.rx.value: j.rx.value]

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_getitem_numpy_with_tuple(self, lazy):
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
    def test_numpy_ufunc(self, ufunc):
        np = pytest.importorskip("numpy")
        ufunc = getattr(np, ufunc)
        l = [1, 2, 3]
        assert ufunc(rx(l)).rx.value == ufunc(l)
        array = np.ndarray([1, 2, 3])
        assert ufunc(rx(array)).rx.value == ufunc(array)

class TestValueAssignment:
    """Setting and mutating the value of a root expression."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_empty_construct(self, lazy):
        i = rx(lazy=lazy)
        assert i.rx.value is None
        i.rx.value = 2
        assert i.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_set_new_value_assignment(self, lazy):
        i = rx(1, lazy=lazy)
        assert i.rx.value == 1
        i.rx.value = 2
        assert i.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_set_new_value_method(self, lazy):
        i = rx(1, lazy=lazy)
        assert i.rx.value == 1
        i.rx.set(2)
        assert i.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_increment_value(self, lazy):
        i = rx(1, lazy=lazy)
        assert i.rx.value == 1
        i.rx.value += 2
        assert i.rx.value == 3

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_multiply_value_inplace(self, lazy):
        i = rx(3, lazy=lazy)
        assert i.rx.value == 3
        i.rx.value *= 2
        assert i.rx.value == 6

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_pipeline_set_new_value(self, lazy):
        i = rx(1, lazy=lazy)
        j = i + 2
        assert j.rx.value == 3
        i.rx.value = 2
        assert j.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_reflect_param_value(self, lazy):
        P = Parameters(integer=1)
        i = rx(P.param.integer, lazy=lazy)
        assert i.rx.value == 1
        P.integer = 2
        assert i.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_skip_value(self, lazy):
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
    def test_reactive_skip_value_return(self, lazy):
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

class TestErrorHandling:
    """``error_mode``, error labels, and error handling in ``bind()``."""

    def test_reactive_error_propagates_as_value(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        source = rx(1, error_mode="propagate")
        failed = source.rx.pipe(fail)
        downstream = failed + 1

        assert isinstance(failed.rx.value, param.ReactiveError)
        assert not failed.rx.value
        assert str(failed.rx.value) == "bad 1"
        assert failed.rx.value.exception.args == ("bad 1",)
        assert failed.rx.value.node() is failed
        assert downstream.rx.value is failed.rx.value
        assert failed.rx.error is failed.rx.value

    def test_reactive_error_default_raises(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        failed = rx(1, lazy=True).rx.pipe(fail)
        with pytest.raises(ValueError, match="bad 1"):
            failed.rx.value
        assert isinstance(failed.rx.error, ValueError)

    def test_reactive_error_mode_is_validated(self):
        with pytest.raises(ValueError, match="error_mode"):
            rx(1, error_mode="ignore")

    def test_reactive_error_process_failures(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        source = rx(1, error_mode="propagate")
        failed = source.rx.pipe(fail)
        handled = failed.rx.pipe(
            lambda error: error.exception.args[0], process_failures=True
        )

        assert handled.rx.value == "bad 1"
        assert handled.rx.error is None

    def test_reactive_error_label_is_none_by_default(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        failed = rx(1, error_mode="propagate").rx.pipe(fail)
        assert failed.rx.value.label is None

    def test_reactive_error_label_round_trips_through_pipe_and_operator(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        source = rx(1, error_mode="propagate", label="price feed")

        # The label is inherited across multiple .rx.pipe hops via _clone, and the
        # ReactiveError minted where the pipeline finally fails carries it.
        piped = source.rx.pipe(lambda v: v + 1).rx.pipe(fail)
        assert piped.rx.value.label == "price feed"

        # Same for a node reached through an operator overload.
        operated = (source + 1).rx.pipe(fail)
        assert operated.rx.value.label == "price feed"

    def test_reactive_label_getter_setter(self):
        expr = rx(1)
        assert expr.rx.label is None

        expr.rx.label = "price feed"
        assert expr.rx.label == "price feed"

        piped = expr.rx.pipe(lambda v: v + 1)
        assert piped.rx.label == "price feed"

    def test_reactive_label_setter_raises_on_non_rx(self):
        class P(param.Parameterized):
            a = param.Number(default=1)

        with pytest.raises(AttributeError):
            P().param.a.rx.label = "nope"

    def test_bind_reactive_error_short_circuits_by_default(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        calls = []

        def consumer(x):
            calls.append(x)
            return x

        failing = rx(1, error_mode="propagate").rx.pipe(fail)
        bound = bind(consumer, failing)

        result = bound()
        assert isinstance(result, param.ReactiveError)
        assert calls == []

    def test_bind_reactive_error_process_failures_calls_function(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        calls = []

        def consumer(x):
            calls.append(x)
            return x

        failing = rx(1, error_mode="propagate").rx.pipe(fail)
        bound = bind(consumer, failing, process_failures=True)

        result = bound()
        assert isinstance(result, param.ReactiveError)
        assert calls == [result]

    async def test_bind_reactive_error_short_circuits_coroutine(self):
        def fail(value):
            raise ValueError(f"bad {value}")

        calls = []

        async def consumer(x):
            calls.append(x)
            return x

        failing = rx(1, error_mode="propagate").rx.pipe(fail)

        result = await bind(consumer, failing)()
        assert isinstance(result, param.ReactiveError)
        assert calls == []

        result = await bind(consumer, failing, process_failures=True)()
        assert isinstance(result, param.ReactiveError)
        assert calls == [result]

class TestReflectingExternalState:
    """Reflecting parameters, other expressions, bound methods/functions, and dataframes."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_pipeline_reflect_param_value(self, lazy):
        P = Parameters(integer=1)
        i = rx(P.param.integer, lazy=lazy) + 2
        assert i.rx.value == 3
        P.integer = 2
        assert i.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_reactive_reflect_other_rx(self, lazy):
        i = rx(1, lazy=lazy)
        j = rx(i, lazy=lazy)
        assert j.rx.value == 1
        i.rx.value = 2
        assert j.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_pipeline_reflect_other_reactive_expr(self, lazy):
        i = rx(1, lazy=lazy)
        j = i + 2
        k = rx(j, lazy=lazy)
        assert k.rx.value == 3
        i.rx.value = 2
        assert k.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_reflect_bound_method(self, lazy):
        P = Parameters(integer=1)
        i = rx(P.multiply_integer, lazy=lazy)
        assert i.rx.value == 2
        P.integer = 2
        assert i.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_pipeline_reflect_bound_method(self, lazy):
        P = Parameters(integer=1)
        i = rx(P.multiply_integer, lazy=lazy) + 2
        assert i.rx.value == 4
        P.integer = 2
        assert i.rx.value == 6

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_reflect_bound_function(self, lazy):
        P = Parameters(integer=1)
        i = rx(bind(lambda v: v * 2, P.param.integer), lazy=lazy)
        assert i.rx.value == 2
        P.integer = 2
        assert i.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_pipeline_reflect_bound_function(self, lazy):
        P = Parameters(integer=1)
        i = rx(bind(lambda v: v * 2, P.param.integer), lazy=lazy) + 2
        assert i.rx.value == 4
        P.integer = 2
        assert i.rx.value == 6

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_dataframe_method_chain(self, dataframe, lazy):
        pd = pytest.importorskip("pandas")
        dfi = rx(dataframe, lazy=lazy).groupby('str')[['float']].mean().reset_index()
        pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_dataframe_attribute_chain(self, dataframe, lazy):
        np = pytest.importorskip("numpy")
        array = rx(dataframe).str.values.rx.value
        np.testing.assert_array_equal(array, dataframe.str.values)

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_dataframe_param_value_method_chain(self, dataframe, lazy):
        pd = pytest.importorskip("pandas")
        P = Parameters(string='str')
        dfi = rx(dataframe, lazy=lazy).groupby(P.param.string)[['float']].mean().reset_index()
        pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('str')[['float']].mean().reset_index())
        P.string = 'int'
        pd.testing.assert_frame_equal(dfi.rx.value, dataframe.groupby('int')[['float']].mean().reset_index())

class TestSpecialMethods:
    """``len``, ``bool``, boolean operators, ``map``, ``iter``, membership, and ``.rx.where``."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_len(self, lazy):
        i = rx([1, 2, 3], lazy=lazy)
        l = i.rx.len()
        assert l.rx.value == 3
        i.rx.value = [1, 2]
        assert l.rx.value == 2

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_bool(self, lazy):
        i = rx(1, lazy=lazy)
        b = i.rx.bool()
        assert b.rx.value is True
        i.rx.value = 0
        assert b.rx.value is False

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_not_(self, lazy):
        i = rx(1, lazy=lazy)
        b = i.rx.not_()
        assert b.rx.value is False
        i.rx.value = 0
        assert b.rx.value is True

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_and_(self, lazy):
        i = rx('', lazy=lazy)
        b = i.rx.and_('foo')
        assert b.rx.value == ''
        i.rx.value = 'bar'
        assert b.rx.value == 'foo'

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_or_(self, lazy):
        i = rx('', lazy=lazy)
        b = i.rx.or_('')
        assert b.rx.value == ''
        i.rx.value = 'foo'
        assert b.rx.value == 'foo'

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_map(self, lazy):
        i = rx(range(3), lazy=lazy)
        b = i.rx.map(lambda x: x*2)
        assert b.rx.value == [0, 2, 4]
        i.rx.value = range(1, 4)
        assert b.rx.value == [2, 4, 6]

    @pytest.mark.parametrize('lazy', [False, True])
    async def test_reactive_async_map(self, lazy):
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
    def test_reactive_map_args(self, lazy):
        i = rx(range(3), lazy=lazy)
        j = rx(2, lazy=lazy)
        b = i.rx.map(lambda x, m: x*m, j)
        assert b.rx.value == [0, 2, 4]
        j.rx.value = 3
        assert b.rx.value == [0, 3, 6]

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_iter(self, lazy):
        i = rx(('a', 'b'), lazy=lazy)
        if lazy: i.rx.value
        a, b = i
        assert a.rx.value == 'a'
        assert b.rx.value == 'b'
        i.rx.value = ('b', 'a')
        assert a.rx.value == 'b'
        assert b.rx.value == 'a'

    def test_reactive_iter_lazy_fails(self):
        i = rx(('a', 'b'), lazy=True)
        with pytest.raises(RuntimeError):
            a, b = i

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_multi_iter(self, lazy):
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
    def test_reactive_is(self, lazy):
        i = rx(None, lazy=lazy)
        is_ = i.rx.is_(None)
        assert is_.rx.value
        i.rx.value = False
        assert not is_.rx.value

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_in(self, lazy):
        i = rx(2, lazy=lazy)
        in_ = i.rx.in_([1, 2, 3])
        assert in_.rx.value
        i.rx.value = 4
        assert not in_.rx.value

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_is_not(self, lazy):
        i = rx(None, lazy=lazy)
        is_ = i.rx.is_not(None)
        assert not is_.rx.value
        i.rx.value = False
        assert is_.rx.value

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_where_expr(self, lazy):
        p = Parameters()
        r = rx(p.param.boolean, lazy=lazy).rx.where('A', 'B')
        assert r.rx.value == 'B'
        p.boolean = True
        assert r.rx.value == 'A'

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_where_expr_refs(self, lazy):
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

class TestWatch:
    """``.rx.watch()`` and its ``onlychanged``/lazy behavior."""

    def test_reactive_watch_on_set_input(self):
        string = rx('string')
        new_string = string + '!'
        items = []
        new_string.rx.watch(items.append)
        string.rx.value = 'new string'
        assert items == ['new string!']

    def test_reactive_watch_onlychanged_skips_a_masked_ticks_repeat_value(self):
        a = rx(2)
        b = rx(10) * a
        items = []
        b.rx.watch(items.append)

        b.rx.overrides[0] = 1
        a.rx.value = 5
        a.rx.value = 9

        assert items == [10]
        assert b.rx.value == 10

    def test_reactive_watch_onlychanged_still_delivers_real_changes(self):
        a = rx(1)
        items = []
        (a + 0).rx.watch(items.append)

        a.rx.value = 2
        a.rx.value = 2  # setting the same value does not even tick the parameter
        a.rx.value = 3

        assert items == [2, 3]

    def test_reactive_watch_onlychanged_false_delivers_every_recompute(self):
        a = rx(2)
        b = rx(10) * a
        items = []
        b.rx.watch(items.append, onlychanged=False)

        b.rx.overrides[0] = 1
        a.rx.value = 5
        a.rx.value = 9

        assert items == [10, 10, 10]

    def test_reactive_watch_onlychanged_tracks_each_watcher_independently(self):
        a = rx(1)
        first, second = [], []
        a.rx.watch(first.append)
        a.rx.value = 5
        a.rx.watch(second.append)
        a.rx.value = 7

        assert first == [5, 7]
        # The second watcher's own first delivery, unaffected by what the first
        # watcher already recorded as its own last-seen value.
        assert second == [7]

    @pytest.mark.filterwarnings("ignore::UserWarning")
    def test_reactive_watch_lazy_on_set_input(self):
        string = rx('string', lazy=True)
        new_string = string + '!'
        items = []
        new_string.rx.watch(items.append)
        string.rx.value = 'new string'
        assert items == ['new string!']

    async def test_reactive_watch_async_on_event(self):
        p = Parameters()
        event = rx(p.param.event)
        items = []
        event.rx.watch(items.append)
        p.param.trigger('event')
        await async_wait_until(lambda: items == [True])

    @pytest.mark.filterwarnings("ignore::UserWarning")
    async def test_reactive_watch_lazy_async_on_event(self):
        p = Parameters()
        event = rx(p.param.event, lazy=True)
        items = []
        event.rx.watch(items.append)
        p.param.trigger('event')
        await async_wait_until(lambda: items == [True])

class TestCloneAndWhen:
    """Cloning semantics, re-evaluation, and ``.rx.when()``."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_set_value_non_root_raises(self, lazy):
        rx_val = rx(1, lazy=lazy) + 1
        with pytest.raises(AttributeError):
            rx_val.rx.value = 3

    @pytest.mark.parametrize(('input', 'op', 'expected'), [
        ('bob', lambda _rx: _rx.title(), 'Bob'),
        ('bob', lambda _rx: _rx.rx.map(str.upper), [*'BOB']),
    ])
    def test_reactive_clone_evaluates_once_lazy(self, input: str, op: Callable[[rx], Any], expected: Any):
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
    def test_reactive_clone_evaluates_once_eager(self, input: str, op: Callable[[rx], Any], expected: Any):
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
    def test_reactive_clone_reevaluates(self, inputs: list[str], op: Callable[[rx], Any], expecteds: list[Any], lazy: bool):
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
    def test_reactive_when(self, lazy):
        p = Parameters(integer=3)
        integer = rx(p.param.integer, lazy=lazy).rx.when(p.param.event)
        assert integer.rx.value == 3
        p.integer = 4
        assert integer.rx.value == 3
        p.param.trigger('event')
        assert integer.rx.value == 4

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_when_initial(self, lazy):
        p = Parameters(integer=3)
        integer = rx(p.param.integer, lazy=lazy).rx.when(p.param.event, initial=None)
        assert integer.rx.value is None
        p.integer = 4
        assert integer.rx.value is None
        p.param.trigger('event')
        assert integer.rx.value == 4

class TestResolveMethod:
    """``.rx.resolve()``, including nested and recursive resolution."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_reactive_resolve(self, lazy):
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
    def test_reactive_resolve_nested(self, lazy):
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
    def test_reactive_resolve_recursive(self, lazy):
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

class TestAwaiting:
    """``.rx.awaiting``."""

    def test_reactive_awaiting_sync_expression(self):
        expr = rx(1) + 2

        assert expr.rx.value == 3
        assert not expr.rx.awaiting

    def test_reactive_awaiting_on_parameter(self):
        class P(param.Parameterized):
            a = param.Number(default=1)

        assert not P().param.a.rx.awaiting

    def test_reactive_awaiting_skip_is_not_awaiting(self):
        def maybe(value):
            if value < 5:
                raise Skip
            return value

        expr = rx(0).rx.pipe(maybe)

        assert expr.rx.value != 0
        assert expr._skipped
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_async_pipe(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        expr = rx(0).rx.pipe(async_func)

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 2)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_not_scheduled_until_requested(self):
        """
        Reading awaiting must not itself schedule a resolution, so an expression
        whose value has never been requested is not awaiting.
        """
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        expr = rx(0).rx.pipe(async_func)

        assert not expr.rx.awaiting
        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting

    async def test_reactive_awaiting_visible_downstream_of_async_node(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        expr = rx(0).rx.pipe(async_func) + 10

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 12)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_subscript_skips_until_async_node_settles(self):
        async def async_func():
            await asyncio.sleep(0.02)
            return {'value': 42}

        expr = rx(async_func)['value']

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 42)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_subscript_argument_skips_until_async_node_settles(self):
        async def async_func():
            await asyncio.sleep(0.02)
            return {'value': 42}

        source = rx(async_func)
        expr = source[rx('value')]

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 42)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_on_recompute(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        number = rx(0)
        expr = number.rx.pipe(async_func) + 10
        expr.rx.watch()

        await async_wait_until(lambda: expr.rx.value == 12)
        assert not expr.rx.awaiting

        number.rx.value = 5
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 17)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_through_operation_argument(self):
        """An rx passed as an operation argument is upstream of the operation."""
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        inner = rx(0).rx.pipe(async_func)
        expr = rx(100) + inner

        # Requesting the value schedules the inner resolve
        unsettled = expr.rx.value

        assert unsettled != 102
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 102)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_branching_pipeline(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        base = rx(0).rx.pipe(async_func)
        branch1 = base + 100
        branch2 = base + 200

        assert branch1.rx.value is param.Undefined
        assert branch2.rx.value is param.Undefined
        assert branch1.rx.awaiting
        assert branch2.rx.awaiting
        await async_wait_until(lambda: branch1.rx.value == 102)
        await async_wait_until(lambda: branch2.rx.value == 202)
        assert not branch1.rx.awaiting
        assert not branch2.rx.awaiting

    async def test_reactive_awaiting_async_gen_settles_per_emission(self):
        async def gen(value):
            yield value + 1
            await asyncio.sleep(0.1)
            yield value + 2

        expr = rx(0).rx.pipe(gen)

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 1, interval=10)
        assert not expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 2)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_root_async_func(self):
        """
        A coroutine function passed to rx as the object is held on a parameter and
        resolved by the reference machinery rather than as an operation, so its
        settlement is tracked there.
        """
        async def async_func():
            await asyncio.sleep(0.02)
            return 2

        expr = rx(async_func) + 2

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 4)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_root_async_func_on_recompute(self):
        async def async_func(i):
            await asyncio.sleep(0.02)
            return i * 10

        number = rx(1)
        expr = rx(bind(async_func, number)) + 1

        await async_wait_until(lambda: expr.rx.value == 11)
        assert not expr.rx.awaiting

        number.rx.value = 5
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 51)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_root_gen_settles_per_emission(self):
        def gen():
            yield 1
            time.sleep(0.1)
            yield 2

        expr = rx(gen) + 100

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 101, interval=10)
        assert not expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 102)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_async_ref_on_parameterized(self):
        """An async ref on a Parameterized feeding an expression is tracked too."""
        class P(param.Parameterized):
            value = param.Parameter(default=0, allow_refs=True)

        async def async_func():
            await asyncio.sleep(0.02)
            return 7

        p = P()
        expr = p.param.value.rx() + 1
        expr.rx.watch()

        assert expr.rx.value == 1
        assert not expr.rx.awaiting

        p.value = async_func
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 8)
        assert not expr.rx.awaiting

    def test_reactive_awaiting_sync_ref_never_awaits(self):
        class P(param.Parameterized):
            source = param.Number(default=1)
            target = param.Number(default=0, allow_refs=True)

        p = P()
        p.target = p.param.source
        expr = p.param.target.rx() + 1

        assert not expr.rx.awaiting
        p.source = 5
        assert not expr.rx.awaiting
        assert expr.rx.value == 6

    async def test_reactive_awaiting_settles_when_async_ref_yields_nothing(self):
        """A resolution that never produces a value must not stay in flight."""
        def gen():
            return
            yield  # pragma: no cover

        expr = rx(gen) + 100

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: not expr.rx.awaiting)

    async def test_reactive_awaiting_settles_when_async_gen_operation_yields_nothing(self):
        """
        A generator operation whose stream ends without yielding declined to
        produce a value, so it must settle rather than stay in flight forever.
        """
        async def gen(value):
            return
            yield  # pragma: no cover

        expr = rx(1).rx.pipe(gen)

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert expr._skipped

    async def test_reactive_awaiting_settles_when_gen_operation_yields_nothing(self):
        """A synchronous generator operation is wrapped, so it settles too."""
        def gen(value):
            return
            yield  # pragma: no cover

        expr = rx(1).rx.pipe(gen)

        assert expr.rx.value is param.Undefined
        assert expr.rx.awaiting
        await async_wait_until(lambda: not expr.rx.awaiting)

    async def test_reactive_awaiting_settles_when_async_gen_stream_becomes_empty(self):
        """
        A stream that yielded for earlier inputs and yields nothing for the current
        ones settles, keeping its previous value without publishing it again.
        """
        async def gen(value):
            if value > 0:
                yield value * 2

        number = rx(1)
        expr = number.rx.pipe(gen)
        items = []
        expr.rx.watch(items.append)

        await async_wait_until(lambda: expr.rx.value == 2)
        assert items == [2]
        assert not expr.rx.awaiting

        number.rx.value = 0
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert items == [2]
        assert expr._skipped
        assert expr.rx.value == 2

        # A later stream that does yield recovers
        number.rx.value = 5
        await async_wait_until(lambda: items == [2, 10])
        assert not expr.rx.awaiting
        assert not expr._skipped

    async def test_reactive_awaiting_superseded_stream_does_not_claim_generation(self):
        """
        A stream abandoned because its inputs changed must not settle the newer
        resolution that superseded it.
        """
        started = []

        async def gen(value):
            started.append(value)
            await asyncio.sleep(0.05)
            yield value * 2

        number = rx(1)
        expr = number.rx.pipe(gen)
        expr.rx.watch()

        await async_wait_until(lambda: expr.rx.value == 2)

        number.rx.value = 2
        number.rx.value = 3
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 6)
        assert not expr.rx.awaiting

    async def test_reactive_awaiting_visible_through_override(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        placeholder = rx(1)
        override = rx(0).rx.pipe(async_func)
        b = rx(10) * placeholder
        assert b.rx.value == 10
        assert not b.rx.awaiting

        b.rx.overrides[0] = override
        assert b.rx.value != 20  # Reading through the override schedules it.
        assert b.rx.awaiting
        await async_wait_until(lambda: not b.rx.awaiting)
        assert b.rx.value == 20

    async def test_reactive_awaiting_visible_through_override_set_before_first_read(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        placeholder = rx(1)
        override = rx(0).rx.pipe(async_func)
        b = rx(10) * placeholder
        b.rx.overrides[0] = override

        assert b.rx.value != 20  # The first-ever read schedules the override's op.
        assert b.rx.awaiting
        await async_wait_until(lambda: not b.rx.awaiting)
        assert b.rx.value == 20

    async def test_reactive_awaiting_visible_through_ref_holding_rx(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        b = rx(0).rx.pipe(async_func)
        outlet = Outlet(x=b)
        expr = outlet.param.x.rx()

        assert b in set(expr.rx.upstream())
        assert expr.rx.awaiting
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert expr.rx.value == 2

    async def test_reactive_awaiting_visible_through_ref_holding_rx_set_after_construction(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        outlet = Outlet()
        expr = outlet.param.x.rx()
        assert not expr.rx.awaiting

        b = rx(0).rx.pipe(async_func)
        outlet.x = b

        assert b in set(expr.rx.upstream())
        assert expr.rx.awaiting
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert expr.rx.value == 2

class TestStale:
    """``.rx.stale``."""

    def test_reactive_stale_until_first_evaluation(self):
        expr = rx(1) + 2

        assert expr.rx.stale
        assert expr.rx.value == 3
        assert not expr.rx.stale

    def test_reactive_stale_on_parameter(self):
        class P(param.Parameterized):
            a = param.Number(default=1)

        assert not P().param.a.rx.stale

    def test_reactive_stale_on_input_change(self):
        number = rx(1)
        expr = number + 2

        assert expr.rx.value == 3
        assert not expr.rx.stale

        number.rx.value = 5
        assert expr.rx.stale
        assert expr.rx.value == 7
        assert not expr.rx.stale

    def test_reactive_stale_visible_downstream(self):
        """An expression downstream of a stale one is itself stale."""
        number = rx(1)
        upstream = number + 2
        downstream = upstream * 2

        assert downstream.rx.value == 6
        assert not upstream.rx.stale
        assert not downstream.rx.stale

        number.rx.value = 5
        assert upstream.rx.stale
        assert downstream.rx.stale

        # Resolving the upstream expression does not update the downstream one
        assert upstream.rx.value == 7
        assert not upstream.rx.stale
        assert downstream.rx.stale

    def test_reactive_stale_on_bound_function_input_change(self):
        class P(param.Parameterized):
            a = param.Number(default=1)

        p = P()
        expr = rx(bind(lambda a: a + 1, p.param.a)) + 1

        assert expr.rx.value == 3
        assert not expr.rx.stale

        p.a = 5
        assert expr.rx.stale
        assert expr.rx.value == 7
        assert not expr.rx.stale

    def test_reactive_stale_through_operation_argument(self):
        number = rx(1)
        inner = number + 1
        expr = rx(100) + inner

        assert expr.rx.value == 102
        assert not expr.rx.stale

        number.rx.value = 5
        assert expr.rx.stale
        assert expr.rx.value == 106
        assert not expr.rx.stale

    def test_reactive_stale_not_evaluated_when_read(self):
        """Reading stale must not itself resolve the expression."""
        calls = []

        def count(value):
            calls.append(value)
            return value

        expr = rx(1).rx.pipe(count)

        assert expr.rx.stale
        assert calls == []
        assert expr.rx.value == 1
        assert calls == [1]

    async def test_reactive_stale_while_async_operation_in_flight(self):
        """
        An async operation is stale from the moment its inputs change until it has
        produced a value, i.e. scheduling it does not make it up to date.
        """
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        expr = rx(0).rx.pipe(async_func) + 10

        assert expr.rx.stale
        assert expr.rx.value is param.Undefined
        assert expr.rx.stale
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 12)
        assert not expr.rx.stale
        assert not expr.rx.awaiting

    async def test_reactive_stale_on_async_recompute(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        number = rx(0)
        expr = number.rx.pipe(async_func) + 10
        expr.rx.watch()

        await async_wait_until(lambda: expr.rx.value == 12)
        assert not expr.rx.stale

        number.rx.value = 5
        assert expr.rx.stale
        assert expr.rx.awaiting
        await async_wait_until(lambda: expr.rx.value == 17)
        assert not expr.rx.stale

    async def test_reactive_stale_while_async_ref_in_flight(self):
        class P(param.Parameterized):
            value = param.Parameter(default=0, allow_refs=True)

        async def async_func():
            await asyncio.sleep(0.02)
            return 7

        p = P()
        expr = p.param.value.rx() + 1
        expr.rx.watch()

        assert expr.rx.value == 1
        assert not expr.rx.stale

        p.value = async_func
        assert expr.rx.stale
        await async_wait_until(lambda: expr.rx.value == 8)
        assert not expr.rx.stale

    async def test_reactive_stale_branching_pipeline(self):
        number = rx(1)
        base = number + 1
        branch1 = base + 100
        branch2 = base + 200

        assert branch1.rx.value == 102
        assert branch2.rx.value == 202
        assert not branch1.rx.stale
        assert not branch2.rx.stale

        number.rx.value = 5
        assert branch1.rx.stale
        assert branch2.rx.stale

        assert branch1.rx.value == 106
        assert not branch1.rx.stale
        assert branch2.rx.stale

    def test_reactive_stale_skip_keeps_previous_value(self):
        """A skipped operation deliberately keeps its value, so it is not stale."""
        def maybe(value):
            if value < 5:
                raise Skip
            return value

        number = rx(10)
        expr = number.rx.pipe(maybe)

        assert expr.rx.value == 10
        assert not expr.rx.stale

        number.rx.value = 0
        assert expr.rx.stale
        assert expr.rx.value == 10
        assert not expr.rx.stale

    def test_reactive_stale_gated_by_when_ignores_upstream_change(self):
        """
        A gated expression reflects its inputs as of the last gate event, so an
        upstream change alone does not make it stale.
        """
        class State(param.Parameterized):
            submit = param.Event()

        state = State()
        number = rx(1)
        gated = (number + 1).rx.when(state.param.submit)

        assert gated.rx.value == 2
        assert not gated.rx.stale

        number.rx.value = 10
        assert not gated.rx.stale
        assert gated.rx.value == 2

        state.submit = True
        assert gated.rx.stale
        assert gated.rx.value == 11
        assert not gated.rx.stale

    def test_reactive_stale_downstream_of_when_gate(self):
        class State(param.Parameterized):
            submit = param.Event()

        state = State()
        number = rx(1)
        expr = (number + 1).rx.when(state.param.submit) + 100

        assert expr.rx.value == 102
        assert not expr.rx.stale

        number.rx.value = 10
        assert not expr.rx.stale

        state.submit = True
        assert expr.rx.stale
        assert expr.rx.value == 111
        assert not expr.rx.stale

    def test_reactive_stale_where_tracks_selected_branch_only(self):
        condition = rx(True)
        x = rx('x')
        y = rx('y')
        expr = condition.rx.where(x, y).rx() + '!'

        assert expr.rx.value == 'x!'
        assert not expr.rx.stale

        # The unselected branch cannot change the value
        y.rx.value = 'y2'
        assert not expr.rx.stale

        x.rx.value = 'x2'
        assert expr.rx.stale
        assert expr.rx.value == 'x2!'
        assert not expr.rx.stale

        condition.rx.value = False
        assert expr.rx.stale
        assert expr.rx.value == 'y2!'
        assert not expr.rx.stale

    def test_reactive_stale_on_bound_function(self):
        """A bound function evaluates on every read, so it never holds a stale value."""
        class P(param.Parameterized):
            a = param.Number(default=1)

        p = P()
        fn = bind(lambda a: a + 1, p.param.a)

        assert not fn.rx.stale
        assert fn.rx.value == 2
        assert not fn.rx.stale

        p.a = 5
        assert not fn.rx.stale
        assert fn.rx.value == 6

    async def test_reactive_stale_visible_through_override(self):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        placeholder = rx(1)
        b = rx(10) * placeholder
        assert b.rx.value == 10
        assert not b.rx.stale

        override = rx(0).rx.pipe(async_func)
        b.rx.overrides[0] = override
        b.rx.value  # Clears `b`'s own dirty flag; `override` is still settling.
        assert b.rx.stale

        # `.rx.stale` only clears on the next read, so wait for the override
        # to settle, then re-read `b`.
        await async_wait_until(lambda: not override.rx.awaiting)
        assert b.rx.value == 20
        assert not b.rx.stale

    async def test_reactive_stale_visible_through_ref_holding_rx(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def async_func(value):
            await asyncio.sleep(0.02)
            return value + 2

        b = rx(0).rx.pipe(async_func)
        outlet = Outlet(x=b)
        expr = outlet.param.x.rx()

        expr.rx.value  # Clears `expr`'s own dirty flag; `b` is still settling.
        assert expr.rx.stale

        await async_wait_until(lambda: not b.rx.awaiting)
        assert expr.rx.value == 2
        assert not expr.rx.stale

class TestUpdatingStatus:
    """``.rx.updating()``."""

    def test_reactive_updating_sync_flips_true_then_false(self):
        number = rx(1)
        updating = number.rx.updating()
        log = []
        updating.rx.watch(log.append)

        assert updating.rx.value is False

        number.rx.value = 2

        assert updating.rx.value is False
        assert log == [True, False]

    async def test_reactive_updating_spans_async_wait(self):
        """`.rx.updating()` must span the whole async wait, not just flip momentarily."""
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        expr = rx(1).rx.pipe(double)
        updating = expr.rx.updating()
        log = []
        updating.rx.watch(log.append)
        expr.rx.watch(lambda v: None)

        assert expr.rx.value is param.Undefined
        assert updating.rx.value is True
        assert expr.rx.awaiting

        await async_wait_until(lambda: expr.rx.value == 2)

        assert updating.rx.value is False
        assert not expr.rx.awaiting
        assert log == [True, False]

    async def test_reactive_updating_visible_downstream_of_async_node(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        expr = rx(1).rx.pipe(double) + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)

        assert expr.rx.value is param.Undefined
        assert updating.rx.value is True

        await async_wait_until(lambda: expr.rx.value == 3)

        assert updating.rx.value is False

    async def test_reactive_updating_spans_chained_async_operations(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        stage1 = rx(1).rx.pipe(double)
        stage2 = stage1.rx.pipe(double)
        updating = stage2.rx.updating()
        stage2.rx.watch(lambda v: None)

        assert stage2.rx.value is param.Undefined
        assert updating.rx.value is True

        await async_wait_until(lambda: stage1.rx.value == 2, interval=5)
        # stage1 has settled but stage2 is still resolving its own operation
        assert updating.rx.value is True

        await async_wait_until(lambda: stage2.rx.value == 4)
        assert updating.rx.value is False

    async def test_reactive_updating_spans_async_wait_on_branching_pipeline(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value + 2

        base = rx(0).rx.pipe(double)
        branch1 = base + 100
        branch2 = base + 200
        updating1 = branch1.rx.updating()
        updating2 = branch2.rx.updating()
        branch1.rx.watch(lambda v: None)
        branch2.rx.watch(lambda v: None)

        assert branch1.rx.value is param.Undefined
        assert branch2.rx.value is param.Undefined
        assert updating1.rx.value is True
        assert updating2.rx.value is True

        await async_wait_until(lambda: branch1.rx.value == 102)
        await async_wait_until(lambda: branch2.rx.value == 202)

        assert updating1.rx.value is False
        assert updating2.rx.value is False

    async def test_reactive_updating_true_when_created_already_awaiting(self):
        """Attaching `.rx.updating()` mid-flight reports True immediately."""
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        expr = rx(1).rx.pipe(double)
        expr.rx.watch(lambda v: None)
        expr.rx.value

        assert expr.rx.awaiting

        updating = expr.rx.updating()

        assert updating.rx.value is True

        await async_wait_until(lambda: expr.rx.value == 2)

        assert updating.rx.value is False

    async def test_reactive_updating_false_for_never_read_async_expression(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        expr = rx(1).rx.pipe(double)
        updating = expr.rx.updating()

        assert updating.rx.value is False

    async def test_reactive_updating_tracks_override_set_before_construction(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        placeholder = rx(1)
        override = rx(10).rx.pipe(double)
        b = rx(1) * placeholder
        b.rx.overrides[0] = override

        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        assert b.rx.value != 20
        assert updating.rx.value is True

        await async_wait_until(lambda: b.rx.value == 20)
        assert updating.rx.value is False

    async def test_reactive_updating_tracks_override_set_after_construction(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        placeholder = rx(1)
        b = rx(1) * placeholder
        updating = b.rx.updating()  # Constructed BEFORE the override exists.
        b.rx.watch(lambda v: None)

        assert b.rx.value == 1
        assert updating.rx.value is False

        override = rx(10).rx.pipe(double)
        b.rx.overrides[0] = override

        assert b.rx.awaiting
        assert updating.rx.value is True

        await async_wait_until(lambda: b.rx.value == 20)
        assert updating.rx.value is False

    async def test_reactive_updating_tracks_ref_reassigned_after_construction(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        outlet = Outlet()
        expr = outlet.param.x.rx()
        updating = expr.rx.updating()  # Constructed BEFORE the ref exists.
        expr.rx.watch(lambda v: None)

        assert updating.rx.value is False

        outlet.x = rx(10).rx.pipe(double)

        assert updating.rx.value is True

        await async_wait_until(lambda: expr.rx.value == 20)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_after_ref_replaced_by_plain_value(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def slow(value):
            await asyncio.sleep(0.02)
            return value

        src = rx(1)
        old_ref = src.rx.pipe(slow)
        old_ref.rx.watch(lambda v: None)
        outlet = Outlet(x=0)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)

        outlet.x = old_ref
        await async_wait_until(lambda: expr.rx.value == 2)
        assert updating.rx.value is False

        outlet.x = 3  # A plain value, not another ref.
        assert expr.rx.value == 4
        assert not any(n is old_ref for n in expr.rx.upstream())

        src.rx.value = 10  # `old_ref` settles again, but is no longer part of `expr`.
        await async_wait_until(lambda: old_ref.rx.value == 10)
        assert updating.rx.value is False

    async def test_reactive_status_clears_when_async_ref_is_replaced_synchronously(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        class Source(param.Parameterized):
            value = param.Integer(default=4)

        async def slow():
            await asyncio.Event().wait()

        source = Source()
        outlet = Outlet(x=slow)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)

        assert expr.rx.awaiting
        assert updating.rx.value is True

        outlet.x = 3
        assert expr.rx.value == 4
        assert not expr.rx.awaiting
        assert not expr.rx.stale
        await asyncio.sleep(0)
        assert updating.rx.value is False

        outlet.x = slow
        assert expr.rx.awaiting
        assert updating.rx.value is True

        outlet.x = source.param.value
        assert expr.rx.value == 5
        assert not expr.rx.awaiting
        assert not expr.rx.stale
        await asyncio.sleep(0)
        assert updating.rx.value is False

    async def test_reactive_sync_ref_replacement_survives_a_raising_updating_watcher(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        class Source(param.Parameterized):
            value = param.Integer(default=4)

        async def slow():
            await asyncio.sleep(0.05)
            return 0

        outlet = Outlet(x=1)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        outlet.x = slow
        updating.rx.watch(lambda value: (_ for _ in ()).throw(ValueError) if not value else None)

        with pytest.raises(ValueError):
            outlet.x = Source().param.value

        assert outlet.x == 4
        assert outlet._param__private.refs['x'] is not None

    async def test_reactive_invalid_value_clears_updating_after_an_async_ref(self):
        class Outlet(param.Parameterized):
            x = param.Integer(default=0, allow_refs=True)

        async def slow():
            await asyncio.Event().wait()

        outlet = Outlet(x=1)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda value: None)
        outlet.x = slow

        with pytest.raises(ValueError):
            outlet.x = 'bad'

        assert outlet.x == 1
        assert expr.rx.awaiting is False
        assert updating.rx.value is False

    def test_reactive_plain_value_tick_does_not_notify_graph_change(self, monkeypatch):
        calls = []
        original = rx._notify_graph_change
        def spy(self):
            calls.append(self)
            return original(self)
        monkeypatch.setattr(rx, '_notify_graph_change', spy)

        a = rx(1)
        b = a + 1
        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        a.rx.value = 2

        assert calls == []
        assert updating.rx.value is False

    async def test_reactive_updating_ignores_settle_from_node_no_longer_upstream(self):
        async def double(value):
            await asyncio.sleep(0.02)
            return value * 2

        b = rx(1) * rx(1)
        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        src = rx(10)
        override = src.rx.pipe(double)
        b.rx.overrides[0] = override
        await async_wait_until(lambda: not b.rx.awaiting)
        del b.rx.overrides[0]
        await async_wait_until(lambda: updating.rx.value is False)

        override.rx.watch(lambda v: None)
        src.rx.value = 20
        await async_wait_until(lambda: not override.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_when_a_ref_settles_without_changing_the_value(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def slow(value):
            await asyncio.sleep(0.02)
            return value

        src = rx(1)
        outlet = Outlet(x=src.rx.pipe(slow))
        expr = outlet.param.x.rx() * 0  # No value-changed watcher fires on this.
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_tracks_a_bare_async_callable_ref(self):
        # `param.bind(...)` exercises `_awaiting_ref` directly, not
        # `_ref_inputs()`, and settles to the same value each time.
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.02)
            return 1

        src = rx(1)
        outlet = Outlet(x=1)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)

        outlet.x = param.bind(const, src)
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

        # A dependency change re-runs the already-bound callable; nothing
        # reassigns the ref itself, so this must not rely on `_watch_ref_change`.
        src.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_tracks_a_bare_async_callable_ref_passed_as_operation_arg(self):
        # `outlet.param.x` is passed directly as an operation argument, not
        # wrapped in `.rx()`, so this exercises `_ref_capable_params`'
        # operation-args branch, not `_fn_params`.
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.1)
            return 1

        async def add(a, b):
            await asyncio.sleep(0.01)
            return a + b

        src = rx(1)
        a = rx(1)
        outlet = Outlet(x=param.bind(const, src))
        expr = a.rx.pipe(add, outlet.param.x)
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        a.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_for_a_ref_inherited_from_prev(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.1)
            return 1

        async def add(a, b):
            await asyncio.sleep(0.01)
            return a + b

        src = rx(1)
        a = rx(1)
        b = rx(0)
        outlet = Outlet(x=param.bind(const, src))
        first = a.rx.pipe(lambda x, y: x + (y or 0), outlet.param.x)
        expr = first.rx.pipe(add, b)
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        b.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_registers_one_listener_for_an_inherited_ref(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.01)
            return 1

        src = rx(1)
        outlet = Outlet(x=param.bind(const, src))
        expr = rx(1).rx.pipe(lambda x, y: x + (y or 0), outlet.param.x)
        for _ in range(50):
            expr = expr + 1

        updating = expr.rx.updating()
        listeners = outlet._param__private.async_ref_settle_watchers['x']

        assert len(listeners) == 1
        await async_wait_until(lambda: not expr.rx.awaiting)
        src.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True
        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_for_a_ref_nested_in_a_bind_argument(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.1)
            return 1

        async def add(a, b):
            await asyncio.sleep(0.01)
            return a + b

        src = rx(1)
        a = rx(1)
        outlet = Outlet(x=param.bind(const, src))
        expr = a.rx.pipe(add, bind(lambda v: v, outlet.param.x))
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        a.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_for_a_ref_reached_through_param_depends(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        class Holder(param.Parameterized):
            o = param.Parameter()

            @param.depends('o.x')
            def get(self):
                return self.o.x

        async def const(value):
            await asyncio.sleep(0.1)
            return 1

        async def add(a, b):
            await asyncio.sleep(0.01)
            return a + b

        src = rx(1)
        a = rx(1)
        outlet = Outlet(x=param.bind(const, src))
        holder = Holder(o=outlet)
        expr = a.rx.pipe(add, holder.get)
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        a.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_for_a_ref_nested_in_an_operation_arg(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def const(value):
            await asyncio.sleep(0.1)
            return 1

        async def add(a, d):
            await asyncio.sleep(0.01)
            return a + d["k"][0]

        src = rx(1)
        a = rx(1)
        outlet = Outlet(x=param.bind(const, src))
        expr = a.rx.pipe(add, d={"k": [outlet.param.x]})
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        a.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        assert updating.rx.value is True

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert updating.rx.value is False

    async def test_reactive_awaiting_ref_unsticks_when_a_settle_listener_raises(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def double(value):
            await asyncio.sleep(0.05)
            return value * 2

        def boom(scheduled):
            if scheduled:
                raise ValueError("watcher failed")

        src = rx(1)
        outlet = Outlet(x=1)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        watcher = updating.rx.watch(boom)

        with pytest.raises(ValueError, match="watcher failed"):
            outlet.x = bind(double, src)

        await async_wait_until(lambda: not expr.rx.awaiting)
        assert outlet.x == 2
        assert 'x' in outlet._param__private.refs
        assert updating.rx.value is False

        updating.rx.unwatch(watcher)
        src.rx.value = 5
        await async_wait_until(lambda: outlet.x == 10)
        assert expr.rx.value == 11
        assert updating.rx.value is False

    async def test_reactive_updating_unsticks_when_an_override_is_removed_mid_flight(self):
        async def slow(value):
            await asyncio.sleep(0.02)
            return 1

        src = rx(1)
        b = rx(2) * rx(1)
        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        b.rx.overrides[0] = src.rx.pipe(slow)
        await async_wait_until(lambda: not b.rx.awaiting)

        src.rx.value = 2
        await async_wait_until(lambda: b.rx.awaiting)
        del b.rx.overrides[0]

        await async_wait_until(lambda: updating.rx.value is False)

    async def test_reactive_updating_true_for_a_node_re_entering_the_graph_already_settling(self):
        async def slow(value):
            await asyncio.sleep(0.1)
            return value

        src = rx(1)
        override = src.rx.pipe(slow)
        override.rx.watch(lambda v: None)
        b = rx(0) + rx(0)
        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        b.rx.overrides[0] = override
        await async_wait_until(lambda: not b.rx.awaiting)
        del b.rx.overrides[0]

        src.rx.value = 5
        await async_wait_until(lambda: override.rx.awaiting)
        assert updating.rx.value is False

        b.rx.overrides[0] = override
        assert updating.rx.value is True

    def test_reactive_updating_does_not_pin_a_cleared_override(self):
        b = rx(1) * rx(1)
        updating = b.rx.updating()
        b.rx.watch(lambda v: None)

        override = rx(99)
        ref = weakref.ref(override)
        b.rx.overrides[0] = override
        del b.rx.overrides[0]
        del override
        gc.collect()

        assert ref() is None
        assert updating.rx.value is False

    def test_reactive_updating_does_not_pin_a_replaced_ref(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        outlet = Outlet()
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)

        old_ref = rx(5)
        ref = weakref.ref(old_ref)
        outlet.x = old_ref
        del old_ref
        outlet.x = 3  # A plain value, not another ref.
        gc.collect()

        assert ref() is None
        assert updating.rx.value is False

class TestReaderBookkeeping:
    """Settle-watcher and upstream-walk bookkeeping."""

    def test_reactive_settle_watcher_does_not_pin_target(self):
        """A settle watcher is a weak ref, so it does not keep a dropped target alive."""
        class Target(param.Parameterized):
            object = param.Parameter(default=False)

        a = rx(1)
        target = Target()
        a._watch_settle_change(target)
        assert len(a._settle_watchers) == 1

        ref = weakref.ref(target)
        del target
        gc.collect()

        assert ref() is None
        assert a._settle_watchers == set()

    def test_reactive_upstream_walk_terminates_on_reused_input(self):
        a = rx(1)
        b = a + 1
        expr = b + a

        nodes = list(expr._upstream())

        assert expr.rx.value == 3
        assert len(nodes) == len({id(node) for node in nodes})
        assert any(node is expr for node in nodes)


class _Source(param.Parameterized):
    x = param.Number(default=1)

def _watcher_count(owner):
    watchers = owner._param__private.watchers
    return sum(len(lst) for what in watchers.values() for lst in what.values())

class TestDisposeAndLifecycle:
    """Unwatching, ``.rx.dispose()``, and node lifecycle."""

    def test_reactive_watch_returns_watcher_unwatch_stops_only_that_callback(self):
        calls = []
        other_calls = []
        a = rx(1)
        watcher = a.rx.watch(calls.append)
        a.rx.watch(other_calls.append)

        a.rx.value = 2
        assert calls == [2]
        assert other_calls == [2]

        a.rx.unwatch(watcher)
        a.rx.value = 3
        assert calls == [2]
        assert other_calls == [2, 3]

    def test_reactive_dispose_removes_watchers_on_every_upstream_source(self):
        source = _Source()
        a = rx(1)
        b = rx(source.param.x)
        c = a + b
        assert c.rx.value == 2

        a_owner = a._internal_params[0].owner
        assert _watcher_count(a_owner) > 0
        assert _watcher_count(source) > 0

        c.rx.dispose()

        assert _watcher_count(a_owner) == 0
        assert _watcher_count(source) == 0

    def test_reactive_dispose_cascades_when_sole_reader(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2

        b.rx.dispose()

        assert b._disposed
        assert a._disposed
        with pytest.raises(RuntimeError, match='disposed'):
            a.rx.value

    def test_reactive_dispose_raises_when_node_has_rx_reader(self):
        a = rx(1)
        b = a + 1
        c = b * 2
        assert c.rx.value == 4

        with pytest.raises(RuntimeError, match='still read'):
            b.rx.dispose()

        a.rx.value = 10
        assert c.rx.value == 22

    def test_reactive_dispose_leaves_ancestor_with_remaining_rx_reader_alone(self):
        a = rx(1)
        b = a + 1
        c = a + 2
        assert b.rx.value == 2
        assert c.rx.value == 3

        b.rx.dispose()

        a.rx.value = 10
        assert c.rx.value == 12

        c.rx.dispose()
        assert a._disposed

    def test_reactive_dispose_prunes_a_remaining_reader_dying_later(self):
        a = rx(1)
        b = a + 1
        c = a + 2
        b.rx.dispose()

        del c
        gc.collect()

        assert a._readers == []
        a.rx.dispose()

    def test_reactive_dispose_follows_operation_argument_route(self):
        a = rx(2)
        b = rx(3).rx.pipe(lambda x, y: x + y, y=a)
        assert b.rx.value == 5
        assert len(a._readers) == 1

        b.rx.dispose()
        assert a._disposed

    def test_reactive_dispose_raises_on_override_value_still_masking_an_input(self):
        placeholder = rx(1)
        override = rx(2)
        b = rx(10) * placeholder
        assert b.rx.value == 10

        b.rx.overrides[0] = override
        assert b.rx.value == 20

        with pytest.raises(RuntimeError, match='still read'):
            override.rx.dispose()

        del b.rx.overrides[0]
        override.rx.dispose()
        assert override._disposed

    def test_reactive_override_drops_the_masked_raw_input_reader_link(self):
        placeholder = rx(1)
        override = rx(2)
        b = rx(10) * placeholder
        assert b in set(placeholder.rx.downstream())

        b.rx.overrides[0] = override
        assert b not in set(placeholder.rx.downstream())
        placeholder.rx.dispose()
        assert placeholder._disposed

        b.rx.dispose()
        override.rx.dispose()

    def test_reactive_unmasking_restores_the_raw_input_reader_link(self):
        placeholder = rx(1)
        override = rx(2)
        b = rx(10) * placeholder
        b.rx.overrides[0] = override
        del b.rx.overrides[0]

        assert b in set(placeholder.rx.downstream())
        with pytest.raises(RuntimeError, match='still read'):
            placeholder.rx.dispose()

        override.rx.dispose()
        b.rx.dispose()
        placeholder.rx.dispose()

    def test_reactive_masking_a_shared_input_drops_the_right_readers_entry(self):
        # `a` has two readers before the mask, so `rx.__eq__`-vs-identity
        # confusion in a naive `list.remove()` would drop the wrong one.
        a = rx(1)
        other = rx(0).rx.pipe(lambda x, y: x + y, a)
        b = rx(0).rx.pipe(lambda x, y: x + y, a)
        assert {other, b} == set(a.rx.downstream()) - {a}

        b.rx.overrides[0] = rx(10)

        assert set(a.rx.downstream()) - {a} == {other}
        assert not (b._readers or ())
        b.rx.dispose()
        assert b._disposed

    def test_reactive_delitem_raises_before_mutating_if_masked_input_was_disposed(self):
        placeholder = rx(1)
        b = rx(10) + placeholder
        b.rx.overrides[0] = rx(2)
        placeholder.rx.dispose()

        with pytest.raises(RuntimeError, match='Cannot remove this override'):
            del b.rx.overrides[0]

        assert 0 in b.rx.overrides
        assert b.rx.value == 12

    def test_reactive_override_reader_links_follow_a_method_chain_clone(self):
        placeholder = rx('a')
        override = rx('z')
        b = rx('x').rx.pipe(lambda x, y: x + y, placeholder)
        b.rx.overrides[0] = override
        c = b.upper()
        assert c.rx.value == 'XZ'

        del b.rx.overrides[0]
        assert c.rx.value == 'XA'

        assert not (override._readers or ())
        override.rx.dispose()
        assert override._disposed

        assert b in set(placeholder.rx.downstream())
        with pytest.raises(RuntimeError, match='still read'):
            placeholder.rx.dispose()

    def test_reactive_override_does_not_relink_disposed_method_chain_clones(self):
        placeholder = rx('a')
        b = rx('x').rx.pipe(lambda x, y: x + y, placeholder)
        watcher = b.rx.watch(lambda v: None)
        clone = b.upper()
        clone.rx.value
        clone.rx.dispose()

        override = rx('z')
        b.rx.overrides[0] = override
        assert set(override.rx.downstream()) == {b}

        b.rx.overrides[0] = 'plain'
        assert not (override._readers or ())
        override.rx.dispose()

        del b.rx.overrides[0]
        assert set(placeholder.rx.downstream()) == {b}

        b.rx.unwatch(watcher)
        b.rx.dispose()
        assert placeholder._disposed

    def test_reactive_override_reader_links_follow_a_method_chain_clone_reversed(self):
        placeholder = rx('a')
        override = rx('z')
        b = rx('x').rx.pipe(lambda x, y: x + y, placeholder)
        accessor = b.upper
        accessor.rx.overrides[0] = override

        assert b.rx.value == 'xz'
        assert b in set(override.rx.downstream())
        assert b not in set(placeholder.rx.downstream())

    def test_reactive_override_reader_links_follow_a_cousin_clone(self):
        placeholder = rx('a')
        override = rx('z')
        b = rx('x').rx.pipe(lambda x, y: x + y, placeholder)
        accessor1 = b.upper
        accessor2 = b.lower
        accessor1.rx.overrides[0] = override

        assert accessor2 in set(override.rx.downstream())
        assert accessor2 not in set(placeholder.rx.downstream())

    def test_reactive_operation_siblings_is_not_quadratic_in_chain_length(self):
        head = rx(0)
        for _ in range(700):
            head = head + 1
        b = head.rx.pipe(lambda x, y: x + y, rx(1))

        start = time.perf_counter()
        b.rx.overrides[0] = rx(2)
        del b.rx.overrides[0]
        assert time.perf_counter() - start < 1.5

    def test_reactive_dispose_does_not_cascade_into_ref_still_held_by_owner(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        src = rx(1)
        outlet = Outlet(x=src)
        outlet.param.x.rx().rx.dispose()

        src.rx.value = 5
        assert outlet.x == 5

    def test_reactive_ref_reassignment_leaves_no_stale_reader_link(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        outlet = Outlet(x=rx(1))
        expr = outlet.param.x.rx()
        new = rx(2)
        outlet.x = new
        assert expr.rx.value == 2
        assert expr not in set(new.rx.downstream())

        expr.rx.dispose()
        new.rx.value = 3
        assert new.rx.value == 3

    def test_reactive_override_reader_link_is_per_occurrence(self):
        a = rx(1)
        b = rx(1).rx.pipe(lambda x, y, z: x + y + z, a, rx(0))
        b.rx.overrides[1] = a
        del b.rx.overrides[1]

        assert b in set(a.rx.downstream())
        with pytest.raises(RuntimeError, match='still read'):
            a.rx.dispose()

    def test_reactive_override_reader_link_survives_clearing_a_different_key(self):
        a = rx(1)
        b = rx(1).rx.pipe(lambda x, y, z: x + y + z, rx(0), rx(0))
        b.rx.overrides[0] = a
        b.rx.overrides[1] = a
        del b.rx.overrides[0]

        assert b in set(a.rx.downstream())
        with pytest.raises(RuntimeError, match='still read'):
            a.rx.dispose()

    def test_reactive_dispose_handles_input_reused_within_same_expression(self):
        """`a + a` gives `a` two readers; dispose must drop both to detach it."""
        a = rx(2)
        b = a + a
        assert b.rx.value == 4
        assert len(a._readers) == 2

        b.rx.dispose()
        assert a._disposed

    def test_reactive_dispose_is_idempotent(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2
        b.rx.dispose()
        b.rx.dispose()  # no-op
        assert a._disposed

    def test_reactive_dispose_raises_when_node_has_active_watch(self):
        a = rx(1)
        watcher = a.rx.watch(lambda v: None)

        with pytest.raises(RuntimeError, match='still read'):
            a.rx.dispose()
        assert not a._disposed

        a.rx.unwatch(watcher)
        a.rx.dispose()
        assert a._disposed

    def test_reactive_dispose_cascade_leaves_ancestor_with_active_watch_alone(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2

        got = []
        a.rx.watch(got.append)

        b.rx.dispose()
        assert not a._disposed

        a.rx.value = 5
        assert a.rx.value == 5
        assert got == [5]

    def test_reactive_dispose_cascade_false_leaves_inputs_alone(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2

        b.rx.dispose(cascade=False)

        assert b._disposed
        assert not a._disposed
        a.rx.value = 7
        assert a.rx.value == 7

    def test_reactive_disposed_node_raises_on_value_read(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2
        b.rx.dispose(cascade=False)

        with pytest.raises(RuntimeError, match='disposed'):
            b.rx.value

    def test_reactive_disposed_node_raises_on_attribute_access(self):
        a = rx('hello')
        a.rx.dispose(cascade=False)

        with pytest.raises(RuntimeError, match='disposed'):
            a.upper

    def test_reactive_disposed_node_raises_when_extended_with_new_operation(self):
        a = rx(1)
        b = a + 1
        assert b.rx.value == 2
        b.rx.dispose(cascade=False)

        with pytest.raises(RuntimeError, match='disposed'):
            b + 1

    def test_reactive_dispose_is_not_a_plain_attribute(self):
        class Wrapped:
            def __init__(self):
                self.disposed = False

            def dispose(self):
                self.disposed = True
                return 'disposed'

        wrapped = Wrapped()
        expr = rx(wrapped)

        result = expr.dispose()
        assert result.rx.value == 'disposed'
        assert wrapped.disposed is True

    def test_reactive_readers_pruned_on_gc(self):
        a = rx(1)
        b = a + 1
        assert len(a._readers) == 1

        ref = weakref.ref(b)
        del b
        gc.collect()

        assert ref() is None
        assert a._readers == []

    def test_reactive_dispose_cascade_needs_gc_for_transient_branch(self):
        """A branch's hidden clone sits in a reference cycle; only gc.collect() frees it."""
        a = rx(1)
        tmp = a + 5
        assert tmp.rx.value == 6
        assert len(a._readers) == 1

        del tmp
        assert len(a._readers) == 1

        gc.collect()
        assert a._readers == []

    def test_reactive_resolve_does_not_pin_ref_owner(self):
        """The resolver backing ``.rx.resolve()`` must not outlive the resolved expression."""
        owner = _Source()
        baseline = _watcher_count(owner)

        expr = rx([owner.param.x]).rx.resolve()
        assert expr.rx.value == [1]
        assert _watcher_count(owner) > baseline

        del expr
        gc.collect()
        assert _watcher_count(owner) == baseline

    def test_reactive_watch_on_bind_function_returns_watchers(self):
        a = rx(1)
        bound = bind(lambda v: v + 1, a)

        watchers = bound.rx.watch(lambda v: None)
        assert len(watchers) > 0

        bound.rx.unwatch(watchers)

    async def test_reactive_dispose_cancels_pending_async_task(self):
        async def double(value):
            await asyncio.sleep(0.05)
            return value * 2

        expr = rx(1).rx.pipe(double)
        expr.rx.value
        await asyncio.sleep(0)  # let the scheduled resolution start
        task = expr._current_task
        assert task is not None

        expr.rx.dispose(cascade=False)

        await asyncio.sleep(0.1)
        assert expr._current_ is param.Undefined

    async def test_reactive_dispose_clears_updating_for_an_async_ref(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def slow(value):
            await asyncio.sleep(0.05)
            return value

        src = rx(1)
        ref = src.rx.pipe(slow)
        outlet = Outlet(x=ref)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)

        src.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        ref.rx.dispose()

        assert updating.rx.value is False
        assert expr.rx.awaiting is False

        outlet.x = 10
        assert expr.rx.value == 11
        assert updating.rx.value is False

    async def test_reactive_dispose_finishes_when_an_updating_watcher_raises(self):
        class Outlet(param.Parameterized):
            x = param.Parameter(allow_refs=True)

        async def slow(value):
            await asyncio.sleep(0.05)
            return value

        src = rx(1)
        ref = src.rx.pipe(slow)
        outlet = Outlet(x=ref)
        expr = outlet.param.x.rx() + 1
        updating = expr.rx.updating()
        expr.rx.watch(lambda v: None)
        await async_wait_until(lambda: not expr.rx.awaiting)
        updating.rx.watch(lambda value: (_ for _ in ()).throw(ValueError) if not value else None)

        src.rx.value = 2
        await async_wait_until(lambda: expr.rx.awaiting)
        with pytest.raises(ValueError):
            ref.rx.dispose()

        await asyncio.sleep(0)
        task = ref._current_task
        assert task is None or task.cancelled()
        assert src._disposed

    def test_reactive_when_derived_node_is_not_tracked_as_reader_but_raises_on_stale_read(self):
        """``.rx.when()`` reads its source through a closure, invisible to `_readers`."""
        a = rx(1)
        b = a + 1
        gated = b.rx.when(a)
        assert gated.rx.value == 2
        assert b._readers is None

        b.rx.dispose()

        a.rx.value = 10
        with pytest.raises(RuntimeError, match='disposed'):
            gated.rx.value

class TestGeneratorsAndAsyncFunctions:
    """Async functions and (async) generators as operations or root objects."""

    @pytest.mark.parametrize('lazy', [False, True])
    async def test_reactive_async_func(self, lazy):
        async def async_func():
            await asyncio.sleep(0.02)
            return 2

        async_rx = rx(async_func, lazy=lazy) + 2
        assert async_rx.rx.value is param.Undefined
        await async_wait_until(lambda: async_rx.rx.value == 4)

    @pytest.mark.parametrize('lazy', [False, True])
    async def test_reactive_pipe_async_func(self, lazy):
        async def async_func(value):
            await asyncio.sleep(0.02)
            return value+2

        async_rx = rx(0, lazy=lazy).rx.pipe(async_func)
        assert async_rx.rx.value is param.Undefined
        await async_wait_until(lambda: async_rx.rx.value == 2)

    async def test_reactive_gen(self):
        def gen():
            yield 1
            time.sleep(0.05)
            yield 2

        rxgen = rx(gen)
        assert rxgen.rx.value is param.Undefined
        await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
        await async_wait_until(lambda: rxgen.rx.value == 2)

    async def test_reactive_lazy_gen(self):
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

    async def test_reactive_gen_pipe(self):
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

    async def test_reactive_lazy_gen_pipe(self):
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

    async def test_reactive_gen_with_dep(self):
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

    async def test_reactive_gen_pipe_with_dep(self):
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

    async def test_reactive_async_gen(self):
        async def gen():
            yield 1
            await asyncio.sleep(0.05)
            yield 2

        rxgen = rx(gen)
        assert rxgen.rx.value is param.Undefined
        await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
        await async_wait_until(lambda: rxgen.rx.value == 2)

    async def test_reactive_lazy_async_gen(self):
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

    async def test_reactive_async_gen_pipe(self):
        async def gen(value):
            yield value + 1
            await asyncio.sleep(0.05)
            yield value + 2

        rxgen = rx(0).rx.pipe(gen)
        assert rxgen.rx.value is param.Undefined
        await async_wait_until(lambda: rxgen.rx.value == 1, interval=10)
        await async_wait_until(lambda: rxgen.rx.value == 2)

    async def test_reactive_async_gen_with_dep(self):
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

    async def test_reactive_async_gen_pipe_with_dep(self):
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

class TestAsyncNotificationSemantics:
    """Notification and recomputation semantics while a node is awaiting or superseded."""

    async def test_reactive_async_watcher_not_notified_while_awaiting(self):
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

    async def test_reactive_async_downstream_watcher_not_notified_while_awaiting(self):
        irx = rx(1)
        downstream = irx.rx.pipe(mul_slowly) + 10
        items = []
        downstream.rx.watch(items.append)
        assert downstream.rx.value is param.Undefined
        await async_wait_until(lambda: items == [12])
        irx.rx.value = 2
        assert items == [12]
        await async_wait_until(lambda: items == [12, 14])

    async def test_reactive_async_downstream_not_computed_while_awaiting(self):
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

    async def test_reactive_async_rapid_updates_notify_once(self):
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

    def test_reactive_skip_value_does_not_notify_watcher(self):
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

    def test_reactive_skip_value_does_not_notify_later_watchers(self):
        """A skipped resolution must remain skipped for every watcher reread."""
        P = Parameters(integer=1)

        def skip_values(v):
            if v % 2 == 0:
                return Skip
            return v * 10

        i = rx(P.param.integer).rx.pipe(skip_values)
        first, second, third = [], [], []
        i.rx.watch(first.append)
        i.rx.watch(second.append)
        i.rx.watch(third.append)

        assert i.rx.value == 10
        P.integer = 2
        assert first == second == third == []

        P.integer = 3
        assert first == second == third == [30]

    async def test_reactive_async_ref_not_synced_while_awaiting(self):
        class Ref(param.Parameterized):
            value = param.Integer(default=0, allow_refs=True)

        irx = rx(1)
        p = Ref(value=irx.rx.pipe(mul_slowly))
        await async_wait_until(lambda: p.value == 2)
        irx.rx.value = 2
        assert p.value == 2
        await async_wait_until(lambda: p.value == 4)

    async def test_reactive_async_superseded_updates_not_computed(self):
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

    async def test_reactive_async_gen_superseded_updates_not_computed(self):
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

    async def test_reactive_async_running_task_is_cancelled(self):
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
    async def test_async_shared_rx_superseded_updates_computed_once(self, lazy):
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

class TestAsyncErrorPropagation:
    """Error propagation through async operations and generators."""

    async def test_reactive_async_error_raised_on_read(self):
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

    async def test_reactive_async_error_propagates_downstream(self):
        async def mul(value):
            await asyncio.sleep(0.01)
            raise RuntimeError('boom')

        irx = rx(1)
        downstream = irx.rx.pipe(mul) + 10
        downstream.rx.value
        await async_wait_until(lambda: downstream._prev._error_state is not None)
        with pytest.raises(RuntimeError, match='boom'):
            downstream.rx.value

    async def test_reactive_async_error_propagates_to_shared_branches(self):
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

    async def test_reactive_async_gen_error_ends_stream(self):
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

    async def test_reactive_gen_error_ends_stream(self):
        def gen(value):
            yield value
            raise RuntimeError('boom')

        async_rx = rx(1).rx.pipe(gen)
        async_rx.rx.value
        await async_wait_until(lambda: async_rx._error_state is not None)
        assert not async_rx._awaiting
        with pytest.raises(RuntimeError, match='boom'):
            async_rx.rx.value

    async def test_reactive_async_error_propagate_mode_no_unhandled_exception(self):
        async def boom(value):
            await asyncio.sleep(0.01)
            raise RuntimeError('boom')

        captured = []
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: captured.append(context))
        try:
            source = rx(1, error_mode='propagate')
            errored = source.rx.pipe(boom)
            errored.rx.watch(lambda v: None)
            errored.rx.value
            await async_wait_until(lambda: isinstance(errored.rx.value, param.ReactiveError))
            # Give the loop a chance to surface an unretrieved task exception, and
            # force a collection since that is what triggers Task.__del__.
            await asyncio.sleep(0.05)
            gc.collect()
            await asyncio.sleep(0)
        finally:
            loop.set_exception_handler(previous_handler)

        assert isinstance(errored.rx.value, param.ReactiveError)
        assert str(errored.rx.value) == 'boom'
        assert captured == []

    async def test_reactive_async_gen_error_propagate_mode_ends_stream(self):
        async def gen(value):
            for i in range(3):
                await asyncio.sleep(0.01)
                if i == 2:
                    raise RuntimeError('boom')
                yield value + i

        async_rx = rx(1, error_mode='propagate').rx.pipe(gen)
        async_rx.rx.value
        await async_wait_until(lambda: isinstance(async_rx.rx.value, param.ReactiveError))

        # The raise ends the generator's stream and resolves to a ReactiveError
        # value rather than poisoning _error_state.
        assert not async_rx._awaiting
        assert async_rx._error_state is None
        assert str(async_rx.rx.value) == 'boom'

    async def test_reactive_async_superseded_error_not_recorded(self):
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

class TestSharedBranching:
    """Branching a shared/cloned input."""

    async def test_async_shared_rx_branch_after_settling_resolves(self):
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

    async def test_async_shared_rx_branch_does_not_republish_previous_value(self):
        """An async branch must not notify later watchers with its prior value."""
        irx = rx(1)
        node = irx.rx.pipe(_pair)
        branch = node[0]
        first, second, third = [], [], []
        branch.rx.watch(first.append)
        branch.rx.watch(second.append)
        branch.rx.watch(third.append)

        branch.rx.value
        await async_wait_until(lambda: first == second == third == [2])

        irx.rx.value = 3
        await async_wait_until(lambda: first == [2, 6])
        await async_wait_until(lambda: second == [2, 6] and third == [2, 6])

    async def test_async_shared_rx_branch_while_awaiting_resolves(self):
        irx = rx(1)
        node = irx.rx.pipe(_pair)
        node.rx.value

        first = node[0]
        assert first.rx.value is param.Undefined
        await async_wait_until(lambda: first.rx.value == 2)

    def test_async_shared_rx_branch_does_not_resolve_on_creation(self):
        """Branching an async node must not compute to seed the mirror."""
        calls = []

        async def counted_pair(value):
            calls.append(value)
            await asyncio.sleep(0.02)
            return (value * 2, value * 3)

        node = rx(1).rx.pipe(counted_pair)
        first, second = node[0], node[1]
        assert calls == []

        # Reading drives the compute; with no running loop async_executor runs it
        # to completion, so both branches resolve off the one call.
        assert first.rx.value == 2
        assert second.rx.value == 3
        assert calls == [1]

    def test_shared_rx_branch_still_reuses_a_synchronous_input(self):
        """The synchronous mirror keeps its value, so branches share one compute."""
        calls = []

        def counted_pair(value):
            calls.append(value)
            return (value * 2, value * 3)

        node = rx(1).rx.pipe(counted_pair)
        first, second = node[0], node[1]
        assert (first.rx.value, second.rx.value) == (2, 3)
        assert calls == [1]

    async def test_reactive_pipe_through_sync_child_does_not_resolve_async_ancestor(self):
        calls = []

        async def async_body(value):
            calls.append(value)
            await asyncio.sleep(0.02)
            return value * 2

        def sync_fn(value):
            return value + 1

        a = rx(1).rx.pipe(async_body)
        b = a.rx.pipe(sync_fn)
        c = b.rx.pipe(lambda value: value * 10)

        assert calls == []
        assert a._dirty
        assert a._resolve_generation == 0
        assert a._current_task is None

        await async_wait_until(lambda: c.rx.value == 30)
        assert calls == [1]

    async def test_async_shared_rx_branch_before_resolving_resolves(self):
        irx = rx(1)
        node = irx.rx.pipe(_pair)
        first, second = node[0], node[1]

        assert first.rx.value is param.Undefined
        await async_wait_until(lambda: first.rx.value == 2)

        # The shared node has settled by now, so the sibling branch resolves on
        # its first read.
        assert second.rx.value == 3

    async def test_async_shared_rx_branch_computed_once(self):
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

    async def test_async_shared_rx_branch_notifies_watcher(self):
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

    async def test_async_gen_shared_rx_branch_resolves(self):
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

class TestMiscellaneous:
    """Root invalidation, watcher/parameter edge cases, and dunder/attribute errors."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_root_invalidation(self, lazy):
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

    def test_ensure_ref_can_update_by_watcher_of_same_parameter(self):
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

    def test_reactive_callback_resolve_accessor(self):
        pd = pytest.importorskip("pandas")
        df = pd.DataFrame({"name": ["Bill", "Bob"]})
        dfx = rx(df)
        out = dfx["name"].str._callback()
        assert type(out) is type(df["name"].str)
        assert out._name == df["name"].str._name

    def test_reactive_dunder_len_error(self):
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

    def test_reactive_dunder_bool(self):
        assert bool(rx([1, 2]))

    def test_reactive_set_value_attributeerror(self):
        x = rx(1)
        with pytest.raises(AttributeError, match="'rx' has no attribute 'value'"):
            x.value = 1

    def test_reactive_get_value_attributeerror(self):
        x = rx(1)
        with pytest.raises(AttributeError, match="'rx' object has no attribute 'value'"):
            x.value

    def test_reactive_lazy_get_value_attributeerror(self):
        x = rx(1, lazy=True)
        xv = x.value
        with pytest.raises(AttributeError, match="'int' object has no attribute 'value'"):
            xv.rx.value

class TestGarbageCollection:
    """Triggering once and garbage collection of derived nodes."""

    @pytest.mark.parametrize('lazy', [False, True])
    def test_shared_rx_only_triggers_once(self, lazy):
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
    async def test_async_shared_rx_only_triggers_once(self, lazy):
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

    def test_reactive_derived_node_is_garbage_collected(self):
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

class TestFunctionRootedNodes:
    """A node rooted on a function or bound method does not pin its owner."""

    @pytest.mark.parametrize('factory', [_rx_from_closure, _rx_from_bound_method])
    def test_reactive_function_rooted_node_does_not_pin_its_owner(self, factory):
        # weakref.finalize holds its arguments until the referent is collected, so
        # the invalidation cleanup must not own a path back to the node it cleans up.
        owner = factory()
        assert owner.expr.rx.value == 41

        ref = weakref.ref(owner)
        del owner
        gc.collect()
        assert ref() is None

    @pytest.mark.parametrize('factory', [_rx_from_closure, _rx_from_bound_method])
    def test_reactive_function_rooted_nodes_do_not_accumulate(self, factory):
        refs = []
        for _ in range(50):
            owner = factory()
            owner.expr.rx.value
            refs.append(weakref.ref(owner))
            del owner
        gc.collect()
        assert all(ref() is None for ref in refs)

class TestMeta:
    """``.rx.meta``."""

    def test_reactive_meta_starts_empty(self):
        n = rx(1)
        assert n.rx.meta == {}

    def test_reactive_meta_not_inherited_by_operation(self):
        n = rx(1)
        n.rx.meta['k'] = 'v'
        derived = n + 10
        assert derived.rx.meta == {}
        assert n.rx.meta == {'k': 'v'}

    def test_reactive_meta_not_inherited_by_attribute_access(self):
        n = rx('hello')
        n.rx.meta['k'] = 'v'
        derived = n.upper
        assert derived.rx.meta == {}

    def test_reactive_meta_not_inherited_by_prev_chain(self):
        n = rx(1)
        n.rx.meta['k'] = 'v'
        piped = n.rx.pipe(lambda x: x + 1)
        assert piped.rx.meta == {}
        assert n.rx.meta == {'k': 'v'}

    def test_reactive_meta_not_inherited_by_branch(self):
        n = rx((1, 2))
        n.rx.meta['k'] = 'v'
        first, second = n[0], n[1]
        assert first.rx.meta == {}
        assert second.rx.meta == {}
        assert n.rx.meta == {'k': 'v'}

    def test_reactive_meta_survives_own_invalidation_and_recompute(self):
        p = Parameters()
        n = rx(p.param.integer)
        n.rx.meta['k'] = 'v'
        assert n.rx.value == 7
        p.integer = 42
        assert n.rx.value == 42
        assert n.rx.meta == {'k': 'v'}

    def test_reactive_meta_mutation_does_not_dirty_or_notify(self):
        n = rx(1)
        n.rx.value  # resolve so the node starts out clean
        watched = []
        n.rx.watch(watched.append)
        generation = n._resolve_generation
        dirty = n._dirty

        n.rx.meta['k'] = 'v'

        assert n._dirty == dirty
        assert n._resolve_generation == generation
        assert watched == []

    def test_reactive_meta_not_available_on_parameter_rx(self):
        p = Parameters()
        with pytest.raises(AttributeError, match="only available on `rx` nodes"):
            p.param.integer.rx.meta

class TestCallback:
    """``_callback``, the display-consumer adapter Panel's ``ReactiveExpr`` uses."""

    def test_reactive_callback_sees_an_override(self):
        factor = rx(2)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=factor)
        cb = n._callback
        assert cb() == 20

        n.rx.overrides['factor'] = 1

        assert cb() == 10

    def test_reactive_callback_skips_while_a_masked_tick_leaves_the_value_unchanged(self):
        a = rx(2)
        b = rx(10) * a
        cb = b._callback
        assert cb() == 20

        b.rx.overrides[0] = 1
        assert cb() == 10

        a.rx.value = 5
        with pytest.raises(Skip):
            cb()
        a.rx.value = 9
        with pytest.raises(Skip):
            cb()

        del b.rx.overrides[0]
        assert cb() == 90

    async def test_reactive_callback_skips_while_still_resolving(self):
        async def slow(v):
            await asyncio.sleep(0.05)
            return v * 100

        source = rx(1)
        node = source.rx.pipe(slow)
        cb = node._callback
        node.rx.value
        await async_wait_until(lambda: node.rx.value == 100)
        assert cb() == 100

        source.rx.value = 2

        # Immediately after the input changed the node has not resolved yet, so
        # the callback must not report the previous, now-stale value.
        with pytest.raises(Skip):
            cb()

        await async_wait_until(lambda: node.rx.value == 200)
        assert cb() == 200

    def test_reactive_callback_recomputes_for_a_constant_expression(self):
        n = rx(1)
        cb = n._callback
        assert cb() == 1
        n.rx.value = 2
        assert cb() == 2

class TestOverrides:
    """``.rx.overrides``."""

    def test_reactive_overrides_start_empty(self):
        n = rx(1).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        assert dict(n.rx.overrides) == {}
        assert len(n.rx.overrides) == 0
        assert 'factor' not in n.rx.overrides

    def test_reactive_override_replaces_keyword_input(self):
        factor = rx(2)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=factor)
        assert n.rx.value == 20

        n.rx.overrides['factor'] = 1

        assert n.rx.value == 10
        assert dict(n.rx.overrides) == {'factor': 1}
        assert factor.rx.value == 2

    def test_reactive_override_replaces_positional_input(self):
        n = rx(1) + rx(2)
        assert n.rx.value == 3

        n.rx.overrides[0] = 10

        assert n.rx.value == 11

    def test_reactive_override_accepts_negative_position(self):
        n = rx(1).rx.pipe(lambda value, a, b: (value, a, b), 2, 3)
        n.rx.overrides[-1] = 30
        assert n.rx.value == (1, 2, 30)

    def test_reactive_override_masks_upstream_tick_until_unmasked(self):
        factor = rx(2)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=factor)
        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10

        factor.rx.value = 5

        assert n.rx.value == 10

        del n.rx.overrides['factor']

        assert n.rx.value == 50
        assert dict(n.rx.overrides) == {}

    def test_reactive_override_deleted_unmasks(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10

        del n.rx.overrides['factor']

        assert n.rx.value == 20

    def test_reactive_override_deleting_dormant_input_raises(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        with pytest.raises(KeyError):
            del n.rx.overrides['factor']
        assert n.rx.value == 20

    def test_reactive_override_with_none_masks_the_input(self):
        """``None`` is a value like any other, so it masks rather than unmasks."""
        n = rx(10).rx.pipe(lambda value, factor: (value, factor), factor=rx(2))
        assert n.rx.value == (10, 2)

        n.rx.overrides['factor'] = None

        assert n.rx.value == (10, None)
        assert dict(n.rx.overrides) == {'factor': None}
        assert n.rx.overrides['factor'] is None

        del n.rx.overrides['factor']

        assert n.rx.value == (10, 2)

    def test_reactive_override_reference_holding_none_keeps_masking(self):
        """An override that follows a reference masks even when it holds ``None``."""
        override = rx(5)
        n = rx(10).rx.pipe(lambda value, factor: (value, factor), factor=rx(2))
        n.rx.overrides['factor'] = override
        assert n.rx.value == (10, 5)

        override.rx.value = None

        assert n.rx.value == (10, None)

        override.rx.value = 3

        assert n.rx.value == (10, 3)

    def test_reactive_override_invalidates_downstream_nodes(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        derived = n + 1
        branched = (n / 2).rx.pipe(lambda value: [value])
        assert derived.rx.value == 21
        assert branched.rx.value == [10]

        n.rx.overrides['factor'] = 1

        assert derived.rx.value == 11
        assert branched.rx.value == [5]

    def test_reactive_override_masked_tick_does_not_recompute_the_node(self):
        """
        A masked input cannot change the value, so a tick of it must not invalidate
        the node.
        """
        calls = []
        source = rx(2)
        n = rx(10).rx.pipe(
            lambda value, factor: calls.append(factor) or value * factor, factor=source
        )
        assert n.rx.value == 20

        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10
        assert calls == [2, 1]

        source.rx.value = 5
        source.rx.value = 9

        assert n.rx.value == 10
        assert calls == [2, 1]
        assert not n._dirty

    def test_reactive_override_masked_tick_does_not_recompute_downstream(self):
        """
        A reader watches the parameters of its whole input graph, so a mask upstream
        of it has to keep its own operation from re-running too.
        """
        downstream_calls = []
        source = rx(2)
        n = rx(10) * source
        downstream = n.rx.pipe(
            lambda value: downstream_calls.append(value) or value * 10
        )
        assert downstream.rx.value == 200

        n.rx.overrides[0] = 1
        assert downstream.rx.value == 100
        assert downstream_calls == [20, 10]

        source.rx.value = 5
        source.rx.value = 9

        assert downstream.rx.value == 100
        assert downstream_calls == [20, 10]

    def test_reactive_override_unmasking_restores_invalidation(self):
        calls = []
        source = rx(2)
        n = rx(10).rx.pipe(
            lambda value, factor: calls.append(factor) or value * factor, factor=source
        )
        assert n.rx.value == 20

        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10
        source.rx.value = 5
        assert calls == [2, 1]

        del n.rx.overrides['factor']

        assert n.rx.value == 50
        source.rx.value = 9
        assert n.rx.value == 90

    def test_reactive_override_keeps_invalidating_through_an_unmasked_route(self):
        """A parameter feeding an unmasked input as well must still invalidate."""
        calls = []
        source = rx(2)
        n = rx(10).rx.pipe(
            lambda value, masked, live: calls.append((masked, live)) or value + masked + live,
            masked=source,
            live=source,
        )
        assert n.rx.value == 14

        n.rx.overrides['masked'] = 1

        assert n.rx.value == 13

        source.rx.value = 5

        assert n.rx.value == 16
        assert calls[-1] == (1, 5)

    def test_reactive_override_keeps_invalidating_through_the_pipeline_input(self):
        """A parameter feeding the input of the pipeline is never masked."""
        source = rx(2)
        n = (source + 0).rx.pipe(lambda value, factor: value * factor, factor=source)
        assert n.rx.value == 4

        n.rx.overrides['factor'] = 10

        assert n.rx.value == 20

        source.rx.value = 3

        assert n.rx.value == 30

    def test_reactive_override_masked_tick_still_updates_other_consumers(self):
        """Masking is node-local, so the input keeps serving everyone else."""
        source = rx(2)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=source)
        sibling = rx(100).rx.pipe(lambda value, factor: value + factor, factor=source)
        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10
        assert sibling.rx.value == 102

        source.rx.value = 5

        assert n.rx.value == 10
        assert sibling.rx.value == 105

    def test_reactive_override_reference_tick_still_invalidates(self):
        """The override's own reference is live, unlike the input it masks."""
        calls = []
        source = rx(2)
        override = rx(1)
        n = rx(10).rx.pipe(
            lambda value, factor: calls.append(factor) or value * factor, factor=source
        )
        n.rx.overrides['factor'] = override
        assert n.rx.value == 10

        override.rx.value = 3

        assert n.rx.value == 30
        assert calls[-1] == 3

    def test_reactive_override_notifies_watcher_on_node_and_downstream(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        derived = n + 1
        on_node, on_derived = [], []
        n.rx.watch(on_node.append)
        derived.rx.watch(on_derived.append)

        n.rx.overrides['factor'] = 1

        assert on_node == [10]
        assert on_derived == [11]

    def test_reactive_override_notifies_bound_consumer(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        values = []
        bind(values.append, n, watch=True)

        n.rx.overrides['factor'] = 1

        assert values == [10]

    def test_reactive_override_notifies_consumer_reading_node_as_reference(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        consumer = rx(1).rx.pipe(lambda value, other: value + other, other=n)
        assert consumer.rx.value == 21

        n.rx.overrides['factor'] = 1

        assert consumer.rx.value == 11

    def test_reactive_override_leaves_other_consumer_of_same_input_alone(self):
        factor = rx(2)
        calls = []

        def other(value, factor):
            calls.append(factor)
            return value + factor

        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=factor)
        sibling = rx(100).rx.pipe(other, factor=factor)
        watched = []
        sibling.rx.watch(watched.append)
        assert n.rx.value == 20
        assert sibling.rx.value == 102
        assert calls == [2]

        n.rx.overrides['factor'] = 1

        assert n.rx.value == 10
        assert watched == []
        assert sibling.rx.value == 102
        assert calls == [2]

    def test_reactive_override_masks_failed_input(self):
        failing = rx(0, error_mode='propagate').rx.pipe(lambda divisor: 1 / divisor)
        n = rx(7).rx.pipe(lambda value, extra: value + extra, extra=failing)
        assert isinstance(n.rx.value, param.ReactiveError)

        n.rx.overrides['extra'] = 5

        assert n.rx.value == 12

        del n.rx.overrides['extra']

        assert isinstance(n.rx.value, param.ReactiveError)

    def test_reactive_override_masks_skipped_input(self):
        def skipping(value):
            raise Skip

        skipped = rx(1).rx.pipe(skipping)
        n = rx(7).rx.pipe(lambda value, extra: value + extra, extra=skipped)
        assert n.rx.value is None

        n.rx.overrides['extra'] = 2

        assert n.rx.value == 9

    async def test_reactive_override_masks_unresolved_async_input(self):
        async def slow(value):
            await asyncio.sleep(0.05)
            return value * 2

        pending = rx(3).rx.pipe(slow)
        n = rx(7).rx.pipe(lambda value, extra: value + extra, extra=pending)
        assert n.rx.value is None

        n.rx.overrides['extra'] = 5

        assert n.rx.value == 12

        del n.rx.overrides['extra']

        await async_wait_until(lambda: n.rx.value == 13)

    def test_reactive_override_does_not_evaluate_the_masked_input(self):
        calls = []

        def counted(value):
            calls.append(value)
            return value

        source = rx(2)
        masked = source.rx.pipe(counted)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=masked)
        assert n.rx.value == 20
        assert calls == [2]

        n.rx.overrides['factor'] = 1
        assert n.rx.value == 10

        source.rx.value = 3

        assert n.rx.value == 10
        assert calls == [2]

    def test_reactive_override_applies_to_branches(self):
        n = rx([1, 2]).rx.pipe(
            lambda value, factor: [v * factor for v in value], factor=rx(2)
        )
        first, second = n
        assert (first.rx.value, second.rx.value) == (2, 4)

        n.rx.overrides['factor'] = 10

        assert (first.rx.value, second.rx.value) == (10, 20)

    def test_reactive_overrides_not_inherited_by_derived_node(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = 1
        derived = n + 1

        assert dict(derived.rx.overrides) == {}
        with pytest.raises(KeyError, match="not an input of this node"):
            derived.rx.overrides['factor'] = 2

    def test_reactive_overrides_not_inherited_by_branch(self):
        n = rx([1, 2]).rx.pipe(
            lambda value, factor: [v * factor for v in value], factor=rx(2)
        )
        n.rx.overrides['factor'] = 10
        first = n[0]

        assert dict(first.rx.overrides) == {}
        with pytest.raises(KeyError, match="not an input of this node"):
            first.rx.overrides['factor'] = 2

    def test_reactive_overrides_rejects_unknown_input(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, 5, factor=rx(2))
        with pytest.raises(KeyError, match="positional indices 0-0 and keywords 'factor'"):
            n.rx.overrides['unknown'] = 1
        with pytest.raises(KeyError, match="not an input of this node"):
            n.rx.overrides[1] = 1
        with pytest.raises(KeyError):
            n.rx.overrides['factor']

    def test_reactive_overrides_rejects_unsupported_key(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        with pytest.raises(TypeError, match="addressed by keyword name or positional index"):
            n.rx.overrides[object()] = 1

    def test_reactive_overrides_mapping_interface(self):
        n = rx(10).rx.pipe(lambda value, a, factor: value, 1, factor=rx(2))
        overrides = n.rx.overrides
        assert repr(overrides) == 'overrides({})'
        assert overrides.get('factor') is None

        overrides.update({'factor': 3, 0: 4})

        assert dict(overrides) == {'factor': 3, 0: 4}
        assert list(overrides) == ['factor', 0]
        assert len(overrides) == 2
        assert repr(overrides) == "overrides({'factor': 3, 0: 4})"

        overrides.clear()

        assert dict(n.rx.overrides) == {}

    def test_reactive_overrides_not_available_on_input_node(self):
        with pytest.raises(AttributeError, match="applies an operation to inputs"):
            rx(1).rx.overrides

    def test_reactive_overrides_not_available_on_parameter_rx(self):
        p = Parameters()
        with pytest.raises(AttributeError, match="only available on `rx` nodes"):
            p.param.integer.rx.overrides

    def test_reactive_node_without_overrides_allocates_no_channel(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=2)
        assert n.rx.value == 20
        assert n._override_channel is None
        assert n._operation.get('overrides') is None

    def test_reactive_override_propagates_without_any_parameters(self):
        # Nothing else can invalidate a node that depends on no parameter.
        n = rx(bind(lambda: 10)).rx.pipe(lambda value, factor: value * factor, factor=2)
        derived = n + 1
        assert (n.rx.value, derived.rx.value) == (20, 21)

        n.rx.overrides['factor'] = 1

        assert (n.rx.value, derived.rx.value) == (10, 11)

    @pytest.mark.parametrize(('ctx', 'expected'), [
        (contextlib.nullcontext, [1100, 3000]),
        (batch, [3000]),
    ], ids=['without_batch', 'inside_batch'])
    def test_reactive_override_sheet_across_nodes(self, ctx, expected):
        """
        ``node1`` and ``node2`` have distinct override channels, so setting one
        then the other, without ``batch()``, delivers a value crossing the
        first with the second's stale input; ``batch()`` avoids it.
        """
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        node1 = rx(lambda x: x * 10)(x=a.param.x)
        node2 = rx(lambda y: y * 10)(y=b.param.y)
        combined = rx(lambda n1, n2: n1 + n2)(n1=node1, n2=node2)
        calls = []
        combined.rx.watch(calls.append)
        calls.clear()

        with ctx():
            node1.rx.overrides['x'] = 100
            node2.rx.overrides['y'] = 200

        assert calls == expected

class TestUpstreamDownstream:
    """``_upstream()`` and ``_downstream()`` graph walking."""

    def test_reactive_readers_do_not_keep_nodes_alive(self):
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        refs = []
        for _ in range(3):
            reader = n + 1
            refs.append(weakref.ref(reader))
            del reader
        gc.collect()

        assert all(ref() is None for ref in refs)
        assert not n._readers

        # A surviving reader is still invalidated.
        reader = n + 1
        assert reader.rx.value == 21
        n.rx.overrides['factor'] = 1
        assert reader.rx.value == 11

    def test_reactive_upstream_sees_prev_shared_and_operation_argument(self):
        a = rx(1)
        branch = rx((1, 2))
        first, second = branch[0], branch[1]
        piped = rx(2).rx.pipe(lambda x, y: x + y, y=a)

        upstream = set(piped.rx.upstream())
        assert a in upstream
        assert branch not in upstream  # Unrelated graph.

        branch_upstream = set(first.rx.upstream())
        assert branch in branch_upstream
        assert second not in branch_upstream

    def test_reactive_upstream_empty_for_an_input_node(self):
        a = rx(1)
        assert list(a.rx.upstream()) == []

    def test_reactive_upstream_empty_on_non_rx_namespace(self):
        p = Parameters()
        assert list(p.param.integer.rx.upstream()) == []

    def test_reactive_downstream_sees_reader_through_prev(self):
        a = rx(1)
        derived = a + 1
        assert derived in set(a.rx.downstream())

    def test_reactive_downstream_sees_reader_through_shared_branch(self):
        branch = rx((1, 2))
        first, second = branch[0], branch[1]
        downstream = set(branch.rx.downstream())
        assert first in downstream
        assert second in downstream

    def test_reactive_downstream_sees_reader_through_operation_argument(self):
        # This is the route `_upstream()` already walked that `_readers` did not
        # register a reader for until the operation-argument route was added to
        # `_direct_inputs()`.
        a = rx(1)
        piped = rx(2).rx.pipe(lambda x, y: x + y, y=a)
        assert piped in set(a.rx.downstream())

    def test_reactive_downstream_does_not_see_an_unconsumed_node(self):
        a = rx(1)
        rx(2)  # Never reads from `a`.
        assert list(a.rx.downstream()) == []

    def test_reactive_downstream_transitively_walks_further_nodes(self):
        a = rx(1)
        b = a + 1
        c = b * 2
        downstream = set(a.rx.downstream())
        assert b in downstream
        assert c in downstream

    def test_reactive_downstream_drops_a_collected_node(self):
        a = rx(1)
        derived = a + 1
        assert derived in set(a.rx.downstream())

        del derived
        gc.collect()

        assert list(a.rx.downstream()) == []

    def test_reactive_downstream_excludes_self(self):
        a = rx(1)
        b = a + 1
        assert a not in set(a.rx.downstream())
        assert a not in set(b.rx.downstream())

    def test_reactive_downstream_empty_on_non_rx_namespace(self):
        p = Parameters()
        assert list(p.param.integer.rx.downstream()) == []

    def test_reactive_upstream_and_downstream_exclude_bind_only_dependency(self):
        # `.rx.upstream()`/`.rx.downstream()` only walk pipeline edges (`_prev`,
        # `_shared`, an rx operation argument). A plain `rx(bind(...))` reads its
        # dependency through the bind/depends machinery instead, with no
        # `_operation` of its own, so that route is not covered. Documenting the
        # current scope rather than asserting it is desirable; broadening this is
        # tracked separately.
        a = rx(1)
        b = rx(bind(lambda v: v + 1, a))
        assert a not in set(b.rx.upstream())
        assert b not in set(a.rx.downstream())

    def test_reactive_upstream_and_downstream_exclude_when_gate(self):
        src = rx(1)
        gate = rx(True)
        gated = src.rx.when(gate)
        assert src not in set(gated.rx.upstream())
        assert gated not in set(src.rx.downstream())

    def test_reactive_upstream_and_downstream_exclude_where_branches(self):
        cond = rx(True)
        x, y = rx('a'), rx('b')
        w = cond.rx.where(x, y)
        assert cond not in set(w.rx.upstream())
        assert w not in set(cond.rx.downstream())

    def test_reactive_upstream_and_downstream_include_override_value(self):
        fx = rx(2)
        override = rx(3)
        value = rx(100).rx.pipe(lambda price, fx: price * fx, fx=fx)
        value.rx.overrides['fx'] = override

        upstream = set(value.rx.upstream())
        assert override in upstream
        assert fx not in upstream
        assert value in set(override.rx.downstream())

        del value.rx.overrides['fx']
        upstream = set(value.rx.upstream())
        assert override not in upstream
        assert fx in upstream
        assert value not in set(override.rx.downstream())

class TestHashing:
    """``rx`` is hashable and usable as a dict key / set member."""

    def test_reactive_rx_is_hashable(self):
        a = rx(1)
        assert hash(a) == hash(a)
        assert hash(a) == object.__hash__(a)

    def test_reactive_rx_hash_stable_across_value_assignment(self):
        a = rx(1)
        before = hash(a)
        a.rx.value = 2
        assert hash(a) == before

    def test_reactive_rx_hash_distinguishes_distinct_nodes(self):
        a, b = rx(1), rx(1)
        assert hash(a) != hash(b) or a is b

    def test_reactive_rx_usable_as_dict_key_and_set_member(self):
        a, b = rx(1), rx(2)
        mapping = {a: 'a', b: 'b'}
        assert mapping[a] == 'a'
        assert mapping[b] == 'b'
        assert {a, b, a} == {a, b}

class TestOverridesFollowingReferences:
    """``.rx.overrides`` values that are themselves references."""

    def test_reactive_override_follows_a_parameter(self):
        p = Parameters()
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        reader = n + 1
        watched = []
        reader.rx.watch(watched.append)
        assert n.rx.value == 20

        n.rx.overrides['factor'] = p.param.integer

        assert n.rx.value == 70
        assert watched == [71]

        p.integer = 3

        assert n.rx.value == 30
        assert watched == [71, 31]
        # The mapping reports what it was set to, not the resolved value.
        assert n.rx.overrides['factor'] is p.param.integer

    def test_reactive_override_follows_an_expression(self):
        other = rx(7)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = other
        assert n.rx.value == 70

        other.rx.value = 8

        assert n.rx.value == 80

    def test_reactive_override_follows_a_bound_function(self):
        p = Parameters()
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = bind(lambda integer: integer + 1, p.param.integer)
        assert n.rx.value == 80

        p.integer = 1

        assert n.rx.value == 20

    def test_reactive_override_follows_nested_references(self):
        p = Parameters()
        n = rx(1).rx.pipe(lambda value, pair: (value, pair), pair=(0, 0))
        n.rx.overrides['pair'] = [p.param.integer, 2]
        assert n.rx.value == (1, [7, 2])

        p.integer = 9

        assert n.rx.value == (1, [9, 2])

    def test_reactive_override_parameter_resolving_to_none_keeps_masking(self):
        class Nullable(param.Parameterized):
            value = param.Number(default=3, allow_None=True)

        p = Nullable()
        n = rx(10).rx.pipe(lambda value, factor: (value, factor), factor=rx(2))
        n.rx.overrides['factor'] = p.param.value
        assert n.rx.value == (10, 3)

        p.value = None

        assert n.rx.value == (10, None)

        p.value = 4

        assert n.rx.value == (10, 4)

    async def test_reactive_override_masks_while_its_reference_is_unresolved(self):
        async def slow(value):
            await asyncio.sleep(0.05)
            return value * 100

        pending = rx(3).rx.pipe(slow)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        assert n.rx.value == 20

        n.rx.overrides['factor'] = pending

        # The override is the input now, so an unresolved one skips.
        assert n.rx.value == 20
        assert n._skipped

        await async_wait_until(lambda: n.rx.value == 3000)

    async def test_reactive_override_follows_an_async_reference(self):
        async def slow(value):
            await asyncio.sleep(0.05)
            return value * 100

        source = rx(3)
        pending = source.rx.pipe(slow)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = pending

        await async_wait_until(lambda: n.rx.value == 3000)

        source.rx.value = 4

        await async_wait_until(lambda: n.rx.value == 4000)

    def test_reactive_override_propagates_a_failed_reference(self):
        broken = rx(0, error_mode='propagate').rx.pipe(lambda divisor: 1 / divisor)
        n = rx(7).rx.pipe(lambda value, extra: value + extra, extra=1)
        assert n.rx.value == 8

        n.rx.overrides['extra'] = broken

        assert isinstance(n.rx.value, param.ReactiveError)

        n.rx.overrides['extra'] = 5

        assert n.rx.value == 12

    def test_reactive_override_stops_following_a_replaced_reference(self):
        p = Parameters()
        other = Parameters(integer=100)
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = p.param.integer
        assert n.rx.value == 70

        n.rx.overrides['factor'] = other.param.integer
        assert n.rx.value == 1000

        p.integer = 3

        assert n.rx.value == 1000

    def test_reactive_override_stops_following_an_unmasked_reference(self):
        p = Parameters()
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = p.param.integer
        assert n.rx.value == 70

        del n.rx.overrides['factor']
        assert n.rx.value == 20

        watched = []
        n.rx.watch(watched.append)
        p.integer = 3

        assert n.rx.value == 20
        assert watched == []
        assert not n._operation['override_watchers']

    def test_reactive_override_reference_does_not_keep_the_node_alive(self):
        p = Parameters()
        n = rx(10).rx.pipe(lambda value, factor: value * factor, factor=rx(2))
        n.rx.overrides['factor'] = p.param.integer
        assert n.rx.value == 70
        ref = weakref.ref(n)

        del n
        gc.collect()

        assert ref() is None
        assert not p.param.watchers.get('integer', {}).get('value', [])

class TestCurrentNode:
    """``current_node()``."""

    def test_current_node_is_none_outside_operation_body(self):
        assert current_node() is None

    def test_current_node_is_none_for_a_body_never_invoked(self):
        # Simply constructing/piping does not evaluate the body.
        def kernel(value):
            return value  # pragma: no cover

        rx(1).rx.pipe(kernel)
        assert current_node() is None

    def test_current_node_returns_the_node_in_a_sync_operation_body(self):
        seen = []

        def kernel(value):
            seen.append(current_node())
            return value

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value

        assert len(seen) == 1 and seen[0] is expr
        assert current_node() is None

    def test_current_node_lets_a_body_write_its_own_meta(self):
        def kernel(value):
            node = current_node()
            node.rx.meta['trace'] = {'value': value}
            return value * 2

        expr = rx(1).rx.pipe(kernel)

        assert expr.rx.value == 2
        assert expr.rx.meta == {'trace': {'value': 1}}

    def test_current_node_meta_not_inherited_by_derived_node(self):
        def kernel(value):
            current_node().rx.meta['trace'] = {'value': value}
            return value

        expr = rx(1).rx.pipe(kernel)
        derived = expr + 1

        assert derived.rx.value == 2
        assert expr.rx.meta == {'trace': {'value': 1}}
        assert derived.rx.meta == {}

    def test_current_node_meta_overwritten_on_recompute(self):
        p = Parameters()

        def kernel(value):
            current_node().rx.meta['trace'] = {'value': value}
            return value

        expr = rx(p.param.integer).rx.pipe(kernel)
        assert expr.rx.value == 7
        assert expr.rx.meta == {'trace': {'value': 7}}

        p.integer = 42
        assert expr.rx.value == 42
        assert expr.rx.meta == {'trace': {'value': 42}}

    def test_current_node_body_that_does_not_use_it_is_unaffected(self):
        def kernel(value):
            return value + 1

        expr = rx(1).rx.pipe(kernel)

        assert expr.rx.value == 2
        assert expr.rx.meta == {}

    def test_current_node_nested_resolution_restores_outer_node(self):
        inner_seen = []

        def inner_kernel(value):
            inner_seen.append(current_node())
            return value

        inner = rx(5).rx.pipe(inner_kernel)

        outer_seen = []

        def kernel(value):
            outer_seen.append(current_node())
            inner.rx.value  # resolves a second, unrelated node
            outer_seen.append(current_node())
            return value

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value

        assert len(outer_seen) == 2 and outer_seen[0] is expr and outer_seen[1] is expr
        assert len(inner_seen) == 1 and inner_seen[0] is inner

    def test_current_node_does_not_see_argument_bodies(self):
        """
        A bound function used as a plain (non-``rx``) argument is not itself an
        operation body of any node, so it sees no current node, before or after
        this fix moved the var's scope to exclude argument resolution.
        """
        seen = []

        def arg_fn(value):
            seen.append(current_node())
            return value

        def kernel(value, extra):
            return value

        p = Parameters()
        expr = rx(1).rx.pipe(kernel, bind(arg_fn, p.param.integer))
        expr.rx.value

        assert len(seen) == 1 and seen[0] is None

    def test_current_node_nested_rx_argument_sees_its_own_node(self):
        inner_seen = []

        def inner_kernel(value):
            inner_seen.append(current_node())
            return value

        inner = rx(5).rx.pipe(inner_kernel)

        outer_seen = []

        def kernel(value, extra):
            outer_seen.append(current_node())
            return value

        expr = rx(1).rx.pipe(kernel, inner)
        expr.rx.value

        assert len(inner_seen) == 1 and inner_seen[0] is inner
        assert len(outer_seen) == 1 and outer_seen[0] is expr

    def test_current_node_reset_after_sync_exception(self):
        def kernel(value):
            raise ValueError('boom')

        expr = rx(1).rx.pipe(kernel)
        with pytest.raises(ValueError, match='boom'):
            expr.rx.value

        assert current_node() is None

    def test_current_node_root_bind_function(self):
        p = Parameters()
        seen = []

        def g(value):
            seen.append(current_node())
            return value

        expr = rx(bind(g, p.param.integer))

        assert expr.rx.value == 7
        assert len(seen) == 1 and seen[0] is expr

    async def test_current_node_returns_the_node_in_an_async_operation_body(self):
        seen = []

        async def kernel(value):
            await asyncio.sleep(0.01)
            seen.append(current_node())
            return value * 2

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 1 and seen[0] is expr

    async def test_current_node_returns_the_node_across_a_sync_generator_body(self):
        seen = []

        def kernel(value):
            seen.append(current_node())
            yield value
            time.sleep(0.02)
            seen.append(current_node())
            yield value * 2

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 2 and seen[0] is expr and seen[1] is expr

    async def test_current_node_returns_the_node_across_an_async_generator_body(self):
        seen = []

        async def kernel(value):
            seen.append(current_node())
            yield value
            await asyncio.sleep(0.02)
            seen.append(current_node())
            yield value * 2

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 2 and seen[0] is expr and seen[1] is expr

    async def test_current_node_isolated_between_concurrent_async_nodes(self):
        seen = {}

        async def kernel(label, value):
            await asyncio.sleep(0.02 if label == 'A' else 0.01)
            seen[label] = current_node()
            await asyncio.sleep(0.02)
            assert current_node() is seen[label]
            return value

        async def kernel_a(value):
            return await kernel('A', value)

        async def kernel_b(value):
            return await kernel('B', value)

        expr_a = rx(1).rx.pipe(kernel_a)
        expr_b = rx(2).rx.pipe(kernel_b)
        expr_a.rx.value
        expr_b.rx.value

        await async_wait_until(lambda: 'A' in seen and 'B' in seen)
        await asyncio.sleep(0.03)

        assert seen['A'] is expr_a
        assert seen['B'] is expr_b

    async def test_current_node_visible_inside_asyncio_to_thread(self):
        seen = []

        def blocking_kernel(value):
            seen.append(current_node())
            return value * 2

        async def kernel(value):
            return await asyncio.to_thread(blocking_kernel, value)

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 1 and seen[0] is expr

    async def test_current_node_not_leaked_into_watcher_of_async_node(self):
        """
        ``trigger.param.trigger('value')`` runs on the same asyncio Task as the
        operation body, so the var must be reset before it fires, not just before
        the Task ends, or a watcher fired synchronously from settlement sees the
        async node as if it were still inside that node's own body.
        """
        async def kernel(value):
            await asyncio.sleep(0.01)
            return value * 2

        expr = rx(1).rx.pipe(kernel)
        seen = []
        expr.rx.watch(lambda event: seen.append(current_node()))

        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 1 and seen[0] is None

    async def test_current_node_not_leaked_into_watcher_of_async_generator_node(self):
        async def kernel(value):
            yield value
            await asyncio.sleep(0.01)
            yield value * 2

        expr = rx(1).rx.pipe(kernel)
        seen = []
        expr.rx.watch(lambda event: seen.append(current_node()))

        expr.rx.value
        await async_wait_until(lambda: expr.rx.value == 2)

        assert len(seen) == 2 and seen[0] is None and seen[1] is None

    async def test_current_node_reset_after_async_exception(self):
        async def kernel(value):
            await asyncio.sleep(0.01)
            raise ValueError('boom')

        expr = rx(1).rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: expr._error_state is not None)

        assert current_node() is None

    async def test_current_node_reset_on_propagated_async_error(self):
        async def kernel(value):
            await asyncio.sleep(0.01)
            raise ValueError('boom')

        expr = rx(1, error_mode='propagate').rx.pipe(kernel)
        expr.rx.value
        await async_wait_until(lambda: isinstance(expr.rx.value, param.ReactiveError))

        assert current_node() is None



@pytest.fixture
def clean_accessors():
    before = dict(rx._accessors)
    try:
        yield
    finally:
        rx._accessors.clear()
        rx._accessors.update(before)

class TestRegisterAccessorLaziness:
    """Laziness of ``rx.register_accessor()``."""

    def test_reactive_accessor_name_not_turned_into_getattr_operation(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx('a string with a my_accessor-like attribute? no.')
        assert n.my_accessor == 'accessor-value'

    async def test_reactive_accessor_name_not_turned_into_getattr_operation_when_undefined(self, clean_accessors):
        async def body(x):
            await asyncio.sleep(0.05)
            return x * 2

        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx(0).rx.pipe(body)
        assert n._current is param.Undefined
        assert n.my_accessor == 'accessor-value'

        await async_wait_until(lambda: n.rx.value == 0)

    def test_reactive_dir_lists_registered_accessor_names(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: node, predicate=lambda value: isinstance(value, int))

        n = rx(1)
        assert 'my_accessor' in dir(n)
        # Still listed once it has actually been instantiated.
        n.my_accessor
        assert 'my_accessor' in dir(n)

    def test_reactive_dir_does_not_list_accessor_when_predicate_fails(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: node, predicate=lambda value: isinstance(value, str))

        n = rx(1)
        assert 'my_accessor' not in dir(n)

    def test_reactive_register_accessor_predicate_not_evaluated_at_construction(self, clean_accessors):
        predicate_calls = []

        def predicate(value):
            predicate_calls.append(value)
            return False

        rx.register_accessor('my_accessor', lambda node: node, predicate=predicate)

        rx(1) + 1

        assert predicate_calls == []

    async def test_reactive_register_accessor_does_not_resolve_async_node_at_construction(self, clean_accessors):
        calls = []

        async def body(x):
            calls.append(x)
            await asyncio.sleep(0.01)
            return x * 2

        rx.register_accessor('my_accessor', lambda node: node, predicate=lambda value: False)

        rx(1).rx.pipe(body)
        await asyncio.sleep(0.1)

        assert calls == []

    async def test_reactive_register_accessor_does_not_resolve_async_ancestor_through_sync_child(self, clean_accessors):
        calls = []

        async def body(x):
            calls.append(x)
            await asyncio.sleep(0.01)
            return x * 2

        def sync_fn(x):
            return x + 1

        rx.register_accessor('my_accessor', lambda node: node, predicate=lambda value: False)

        a = rx(1).rx.pipe(body)
        b = a.rx.pipe(sync_fn)
        b.rx.pipe(lambda value: value * 10)
        await asyncio.sleep(0.1)

        assert calls == []

    def test_reactive_accessor_installed_lazily_on_first_access(self, clean_accessors):
        installed_for = []

        def accessor(node):
            installed_for.append(node)
            return 'accessor-value'

        rx.register_accessor('my_accessor', accessor, predicate=lambda value: isinstance(value, int))

        n = rx(1)
        assert installed_for == []

        assert n.my_accessor == 'accessor-value'
        assert installed_for == [n]

        # Cached on the instance: accessing again does not re-instantiate.
        assert n.my_accessor == 'accessor-value'
        assert installed_for == [n]

    def test_reactive_accessor_installed_when_value_later_matches_predicate(self, clean_accessors):
        rx.register_accessor(
            'my_accessor', lambda node: 'matched', predicate=lambda value: isinstance(value, str)
        )

        n = rx(1)
        with pytest.raises(AttributeError):
            n.my_accessor

        n.rx.value = 'a string now'
        assert n.my_accessor == 'matched'

    def test_reactive_setattr_on_registered_accessor_name_raises(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx(1)
        assert n.my_accessor == 'accessor-value'

        with pytest.raises(AttributeError, match="'my_accessor' is a registered accessor"):
            n.my_accessor = 'oops'

        # The accessor is not shadowed by the failed assignment.
        assert n.my_accessor == 'accessor-value'

    def test_reactive_setattr_on_registered_accessor_name_raises_before_first_access(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx(1)
        with pytest.raises(AttributeError, match="'my_accessor' is a registered accessor"):
            n.my_accessor = 'oops'

        assert n.my_accessor == 'accessor-value'

    def test_reactive_setattr_on_other_names_is_unaffected(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx(1)
        n.some_other_name = 'fine'
        assert n.some_other_name == 'fine'

    def test_reactive_dir_lists_accessor_name_blocked_from_shadowing(self, clean_accessors):
        rx.register_accessor('my_accessor', lambda node: 'accessor-value')

        n = rx(1)
        with pytest.raises(AttributeError):
            n.my_accessor = 'oops'
        assert 'my_accessor' in dir(n)

    def test_reactive_accessor_memoize_false_reinstantiates_on_each_access(self, clean_accessors):
        calls = []

        def accessor(node):
            calls.append(node)
            return f'accessor-value-{len(calls)}'

        rx.register_accessor('my_accessor', accessor, memoize=False)

        n = rx(1)
        assert n.my_accessor == 'accessor-value-1'
        assert n.my_accessor == 'accessor-value-2'
        assert n.my_accessor == 'accessor-value-3'
        assert calls == [n, n, n]

    def test_reactive_accessor_memoize_false_reevaluates_predicate_each_access(self, clean_accessors):
        predicate_calls = []

        def predicate(value):
            predicate_calls.append(value)
            return isinstance(value, int)

        rx.register_accessor('my_accessor', lambda node: node.rx.value, predicate=predicate, memoize=False)

        n = rx(1)
        assert n.my_accessor == 1
        assert n.my_accessor == 1
        assert predicate_calls == [1, 1]

        n.rx.value = 'a string now'
        with pytest.raises(AttributeError):
            n.my_accessor
        assert predicate_calls == [1, 1, 'a string now']

    def test_reactive_accessor_memoize_true_still_instantiates_once(self, clean_accessors):
        installed_for = []

        def accessor(node):
            installed_for.append(node)
            return 'accessor-value'

        rx.register_accessor('my_accessor', accessor, memoize=True)

        n = rx(1)
        assert n.my_accessor == 'accessor-value'
        assert n.my_accessor == 'accessor-value'
        assert installed_for == [n]

class TestCollect:
    """``param.reactive.collect()``."""

    async def test_reactive_collect_reports_partial_results_as_inputs_settle(self):
        async def delayed(v, delay):
            await asyncio.sleep(delay)
            return v

        # Spaced out well past the polling interval below, so each settlement is
        # observed on its own rather than several being coalesced into one poll.
        a = rx(1).rx.pipe(delayed, delay=0.05)
        b = rx(2).rx.pipe(delayed, delay=0.15)
        c = rx(3).rx.pipe(delayed, delay=0.25)
        collected = collect(a, b, c)

        values = []
        collected.rx.watch(values.append)
        collected.rx.value
        assert collected.rx.awaiting

        await async_wait_until(
            lambda: values == [Collected(args=(1, param.Undefined, param.Undefined), kwargs={})],
            interval=10,
        )
        assert collected.rx.awaiting

        await async_wait_until(
            lambda: values == [
                Collected(args=(1, param.Undefined, param.Undefined), kwargs={}),
                Collected(args=(1, 2, param.Undefined), kwargs={}),
            ],
            interval=10,
        )
        assert collected.rx.awaiting

        await async_wait_until(
            lambda: values == [
                Collected(args=(1, param.Undefined, param.Undefined), kwargs={}),
                Collected(args=(1, 2, param.Undefined), kwargs={}),
                Collected(args=(1, 2, 3), kwargs={}),
            ],
            interval=10,
        )
        assert not collected.rx.awaiting

    def test_reactive_collect_returns_a_namedtuple_of_args_and_kwargs(self):
        a, b = rx(1), rx(2)
        collected = collect(a, b, c=rx(3))
        assert collected.rx.value == Collected(args=(1, 2), kwargs={'c': 3})
        assert not collected.rx.awaiting

    def test_reactive_collect_args_and_kwargs_are_reactive_attributes(self):
        a, b = rx(1), rx(2)
        collected = collect(a, b)
        assert collected.args.rx.value == (1, 2)
        assert collected.args.rx.pipe(sum).rx.value == 3
        assert collected.kwargs.rx.value == {}

    def test_reactive_collect_includes_non_reactive_inputs(self):
        collected = collect(rx(1), 2, c=3)
        assert collected.rx.value == Collected(args=(1, 2), kwargs={'c': 3})
        assert not collected.rx.awaiting

    def test_reactive_collect_kwargs_order_follows_argument_order_not_settle_order(self):
        """A key already present keeps its argument-order slot when it resettles."""
        a = rx(1)
        collected = collect(b=rx(2), a=a)
        assert list(collected.rx.value.kwargs) == ['b', 'a']

        a.rx.value = 10
        assert list(collected.rx.value.kwargs) == ['b', 'a']
        assert collected.rx.value.kwargs == {'b': 2, 'a': 10}

    def test_reactive_collect_empty_settles_immediately_to_an_empty_namedtuple(self):
        collected = collect()
        assert collected.rx.value == Collected(args=(), kwargs={})
        assert not collected.rx.awaiting

    async def test_reactive_collect_keeps_stale_slot_while_its_input_resettles(self):
        async def delayed(v, delay=0.05):
            await asyncio.sleep(delay)
            return v

        src = rx(1)
        a = src.rx.pipe(delayed)
        b = rx(2)
        collected = collect(a, b=b)

        events = []
        collected.rx.watch(events.append)
        collected.rx.value
        await async_wait_until(lambda: events == [Collected(args=(1,), kwargs={'b': 2})])

        src.rx.value = 10
        # No spurious duplicate published while 'a' resettles.
        assert collected.rx.value == Collected(args=(1,), kwargs={'b': 2})
        assert collected.rx.awaiting
        assert events == [Collected(args=(1,), kwargs={'b': 2})]

        await async_wait_until(
            lambda: events == [
                Collected(args=(1,), kwargs={'b': 2}),
                Collected(args=(10,), kwargs={'b': 2}),
            ]
        )
        assert not collected.rx.awaiting

    def test_reactive_collect_error_mode_propagate_holds_error_at_its_slot(self):
        def fail(v):
            raise ValueError('boom')

        a = rx(1)
        b = rx(2).rx.pipe(fail)
        c = rx(3)
        collected = collect(a, c=c, b=b, error_mode='propagate')

        value = collected.rx.value
        assert value.args == (1,)
        assert value.kwargs['c'] == 3
        assert isinstance(value.kwargs['b'], param.ReactiveError)

    def test_reactive_collect_error_mode_raise_fails_the_whole_node(self):
        def fail(v):
            raise ValueError('boom')

        collected = collect(rx(1), b=rx(2).rx.pipe(fail))
        with pytest.raises(ValueError, match='boom'):
            collected.rx.value

    def test_reactive_collect_error_mode_raise_fails_even_when_upstream_propagates(self):
        def fail(v):
            raise ValueError('boom')

        upstream = rx(1, error_mode='propagate').rx.pipe(fail)
        assert isinstance(upstream.rx.value, param.ReactiveError)

        collected = collect(upstream)
        with pytest.raises(ValueError, match='boom'):
            collected.rx.value

    def test_reactive_collect_is_a_plain_function_not_an_attribute_of_rx(self):
        """Can't shadow a wrapped object's own attribute of the same name."""
        class Obj:
            def collect(self, x):
                return f'collected {x}'

        assert rx(Obj()).collect(3).rx.value == 'collected 3'
        assert not hasattr(rx, 'collect')
        assert not hasattr(rx(1).rx, 'collect')

    def test_reactive_collect_kwargs_is_read_only(self):
        collected = collect(a=rx(1))
        with pytest.raises(TypeError):
            collected.rx.value.kwargs['a'] = 2

    def test_reactive_collect_overrides_a_positional_or_keyword_slot(self):
        collected = collect(rx(1), b=rx(2))
        collected.rx.overrides[0] = 100
        collected.rx.overrides['b'] = 200
        assert collected.rx.value == Collected(args=(100,), kwargs={'b': 200})

    def test_reactive_collect_numpy_array_does_not_crash_the_change_check(self):
        np = pytest.importorskip("numpy")
        a = rx(np.array([1, 2]))
        collected = collect(a)
        events = []
        collected.rx.watch(events.append)
        collected.rx.value

        a.rx.value = np.array([1, 2])  # equal content; must not raise
        a.rx.value = np.array([3, 4])
        assert len(events) == 2

    async def test_reactive_pipe_multi_arg_still_waits_for_every_input(self):
        """`collect` doesn't change plain `.rx.pipe`'s behavior."""
        async def delayed(v, delay):
            await asyncio.sleep(delay)
            return v

        a = rx(1).rx.pipe(delayed, delay=0.02)
        b = rx(2).rx.pipe(delayed, delay=0.15)
        combined = a.rx.pipe(lambda x, y: (x, y), y=b)

        combined.rx.watch()
        combined.rx.value
        await asyncio.sleep(0.05)
        assert combined.rx.value is param.Undefined
        assert combined.rx.awaiting

        await async_wait_until(lambda: combined.rx.value == (1, 2))


class TestDistinct:
    """``.rx.distinct()``."""

    def test_reactive_distinct_suppresses_downstream_recompute_when_value_repeats(self):
        trigger = rx(0)
        parity_calls, doubled_calls = [], []

        def parity(v):
            parity_calls.append(v)
            return v % 2

        def doubled(v):
            doubled_calls.append(v)
            return v * 1000

        parity_node = trigger.rx.pipe(parity).rx.distinct()
        doubled_node = parity_node.rx.pipe(doubled)
        results = []
        doubled_node.rx.watch(results.append)

        trigger.rx.value = 2  # same parity as 0 -- distinct() must swallow this
        trigger.rx.value = 3  # parity flips -- must propagate

        # `parity` has to run on every recompute to find out whether the
        # output changed; `doubled`, downstream of `.rx.distinct()`, only
        # runs for the genuinely distinct values.
        assert parity_calls == [0, 2, 3]
        assert doubled_calls == [1]
        assert results == [1000]

    def test_reactive_distinct_default_equality_matches_comparator_is_equal(self):
        # `a`'s value genuinely changes each time (so this isn't just Param's
        # own equal-value assignment no-op); only the *piped* list result
        # repeats, structurally, via Comparator.is_equal's list comparison.
        a = rx(0)
        node = a.rx.pipe(lambda v: [v % 2]).rx.distinct()
        results = []
        node.rx.watch(results.append)

        a.rx.value = 1  # first-ever recompute -- produces [1], nothing to compare against yet
        assert results == [[1]]
        a.rx.value = 3  # produces [1] again -- equal per Comparator.is_equal
        assert results == [[1]]
        a.rx.value = 4  # produces [0] -- distinct
        assert results == [[1], [0]]

    def test_reactive_distinct_custom_fn_overrides_default_equality(self):
        a = rx(0)
        node = a.rx.pipe(lambda v: v).rx.distinct(fn=lambda old, new: old % 3 == new % 3)
        results = []
        node.rx.watch(results.append)

        a.rx.value = 1  # first-ever recompute -- nothing to compare against yet
        assert results == [1]
        a.rx.value = 4  # 4 % 3 == 1 % 3 -- considered equal by the custom fn
        assert results == [1]
        a.rx.value = 5  # 5 % 3 != 1 % 3
        assert results == [1, 5]

    def test_reactive_distinct_uses_comparator_equalities_registry(self):
        class Frame:
            def __init__(self, v):
                self.v = v

        Comparator.equalities[Frame] = lambda a, b: a.v == b.v
        try:
            trigger = rx(0)
            node = trigger.rx.pipe(lambda v: Frame(v % 2)).rx.distinct()
            results = []
            node.rx.pipe(lambda f: f.v).rx.watch(results.append)

            trigger.rx.value = 2  # Frame(0) == Frame(0) via the registered equality
            trigger.rx.value = 5  # Frame(1) != Frame(0)

            assert results == [1]
        finally:
            del Comparator.equalities[Frame]

    def test_reactive_distinct_fn_exception_is_not_swallowed(self):
        def bad_fn(old, new):
            raise RuntimeError('boom')

        a = rx(1)
        node = a.rx.pipe(lambda v: v).rx.distinct(fn=bad_fn)
        node.rx.watch(lambda v: None)

        a.rx.value = 2  # first-ever recompute -- bad_fn isn't consulted yet
        with pytest.raises(RuntimeError, match='boom'):
            a.rx.value = 3  # second recompute -- now bad_fn actually runs

    def test_reactive_distinct_value_reflects_latest_distinct_result(self):
        a = rx(1)
        node = a.rx.pipe(lambda v: v % 2).rx.distinct()
        assert node.rx.value == 1
        a.rx.value = 3
        assert node.rx.value == 1
        a.rx.value = 4
        assert node.rx.value == 0
