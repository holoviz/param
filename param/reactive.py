"""
Reactive API for Dynamic Expression Pipelines.

`rx` provides a wrapper around Python objects, enabling the creation of
reactive expression pipelines that dynamically update based on changes to their
underlying parameters or widgets. This approach simplifies the implementation of
dynamic, interactive behavior in Python code, particularly for data manipulation
and visualization tasks.

Overview
--------

An `rx` instance tracks and records the operations applied to a wrapped object,
constructing a chain of transformations that can reactively update as inputs change.
These operations are recorded and evaluated lazily, ensuring that the object state
remains up-to-date while enabling efficient re-computation.

The original input object is stored in a shared mutable list accessible via the
`_obj` property. This shared reference allows all `rx` instances derived from the
same object to reflect updates, whether through the `.value` property or due to
modifications in the underlying data.

Core Features
-------------

The `rx` implementation intercepts and records various operations performed on an
object, including:

- **Attribute Access**: Captured using `__getattribute__` to watch for method or
  property usage.
- **Method Calls**: Handled through `__call__` after an attribute is accessed.
- **Indexing**: Tracked via `__getitem__` for slicing or item access.
- **Operators**: Supports all standard operators (e.g., `__add__`, `__gt__`) to
  enable arithmetic and logical expressions.
- **NumPy Integration**: Overrides `__array_ufunc__` to capture NumPy universal
  function calls.

This functionality makes `rx` objects particularly well-suited for interactive
environments such as Jupyter notebooks or Python REPLs. Lazy evaluation ensures that
pipeline operations are executed only when their result is needed, enabling dynamic
inspection and interactive exploration. For instance, tab-completion and docstring
retrieval (`dfi.A.max?`) work seamlessly with reactive expressions.

Reactive Expression Mechanics
-----------------------------

When an operation is applied to an `rx` instance:

1. The operation is recorded in a structured format (stored in `_operation`).
2. A new `rx` instance is created using the `_clone` method.
3. The `_dirty` attribute is set to `True` for dependent objects, indicating the
   need for re-evaluation.

Each `_operation` dictionary includes:

- `fn`: The function or method to execute.
- `args`: Positional arguments for the function or method.
- `kwargs`: Keyword arguments for the function or method.
- `reverse`: A flag indicating whether the input object and first argument should
  be swapped during execution.

Chain Tracking and Dependencies
-------------------------------

Reactive pipelines consist of chains of `rx` instances, with each instance linked
to its predecessor. The `_depth` attribute indicates the chain depth, starting at
0 for the root object. Note that `_depth` reflects the chain's outer structure, not
the total number of reactive instances in a pipeline.

Instances also track their dependencies to ensure accurate updates:
- `_method`: Temporarily stores the method or attribute accessed (e.g., `'head'`
  in `dfi.head()`).
- `_dirty`: Indicates whether the current value needs re-computation. Exposed
  publicly, together with the state of the nodes feeding a node, as
  `.rx.stale`.
- `_current`: Stores the result of the most recent computation.

Benefits and Use Cases
----------------------

The reactive approach eliminates the need for explicit callbacks and manual state
management, making it ideal for:

- Real-time data processing and visualization pipelines.
- Interactive dashboards and applications.
- Simplifying complex workflows with dynamic dependencies.

By leveraging Python's operator overloading and lazy evaluation, `rx` provides a
powerful and intuitive way to manage dynamic behavior in Python applications.
"""
from __future__ import annotations

import contextvars
import inspect
import logging
import math
import operator
import typing as t
import warnings
import weakref

from collections import namedtuple
from collections.abc import (
    AsyncGenerator, Callable, Coroutine, Generator, Iterable, Iterator,
    MutableMapping, Sized
)
from itertools import chain
from functools import partial
from types import FunctionType, MethodType, MappingProxyType

from .depends import depends
from .display import _display_accessors, _reactive_display_objs
from .parameterized import (
    Comparator, Parameter, Parameterized, Skip, Undefined, eval_function_with_deps,
    get_method_owner, register_reference_transform, resolve_ref, resolve_value,
    transform_reference, _watch_ref_change
)
from .parameters import Boolean, Event, String
from ._utils import _to_async_gen, iscoroutinefunction, full_groupby

if t.TYPE_CHECKING:
    import builtins
    from typing_extensions import Self

    from .parameterized import Watcher

    _P = t.ParamSpec('_P')
    _R = t.TypeVar('_R')
    _Y = t.TypeVar('_Y')


logger = logging.getLogger(__name__)


class ReactiveError:
    """A value representing an error raised while evaluating a reactive expression."""

    def __init__(self, exception: Exception, node=None):
        self.exception = exception
        self.node = weakref.ref(node) if node is not None else None

    @property
    def label(self) -> str | None:
        """The label of the node that produced this error, or None if unset."""
        node = self.node() if self.node is not None else None
        return getattr(node, '_label', None) if node is not None else None

    def __bool__(self):
        return False

    def __str__(self):
        return str(self.exception)

    def __repr__(self):
        return f"ReactiveError({self.exception!r})"

    def __getitem__(self, key):
        return t.cast('t.Any', self.exception)[key]

    def __getattr__(self, name):
        return getattr(self.exception, name)


class Wrapper(Parameterized):
    """Helper class to allow updating literal values easily."""

    object: t.Any = Parameter(allow_refs=False)


class GenWrapper(Parameterized):
    """Helper class to allow streaming from generator functions."""

    object: t.Any = Parameter(allow_refs=True)


class Trigger(Parameterized):
    """Helper class to allow triggering an event under some condition."""

    name = String(default='trigger', constant=True)

    value = Event()

    def __init__(self, parameters=None, internal=False, **params):
        super().__init__(**params)
        self.internal = internal
        self.parameters = parameters

class Resolver(Parameterized):
    """Helper class to allow (recursively) resolving references."""

    object: t.Any = Parameter(allow_refs=True)

    recursive = Boolean(default=False)

    value: t.Any = Parameter()

    def __init__(self, **params):
        self._finalizers: list[weakref.finalize] = []
        super().__init__(**params)

    def _resolve_value(self, *events):
        nested = self.param.object.nested_refs
        refs = resolve_ref(self.object, nested)
        value = resolve_value(self.object, nested)
        if self.recursive:
            new_refs = [r for r in resolve_ref(value, nested) if r not in refs]
            while new_refs:
                refs += new_refs
                value = resolve_value(value, nested)
                new_refs = [r for r in resolve_ref(value, nested) if r not in refs]
            if events:
                self._update_refs(refs)
        self.value = value
        return refs

    @depends('object', watch=True, on_init=True)
    def _resolve_object(self):
        refs = self._resolve_value()
        self._update_refs(refs)

    def _update_refs(self, refs):
        """Weakly watch every ``Parameterized`` a resolved reference points to."""
        for finalizer in self._finalizers:
            finalizer()
        self._finalizers = []
        for _, params in full_groupby(refs, lambda x: id(x.owner)):
            owner = params[0].owner
            invalidator = _WeakInvalidator(self._resolve_value)
            invalidator._watcher = owner.param.watch(invalidator, [p.name for p in params])
            self._finalizers.append(weakref.finalize(
                self, _remove_watcher, weakref.ref(owner), weakref.ref(invalidator)
            ))


class NestedResolver(Resolver):

    object: t.Any = Parameter(allow_refs=True, nested_refs=True)


class InputOverrides(MutableMapping):
    """
    The mapping returned by :attr:`reactive_ops.overrides`.

    Keys address the inputs a node was wired with, by keyword name or positional
    index. Values are either plain values or references the node follows.
    Deleting a key unmasks the input again.
    """

    def __init__(self, node: rx):
        self._node = node

    @property
    def _overrides(self) -> dict[t.Any, t.Any] | None:
        operation = self._node._operation
        return None if operation is None else operation.get('overrides')

    def _resolve_key(self, key: t.Any) -> t.Any:
        operation = t.cast('dict', self._node._operation)
        args = operation.get('args') or ()
        kwargs = operation.get('kwargs') or {}
        if isinstance(key, str):
            if key in kwargs:
                return key
        elif isinstance(key, int) and not isinstance(key, bool):
            if -len(args) <= key < len(args):
                return key + len(args) if key < 0 else key
        else:
            raise TypeError(
                "Input overrides are addressed by keyword name or positional "
                f"index, not by {type(key).__name__!r}."
            )
        nargs, names = len(args), sorted(kwargs)
        inputs = []
        if nargs:
            inputs.append(f"positional indices 0-{nargs-1}")
        if names:
            inputs.append("keywords " + ", ".join(repr(name) for name in names))
        raise KeyError(
            f"{key!r} is not an input of this node, which has "
            f"{' and '.join(inputs) if inputs else 'no inputs'}. Only an input "
            "the node was wired with can be overridden."
        )

    def _resolve_raw(self, key: t.Any) -> t.Any:
        """Return the raw, un-overridden ``args``/``kwargs`` value at ``key``."""
        operation = t.cast('dict', self._node._operation)
        if isinstance(key, str):
            return operation.get('kwargs', {})[key]
        return operation.get('args', ())[key]

    def _unwatch(self, key: t.Any):
        """
        Drop the reader link on whatever is currently active at ``key`` -
        the override if one is set, otherwise the raw wired input, whose
        link must go too the first time a key is masked or it can never be
        disposed - and stop watching whatever references it depended on.
        Also drops the link for every ``_operation_siblings()`` node, since
        they read the same ``operation`` dict.

        Called before ``overrides`` is mutated, in both ``__setitem__`` and
        ``__delitem__``, so ``self._overrides`` still reflects the value
        being replaced or removed.
        """
        node = self._node
        operation = t.cast('dict', node._operation)
        overrides = operation.get('overrides') or {}
        current = overrides[key] if key in overrides else self._resolve_raw(key)
        readers = (node, *node._operation_siblings())
        for target in _iter_rx(current):
            for reader in readers:
                target._drop_reader(reader)
        finalizers = node._finalizers
        for finalizer in (operation.get('override_watchers') or {}).pop(key, ()):
            # Firing the finalizer now both unwatches the source and
            # marks it dead, so it is safe to drop from `_finalizers`.
            finalizer()
            if finalizers is not None:
                try:
                    finalizers.remove(finalizer)
                except ValueError:
                    pass

    def __getitem__(self, key: t.Any) -> t.Any:
        key = self._resolve_key(key)
        overrides = self._overrides
        if not overrides or key not in overrides:
            raise KeyError(key)
        return overrides[key]

    def __setitem__(self, key: t.Any, value: t.Any):
        key = self._resolve_key(key)
        node = self._node
        operation = t.cast('dict', node._operation)
        overrides = operation.get('overrides')
        if overrides is None:
            overrides = operation['overrides'] = {}
        self._unwatch(key)
        overrides[key] = value
        # Register as a reader, like `rx.__init__` does for an ordinary
        # operation argument, on `node` and every `_operation_siblings()`.
        readers = (node, *node._operation_siblings())
        for target in _iter_rx(value):
            for reader in readers:
                target._register_reader(reader)
        refs = resolve_ref(value, recursive=True)
        if refs:
            watchers = operation.setdefault('override_watchers', {})
            watchers[key] = node._watch_override(refs)
        node._invalidate_overrides()

    def __delitem__(self, key: t.Any):
        key = self._resolve_key(key)
        overrides = self._overrides
        if not overrides or key not in overrides:
            raise KeyError(key)
        raw = self._resolve_raw(key)
        # A masked input isn't read (see `_unwatch()`), so it may already be
        # disposed; unmasking it would then silently wire this node to an
        # `rx` that raises on every future read, so check before mutating.
        disposed = next((target for target in _iter_rx(raw) if target._disposed), None)
        if disposed is not None:
            raise RuntimeError(
                f"Cannot remove this override: the input it was masking, {disposed!r}, "
                "was disposed by .rx.dispose() while masked and can no longer be read. "
                "Dispose the overriding node instead of removing the override."
            )
        self._unwatch(key)
        del overrides[key]
        # Unmasked again, so re-register the reader link `rx.__init__`
        # would have set up had the override never existed, on `node` and
        # every `_operation_siblings()`.
        node = self._node
        readers = (node, *node._operation_siblings())
        for target in _iter_rx(raw):
            for reader in readers:
                target._register_reader(reader)
        node._invalidate_overrides()

    def __iter__(self) -> Iterator[t.Any]:
        return iter(self._overrides or {})

    def __len__(self) -> int:
        return len(self._overrides or {})

    def __repr__(self) -> str:
        return f"overrides({(self._overrides or {})!r})"


class reactive_ops:
    """
    The reactive operations namespace.

    Provides reactive versions of operations that cannot be made reactive through
    operator overloading. This includes operations such as ``.rx.and_`` and ``.rx.bool``.

    Calling this namespace (``()``) creates and returns a reactive expression, enabling
    dynamic updates and computation tracking.

    Returns
    -------
    rx
        A reactive expression representing the operation applied to the current value.

    References
    ----------
    For more details, see the user guide:
    https://param.holoviz.org/user_guide/Reactive_Expressions.html#special-methods-on-rx

    Examples
    --------
    Create a Parameterized instance and access its reactive operations property:

    >>> import param
    >>> class P(param.Parameterized):
    ...     a = param.Number()
    >>> p = P(a=1)

    Retrieve the current value reactively:

    >>> a_value = p.param.a.rx.value

    Create a reactive expression by calling the namespace:

    >>> rx_expression = p.param.a.rx()

    Use special methods from the reactive ops namespace for reactive operations:

    >>> condition = p.param.a.rx.and_(True)
    >>> piped = p.param.a.rx.pipe(lambda x: x * 2)

    """

    def __init__(self, reactive):
        self._reactive = reactive

    def _as_rx(self):
        return self._reactive if isinstance(self._reactive, rx) else self()

    def __call__(self) -> 'rx':
        """Create a reactive expression."""
        rxi = self._reactive
        return rxi if isinstance(rxi, rx) else rx(rxi)

    @property
    def error(self):
        """Return the current :class:`ReactiveError` or exception, if any."""
        if isinstance(self._reactive, rx):
            try:
                value = self._reactive._resolve()
            except Exception as exc:
                return exc
            return value if isinstance(value, ReactiveError) else None
        return None

    @property
    def label(self) -> str | None:
        """
        Get or set a human-readable label for this node.

        The label is inherited by nodes derived via `.rx.pipe` and operator
        overloads, and is reported back on a :class:`ReactiveError` this node
        (or a node derived from it) produces, via `ReactiveError.label`.

        .. versionadded:: 2.5.0
        """
        if isinstance(self._reactive, rx):
            return self._reactive._label
        return None

    @label.setter
    def label(self, value: str | None):
        if not isinstance(self._reactive, rx):
            raise AttributeError(
                "Cannot set a label on a reactive reference that is not an "
                "rx expression."
            )
        self._reactive._label = value

    def and_(self, other) -> 'rx':
        """
        Perform a logical AND operation with the given operand.

        This method computes a logical AND (``and``) operation between the current
        value of the reactive expression and the provided operand. The result is
        returned as a new reactive expression.

        Parameters
        ----------
        other : any
            The operand to combine with the current value using the AND operation.

        Returns
        -------
        rx
            A new reactive expression representing the result of the AND operation.

        Examples
        --------
        Create two reactive expressions and combine them using ``and_``:

        >>> import param
        >>> a = param.rx(True)
        >>> b = param.rx(False)
        >>> result = a.rx.and_(b)
        >>> result.rx.value
        False

        Combine a reactive expression with a static value:

        >>> result = a.rx.and_(True)
        >>> result.rx.value
        True
        """
        return self._as_rx()._apply_operator(lambda obj, other: obj and other, other)

    def bool(self) -> 'rx':
        """
        Evaluate the truthiness of the current object.

        This method computes the boolean value of the current reactive expression.
        The result is returned as a new reactive expression, allowing the truthiness
        of the object to be used in further reactive operations.

        Returns
        -------
        rx
            A new reactive expression representing the boolean value of the object.

        Examples
        --------
        Create a reactive expression and evaluate its truthiness:

        >>> import param
        >>> rx_value = param.rx(5)
        >>> rx_bool = rx_value.rx.bool()
        >>> rx_bool.rx.value
        True

        Evaluate the truthiness of an empty reactive expression:

        >>> rx_empty = param.rx([])
        >>> rx_bool = rx_empty.rx.bool()
        >>> rx_bool.rx.value
        False
        """
        return self._as_rx()._apply_operator(bool)

    def buffer(self, n) -> 'rx':
        """
        Collect the last ``n`` items emitted by the reactive expression.

        This method creates a new reactive expression that maintains a buffer of the
        most recent ``n`` items emitted by the current reactive expression. As new values
        are emitted, older values are discarded to keep the buffer size constant.

        Parameters
        ----------
        n : int
            The maximum number of items to retain in the buffer.

        Returns
        -------
        rx
            A new reactive expression containing the buffered items as a list.

        Examples
        --------
        Create a reactive expression and buffer the last 3 emitted items:

        >>> import param
        >>> rx_value = param.rx(1)
        >>> rx_buffer = rx_value.rx.buffer(3)
        >>> rx_buffer.rx.value
        [1]

        Emit new values and observe the buffered results:

        >>> rx_value.rx.value = 2
        >>> rx_value.rx.value = 3
        >>> rx_value.rx.value = 4
        >>> rx_buffer.rx.value
        [2, 3, 4]
        """
        items = []
        def push(new, n):
            items.append(new)
            while len(items) > n:
                items.pop(0)
            return items
        return self._as_rx()._apply_operator(push, n)

    def in_(self, other) -> 'rx':
        """
        Check if the current object is contained "in" the given operand.

        This method performs a containment check, equivalent to the ``in`` keyword in Python,
        but within a reactive expression. The result is returned as a new reactive expression.

        Parameters
        ----------
        other : any
            The collection or operand to check for containment.

        Returns
        -------
        rx
            A new reactive expression representing the result of the containment check.

        Examples
        --------
        Check if a reactive value is in a list:

        >>> import param
        >>> rx_value = param.rx(2)
        >>> rx_in = rx_value.rx.in_([1, 2, 3])
        >>> rx_in.rx.value
        True

        Check containment with a string:

        >>> rx_char = param.rx('a')
        >>> rx_in = rx_char.rx.in_('alphabet')
        >>> rx_in.rx.value
        True

        Update the reactive value and observe changes:

        >>> rx_char.rx.value = 'c'
        >>> rx_in.rx.value
        False
        """
        return self._as_rx()._apply_operator(operator.contains, other, reverse=True)

    def is_(self, other) -> 'rx':
        """
        Perform a logical "is" comparison with the given operand.

        This method checks if the current object is the same object (i.e., identical in
        memory) as the given operand. The result is returned as a new reactive expression.

        Parameters
        ----------
        other : any
            The operand to compare for object identity.

        Returns
        -------
        rx
            A new reactive expression representing the result of the "is" comparison.

        Examples
        --------
        Check if a reactive value refers to the same object:

        >>> import param
        >>> obj1 = object()
        >>> obj2 = object()
        >>> rx_obj = param.rx(obj1)
        >>> rx_is = rx_obj.rx.is_(obj1)
        >>> rx_is.rx.value
        True

        Compare with a different object:

        >>> rx_is = rx_obj.rx.is_(obj2)
        >>> rx_is.rx.value
        False

        Update the reactive value and re-check identity:

        >>> rx_obj.rx.value = obj2
        >>> rx_is.rx.value
        False
        """
        return self._as_rx()._apply_operator(operator.is_, other)

    def is_not(self, other) -> 'rx':
        """
        Perform a logical "is not" comparison with the given operand.

        This method checks if the current object is not the same object (i.e., not
        identical in memory) as the given operand. The result is returned as a new
        reactive expression.

        Parameters
        ----------
        other : any
            The operand to compare for non-identity.

        Returns
        -------
        rx
            A new reactive expression representing the result of the "is not" comparison.

        Examples
        --------
        Check if a reactive value is not the same object:

        >>> import param
        >>> obj1 = object()
        >>> obj2 = object()
        >>> rx_obj = param.rx(obj1)
        >>> rx_is_not = rx_obj.rx.is_not(obj2)
        >>> rx_is_not.rx.value
        True

        Compare with the same object:

        >>> rx_is_not = rx_obj.rx.is_not(obj1)
        >>> rx_is_not.rx.value
        False

        Update the reactive value and re-check non-identity:

        >>> rx_obj.rx.value = obj2
        >>> rx_is_not.rx.value
        True
        """
        return self._as_rx()._apply_operator(operator.is_not, other)

    def len(self) -> 'rx':
        """
        Return the length of the current object as a reactive expression.

        Since the ``__len__`` method cannot be overloaded reactively, this method
        provides a way to compute the length of the current reactive expression.
        The result is returned as a new reactive expression.

        Returns
        -------
        rx
            A new reactive expression representing the length of the object.

        Examples
        --------
        Compute the length of a reactive list:

        >>> import param
        >>> rx_list = param.rx([1, 2, 3])
        >>> rx_len = rx_list.rx.len()
        >>> rx_len.rx.value
        3

        Update the reactive list and observe the length update:

        >>> rx_list.rx.value = [1, 2, 3, 4, 5]
        >>> rx_len.rx.value
        5

        Compute the length of a reactive string:

        >>> rx_string = param.rx("Hello World")
        >>> rx_len = rx_string.rx.len()
        >>> rx_len.rx.value
        11
        """
        return self._as_rx()._apply_operator(len)

    def map(self, func, /, *args, **kwargs) -> 'rx':
        """
        Apply a function to each item in the reactive collection.

        This method applies a given function to every item in the current reactive
        collection and returns a new reactive expression containing the results.

        Parameters
        ----------
        func : callable
            The function to apply to each item in the collection.
        *args : iterable, optional
            Positional arguments to pass to the function.
        **kwargs : dict, optional
            Keyword arguments to pass to the function.

        Returns
        -------
        rx
            A new reactive expression containing the results of applying ``func``
            to each item.

        Raises
        ------
        TypeError
            If ``func`` is a generator or asynchronous generator function, which
            are not supported.

        Examples
        --------
        Apply a function to double each item in a reactive list:

        >>> import param
        >>> reactive_list = param.rx([1, 2, 3])
        >>> reactive_doubled = reactive_list.rx.map(lambda x: x * 2)
        >>> reactive_doubled.rx.value
        [2, 4, 6]

        Use positional arguments in the function:

        >>> reactive_offset = reactive_list.rx.map(lambda x, offset: x + offset, offset=10)
        >>> reactive_offset.rx.value
        [11, 12, 13]

        Use keyword arguments in the function:

        >>> reactive_power = reactive_list.rx.map(lambda x, power=1: x ** power, power=3)
        >>> reactive_power.rx.value
        [1, 8, 27]
        """
        if inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
            raise TypeError(
                "Cannot map a generator function. Only regular function "
                "or coroutine functions are permitted."
            )
        if inspect.iscoroutinefunction(func):
            import asyncio
            async def apply_async(vs, *args, **kwargs):
                return list(await asyncio.gather(*(func(v, *args, **kwargs) for v in vs)))
            return self._as_rx()._apply_operator(apply_async, *args, **kwargs)
        else:
            def apply(vs, *args, **kwargs):
                return [func(v, *args, **kwargs) for v in vs]
            return self._as_rx()._apply_operator(apply, *args, **kwargs)

    @property
    def meta(self) -> dict[t.Any, t.Any]:
        """
        A per-node mapping of user metadata.

        Unlike the reactive expression itself, metadata is local to this exact
        node: it is not inherited by nodes derived from it (through operators,
        attribute access, method calls, ``.rx.pipe``, indexing, etc.), and it is
        not shared with mirrors created by branching (``expr[0]``, ``expr[1]``).
        Each node starts with its own empty mapping.

        Metadata takes no part in a node's identity or evaluation: mutating it
        does not dirty the node, notify watchers, or otherwise affect
        computation. It exists purely as a place for a library built on ``rx``
        to attach state to a specific node, such as a provenance record or a
        cache key.

        Returns
        -------
        dict
            The mutable metadata mapping for this node.

        Examples
        --------
        >>> import param
        >>> a = param.rx(1)
        >>> a.rx.meta['trace'] = 'created at step 1'
        >>> b = a + 1
        >>> 'trace' in b.rx.meta
        False
        """
        rxi = self._reactive
        if not isinstance(rxi, rx):
            raise AttributeError(
                "'.rx.meta' is only available on `rx` nodes, not on "
                f"the `.rx` namespace of a {type(rxi).__name__!r} object."
            )
        if rxi._meta is None:
            rxi._meta = {}
        return rxi._meta

    @property
    def overrides(self) -> InputOverrides:
        """
        A mutable mapping of overrides for the inputs of this node.

        Allows assigning values in the mapping addressed by keyword
        name or positional index. Setting one makes this node compute
        as if that input held the given value, leaving the input
        itself, and therefore its other consumers, untouched. Deleting
        the key unmasks the original input.

        >>> import param
        >>> fx = param.rx(2)
        >>> expr = param.rx(10).rx.pipe(lambda value, fx: value * fx, fx=fx)
        >>> expr.rx.overrides['fx'] = 1
        >>> expr.rx.value
        10
        >>> del expr.rx.overrides['fx']
        >>> expr.rx.value
        20

        An override may also be a reference, e.g. a ``Parameter``, an expression, a
        bound function, a widget, which the node then follows:

        >>> expr.rx.overrides['fx'] = param.rx(3)
        >>> expr.rx.value
        30

        The override stands in for the input and is resolved in its place, ahead
        of the guards the input would have faced, i.e. it even overrides input
        holding errors or undefined values. Any value masks the input, including
        ``None``, so an override that follows a reference keeps masking when that
        reference happens to hold ``None``.

        Overrides are node-local, like ``.rx.meta``: a derived node
        (``expr + 1``) has its own, empty mapping.

        Returns
        -------
        InputOverrides
            The mutable mapping of overridden inputs for this node.

        Raises
        ------
        AttributeError
            If the ``.rx`` namespace does not belong to an ``rx`` node, or if
            the node has no inputs because it is the input of an expression.
        """
        rxi = self._reactive
        if not isinstance(rxi, rx):
            raise AttributeError(
                "'.rx.overrides' is only available on `rx` nodes, not on "
                f"the `.rx` namespace of a {type(rxi).__name__!r} object."
            )
        if rxi._operation is None:
            raise AttributeError(
                "'.rx.overrides' is only available on a node that applies an "
                "operation to inputs. This node is the input of an expression; "
                "set its value with '.rx.value' instead."
            )
        return InputOverrides(rxi)

    def not_(self) -> 'rx':
        """
        Perform a logical NOT operation on the current reactive value.

        This method computes the logical negation (``not``) of the current reactive
        expression and returns the result as a new reactive expression.

        Returns
        -------
        rx
            A new reactive expression representing the result of the NOT operation.

        Examples
        --------
        Apply a logical NOT operation to a reactive boolean:

        >>> import param
        >>> rx_bool = param.rx(True)
        >>> rx_not = rx_bool.rx.not_()
        >>> rx_not.rx.value
        False

        Update the reactive value and observe the change:

        >>> rx_bool.rx.value = False
        >>> rx_not.rx.value
        True
        """
        return self._as_rx()._apply_operator(operator.not_)

    def or_(self, other)-> 'rx':
        """
        Perform a logical OR operation with the given operand.

        This method computes a logical OR (``or``) operation between the current
        reactive value and the provided operand. The result is returned as a new
        reactive expression.

        Parameters
        ----------
        other : any
            The operand to combine with the current value using the OR operation.

        Returns
        -------
        rx
            A new reactive expression representing the result of the OR operation.

        Examples
        --------
        Combine two reactive boolean values using OR:

        >>> import param
        >>> rx_bool1 = param.rx(False)
        >>> rx_bool2 = param.rx(True)
        >>> rx_or = rx_bool1.rx.or_(rx_bool2)
        >>> rx_or.rx.value
        True

        Combine a reactive value with a static boolean:

        >>> rx_or_static = rx_bool1.rx.or_(True)
        >>> rx_or_static.rx.value
        True

        Update the reactive value and observe the change:

        >>> rx_bool1.rx.value = True
        >>> rx_or.rx.value
        True
        """
        return self._as_rx()._apply_operator(lambda obj, other: obj or other, other)

    def pipe(self, func, /, *args, process_failures=False, **kwargs)-> 'rx':
        """
        Apply a chainable function to the current reactive value.

        This method allows applying a custom function to the current reactive
        expression. The result is returned as a new reactive expression, making
        it possible to create dynamic and chainable pipelines.

        Parameters
        ----------
        func : callable
            The function to apply to the current value.
        *args : iterable, optional
            Positional arguments to pass to the function.
        **kwargs : dict, optional
            Keyword arguments to pass to the function.

        Returns
        -------
        rx
            A new reactive expression representing the result of applying ``func``.

        Examples
        --------
        Apply a custom function to transform a reactive value:

        >>> import param
        >>> rx_value = param.rx(10)
        >>> rx_result = rx_value.rx.pipe(lambda x: x * 2)
        >>> rx_result.rx.value
        20

        Use positional arguments with the function:

        >>> def add(x, y):
        ...     return x + y
        >>> rx_result = rx_value.rx.pipe(add, 5)
        >>> rx_result.rx.value
        15

        Use keyword arguments with the function:

        >>> def multiply(x, factor=1):
        ...     return x * factor
        >>> rx_result = rx_value.rx.pipe(multiply, factor=3)
        >>> rx_result.rx.value
        30
        """
        return self._as_rx()._apply_operator(
            func, *args, process_failures=process_failures, **kwargs
        )

    def resolve(self, nested=True, recursive=False) -> 'rx':
        """
        Resolve references held by the reactive expression.

        This method resolves references within the reactive expression, replacing
        any references with their actual values. For example, if the expression
        contains a list of reactive parameters, this operation returns a list of
        their resolved values.

        Parameters
        ----------
        nested : bool, optional
            Whether to resolve references within nested objects such as tuples,
            lists, sets, and dictionaries. Default is True.
        recursive : bool, optional
            Whether to recursively resolve references. If a resolved reference
            itself contains further references, this option enables resolving
            them until no references remain. Default is False.

        Returns
        -------
        rx
            A new reactive expression containing the fully resolved values.

        Examples
        --------
        Resolve a simple reactive list of values:

        >>> import param
        >>> rx_list = param.rx([param.rx(1), param.rx(2), param.rx(3)])
        >>> resolved = rx_list.rx.resolve()
        >>> resolved.rx.value
        [1, 2, 3]

        Enable recursive resolution for deeper references:

        >>> rx_nested = param.rx({'key': param.rx([param.rx(10), param.rx(20)])})
        >>> resolved_nested = rx_nested.rx.resolve(recursive=True)
        >>> resolved_nested.rx.value
        {'key': [10, 20]}
        """
        resolver_type = NestedResolver if nested else Resolver
        resolver = resolver_type(object=self._reactive, recursive=recursive)
        return resolver.param.value.rx()

    @property
    def awaiting(self) -> builtins.bool:
        """
        Whether any asynchronous operation in this expression is still resolving.

        ``True`` from the moment an asynchronous operation is scheduled until it
        produces a value for the current inputs. While a node is awaiting,
        ``.rx.value`` keeps reporting the value it computed from the previous
        inputs (or :obj:`param.Undefined` if no value has been produced yet);
        ``awaiting`` is what lets you tell that value is stale and still
        resolving, as opposed to final or the result of a deliberate skip.

        The whole graph feeding the expression is considered, not just the node
        it is accessed on, so a synchronous operation downstream of an
        asynchronous one reports ``True`` while its input resolves.

        Reading this does not itself schedule anything, so an expression whose
        value has never been requested reports ``False`` until something asks
        for it.

        Both routes an asynchronous callable can take are tracked: one applied
        as an operation, e.g. passed to ``.rx.pipe``, and one passed to ``rx``
        as the object itself, which is held on a parameter and resolved by the
        reference machinery. A generator settles on each value it yields, so it
        reports ``True`` only until its next value arrives rather than until it
        is exhausted. Accessed on a parameter rather than an expression this is
        always ``False``.

        Returns
        -------
        bool
            ``True`` while an asynchronous operation has not yet produced a
            value for the current inputs, ``False`` otherwise.

        Examples
        --------
        Pipe through a coroutine function and observe the expression settle:

        >>> import asyncio, param
        >>> async def double(value):
        ...     await asyncio.sleep(0.1)
        ...     return value * 2
        >>> expr = param.rx(1).rx.pipe(double) + 1

        Requesting the value schedules the operation:

        >>> expr.rx.value is param.Undefined
        True
        >>> expr.rx.awaiting
        True

        Once the coroutine has resolved the expression reports a value again:

        >>> expr.rx.awaiting  # doctest: +SKIP
        False
        """
        reactive = self._reactive
        if not isinstance(reactive, rx):
            return False
        return any(node._settling for node in reactive._upstream())

    @property
    def stale(self) -> builtins.bool:
        """
        Whether the expression has not yet produced a value for its current inputs.

        ``True`` from the moment an input invalidates the expression until it
        recomputes, and before the first evaluation of an expression whose value
        has never been requested. An asynchronous operation stays stale after it
        has been scheduled, since scheduling is not the same as producing a
        value, so ``stale`` and not ``.rx.awaiting`` means the next request for
        the value recomputes it synchronously.

        Returns
        -------
        bool
            ``True`` while the current value does not reflect the current
            inputs, ``False`` otherwise.

        Examples
        --------
        An expression is stale until its value is requested, and again once an
        input changes:

        >>> import param
        >>> a = param.rx(1)
        >>> expr = a + 1
        >>> expr.rx.stale
        True
        >>> expr.rx.value
        2
        >>> expr.rx.stale
        False
        >>> a.rx.value = 2
        >>> expr.rx.stale
        True
        """
        reactive = self._reactive
        if not isinstance(reactive, rx):
            return False
        return any(
            node._dirty or node._root._dirty_obj or node._settling
            for node in reactive._upstream()
        )

    def upstream(self) -> Iterator['rx']:
        """
        Iterate over the ``rx`` nodes this expression derives its value from,
        directly or transitively, excluding itself. Pipeline edges count:
        ``.rx.pipe``/operator chaining, a branch (``expr[0]``), an ``rx``
        passed as an operation argument (or its ``.rx.overrides`` replacement,
        once masked), and an ``rx`` reached through a
        ``Parameter(allow_refs=True)``. A dependency reached only through
        ``bind()``, ``.rx.when``, or ``.rx.where`` is not included.

        Traversal order is unspecified and may change between calls as the
        pipeline is extended. Do not use ``in`` on the iterator to test
        membership: ``rx.__eq__`` builds a comparison expression rather than a
        bool, so ``x in upstream()`` is not a reliable membership test. Use
        ``x in set(upstream())`` instead.

        Returns
        -------
        Iterator[rx]
            Empty if the ``.rx`` namespace does not belong to an ``rx`` node.

        Examples
        --------
        >>> import param
        >>> a = param.rx(1)
        >>> b = a.rx.pipe(lambda x, y: x + y, y=param.rx(2))
        >>> a in set(b.rx.upstream())
        True
        """
        reactive = self._reactive
        if not isinstance(reactive, rx):
            return
        upstream = reactive._upstream()
        next(upstream, None)  # Skip itself.
        yield from upstream

    def downstream(self) -> Iterator['rx']:
        """
        Iterate over the ``rx`` nodes that derive their value from this
        expression, directly or transitively, excluding itself. The reverse
        of :meth:`upstream`, but not a perfect mirror of its scope: a node
        that installed this expression as its ``.rx.overrides`` replacement
        is included, same as :meth:`upstream`, but a node that only reaches
        this one through ``bind()``, ``.rx.when``, ``.rx.where``, or a
        ``Parameter(allow_refs=True)`` is not. The owning ``Parameterized``
        keeps a ref'd expression alive on its own, so it is deliberately
        excluded from the reader bookkeeping this method (and
        :meth:`dispose`'s cascade) relies on.

        Readers are held weakly, so this reflects only what is currently
        alive, and traversal order is unspecified. As with :meth:`upstream`,
        use ``set(downstream())`` rather than ``in`` on the iterator directly.

        Returns
        -------
        Iterator[rx]
            Empty if the ``.rx`` namespace does not belong to an ``rx`` node,
            or if nothing currently reads from it.

        Examples
        --------
        >>> import param
        >>> a = param.rx(1)
        >>> b = a.rx.pipe(lambda x: x + 1)
        >>> b in set(a.rx.downstream())
        True
        """
        reactive = self._reactive
        if not isinstance(reactive, rx):
            return
        downstream = reactive._downstream()
        next(downstream, None)  # Skip itself.
        yield from downstream

    def updating(self) -> 'rx':
        """
        Return a new expression that indicates whether the current expression is updating.

        This method creates a reactive expression that evaluates to ``True`` while the
        current expression is in the process of updating and ``False`` otherwise. This
        can be useful for tracking or reacting to the update state of an expression,
        such as displaying loading indicators or triggering conditional logic.

        Also tracks asynchronous operations feeding the expression (e.g. via
        ``.rx.pipe``) for the whole time ``.rx.awaiting`` is ``True``, not just the
        instant the operation is scheduled or finishes, including one reached only
        through an ``.rx.overrides`` replacement or a ``Parameter(allow_refs=True)``
        fn param, even if the override/ref is set after this method was called.

        Returns
        -------
        ReactiveExpression
            A reactive expression that is ``True`` while the current expression is updating
            and ``False`` otherwise.

        Examples
        --------
        Create a reactive expression and track its update state:

        >>> import param
        >>> rx_value = param.rx(1)

        Create an updating tracker:

        >>> updating = rx_value.rx.updating()
        >>> updating.rx.value
        False

        Simulate an update and observe the change in the updating tracker:

        >>> rx_value.rx.value = 2
        >>> updating.rx.value  # Becomes True during the update process, then False.
        False
        """
        reactive = self._reactive
        # Keyed by `id()`, not the node: a `WeakSet` wraps each membership
        # check in a fresh `weakref.ref`, and `weakref.ref.__eq__` compares
        # referents whenever both are alive - even for two wrappers of the
        # *same* node, since it has no identity fast path of its own - which
        # for two `rx` nodes calls `rx.__eq__`, building a comparison
        # expression rather than a bool. Weak values so a node dropped from
        # the graph (e.g. a cleared override) isn't pinned here forever.
        tracked: dict[int, weakref.ref] = {}
        # `_upstream()` as of the last `rederive()`, so `mark_settling()` can
        # check membership in O(1).
        current: set[rx] = set()

        def recompute() -> None:
            wrapper.param.update(object=any(node._settling for node in current))

        def mark_settling(node: 'rx') -> None:
            # Fired on both settle-schedule and settle-completion (see
            # `_notify_settle_change`'s callers), so recheck the aggregate
            # rather than forcing True: a settle that finishes without
            # changing this expression's own value (e.g. behind a `* 0`, or
            # because the settling node was removed from an override
            # mid-flight) would otherwise never flip `wrapper` back to
            # False. `node` may also have since dropped out of `_upstream()`
            # (e.g. a cleared override); ignore a stale notification rather
            # than let it resurrect `wrapper`. Shared across every node
            # (told apart by the argument) rather than a closure per node,
            # so nothing here holds a reference back to it.
            if node in current:
                recompute()

        def subscribe(node: 'rx') -> None:
            node_id = id(node)
            if node_id in tracked:
                return
            tracked[node_id] = weakref.ref(node, lambda ref: tracked.pop(node_id, None))
            node._watch_settle_change(mark_settling)
            # Re-derive if this node's own inputs change shape, so a node
            # added through an override/ref rewire gets found too.
            node._watch_graph_change(rederive)

        def rederive() -> None:
            if isinstance(reactive, rx):
                nonlocal current
                # Swap in a full replacement rather than mutating `current`
                # in place, so a concurrent `mark_settling()` never sees a
                # node's membership toggled off before it toggles back on.
                new_current = set(reactive._upstream())
                for node in new_current:
                    subscribe(node)
                current = new_current
                # A node already tracked (e.g. one briefly out of and back
                # into an override) is skipped by `subscribe()` above
                # without rechecking it, so recompute here too, catching one
                # that re-entered already settling.
                recompute()

        upstream = list(reactive._upstream()) if isinstance(reactive, rx) else []
        current.update(upstream)
        # Report the correct state immediately if already mid-flight.
        initial = any(node._settling for node in upstream)
        wrapper = t.cast('Callable', Wrapper)(object=initial)
        # `_watch_graph_change`/`_watch_settle_change` hold their callbacks
        # weakly, so keep them alive for as long as `wrapper` (and thus the
        # returned expression) is.
        wrapper._rederive = rederive
        wrapper._mark_settling = mark_settling

        self._watch(lambda e: wrapper.param.update(object=True), precedence=-999)
        self._watch(lambda e: wrapper.param.update(object=False), precedence=999)

        for node in upstream:
            subscribe(node)

        return wrapper.param.object.rx()

    def when(self, *dependencies, initial=Undefined) -> 'rx':
        """
        Create a reactive expression that updates only when specified dependencies change.

        This method creates a new reactive expression that emits the value of the
        current expression only when one of the provided dependencies changes. If
        all dependencies are of type :class:`param.Event` and an initial value is provided,
        the expression will not be evaluated until the first event is triggered.

        Parameters
        ----------
        dependencies : Parameter or reactive expression rx
            Dependencies that trigger an update in the reactive expression.
        initial : object, optional
            A placeholder value that is used until a dependency event is triggered.
            Defaults to ``Undefined``.

        Returns
        -------
        rx
            A reactive expression that updates when the specified dependencies change.

        Examples
        --------
        Use ``.when`` to control when a reactive expression updates:

        >>> import param
        >>> from param import rx
        >>> from time import sleep

        Define an expensive function:

        >>> def expensive_function(a, b):
        ...     print(f'multiplying {a=} and {b=}')
        ...     sleep(1)
        ...     return a * b

        Create reactive values:

        >>> a = rx(1)
        >>> b = rx(2)

        Define a state with an event parameter:

        >>> class State(param.Parameterized):
        ...     submit = param.Event()

        >>> state = State()

        Create a gated reactive expression that only updates when the ``submit`` event is triggered:

        >>> gated_expr = rx(expensive_function)(a, b).rx.when(state.param.submit, initial="Initial Value")
        >>> gated_expr.rx.value
        'Initial Value'

        Trigger the update by setting the `submit` event:

        >>> state.submit = True
        >>> gated_expr.rx.value
        multiplying a=1 and b=2
        2
        """
        deps = [p for d in dependencies for p in resolve_ref(d)]
        is_event = all(isinstance(dep, Event) for dep in deps)
        def eval(*_, evaluated=[]):
            if is_event and initial is not Undefined and not evaluated:
                # Abuse mutable default value to keep track of evaluation state
                evaluated.append(True)
                return initial
            else:
                return self.value
        return t.cast('t.Any', bind(eval, *deps)).rx()

    def where(self, x, y) -> 'rx':
        """
        Return either ``x`` or ``y`` depending on the current state of the expression.

        This method implements a reactive version of a ternary conditional expression.
        It evaluates the current reactive expression as a condition and returns ``x``
        if the condition is ``True``, or ``y`` if the condition is ``False``.

        Parameters
        ----------
        x : object
            The value to return if the reactive condition evaluates to ``True``.
        y : object
            The value to return if the reactive condition evaluates to ``False``.

        Returns
        -------
        rx
            A reactive expression that evaluates to ``x`` or ``y`` based on the current
            state of the condition.

        Examples
        --------
        Use ``.where`` to implement a reactive conditional:

        >>> import param
        >>> rx_value = param.rx(True)
        >>> rx_result = rx_value.rx.where("Condition is True", "Condition is False")

        Check the result when the condition is ``True``:

        >>> rx_result.rx.value
        'Condition is True'

        Change the reactive condition and observe the updated result:

        >>> rx_value.rx.value = False
        >>> rx_result.rx.value
        'Condition is False'

        Combine ``.where`` with reactive expressions for dynamic updates:

        >>> rx_num = param.rx(10)
        >>> rx_condition = rx_num > 5
        >>> rx_result = rx_condition.rx.where("Above 5", "5 or below")
        >>> rx_result.rx.value
        'Above 5'

        Update the reactive value and see the conditional result change:

        >>> rx_num.rx.value = 3
        >>> rx_result.rx.value
        '5 or below'
        """
        xrefs = resolve_ref(x)
        yrefs = resolve_ref(y)
        if isinstance(self._reactive, rx):
            params = self._reactive._params
        else:
            params = resolve_ref(self._reactive)
        trigger = Trigger(parameters=params)
        if xrefs:
            def trigger_x(*args):
                if t.cast("bool", self.value):
                    trigger.param.trigger('value')
            bind(trigger_x, *xrefs, watch=True)
        if yrefs:
            def trigger_y(*args):
                if not t.cast("bool", self.value):
                    trigger.param.trigger('value')
            bind(trigger_y, *yrefs, watch=True)

        def ternary(condition, _):
            return resolve_value(x) if condition else resolve_value(y)
        return t.cast('t.Any', bind(ternary, self._reactive, trigger.param.value))

    # Operations to get the output and set the input of an expression

    def set(self, value):
        """
        Set the input of the pipeline to a new value. Equivalent
        to ``.rx.value = value``.

        Parameters
        ----------
        value : object
            The value to set the pipeline input to.
        """
        self.value = value

    @property
    def value(self):
        """
        Get or set the current state of the reactive expression.

        When getting the value it evaluates the reactive expression, resolving all operations
        and dependencies to return the current value. The value reflects the
        latest state of the expression after applying all transformations or updates.

        Returns
        -------
        any
            The current value of the reactive expression, resolved based on the
            operations and dependencies in its pipeline.

        Examples
        --------
        Access the value of a basic reactive expression:

        >>> import param
        >>> rx_value = param.rx(10)
        >>> rx_value.rx.value
        10

        Update the reactive expression and retrieve the updated value:

        >>> rx_value.rx.value = 20
        >>> rx_value.rx.value
        20

        Evaluate a reactive pipeline:

        >>> rx_pipeline = rx_value.rx.pipe(lambda x: x * 2)
        >>> rx_pipeline.rx.value
        40
        """
        if isinstance(self._reactive, rx):
            return self._reactive._resolve()
        elif isinstance(self._reactive, Parameter):
            owner = self._reactive.owner
            name = self._reactive.name
            if owner is None or name is None:
                return None
            return getattr(owner, name)
        else:
            return self._reactive()

    @value.setter
    def value(self, new):
        """
        Get or set the current state of the reactive expression.

        When getting the value it evaluates the reactive expression, resolving all operations
        and dependencies to return the current value. The value reflects the
        latest state of the expression after applying all transformations or updates.

        Returns
        -------
        any
            The current value of the reactive expression, resolved based on the
            operations and dependencies in its pipeline.

        Examples
        --------
        Access the value of a basic reactive expression:

        >>> import param
        >>> rx_value = param.rx(10)
        >>> rx_value.rx.value
        10

        Update the reactive expression and retrieve the updated value:

        >>> rx_value.rx.value = 20
        >>> rx_value.rx.value
        20

        Evaluate a reactive pipeline:

        >>> rx_pipeline = rx_value.rx.pipe(lambda x: x * 2)
        >>> rx_pipeline.rx.value
        40
        """
        if isinstance(self._reactive, Parameter):
            raise AttributeError(
                "`Parameter.rx.value = value` is not supported. Cannot override "
                "parameter value."
            )
        elif not isinstance(self._reactive, rx):
            raise AttributeError(
                "`bind(...).rx.value = value` is not supported. Cannot override "
                "the output of a function."
            )
        elif self._reactive._root is not self._reactive:
            raise AttributeError(
                "The value of a derived expression cannot be set. Ensure you "
                "set the value on the root node wrapping a concrete value, e.g.:"
                "\n\n    a = rx(1)\n    b = a + 1\n    a.rx.value = 2\n\n "
                "is valid but you may not set `b.rx.value = 2`."
            )
        if self._reactive._wrapper is None:
            raise AttributeError(
                "Setting the value of a reactive expression is only "
                "supported if it wraps a concrete value. A reactive "
                "expression wrapping a Parameter or another dynamic "
                "reference cannot be updated."
            )
        self._reactive._wrapper.object = resolve_value(new)

    def watch(self, fn=None, onlychanged=True, queued=False, precedence=0):
        """
        Add a callback to observe changes in the reactive expression's output.

        This method allows you to attach a callable function (``fn``) that will be
        invoked whenever the output of the reactive expression changes. The callback
        can be either a regular or asynchronous function. If no callable is provided,
        the expression is eagerly evaluated whenever it updates.

        Parameters
        ----------
        fn : callable or coroutine function, optional
            The function to be called whenever the reactive expression changes.
            For function should accept a single argument, which is the new value
            of the reactive expression. If no function provided, the expression
            is simply evaluated eagerly.

        Returns
        -------
        list[param.parameterized.Watcher]
            The watcher(s) this call registered. Pass to :meth:`unwatch` to
            stop just this callback.

        Raises
        ------
        ValueError
            If ``precedence`` is negative, as negative precedences are reserved
            for internal watchers.

        Examples
        --------
        Attach a regular callback to print the updated value:

        >>> import param
        >>> rx_value = param.rx(10)
        >>> watcher = rx_value.rx.watch(lambda v: print(f"Updated value: {v}"))

        Update the reactive value to trigger the callback:

        >>> rx_value.rx.value = 20
        Updated value: 20

        Attach an asynchronous callback:

        >>> import asyncio
        >>> async def async_callback(value):
        ...     await asyncio.sleep(1)
        ...     print(f"Async updated value: {value}")
        >>> _ = rx_value.rx.watch(async_callback)

        Trigger the async callback:

        >>> rx_value.rx.value = 30
        Async updated value: 30  # Printed after a 1-second delay.
        """
        if precedence < 0:
            raise ValueError("User-defined watch callbacks must declare "
                             "a positive precedence. Negative precedences "
                             "are reserved for internal Watchers.")
        elif isinstance(self._reactive, rx) and self._reactive._lazy:
            warnings.warn("Watching a lazy expressions converts it into an eager expression.")
        return self._watch(fn, onlychanged=onlychanged, queued=queued, precedence=precedence)

    def _watch(self, fn=None, onlychanged=True, queued=False, precedence=0):
        last = _unset = object()
        def cb(value):
            from .parameterized import async_executor
            nonlocal last
            if fn is None:
                return
            if onlychanged and last is not _unset and Comparator.is_equal(value, last):
                return
            last = value
            if iscoroutinefunction(fn):
                async_executor(partial(fn, value))
            else:
                fn(value)
        bound = t.cast('t.Any', bind(cb, self._reactive, watch=True))
        watchers = list(bound._watchers)
        reactive = self._reactive
        if isinstance(reactive, rx):
            live = reactive._watchers
            if live is None:
                live = reactive._watchers = []
            live.extend(watchers)
        return watchers

    def unwatch(self, watcher) -> None:
        """
        Undo a previous call to :meth:`watch`.

        Parameters
        ----------
        watcher : param.parameterized.Watcher or list[param.parameterized.Watcher]
            The value :meth:`watch` returned.

        Examples
        --------
        >>> import param
        >>> rx_value = param.rx(10)
        >>> watcher = rx_value.rx.watch(lambda v: print(f"Updated value: {v}"))
        >>> rx_value.rx.unwatch(watcher)
        >>> rx_value.rx.value = 20  # No longer prints anything.
        """
        watchers = watcher if isinstance(watcher, list) else [watcher]
        for w in watchers:
            w.remove()
        reactive = self._reactive
        if isinstance(reactive, rx) and reactive._watchers:
            for w in watchers:
                if w in reactive._watchers:
                    reactive._watchers.remove(w)

    def dispose(self, cascade: builtins.bool = True) -> None:
        """
        Release the invalidation watchers this expression attached to its
        upstream ``Parameterized`` sources, instead of waiting for it to be
        garbage collected.

        Raises if the expression still has a reader, another node built
        from it or a live :meth:`watch` on it (call :meth:`unwatch` first),
        rather than leaving that reader looking at a value that has stopped
        updating. If this was the only reader of one of its inputs, that
        input is disposed too; one still read elsewhere is left alone.
        ``cascade=False`` disposes only this expression, never its inputs,
        for a reader ``dispose()`` cannot see, e.g. a ``Parameter`` with
        ``allow_refs=True``, or a :func:`bind`/``pn.bind`` consumer. Either
        way, using a disposed expression afterwards (reading its value, or
        building a new one from it) raises rather than returning a stale
        value.

        Whether an input actually gets disposed can depend on
        ``gc.collect()`` having run first: branching (``b = a + 1``) clones
        the input into a hidden reader that sits in a reference cycle only
        the cyclic collector can break.

        A no-op if ``self`` does not wrap an ``rx`` expression, or if called
        more than once.

        Examples
        --------
        >>> import param
        >>> a = param.rx(1)
        >>> b = a + 1
        >>> b.rx.dispose()
        """
        if isinstance(self._reactive, rx):
            self._reactive._dispose(cascade=cascade)


def _first_reactive_error(args, kwargs):
    for a in args:
        if isinstance(a, ReactiveError):
            return a
    for v in kwargs.values():
        if isinstance(v, ReactiveError):
            return v
    return None


@t.overload
def bind(
    function: Callable[_P, Generator[_Y, t.Any, t.Any]], *args: t.Any,
    watch: bool = False, process_failures: bool = False, **kwargs: t.Any
) -> Callable[_P, Generator[_Y, t.Any, t.Any]]: ...


@t.overload
def bind(
    function: Callable[_P, AsyncGenerator[_Y, t.Any]], *args: t.Any,
    watch: bool = False, process_failures: bool = False, **kwargs: t.Any
) -> Callable[_P, AsyncGenerator[_Y, t.Any]]: ...


@t.overload
def bind(
    function: Callable[_P, Coroutine[t.Any, t.Any, _R]], *args: t.Any,
    watch: bool = False, process_failures: bool = False, **kwargs: t.Any
) -> Callable[_P, Coroutine[t.Any, t.Any, _R]]: ...


@t.overload
def bind(
    function: Callable[_P, _R], *args: t.Any,
    watch: bool = False, process_failures: bool = False, **kwargs: t.Any
) -> Callable[_P, _R]: ...


def bind(
    function: Callable[..., t.Any], *args: t.Any, watch: bool = False,
    process_failures: bool = False, **kwargs: t.Any
) -> Callable[..., t.Any]:
    """
    Bind constant values, parameters, bound functions or reactive expressions to a function.

    This function creates a wrapper around the given ``function``, binding some or
    all of its arguments to constant values, :class:`Parameter` objects, or
    reactive expressions. The resulting function automatically reflects updates
    to any bound parameters or reactive expressions, ensuring that its output
    remains up-to-date.

    Similar to :func:`functools.partial`, arguments can also be bound to constants,
    leaving a simple callable object. When ``watch=True``, the function is
    automatically evaluated whenever any bound parameter or reactive expression changes.

    Parameters
    ----------
    function : callable, generator, async generator, or coroutine
        The function or coroutine to bind constant, dynamic, or reactive arguments to.
        It can be:

        - A standard callable (e.g., a regular function).
        - A generator function (producing iterables).
        - An async generator function (producing asynchronous iterables).
        - A coroutine function (producing awaitables).
    *args : object, Parameter, bound function or reactive expression rx
        Positional arguments to bind to the function. These can be constants,
        `param.Parameter` objects, bound functions or reactive expressions.
    watch : bool, optional
        If `True`, the function is automatically evaluated whenever a bound
        parameter or reactive expression changes. Defaults to `False`.
    process_failures : bool, optional
        If `False` (the default), a bound argument that resolves to a
        `ReactiveError` short-circuits the call: `function` is not invoked
        and the `ReactiveError` is returned (or yielded) unchanged. If
        `True`, the `ReactiveError` is passed to `function` like any other
        value. Defaults to `False`.

        .. versionadded:: 2.5.0
    **kwargs : object, Parameter, bound function or reactive expression rx
        Keyword arguments to bind to the function. These can also be constants,
        `param.Parameter` objects, bound functions or reactive expressions.

    Returns
    -------
    callable, generator, async generator, or coroutine
        A new function with the bound arguments, annotated with all dependencies.
        The function reflects changes to bound parameters or reactive expressions.

    Notes
    -----
    `process_failures` is consumed by `bind` itself, so a `function` that
    expects its own keyword argument literally named `process_failures` will
    no longer have it forwarded from `**kwargs`; rename that argument on
    `function` to avoid the collision.

    Examples
    --------
    Bind parameters to a function:

    >>> import param
    >>> class Example(param.Parameterized):
    ...     a = param.Number(1)
    ...     b = param.Number(2)
    >>> example = Example()
    >>> def add(a, b):
    ...     return a + b
    >>> bound_add = param.bind(add, example.param.a, example.param.b)
    >>> bound_add()
    3

    Update a parameter and observe the updated result:

    >>> example.a = 5
    >>> bound_add()
    7

    Automatically evaluate the function when bound arguments change:

    >>> bound_watch = param.bind(print, example.param.a, example.param.b, watch=True)
    >>> example.a = 1  # Triggers automatic evaluation
    1 2
    """
    args, kwargs = (
        tuple(transform_reference(arg) for arg in args),
        {key: transform_reference(arg) for key, arg in kwargs.items()}
    )
    dependencies = {}

    # If the wrapped function has a dependency add it
    fn_dep = transform_reference(function)
    if isinstance(fn_dep, Parameter) or hasattr(fn_dep, '_dinfo'):
        dependencies['__fn'] = fn_dep

    # Extract dependencies from args and kwargs
    for i, p in enumerate(args):
        if hasattr(p, '_dinfo'):
            for j, arg in enumerate(p._dinfo['dependencies']):
                dependencies[f'__arg{i}_arg{j}'] = arg
            for kw, kwarg in p._dinfo['kw'].items():
                dependencies[f'__arg{i}_arg_{kw}'] = kwarg
        elif isinstance(p, Parameter):
            dependencies[f'__arg{i}'] = p
    for kw, v in kwargs.items():
        if hasattr(v, '_dinfo'):
            for j, arg in enumerate(v._dinfo['dependencies']):
                dependencies[f'__kwarg_{kw}_arg{j}'] = arg
            for pkw, kwarg in v._dinfo['kw'].items():
                dependencies[f'__kwarg_{kw}_{pkw}'] = kwarg
        elif isinstance(v, Parameter):
            dependencies[kw] = v

    def combine_arguments(wargs, wkwargs, asynchronous=False):
        combined_args = []
        for arg in args:
            if hasattr(arg, '_dinfo'):
                arg = eval_function_with_deps(arg)  # type: ignore[arg-type]
            elif isinstance(arg, Parameter):
                if arg.owner is not None and arg.name is not None:
                    arg = getattr(arg.owner, arg.name)
            combined_args.append(arg)
        combined_args += list(wargs)

        combined_kwargs = {}
        for kw, arg in kwargs.items():
            if hasattr(arg, '_dinfo'):
                arg = eval_function_with_deps(arg)  # type: ignore[arg-type]
            elif isinstance(arg, Parameter):
                if arg.owner is not None and arg.name is not None:
                    arg = getattr(arg.owner, arg.name)
            combined_kwargs[kw] = arg
        for kw, arg in wkwargs.items():
            if asynchronous:
                if kw.startswith('__arg'):
                    index = kw[5:]
                    if index.isdigit():
                        combined_args[int(index)] = arg
                elif kw.startswith('__kwarg'):
                    substring = kw[8:]
                    if substring in combined_kwargs:
                        combined_kwargs[substring] = arg
                continue
            elif kw.startswith('__arg') or kw.startswith('__kwarg') or kw.startswith('__fn'):
                continue
            combined_kwargs[kw] = arg
        return combined_args, combined_kwargs

    def eval_fn():
        if callable(function):
            fn = function
        else:
            p = transform_reference(function)
            if isinstance(p, Parameter):
                if p.owner is None or p.name is None:
                    raise ValueError("Referenced Parameter is unbound.")
                fn = getattr(p.owner, p.name)
            else:
                fn = eval_function_with_deps(p)
        return fn

    wrapped: Callable[..., t.Any]
    if inspect.isgeneratorfunction(function):
        def wrapped_gen(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            if not process_failures:
                err = _first_reactive_error(combined_args, combined_kwargs)
                if err is not None:
                    yield err
                    return
            evaled: Iterable[t.Any] = eval_fn()(*combined_args, **combined_kwargs)
            for val in evaled:
                yield val
        wrapper_fn = t.cast('Callable', depends)(**dependencies, watch=watch)(wrapped_gen)
        t.cast('t.Any', wrapped_gen)._dinfo = wrapper_fn._dinfo
        t.cast('t.Any', wrapped_gen)._watchers = wrapper_fn._watchers
        wrapped = wrapped_gen
    elif inspect.isasyncgenfunction(function):
        async def wrapped_async_gen(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            if not process_failures:
                err = _first_reactive_error(combined_args, combined_kwargs)
                if err is not None:
                    yield err
                    return
            evaled: t.Any = eval_fn()(*combined_args, **combined_kwargs)
            async for val in evaled:
                yield val
        wrapper_fn = t.cast('Callable', depends)(**dependencies, watch=watch)(wrapped_async_gen)
        t.cast('t.Any', wrapped_async_gen)._dinfo = wrapper_fn._dinfo
        t.cast('t.Any', wrapped_async_gen)._watchers = wrapper_fn._watchers
        wrapped = wrapped_async_gen
    elif iscoroutinefunction(function):
        @t.cast('Callable', depends)(**dependencies, watch=watch)
        async def wrapped_coro(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            if not process_failures:
                err = _first_reactive_error(combined_args, combined_kwargs)
                if err is not None:
                    return err
            evaled: t.Any = eval_fn()(*combined_args, **combined_kwargs)
            return await evaled
        wrapped = wrapped_coro
    else:
        @t.cast('t.Any', depends)(**dependencies, watch=watch)
        def wrapped_sync(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(wargs, wkwargs)
            if not process_failures:
                err = _first_reactive_error(combined_args, combined_kwargs)
                if err is not None:
                    return err
            return eval_fn()(*combined_args, **combined_kwargs)
        wrapped = wrapped_sync
    t.cast('t.Any', wrapped).__bound_function__ = function
    t.cast('t.Any', wrapped).rx = reactive_ops(wrapped)
    _reactive_display_objs.add(wrapped)
    for name, accessor in _display_accessors.items():
        setattr(wrapped, name, t.cast('Callable', accessor)(wrapped))
    return wrapped

class _WeakInvalidator:
    """
    A weakly-bound invalidation callback for an ``rx`` pipeline node.

    ``rx`` nodes register invalidation callbacks on their *source* parameters.
    If those callbacks were strong bound-method references the source (which is
    typically long-lived) would keep every derived node — and anything it
    captured, such as large arrays — alive indefinitely. Wrapping the bound
    method in a :class:`weakref.WeakMethod` lets the derived node be garbage
    collected as soon as nothing else references it; once collected the call
    becomes a no-op and the now-dead watcher is removed by a finalizer (see
    ``rx._watch_invalidation``).
    """

    __slots__ = ('_ref', '_watcher', '__weakref__')

    _watcher: Watcher | None

    def __init__(self, method):
        self._ref = weakref.WeakMethod(method)
        self._watcher = None

    def __call__(self, *events):
        method = self._ref()
        if method is not None:
            return method(*events)


def _remove_watcher(
    owner_ref: weakref.ref[Parameterized | type[Parameterized]],
    invalidator_ref: weakref.ref[_WeakInvalidator],
) -> None:
    """
    Unwatch a dead node's invalidation watcher, ignoring if it is already gone.

    Both refs must be weak: ``weakref.finalize`` holds its arguments until the
    referent dies, so a strong owner (or ``Watcher``, whose ``inst`` is the
    owner) would make the node uncollectable. ``Watcher`` subclasses ``tuple``
    and cannot be weakly referenced, so it is reached via the invalidator.
    """
    owner, invalidator = owner_ref(), invalidator_ref()
    if owner is None or invalidator is None or invalidator._watcher is None:
        return
    try:
        owner.param.unwatch(invalidator._watcher)
    except Exception:
        pass


async def _close_stale(obj):
    """
    Discard an awaitable or async generator whose result is no longer needed.

    Closing a coroutine that was never awaited also suppresses the warning
    Python emits when it is garbage collected.
    """
    try:
        if inspect.isasyncgen(obj):
            await obj.aclose()
        elif inspect.iscoroutine(obj):
            obj.close()
    except (StopAsyncIteration, GeneratorExit):
        pass
    except Exception:
        logger.debug(
            "Ignoring close error for stale reactive task.",
            exc_info=True,
        )


def _collect_marker(*args, **kwargs):
    """Serve as a placeholder `fn` for a `collect` operation; `_eval_collect` never calls it."""
    raise NotImplementedError


def _safe_is_equal(a, b):
    """
    Like `Comparator.is_equal`, but never lets a value's own `==` (e.g. a
    numpy array's, which is elementwise and not a bool) raise or produce a
    non-bool result; either case is treated as "not equal" so it doesn't
    wrongly skip publishing a genuinely changed slot.
    """
    if a is b:
        return True
    try:
        return bool(Comparator.is_equal(a, b))
    except Exception:
        return False


Collected = namedtuple('Collected', ['args', 'kwargs'])


def collect(*args, error_mode='raise', **kwargs) -> 'rx':
    """
    Combine several inputs into a :class:`Collected` namedtuple of
    whichever have settled, without waiting for the slowest one.

    ``args``/``kwargs`` fields hold each positional/keyword input's latest
    value, and can be piped further, e.g. ``collect(a, b).args.rx.pipe(sum)``.
    A slot keeps its last value while its input is unsettled again, or
    holds ``Undefined`` if it has never settled; a downstream function fed
    an unsettled slot should account for that, e.g. by checking
    ``.rx.awaiting`` first.

    Parameters
    ----------
    *args, **kwargs : any
        The inputs to collect, typically ``rx`` expressions. A
        non-reactive value is included immediately. ``error_mode`` is
        reserved and can't be one of the collected keyword inputs.
    error_mode : {"raise", "propagate"}, default "raise"
        With "propagate", a failing input resolves to a
        :class:`ReactiveError` in its slot instead of failing every other
        slot too. With "raise" (the default), a failing input fails the
        whole node.

    Returns
    -------
    rx
        A reactive :class:`Collected` namedtuple of the inputs' latest
        values.

    Examples
    --------
    >>> import param
    >>> a, b = param.rx(1), param.rx(2)
    >>> collected = param.reactive.collect(a, b)
    >>> collected.rx.value
    Collected(args=(1, 2), kwargs=mappingproxy({}))
    >>> collected.args.rx.pipe(sum).rx.value
    3
    """
    operation = {
        'fn': _collect_marker,
        'args': args,
        'kwargs': kwargs,
    }
    return rx(None, operation=operation, _current=Undefined, error_mode=error_mode)


# When we only support python >= 3.11 we should exchange 'rx' with Self type annotation below.
# See https://peps.python.org/pep-0673/

_current_node: contextvars.ContextVar[rx | None] = contextvars.ContextVar(
    '_current_node', default=None
)


def current_node() -> rx | None:
    """
    Return the node currently being resolved, or ``None``.

    Set only while a node's own operation function is actually running, using
    a ``contextvars.ContextVar``, so concurrent async nodes on the same event
    loop each see their own node. Not set while an operation's arguments are
    being resolved, nor while watchers are notified of a new value, so it
    never leaks into an unrelated function's execution.

    Only meaningful when called from inside the body of a function passed
    to an operation (``.rx.pipe``, ``bind``, an arithmetic operator, etc.)
    while that operation is being evaluated for a specific node. Lets a
    body attach data to ``.rx.meta`` on the exact node its computation
    belongs to, without that node being passed to it as an argument:

    >>> def kernel(price, fx):
    ...     node = param.current_node()
    ...     if node is not None:
    ...         node.rx.meta['trace'] = {'fx_used': fx}
    ...     return price * fx

    Returns ``None`` outside of any operation body (including in plain user
    code, tests, or a REPL), so callers should guard rather than chain
    straight through to ``.rx.meta``.

    Returns
    -------
    rx | None
        The node being resolved, or ``None`` if called outside of an
        operation's evaluation.
    """
    return _current_node.get()


class rx:
    """
    A class for creating reactive expressions by wrapping objects.

    The ``rx`` class allows you to wrap objects and operate on them interactively,
    recording any operations applied. These recorded operations form a pipeline
    that can be replayed dynamically when an operand changes. This makes ``rx``
    particularly useful for building reactive workflows, such as real-time data
    processing or dynamic user interfaces.

    Parameters
    ----------
    obj : any
        The object to wrap, such as a number, string, list, or any supported
        data structure.
    error_mode : {"raise", "propagate"}, default "raise"
        Whether exceptions raised while evaluating the expression should be
        re-raised or represented as :class:`ReactiveError` values.
    label : str, optional
        An optional human-readable label for this node. Read back via
        ``expr.rx.error.label`` on a `ReactiveError` this node (or a node
        derived from it while inheriting the label) produced. `None` if
        never set. Can also be read and set after construction via
        ``expr.rx.label``.

        .. versionadded:: 2.5.0

    References
    ----------
    For more details, see the user guide:
    https://param.holoviz.org/user_guide/Reactive_Expressions.html

    Examples
    --------
    Instantiate :class:`rx` from an object:

    >>> from param import rx
    >>> reactive_float = rx(3.14)

    Perform operations on the reactive object:

    >>> reactive_result = reactive_float * 2
    >>> reactive_result.value
    6.28

    Update the original value and see the updated result:

    >>> reactive_float.value = 1
    >>> reactive_result.rx.value
    2

    Create a reactive list and compute its length reactively:

    >>> reactive_list = rx([1, 2, 3])
    >>> reactive_length = reactive_list.rx.len()
    >>> reactive_length.rx.value
    3
    """

    _accessors: dict[str, tuple[Callable[[t.Any], t.Any], Callable[[t.Any], bool] | None, bool]] = {}

    _display_options: tuple[str, ...] = ()

    _display_handlers: dict[type, tuple[t.Any, dict[str, t.Any]]] = {}

    _method_handlers: dict[str, Callable] = {}

    # Declared on the class so a node using none of this allocates nothing.
    _override_channel: Trigger | None = None

    _readers: list[weakref.ref] | None = None

    _ref_binding: Callable[..., t.Any] | None = None

    # Weak refs to targets notified when this node schedules async work.
    _settle_watchers: list[weakref.ref] | None = None

    # See `_watch_graph_change()`.
    _graph_watchers: list[weakref.ref] | None = None

    # This node's own invalidation watchers, run early by `_dispose()`.
    _finalizers: list[weakref.finalize] | None = None

    # Watchers registered through `.rx.watch()`; a reader like `_readers`.
    _watchers: list[Watcher] | None = None

    _disposed: bool = False

    # `__eq__` builds an expression, not a bool, so it can't disagree with a
    # hash; restored explicitly so a node can be a `dict` key or `set` member.
    __hash__ = object.__hash__

    @classmethod
    def register_accessor(
        cls, name: str, accessor: Callable[[t.Any], t.Any],
        predicate: Callable[[t.Any], bool] | None = None,
        memoize: bool = True
    ):
        """
        Register an accessor that extends ``rx`` with custom behavior.

        Accessors are instantiated lazily the first time it is accessed on a given
        node. If a ``predicate`` is provided it is evaluated against the node's
        current value at that point in time. If it does not evaluate as true the first
        time, e.g. because the value has not yet settled, it may still be created on
        subsequent accesses.

        Parameters
        ----------
        name: str
          The name of the accessor will be attribute-accessible under.
        accessor: Callable[[rx], any]
          A callable that will return the accessor namespace object
          given the ``rx`` object it is registered on.
        predicate: Callable[[Any], bool] | None
          Called with the node's current value the first time ``name`` is
          accessed on that node; the accessor is only instantiated if a
          callable returns True or if ``predicate`` is None.
        memoize: bool
          Whether to cache the instantiated accessor on the node after the
          first successful access (the default). If ``False`` the accessor
          is re-instantiated, and its ``predicate`` re-evaluated against the
          node's current value, on every access.

        """
        cls._accessors[name] = (accessor, predicate, memoize)

    @classmethod
    def register_display_handler(cls, obj_type, handler, **kwargs):
        """
        Register a display handler for a specific type of object.

        Makes it possible to define custom display options for
        specific objects.

        Parameters
        ----------
        obj_type: type | callable
          The type to register a custom display handler on.
        handler: Viewable | callable
          A Viewable or callable that is given the object to be displayed
          and the custom keyword arguments.
        kwargs: dict[str, Any]
          Additional display options to register for this type.

        """
        cls._display_handlers[obj_type] = (handler, kwargs)

    @classmethod
    def register_method_handler(cls, method, handler):
        """
        Register a handler that is called when a specific method on
        an object is called.
        """
        cls._method_handlers[method] = handler

    def __new__(cls, obj=None, **kwargs):
        wrapper = None
        obj = transform_reference(obj)
        if kwargs.get('fn'):
            # rx._clone codepath
            fn = kwargs.pop('fn')
            wrapper = kwargs.pop('_wrapper', None)
        elif inspect.isgeneratorfunction(obj) or iscoroutinefunction(obj):
            # Resolves generator and coroutine functions lazily
            wrapper = t.cast('Callable', GenWrapper)(object=obj)
            fn = bind(lambda obj: obj, wrapper.param.object)
            obj = Undefined
        elif isinstance(obj, (FunctionType, MethodType)) and hasattr(obj, '_dinfo'):
            # Bound functions and methods are resolved on access
            fn = obj
            obj = None
        elif isinstance(obj, Parameter):
            fn = bind(lambda obj: obj, obj)
            if obj.owner is not None and obj.name is not None:
                obj = getattr(obj.owner, obj.name)
            else:
                obj = None
        else:
            # For all other objects wrap them so they can be updated
            # via .rx.value property
            wrapper = t.cast('Callable', Wrapper)(object=obj)
            fn = bind(lambda obj: obj, wrapper.param.object)
        inst = super(rx, cls).__new__(cls)
        inst._fn = fn
        inst._shared_obj = kwargs.get('_shared_obj', None if obj is None else [obj])
        inst._wrapper = wrapper
        return inst

    def __init__(
        self, obj=None, operation=None, fn=None, depth=0, method=None, prev=None, lazy=False,
        _shared_obj=None, _current=None, _wrapper=None, _shared=None, error_mode='raise',
        label=None,
        **kwargs
    ):
        # _init is used to prevent to __getattribute__ to execute its
        # specialized code.
        self._init = False
        display_opts = {}
        for _, opts in self._display_handlers.values():
            for k, o in opts.items():
                display_opts[k] = o
        display_opts.update({
            dopt: kwargs.pop(dopt) for dopt in self._display_options + tuple(display_opts)
            if dopt in kwargs
        })
        self._display_opts = display_opts
        self._lazy = lazy
        self._method = method
        self._operation = operation
        self._depth = depth
        self._dirty = _current is None or _current is Undefined
        self._dirty_obj = False
        self._current_task = None
        self._resolve_generation = 0
        self._finished_generation = 0
        self._skipped = False
        self._error_state = None
        self._error_mode = error_mode
        if error_mode not in ('raise', 'propagate'):
            raise ValueError("error_mode must be either 'raise' or 'propagate'")
        self._label = label
        self._current_ = _current
        self._meta: dict[t.Any, t.Any] | None = None  # Do not allocate unless needed
        self._live_params_cache: set[tuple[int, str | None]] | None = None
        # _shared is used for branching rx pipelines where we clone the input.
        # Here we store the original shared input, which makes it possible to
        # cache the input value as long as the shared instance does not store
        # a diverging _method accessor.
        self._shared = _shared
        if isinstance(obj, rx) and not prev:
            self._prev = obj
        else:
            self._prev = t.cast('rx', prev)
        # Reverse of `_direct_inputs()`, not `_upstream()` (see
        # `_direct_inputs()` for why refs are excluded).
        for inp in self._direct_inputs():
            inp._register_reader(self)

        # Define special trigger parameter if operation has to be lazily evaluated
        self._trigger: Trigger | None
        if operation and (iscoroutinefunction(operation['fn']) or inspect.isgeneratorfunction(operation['fn'])):
            self._trigger = Trigger(internal=True)
            self._current_ = Undefined
            self._dirty = True  # Otherwise current will be stuck as Undefined.
        else:
            self._trigger = None
        self._root = self._compute_root()
        self._fn_params = self._compute_fn_params()
        # Precompute the (usually empty) ref-capable subset of `_fn_params`,
        # so `_ref_inputs()` - called from `_upstream()` on every node on
        # every walk - has nothing to do for a node with no
        # `Parameter(allow_refs=True)` dependency. `(owner, name)` pairs, so
        # `name`'s `str | None` is narrowed to `str` once, not per use.
        self._ref_capable_params: list[tuple[Parameterized, str]] = [
            (p.owner, p.name) for p in self._fn_params
            if p.name is not None and isinstance(p.owner, Parameterized)
        ]
        self._internal_params = self._compute_params()
        # Filter params that external objects depend on, ensuring
        # that Trigger parameters do not cause double execution
        self._params = [
            p for p in self._internal_params if (not isinstance(p.owner, Trigger) or p.owner.internal)
            or (
                p.owner is not None
                and any(p not in self._internal_params for p in t.cast('t.Any', p.owner).parameters)
            )
        ]
        self._setup_invalidations(depth)
        self._kwargs = kwargs
        self._rx = reactive_ops(self)
        self._init = True
        for name, accessor in _display_accessors.items():
            setattr(self, name, t.cast('Callable', accessor)(self))

    @property
    def rx(self) -> reactive_ops:
        """
        The reactive operations namespace.

        Provides reactive versions of operations that cannot be made reactive through
        operator overloading. This includes operations such as ``.rx.and_`` and ``.rx.bool``.

        References
        ----------
        For more details, see the user guide:
        https://param.holoviz.org/user_guide/Reactive_Expressions.html#special-methods-on-rx

        Examples
        --------
        Create a reactive expression:

        >>> import param
        >>> rx_expression = param.rx(1)

        Retrieve the current value reactively:

        >>> a_value = rx_expression.rx.value

        Use special methods from the reactive ops namespace for reactive operations:

        >>> condition = rx_expression.rx.and_(True)
        >>> piped = rx_expression.rx.pipe(lambda x: x * 2)
        """
        return self._rx

    @property
    def _obj(self):
        if self._shared_obj is None:
            token = _current_node.set(self)
            try:
                self._obj = eval_function_with_deps(self._fn)
            finally:
                _current_node.reset(token)
        elif self._root._dirty_obj:
            root = self._root
            token = _current_node.set(root)
            try:
                root._shared_obj[0] = eval_function_with_deps(root._fn)
            finally:
                _current_node.reset(token)
            t.cast('t.Any', root)._dirty_obj = False
        shared_obj = self._shared_obj
        if shared_obj is None:
            raise RuntimeError("Reactive shared object could not be initialized.")
        return shared_obj[0]

    @_obj.setter
    def _obj(self, obj):
        if self._shared_obj is None:
            self._shared_obj: t.Any = [obj]
        else:
            self._shared_obj[0] = obj

    @property
    def _is_async(self) -> bool:
        if not self._operation:
            return False
        fn = self._operation["fn"]
        return (
            inspect.iscoroutinefunction(fn) or
            inspect.isasyncgenfunction(fn) or
            inspect.isgeneratorfunction(fn)
        )

    @property
    def _awaiting(self) -> bool:
        """
        Whether an asynchronous resolution is in flight that has not yet
        produced a value for the current generation.

        While a node is awaiting, the cached ``_current_`` value was computed
        from inputs that have since been superseded, so resolving the node
        skips instead of reporting the stale value as if it were current.
        """
        return self._resolve_generation != self._finished_generation

    @property
    def _awaiting_ref(self) -> bool:
        """
        Whether an asynchronous reference feeding this node has not yet
        produced a value for the current inputs.

        A coroutine or generator function passed to ``rx`` as the object rather
        than as an operation is held on a parameter and resolved by the
        reference machinery, so its settlement is tracked there instead of by
        this node's own generations.
        """
        for p in self._internal_params:
            owner, name = p.owner, p.name
            if name is None or not isinstance(owner, Parameterized):
                continue
            if owner.param._awaiting_ref(name):
                return True
        return False

    @property
    def _settling(self) -> bool:
        """Whether this node is waiting on an asynchronous result of its own."""
        return self._awaiting or self._awaiting_ref

    def _direct_inputs(self) -> Iterator[t.Any]:
        """
        Yield the ``rx`` nodes this node reads directly from *and* is
        registered as a reader of: its ``_prev`` predecessor, the
        ``_shared`` input it was cloned from when a pipeline branches, and
        any ``rx`` passed as an operation argument (a masked argument is
        substituted with its override, mirroring ``_live_params()``).

        Backs reader registration (``__init__``) and ``_dispose()``'s
        cascade, so deliberately excludes ``_ref_inputs()``: a ref held by a
        ``Parameter(allow_refs=True)`` is kept alive by its owning
        ``Parameterized``, not by this node, so treating it as something
        this node reads would let disposing a throwaway
        ``outlet.param.x.rx()`` view take the ref down with it too, even
        while ``outlet`` still holds it. ``_upstream()`` adds
        ``_ref_inputs()`` back in for its own traversal.
        """
        for inp in (self._prev, self._shared):
            if isinstance(inp, rx):
                yield inp
        operation = self._operation
        if operation:
            overrides = operation.get('overrides') or {}
            args = operation.get('args') or ()
            kwargs = operation.get('kwargs') or {}
            if overrides:
                args = [overrides.get(i, a) for i, a in enumerate(args)]
                kwargs = {k: overrides.get(k, v) for k, v in kwargs.items()}
            yield from _iter_rx((operation['fn'], args, kwargs))

    def _ref_inputs(self) -> Iterator[t.Any]:
        """
        Yield any ``rx`` backing a raw reference this node depends on through
        a ``Parameter(allow_refs=True)``, e.g. ``outlet.param.x.rx()`` where
        ``outlet.x`` was set to an ``rx`` rather than a plain value.

        ``_awaiting_ref`` only recognizes a bare async callable as "still
        resolving", not an already-constructed ``rx`` that is itself awaiting.
        Joining ``_upstream()`` here is what lets
        ``.rx.awaiting``/``.rx.stale``/``.rx.updating()`` see through the
        ref. Not part of ``_direct_inputs()`` (see there for why), so this is
        purely informational: it plays no part in reader/dispose bookkeeping.
        """
        for owner, name in self._ref_capable_params:
            ref = owner._param__private.refs.get(name)
            if ref is not None:
                yield from _iter_rx(ref)

    def _upstream(self) -> Iterator[t.Any]:
        """Yield this node and every ``rx`` node it derives its value from, transitively."""
        seen: set[int] = set()
        stack: list[rx] = [self]
        while stack:
            node = stack.pop()
            if (id_node := id(node)) in seen:
                continue
            seen.add(id_node)
            yield node
            stack.extend(node._direct_inputs())
            stack.extend(node._ref_inputs())

    def _downstream(self) -> Iterator[t.Any]:
        """
        Yield this node and every ``rx`` node that derives its value from it,
        transitively. The reverse of ``_upstream()``, walking ``_readers``
        instead of ``_direct_inputs()``. Weak: a reader collected between two
        calls simply drops out.
        """
        seen: set[int] = set()
        stack: list[rx] = [self]
        while stack:
            node = stack.pop()
            if (id_node := id(node)) in seen:
                continue
            seen.add(id_node)
            yield node
            for ref in tuple(node._readers or ()):
                reader = ref()
                if reader is not None:
                    stack.append(reader)

    def _operation_siblings(self) -> Iterator[t.Any]:
        """
        Yield every other ``rx`` node sharing this node's exact ``_operation``
        dict by identity: a method-chaining clone (``_clone(copy=True)``)
        defaults to sharing ``self._operation`` rather than copying it.
        Overriding an argument on one such node must update the reader link
        on every sibling too, or its link goes stale once the override
        changes. A clone registers itself as a reader of the node it was
        cloned from, so the clone is reachable from that node via
        ``_downstream()`` - but the override can just as well be set through
        the clone instead, in which case the node it was cloned from is
        reachable only via ``_upstream()``. Look both ways.
        """
        operation = self._operation
        if operation is None:
            return
        seen = {id(self)}
        for walk in (self._downstream(), self._upstream()):
            for node in walk:
                if id(node) not in seen and node._operation is operation:
                    seen.add(id(node))
                    yield node

    def _check_disposed(self) -> None:
        if self._disposed:
            raise RuntimeError(
                f"{self!r} has been disposed by .rx.dispose() and can no "
                "longer be resolved, read, or extended with new operations."
            )

    @property
    def _current(self):
        self._check_disposed()
        if self._error_state:
            raise self._error_state
        elif not self._lazy and (self._dirty or self._root._dirty_obj):
            self._resolve()
        return self._current_

    def _compute_root(self):
        if self._prev is None:
            return self
        root = self
        while root._prev is not None:
            root = root._prev
        return root

    def _compute_fn_params(self) -> list[Parameter]:
        if self._fn is None:
            return []

        owner = get_method_owner(self._fn)
        if owner is not None:
            deps = [
                dep.pobj for dep in owner.param.method_dependencies(self._fn.__name__)
            ]
            return deps

        dinfo = getattr(self._fn, '_dinfo', {})
        args = list(dinfo.get('dependencies', []))
        kwargs = list(dinfo.get('kw', {}).values())
        return args + kwargs

    def _compute_params(self) -> list[Parameter]:
        ps = list(self._fn_params)
        if self._trigger:
            ps.append(self._trigger.param.value)

        # Collect parameters on previous objects in chain
        prev = self._prev
        while prev is not None:
            for p in prev._params:
                if p not in ps:
                    ps.append(p)
            prev = prev._prev

        if self._operation is None:
            return ps

        # Accumulate dependencies in args and/or kwargs
        for ref in resolve_ref(self._operation['fn']):
            if ref not in ps:
                ps.append(ref)
        for arg in chain(
            self._operation.get("args", tuple()),
            self._operation.get("kwargs", {}).values(),
        ):
            for ref in resolve_ref(arg, recursive=True):
                if ref not in ps:
                    ps.append(ref)

        return ps

    def _setup_invalidations(self, depth: int = 0):
        """
        Since the parameters of the pipeline can change at any time
        we have to invalidate the internal state of the pipeline.
        To handle both invalidations of the inputs of the pipeline
        and the pipeline itself we set up watchers on both.

        1. The first invalidation we have to set up is to re-evaluate
           the function that feeds the pipeline. Only the root node of
           a pipeline has to perform this invalidation because all
           leaf nodes inherit the same shared_obj. This avoids
           evaluating the same function for every branch of the pipeline.
        2. The second invalidation is for the pipeline itself, i.e.
           if any parameter changes we have to notify the pipeline that
           it has to re-evaluate the pipeline. This is done by marking
           the pipeline as `_dirty`. The next time the `_current` value
           is requested the value is resolved by re-executing the
           pipeline.
        """
        if self._fn is not None:
            for _, params in full_groupby(self._fn_params, lambda x: id(x.owner)):
                fps = [p.name for p in params if p in self._root._fn_params]
                if fps:
                    self._watch_invalidation(params[0].owner, self._invalidate_obj, fps)
        for _, params in full_groupby(self._internal_params, lambda x: id(x.owner)):
            self._watch_invalidation(params[0].owner, self._invalidate_current, [p.name for p in params])

    def _watch_invalidation(self, owner, method, names) -> tuple[_WeakInvalidator, weakref.finalize]:
        """
        Register a *weak* invalidation watcher on a source parameter.

        The callback only holds a weak reference to this node, so a long-lived
        source does not pin the (potentially short-lived) derived node alive.
        A finalizer removes the watcher automatically once this node is garbage
        collected, keeping the source's watcher list from growing without bound.
        The finalizer is handed weak references only (see ``_remove_watcher``).
        It is also returned so a caller that can unwatch sooner than
        disposal (e.g. ``.rx.overrides``) can fire and drop it right away
        instead of letting it pile up in ``_finalizers`` until then.
        """
        invalidator = _WeakInvalidator(method)
        invalidator._watcher = owner.param._watch(invalidator, names, precedence=-1)
        finalizer = weakref.finalize(
            self, _remove_watcher, weakref.ref(owner), weakref.ref(invalidator)
        )
        finalizers = self._finalizers
        if finalizers is None:
            finalizers = self._finalizers = []
        finalizers.append(finalizer)
        return invalidator, finalizer

    def _live_params(self) -> set[tuple[int, str | None]]:
        """
        Return the parameters that can still reach this node's value.

        Every parameter feeding the node qualifies except those that only reach
        it through an overridden input: masking an input makes the value
        independent of it, so a tick of that input cannot change the result and
        must not invalidate the node (see ``.rx.overrides``). Masks upstream
        count too, since a node watches the parameters of its whole input graph
        rather than only its immediate inputs.

        Recomputed whenever one of this node's own inputs is masked or unmasked,
        or a node it (transitively) reads from has its overrides invalidated —
        the only things that change the answer for an already wired graph. See
        ``_invalidate_overrides``, which clears the cache for exactly this set.
        """
        cache = self._live_params_cache
        if cache is not None:
            return cache
        live = {(id(p.owner), p.name) for p in self._fn_params}
        for trigger in (self._trigger, self._override_channel):
            if trigger is not None:
                live.add((id(trigger), 'value'))
        for node in (self._prev, self._shared):
            if node is not None:
                live |= node._live_params()
        operation = self._operation
        if operation is not None:
            live |= {(id(p.owner), p.name) for p in resolve_ref(operation['fn'])}
            overrides = operation.get('overrides') or {}
            args = operation.get('args') or ()
            kwargs = operation.get('kwargs') or {}
            for key, arg in chain(enumerate(args), kwargs.items()):
                # A masked input is resolved from its override, which is watched
                # separately, so nothing the input depends on is live.
                if key not in overrides:
                    live |= _input_live_params(arg)
        self._live_params_cache = live
        return live

    def _invalidate_current(self, *events):
        if all(event.obj is self._trigger for event in events):
            return
        live = self._live_params()
        if not any((id(event.obj), event.name) in live for event in events):
            # Every parameter that changed only reaches this node through an
            # input that is currently masked.
            return
        self._dirty = True
        self._error_state = None

    def _invalidate_obj(self, *events):
        t.cast('t.Any', self._root)._dirty_obj = True
        self._error_state = None

    def _register_reader(self, reader: Self):
        """
        Record that ``reader`` computes its value from this node, for
        ``_invalidate_overrides``, ``_downstream()``, and ``_dispose()``.
        Weak, so a node is not kept alive by the node it derives from.
        """
        readers = self._readers
        if readers is None:
            readers = self._readers = []
        readers.append(weakref.ref(reader, readers.remove))

    def _drop_reader(self, reader: Self) -> bool:
        """
        Drop one occurrence of `reader` (pruning dead entries along the way)
        and return whether any reader remains. One occurrence, not every
        one: `reader` may be registered more than once (e.g. as both an
        operation argument and an override of a different argument), and
        each call here should undo exactly one `_register_reader()` call.

        Rebuilds the contents of `self._readers` in place instead of calling
        `list.remove()` on a live entry: `weakref.ref.__eq__` compares
        referents when both are alive, which for two `rx` nodes runs
        `rx.__eq__` and returns a truthy expression rather than a bool, so
        `list.remove()` would drop whichever entry compares "equal" first
        rather than the right one. In place, not a fresh list assigned to
        `self._readers`: each entry's GC callback is `readers.remove` bound
        to *this* list object (see `_register_reader`), so replacing the
        list would leave a remaining reader's future death unable to find
        its own entry, stranding a dead ref here forever.
        """
        readers = self._readers
        if readers is None:
            return False
        dropped = False
        kept = []
        for ref in readers:
            target = ref()
            if target is None:
                continue
            elif target is reader and not dropped:
                dropped = True
            else:
                kept.append(ref)
        readers[:] = kept
        return bool(kept)

    def _dispose(self, cascade: bool = True, _cascaded: bool = False) -> None:
        """
        See ``reactive_ops.dispose``; a plain method, not ``dispose``, so it
        does not shadow a same-named method on the wrapped value. Raises if
        called directly with a reader still present; reached via a cascade
        instead, it is left alone rather than raising.
        """
        if self._disposed:
            return
        if self._readers or self._watchers:
            if _cascaded:
                return
            raise RuntimeError(
                f"Cannot dispose {self!r}: it is still read by another node "
                "and/or has an active .rx.watch() callback. Dispose the "
                "reader(s) first, or call .rx.unwatch() to remove the watch."
            )
        self._disposed = True
        task = self._current_task
        if task is not None and not task.done():
            task.cancel()
        finalizers, self._finalizers = self._finalizers, None
        for finalizer in finalizers or ():
            finalizer()
        if cascade:
            for node in self._direct_inputs():
                if not node._drop_reader(self):
                    node._dispose(cascade=cascade, _cascaded=True)

    def _ensure_override_channel(self) -> Trigger:
        """
        Return this node's override channel, creating it on first use.

        The channel is the parameter a consumer watches to hear that this node's
        inputs were overridden. A consumer resolves what it depends on once, when
        it is created, so the channel is minted as soon as a node is consumed as
        a reference (see ``_rx_transform``) rather than when an override is first
        set. A node never consumed as a reference never allocates one.
        """
        if self._override_channel is None:
            self._override_channel = Trigger(internal=True)
        return self._override_channel

    def _invalidate_overrides(self, *events):
        """
        Invalidate this node and its readers after one of its overrides changed.

        An override is not a parameter, so ``_setup_invalidations`` does not cover
        it: dirty this node and everything reading its result, drop their cached
        ``_live_params()`` (masking a different set of inputs now), then notify
        the consumers watching their override channels. Nodes reading the same
        *inputs* without reading this node's result are deliberately left alone.
        """
        nodes = []
        seen = set()
        seeds = [self] if self._shared is None else [self, self._shared]
        queue = list(seeds)
        while queue:
            node = queue.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            nodes.append(node)
            for ref in tuple(node._readers or ()):
                reader = ref()
                if reader is not None:
                    queue.append(reader)
        for node in nodes:
            node._dirty = True
            node._error_state = None
            node._live_params_cache = None
        # Only `seeds` had their own `_direct_inputs()` change; a downstream
        # reader learns of it transitively once it re-derives (`.rx.updating()`).
        # Notify before triggering the override channels below, since an
        # active `.rx.watch()` resolves eagerly and could schedule async work
        # a freshly re-derived subscription needs to see coming.
        for node in seeds:
            node._notify_graph_change()
        for node in nodes:
            channel = node._override_channel
            if channel is not None:
                channel.param.trigger('value')

    def _watch_override(self, refs) -> list[weakref.finalize]:
        """
        Watch the references an override is set to.

        They cannot join the node's parameters, which are fixed when it is
        constructed, so they are routed to ``_invalidate_overrides`` instead.
        The finalizers are returned so unmasking or replacing the override can
        fire and drop them right away, instead of leaving them to accumulate in
        ``_finalizers`` until this node is disposed of.
        """
        finalizers = []
        for _, params in full_groupby(refs, lambda x: id(x.owner)):
            owner = params[0].owner
            if owner is None:
                continue
            _, finalizer = self._watch_invalidation(
                owner, self._invalidate_overrides, [p.name for p in params]
            )
            finalizers.append(finalizer)
        return finalizers

    def _watch_settle_change(self, callback: Callable[[t.Any], None]) -> None:
        """
        Run ``callback(self)`` when this node schedules an asynchronous
        resolution.

        Passing the node lets one shared callback serve many nodes, instead
        of a per-node closure over ``self`` that would hold a strong
        reference back to it, defeating the point of watching it weakly.

        Uses ``weakref.WeakMethod`` for a bound-method ``callback``, like
        ``_watch_ref_change``: a plain ``weakref.ref`` to a bound method is
        collected immediately, since nothing else keeps it alive.
        """
        watchers = self._settle_watchers
        if watchers is None:
            watchers = self._settle_watchers = []
        # Weak so a long-lived upstream node does not keep the (possibly much
        # shorter-lived) `.rx.updating()` wrapper alive; dropped automatically
        # once `callback` is collected, like `_readers`.
        ref_type = weakref.WeakMethod if inspect.ismethod(callback) else weakref.ref
        watchers.append(ref_type(callback, watchers.remove))

    def _notify_settle_change(self) -> None:
        """Notify targets registered through `_watch_settle_change`."""
        watchers = self._settle_watchers
        if watchers:
            for ref in tuple(watchers):
                callback = ref()
                if callback is not None:
                    callback(self)

    def _watch_graph_change(self, callback: Callable[[], None]) -> None:
        """
        Register ``callback`` to run when this node's own direct inputs may
        have changed shape: an override set/cleared, or an
        ``allow_refs=True`` fn param reassigned. Lets ``.rx.updating()``
        extend its subscriptions to a node that enters the graph later,
        instead of only seeing ``_upstream()`` as it was at construction
        time. Weak, and handles a bound-method ``callback``, like
        ``_watch_settle_change``.
        """
        watchers = self._graph_watchers
        if watchers is None:
            watchers = self._graph_watchers = []
            # Also register per ref-capable fn param: `_invalidate_current`
            # alone would miss a reassignment to a fresh async ref, which
            # resolves to `Undefined` and never fires a normal watcher.
            for owner, name in self._ref_capable_params:
                _watch_ref_change(owner, name, self._notify_graph_change)
        ref_type = weakref.WeakMethod if inspect.ismethod(callback) else weakref.ref
        watchers.append(ref_type(callback, watchers.remove))

    def _notify_graph_change(self) -> None:
        """Notify targets registered through `_watch_graph_change`."""
        watchers = self._graph_watchers
        if watchers:
            for ref in tuple(watchers):
                callback = ref()
                if callback is not None:
                    callback()

    async def _resolve_async(self, obj=None, generation: int = 0):
        import asyncio

        def stale():
            return generation != self._resolve_generation

        if stale():
            # A newer resolution was requested before this task was scheduled,
            # so nothing has awaited obj yet and the operation has not begun.
            # Close it instead of computing a result that is already superseded.
            # This must happen before _current_task is claimed below, otherwise
            # the finally clause would clear the genuinely current task and hide
            # it from the next _lazy_resolve.
            await _close_stale(obj)
            return
        trigger = self._trigger
        if trigger is None:
            return
        self._current_task = task = asyncio.current_task()
        try:
            if obj is None:
                shared = self._shared
                if shared is None:
                    return
                if shared._current_task:
                    await shared._current_task
                if stale():
                    return
                self._current_ = shared.rx.value
                self._skipped = False
                self._finished_generation = generation
                trigger.param.trigger('value')
            elif inspect.isasyncgen(obj):
                # Manually drive generator (as opposed to async for) to ensure
                # current_node is only set while generator body is advancing
                broke = False
                while True:
                    token = _current_node.set(self)
                    try:
                        val = await obj.__anext__()
                    except StopAsyncIteration:
                        break
                    finally:
                        _current_node.reset(token)
                    if stale():
                        await _close_stale(obj)
                        broke = True
                        break
                    self._current_ = val
                    self._skipped = False
                    self._finished_generation = generation
                    trigger.param.trigger('value')
                if not broke and not stale() and self._finished_generation != generation:
                    # The generator did not yield anything, so we skip and keep
                    # the previous output
                    self._skipped = True
                    self._finished_generation = generation
            else:
                token = _current_node.set(self)
                try:
                    value = await obj
                finally:
                    _current_node.reset(token)
                if stale():
                    return
                self._current_ = value
                self._skipped = False
                self._finished_generation = generation
                trigger.param.trigger('value')
        except asyncio.CancelledError:
            return
        except Exception as e:
            if stale():
                return
            self._finished_generation = generation
            if self._dirty or self._root._dirty_obj:
                # Ignoring as the inputs were invalidated while the async operation was running
                return
            if self._error_mode == 'propagate':
                self._current_ = ReactiveError(e, self)
                self._skipped = False
                trigger.param.trigger('value')
                return
            # Mirror the synchronous path in _resolve.
            # For an async generator an raised exception ends the stream.
            self._error_state = e
            trigger.param.trigger('value')
        finally:
            if self._current_task is task:
                self._current_task = None
            # `_settling` may have just flipped False; `.rx.updating()` needs
            # to hear that even when this node's own recompute produces the
            # same value as before, since a value-changed watcher then never
            # fires (see `_watch_settle_change`'s callers).
            self._notify_settle_change()

    def _lazy_resolve(self, obj = None):
        from .parameterized import async_executor
        if inspect.isgenerator(obj):
            obj = _to_async_gen(obj)
        self._resolve_generation += 1
        generation = self._resolve_generation
        previous_task = self._current_task
        if previous_task is not None and not previous_task.done():
            previous_task.cancel()
        self._notify_settle_change()
        async_executor(partial(self._resolve_async, obj, generation))

    def _resolve(self):
        self._check_disposed()
        if self._error_state:
            raise self._error_state
        elif self._dirty or self._root._dirty_obj:
            try:
                obj = self._obj if self._prev is None else self._prev._resolve()
                operation = self._operation
                if isinstance(obj, ReactiveError) and not (operation or {}).get('process_failures'):
                    self._current_ = obj
                    self._skipped = False
                    self._dirty = False
                    return obj
                if obj is Skip or obj is Undefined:
                    self._current_ = Undefined
                    raise Skip
                elif self._prev is not None and self._prev._skipped:
                    raise Skip
                elif (
                    self._shared is not None and
                    self._method is None and
                    self._shared._method is None
                ):
                    # If this rx is cloned from an shared input then we make use
                    # of the shared.rx.value to ensure branching pipelines do
                    # not have to recompute the inputs multiple times.
                    shared = self._shared
                    value = shared.rx.value # triggers async resolve
                    if self._is_async and (
                        shared._awaiting or shared._current_task is not None
                    ):
                        # The shared node is still processing, resolve when finished
                        self._lazy_resolve()
                        raise Skip
                    # Returns instead of raising Skip because this path does
                    # resolve to a value, so it must mirror the shared node's
                    # skip state rather than be marked skipped by the handler.
                    self._current_ = value
                    self._skipped = shared._skipped
                    if self._is_async:
                        # The value was adopted without scheduling a task, so
                        # claim a generation for it. This supersedes a task an
                        # earlier operation may have scheduled and still awaits a resolution.
                        self._resolve_generation += 1
                        self._finished_generation = self._resolve_generation
                    self._dirty = False
                    return self._current_
                if operation:
                    obj = self._eval_operation(obj, operation)
                    if self._is_async:
                        self._lazy_resolve(obj)
                        if self._finished_generation == self._resolve_generation:
                            # Handle case where async call is resolved synchronously
                            # e.g. when there is no running event loop
                            self._skipped = False
                            self._dirty = False
                            return self._current_
                        obj = Skip
                    if obj is Skip:
                        raise Skip
            except Skip:
                self._dirty = False
                self._skipped = True
                return self._current_
            except Exception as e:
                if self._error_mode == 'propagate':
                    self._current_ = ReactiveError(e, self)
                    self._dirty = False
                    self._skipped = False
                    return self._current_
                self._error_state = e
                raise e
            self._current_ = current = obj
            self._skipped = False
        else:
            current = self._current_
            # A node awaiting an asynchronous result still holds the value it
            # computed from the previous inputs; report it as skipped so it is
            # not propagated as if it were current. Preserve an explicit skip
            # across rereads so a second watcher cannot publish that value.
            self._skipped = self._skipped or self._awaiting
        self._dirty = False
        if self._method:
            # E.g. `pi = dfi.A` leads to `pi._method` equal to `'A'`.
            current = getattr(current, self._method, current)
        if hasattr(current, '__call__'):
            self.__call__.__func__.__doc__ = self.__call__.__doc__
        return current

    def _transform_output(self, obj):
        """Apply custom display handlers before their output."""
        applies = False
        for predicate, (handler, opts) in self._display_handlers.items():
            display_opts = {
                k: v for k, v in self._display_opts.items() if k in opts
            }
            display_opts.update(self._kwargs)
            try:
                applies = predicate(obj, **display_opts)
            except TypeError:
                applies = predicate(obj)
            if applies:
                new = handler(obj, **display_opts)
                if new is not obj:
                    return new
        return obj

    @property
    def _callback(self) -> Callable[..., t.Any]:
        params = [*self._params, self._ensure_override_channel().param.value]
        last = _unset = object()
        def evaluate(*args, **kwargs):
            nonlocal last
            out = self._current
            if self._skipped:
                raise Skip
            if self._method:
                out = getattr(out, self._method)
            out = self._transform_output(out)
            if last is not _unset and Comparator.is_equal(out, last):
                raise Skip
            last = out
            return out
        return bind(evaluate, *params)

    def _clone(self, operation=None, copy=False, **kwargs) -> Self:
        operation = operation or self._operation
        depth = self._depth + 1
        if copy:
            if any(node._is_async for node in self._upstream()):
                current = self._current_
            else:
                current = self._current
            kwargs = dict(
                self._kwargs, _current=current, method=self._method,
                prev=self._prev, _shared=self, **kwargs
            )
        else:
            kwargs = dict(prev=self, **dict(self._kwargs, **kwargs))
        kwargs = dict(self._display_opts, **kwargs)
        error_mode = t.cast('str', kwargs.pop('error_mode', self._error_mode))
        label = kwargs.pop('label', self._label)
        return type(self)(
            self._obj, operation=operation, depth=depth, fn=self._fn, lazy=self._lazy,
            _shared_obj=self._shared_obj, _wrapper=self._wrapper,
            error_mode=error_mode, label=label,
            **kwargs
        )

    def __dir__(self):
        resolved = self._current
        current = resolved
        if self._method:
            current = getattr(current, self._method)
        extras = {attr for attr in dir(current) if not attr.startswith('_')}
        # Explicitly list registered but uninstantiated accessors
        accessor_names = {
            name for name, (_, predicate, memoize) in rx._accessors.items()
            if (name not in self.__dict__ or not memoize)
            and (predicate is None or predicate(resolved))
        }
        try:
            return sorted(set(super().__dir__()) | extras | accessor_names)
        except Exception:
            return sorted(set(dir(type(self))) | set(self.__dict__) | extras | accessor_names)

    def _resolve_accessor(self) -> Self:
        if not self._method:
            # No method is yet set, as in `dfi.A`, so return a copied clone.
            return self._clone(copy=True)
        # This is executed when one runs e.g. `dfi.A > 1`, in which case after
        # dfi.A the _method 'A' is set (in __getattribute__) which allows
        # _resolve_accessor to record the attribute access as an operation.
        operation = {
            'fn': getattr,
            'args': (self._method,),
            'kwargs': {},
            'reverse': False
        }
        self._method = None
        return self._clone(operation)

    def __getattribute__(self, name):
        self_dict = super().__getattribute__('__dict__')
        if not self_dict.get('_init') or name == 'rx' or name.startswith('_'):
            return super().__getattribute__(name)
        if self_dict.get('_disposed'):
            super().__getattribute__('_check_disposed')()

        current = self_dict['_current_']
        dirty = self_dict['_dirty']
        if self_dict['_lazy']:
            # there is no current, delay the getattr to later
            operation = {
                'fn': lambda obj, name: getattr(obj, name),
                'args': (name,),
                'kwargs': {},
            }
            return self._clone(operation)

        if dirty:
            self._resolve()
            current = self_dict['_current_']

        # Capture uninstantiated accessor access
        if name in rx._accessors and (name not in self_dict or not rx._accessors[name][2]):
            accessor, predicate, memoize = rx._accessors[name]
            if predicate is None or predicate(current):
                value = accessor(self)
                if memoize:
                    # Bypass __setattr__ (which blocks reassignment of
                    # registered accessor names) to cache the instantiated
                    # accessor directly on the instance.
                    self_dict[name] = value
                return value

        method = self_dict['_method']
        if method:
            current = getattr(current, method)
        # Getting all the public attributes available on the current object,
        # e.g. `sum`, `head`, etc.
        extras = [d for d in dir(current) if not d.startswith('_')]
        if (name in extras or current is Undefined) and name not in super().__dir__():
            new = self._resolve_accessor()
            # Setting the method name for a potential use later by e.g. an
            # operator or method, as in `dfi.A > 2`. or `dfi.A.max()`
            new._method = name
            try:
                new.__doc__ = getattr(current, name).__doc__
            except Exception:
                pass
            return new
        return super().__getattribute__(name)

    def __call__(self, *args, **kwargs):
        new = self._clone(copy=True)
        method = new._method or '__call__'
        if method == '__call__' and self._depth == 0 and not hasattr(self._current, '__call__') and not self._lazy:
            return self.set_display(*args, **kwargs)

        if method in rx._method_handlers:
            handler = rx._method_handlers[method]
            method = handler(self)
        new._method = None
        kwargs = dict(kwargs)
        operation = {
            'fn': method,
            'args': args,
            'kwargs': kwargs,
            'reverse': False
        }
        return new._clone(operation)

    #----------------------------------------------------------------
    # rx pipeline APIs
    #----------------------------------------------------------------

    def __array_ufunc__(self, ufunc, method, *args, **kwargs) -> Self:
        new = self._resolve_accessor()
        operation = {
            'fn': getattr(ufunc, method),
            'args': args[1:],
            'kwargs': kwargs,
            'reverse': False
        }
        return new._clone(operation)

    def _apply_operator(
        self, operator: Callable, *args, reverse: bool = False, process_failures=False,
        **kwargs
    ) -> Self:
        new = self._resolve_accessor()
        operation = {
            'fn': operator,
            'args': args,
            'kwargs': kwargs,
            'reverse': reverse
        }
        operation['process_failures'] = process_failures
        return new._clone(operation)

    # Builtin functions

    def __abs__(self):
        return self._apply_operator(abs)

    def __str__(self):  # type: ignore[bad-override]
        return self._apply_operator(str)

    def __round__(self, ndigits=None):
        args = () if ndigits is None else (ndigits,)
        return self._apply_operator(round, *args)

    # Unary operators
    def __ceil__(self):
        return self._apply_operator(math.ceil)
    def __floor__(self):
        return self._apply_operator(math.floor)
    def __invert__(self):
        return self._apply_operator(operator.inv)
    def __neg__(self):
        return self._apply_operator(operator.neg)
    def __pos__(self):
        return self._apply_operator(operator.pos)
    def __trunc__(self):
        return self._apply_operator(math.trunc)

    # Binary operators
    def __add__(self, other):
        return self._apply_operator(operator.add, other)
    def __and__(self, other):
        return self._apply_operator(operator.and_, other)
    def __contains_(self, other):
        return self._apply_operator(operator.contains, other)
    def __divmod__(self, other):
        return self._apply_operator(divmod, other)
    def __eq__(self, other):  # type: ignore[bad-override]
        return self._apply_operator(operator.eq, other)
    def __floordiv__(self, other):
        return self._apply_operator(operator.floordiv, other)
    def __ge__(self, other):
        return self._apply_operator(operator.ge, other)
    def __gt__(self, other):
        return self._apply_operator(operator.gt, other)
    def __le__(self, other):
        return self._apply_operator(operator.le, other)
    def __lt__(self, other):
        return self._apply_operator(operator.lt, other)
    def __lshift__(self, other):
        return self._apply_operator(operator.lshift, other)
    def __matmul__(self, other):
        return self._apply_operator(operator.matmul, other)
    def __mod__(self, other):
        return self._apply_operator(operator.mod, other)
    def __mul__(self, other):
        return self._apply_operator(operator.mul, other)
    def __ne__(self, other):  # type: ignore[bad-override]
        return self._apply_operator(operator.ne, other)
    def __or__(self, other):
        return self._apply_operator(operator.or_, other)
    def __rshift__(self, other):
        return self._apply_operator(operator.rshift, other)
    def __pow__(self, other):
        return self._apply_operator(operator.pow, other)
    def __sub__(self, other):
        return self._apply_operator(operator.sub, other)
    def __truediv__(self, other):
        return self._apply_operator(operator.truediv, other)
    def __xor__(self, other):
        return self._apply_operator(operator.xor, other)

    # Reverse binary operators
    def __radd__(self, other):
        return self._apply_operator(operator.add, other, reverse=True)
    def __rand__(self, other):
        return self._apply_operator(operator.and_, other, reverse=True)
    def __rdiv__(self, other):
        return self._apply_operator(operator.truediv, other, reverse=True)
    def __rdivmod__(self, other):
        return self._apply_operator(divmod, other, reverse=True)
    def __rfloordiv__(self, other):
        return self._apply_operator(operator.floordiv, other, reverse=True)
    def __rlshift__(self, other):
        return self._apply_operator(operator.lshift, other, reverse=True)
    def __rmod__(self, other):
        return self._apply_operator(operator.mod, other, reverse=True)
    def __rmul__(self, other):
        return self._apply_operator(operator.mul, other, reverse=True)
    def __ror__(self, other):
        return self._apply_operator(operator.or_, other, reverse=True)
    def __rpow__(self, other):
        return self._apply_operator(operator.pow, other, reverse=True)
    def __rsub__(self, other):
        return self._apply_operator(operator.sub, other, reverse=True)
    def __rtruediv__(self, other):
        return self._apply_operator(operator.truediv, other, reverse=True)
    def __rxor__(self, other):
        return self._apply_operator(operator.xor, other, reverse=True)

    def __getitem__(self, other):
        return self._apply_operator(operator.getitem, other)

    def __iter__(self):
        if isinstance(self._current, Iterator):
            while True:
                try:
                    new = self._apply_operator(next)
                    new.rx.value
                except RuntimeError:
                    break
                yield new
            return
        elif not isinstance(self._current, Iterable):
            if self._lazy:
                raise RuntimeError(
                    "Lazy rx expressions must be resolved before being iterated over. "
                    "Access the current value using .rx.value before iterating."
                )
            else:
                raise TypeError(f'Cannot unpack non-iterable {type(self._current).__name__} object.')
        elif not isinstance(self._current, Sized):
            raise TypeError(f'cannot determine length of {type(self._current).__name__} object.')
        items = self._apply_operator(list)
        for i in range(len(self._current)):
            yield items[i]

    def __bool__(self):
        # Implemented otherwise truth value testing (e.g. if rx: ...)
        # defers to __len__ which raises an error.
        return True

    def __len__(self):
        raise TypeError(
            'len(<rx_obj>) is not supported. Use `<rx_obj>.rx.len()` to '
            'obtain the length as a reactive expression, or '
            '`len(<rx_obj>.rx.value)` to obtain the length of the underlying '
            'expression value.'
        )

    def _resolve_input(self, arg):
        """
        Resolve one input of an operation, or the override standing in for it.

        Raises ``Skip`` for an input that is settling, unresolved or skipped, and
        returns a ``ReactiveError`` for the caller to propagate or hand on.
        """
        if any(ref._settling for ref in _iter_rx(arg)):
            raise Skip
        val = resolve_value(arg)
        if val is Skip or val is Undefined:
            raise Skip
        return val

    def _eval_operation(self, obj, operation):
        if operation['fn'] is _collect_marker:
            return self._eval_collect(operation)
        fn, args, kwargs = operation['fn'], operation['args'], operation['kwargs']
        # Resolving an override in its input's place is what lets it mask an
        # input that failed or never arrived (see .rx.overrides).
        overrides = operation.get('overrides') or {}
        process_failures = operation.get('process_failures')
        resolved_args = []
        for i, arg in enumerate(args):
            val = self._resolve_input(overrides[i] if i in overrides else arg)
            if isinstance(val, ReactiveError) and not process_failures:
                return val
            resolved_args.append(val)
        resolved_kwargs = {}
        for k, arg in kwargs.items():
            val = self._resolve_input(overrides[k] if k in overrides else arg)
            if isinstance(val, ReactiveError) and not process_failures:
                return val
            resolved_kwargs[k] = val
        token = _current_node.set(self)
        try:
            if isinstance(fn, str):
                obj = getattr(obj, fn)(*resolved_args, **resolved_kwargs)
            elif operation.get('reverse'):
                obj = fn(resolved_args[0], obj, *resolved_args[1:], **resolved_kwargs)
            else:
                obj = fn(obj, *resolved_args, **resolved_kwargs)
        finally:
            _current_node.reset(token)
        return obj

    def _eval_collect(self, operation):
        """
        Resolve each `collect` input independently instead of skipping the
        whole node while any one input is unsettled.
        """
        args, kwargs = operation['args'], operation['kwargs']
        overrides = operation.get('overrides') or {}
        previous = self._current_
        prev_args = previous.args if isinstance(previous, Collected) else ()
        prev_kwargs = previous.kwargs if isinstance(previous, Collected) else {}

        def resolve_one(key, arg, prev_val):
            arg = overrides[key] if key in overrides else arg
            try:
                val = self._resolve_input(arg)
            except Skip:
                # Not ready; keep the slot's previous value (or Undefined).
                return prev_val
            except Exception as e:
                if self._error_mode != 'propagate':
                    raise
                return ReactiveError(e, self)
            if isinstance(val, ReactiveError) and self._error_mode != 'propagate':
                raise val.exception  # upstream propagated; this node doesn't
            return val

        new_args = tuple(
            resolve_one(i, arg, prev_args[i] if i < len(prev_args) else Undefined)
            for i, arg in enumerate(args)
        )
        new_kwargs = {
            k: resolve_one(k, arg, prev_kwargs.get(k, Undefined))
            for k, arg in kwargs.items()
        }
        if (
            isinstance(previous, Collected)
            and len(new_args) == len(prev_args)
            and all(map(_safe_is_equal, new_args, prev_args))
            and new_kwargs.keys() == prev_kwargs.keys()
            and all(_safe_is_equal(v, prev_kwargs[k]) for k, v in new_kwargs.items())
        ):
            raise Skip  # nothing changed; don't republish the same value
        # A read-only view, so a watcher mutating a slot in place (a user
        # error) can't corrupt the previous-value fallback above.
        return Collected(args=new_args, kwargs=MappingProxyType(new_kwargs))

    def __setattr__(self, name, value):
        # Setting value instead of rx.value is a common user mistake.
        # They are more but we don't want to restrict __setattr__ too much
        # so only catch value and registered accessor names, for now.
        if name == "value":
            raise AttributeError(
                "'rx' has no attribute 'value', try "
                "'<reactive_expr>.rx.value = <val>'."
            )
        elif name in rx._accessors:
            raise AttributeError(
                f"{name!r} is a registered accessor and cannot be "
                "reassigned; did you mean to set an attribute on the "
                "node's value?"
            )
        super().__setattr__(name, value)


def _iter_rx(value: t.Any) -> Iterator[rx]:
    """
    Yield the reactive expressions nested anywhere inside a reference.

    Mirrors the containers ``resolve_value`` descends into, so an ``rx`` used
    as an operation argument is found wherever ``resolve_value`` would find it.
    """
    if isinstance(value, rx):
        yield value
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from _iter_rx(v)
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _iter_rx(k)
            yield from _iter_rx(v)
    elif isinstance(value, slice):
        for v in (value.start, value.stop, value.step):
            yield from _iter_rx(v)


def _input_live_params(arg: t.Any) -> set[tuple[int, str | None]]:
    """
    Return the parameters through which ``arg`` can reach the value of the node
    it is an input of.

    An ``rx`` input contributes the parameters that are live for it rather than
    every parameter it was wired with, so an input masked inside it stays
    masked for its consumers, plus the channel it announces its own overrides
    on. References that are not expressions contribute their parameters as is.
    """
    nested = list(_iter_rx(arg))
    live: set[tuple[int, str | None]] = set()
    covered: set[tuple[int, str | None]] = set()
    for node in nested:
        live |= node._live_params()
        live.add((id(node._ensure_override_channel()), 'value'))
        covered |= {(id(p.owner), p.name) for p in node._params}
    for ref in resolve_ref(arg, recursive=True):
        key = (id(ref.owner), ref.name)
        if key not in covered:
            live.add(key)
    return live


def _rx_transform(obj):
    if not isinstance(obj, rx):
        return obj
    binding = obj._ref_binding
    if binding is not None:
        return binding
    def resolve(*_):
        value = obj.rx.value
        if obj._skipped or value is Skip or value is Undefined:
            raise Skip
        return value
    # Binding the override channel wakes a consumer created before an override
    # exists. Caching is sound because a node's parameters are fixed at
    # construction, and this runs on every resolve of the reference.
    binding = bind(resolve, *obj._params, obj._ensure_override_channel().param.value)
    obj._ref_binding = binding
    return binding

register_reference_transform(_rx_transform)
