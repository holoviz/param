"""
reactive API

`rx` is a wrapper around a Python object that lets users create
reactive expression pipelines by calling existing APIs on an object with dynamic
parameters or widgets.

An `rx` instance watches what operations are applied to the object
and records these on each instance, which are then strung together
into a chain.

The original input to an `rx` object is stored in a mutable list and can be
accessed via the `_obj` property. The shared mutable data structure
ensures that all `rx` instances created from the same object can
hold a shared reference that can be updated, e.g. via the `.value`
property or because the input was itself a reference to some object that
can potentially be updated.

When an operation is applied to an `rx` instance, it will
record the operation and create a new instance using the `_clone` method,
e.g. `dfi.head()` first records that the `'head'` attribute is
accessed, which is achieved by overriding `__getattribute__`. A new
reactive object is returned, which will then record that it is
being called, and that new object will be itself called, as
`rx` implements `__call__`. `__call__` returns another
`rx` instance. To be able to watch all the potential
operations that may be applied to an object, `rx` implements:

- `__getattribute__`: Watching for attribute accesses
- `__call__`: Intercepting both actual calls or method calls if an
  attribute was previously accessed
- `__getitem__`: Intercepting indexing operations
- Operators: Implementing all valid operators `__gt__`, `__add__`, etc.
- `__array_ufunc__`: Intercepting numpy universal function calls

The `rx` object evaluates operations lazily, but whenever the
current value is needed the operations are automatically
evaluated. Note that even attribute access or tab-completion
operations can result in evaluation of the pipeline. This is very
useful in a REPL, as this allows inspecting the transformed
object at any point of the pipeline, and as such provide correct
auto-completion and docstrings. E.g. executing `dfi.A.max?` in an
interactive REPL or notebook where it allows returning the docstring
of the method being accessed.

The actual operations are stored as a dictionary on the `_operation`
attribute of each instance. They contain 4 keys:

- `fn`: The function to apply (either an actual function or a string
        indicating the operation is a method on the object)
- `args`: Any arguments to supply to the `fn`.
- `kwargs`: Any keyword arguments to supply to the `fn`.
- `reverse`: If the function is not a method this indicates whether
             the first arg and the input object should be supplied in
             reverse order.

The `_depth` attribute starts at 0 and is incremented by 1 every time
a new `rx` instance is created part of a chain. The root
instance in a reactive expression  has a `_depth` of 0. A reactive
expression can consist of multiple chains, such as `dfi[dfi.A > 1]`,
as the `rx` instance is referenced twice in the expression. As a
consequence `_depth` is not the total count of `rx` instance
creations of a pipeline, it is the count of instances created in the
outer chain. In the example, that would be `dfi[]`. Each `rx`
instance keeps a reference to the previous instance in the chain and
each instance tracks whether its current value is up-to-date via the
`_dirty` attribute, which is set to False if any dependency changes.

The `_method` attribute is a string that temporarily stores the
method/attr accessed on the object, e.g. `_method` is 'head' in
`dfi.head()`, until the `rx` instance created in the pipeline
is called at which point `_method` is reset to None. In cases such as
`dfi.head` or `dfi.A`, `_method` is not (yet) reset to None. At this
stage the `rx` instance returned has its `_current` attribute
not updated, e.g. `dfi.A._current` is still the original dataframe,
not the 'A' series. Keeping `_method` is thus useful for instance to
display `dfi.A`, as the evaluation of the object will check whether
`_method` is set or not, and if it's set it will use it to compute the
object returned, e.g. the series `df.A` or the method `df.head`, and
display its repr.
"""
from __future__ import annotations

import asyncio
import inspect
import math
import operator

from collections.abc import Iterable, Iterator
from functools import partial
from types import FunctionType, MethodType
from typing import Any, Callable, Optional

from .depends import depends
from .display import _display_accessors, _reactive_display_objs
from .parameterized import (
    Parameter, Parameterized, Skip, Undefined, eval_function_with_deps, get_method_owner,
    register_reference_transform, resolve_ref, resolve_value, transform_reference
)
from .parameters import Boolean, Event
from ._utils import _to_async_gen, iscoroutinefunction, full_groupby


class Wrapper(Parameterized):
    """Helper class to allow updating literal values easily."""

    object = Parameter(allow_refs=False)


class GenWrapper(Parameterized):
    """Helper class to allow streaming from generator functions."""

    object = Parameter(allow_refs=True)


class Trigger(Parameterized):
    """Helper class to allow triggering an event under some condition."""

    value = Event()

    def __init__(self, parameters=None, internal=False, **params):
        super().__init__(**params)
        self.internal = internal
        self.parameters = parameters

class Resolver(Parameterized):
    """Helper class to allow (recursively) resolving references."""

    object = Parameter(allow_refs=True)

    recursive = Boolean(default=False)

    value = Parameter()

    def __init__(self, **params):
        self._watchers = []
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
        for w in self._watchers:
            (w.inst or w.cls).param.unwatch(w)
        self._watchers = []
        for _, params in full_groupby(refs, lambda x: id(x.owner)):
            self._watchers.append(
                params[0].owner.param.watch(self._resolve_value, [p.name for p in params])
            )


class NestedResolver(Resolver):

    object = Parameter(allow_refs=True, nested_refs=True)


class reactive_ops:
    """
    The reactive namespace.

    Provides reactive versions of operations that cannot be made reactive through operator overloading, such as
    `.rx.and_` and `.rx.bool`. Calling this namespace (`()`) returns a reactive expression.

    Returns
    -------
    Reactive expression
        The result of calling the reactive namespace is a reactive expression.

    User Guide
    ----------
    https://param.holoviz.org/user_guide/Reactive_Expressions.html#special-methods-on-rx

    Examples
    --------
    Create a Parameterized instance:

    >>> import param
    >>> class P(param.Parameterized):
    ...     a = param.Number()
    >>> p = P(a=1)

    Get the current value:

    >>> a = p.param.a.rx.value

    Call it to get a reactive expression:

    >>> rx_value = p.param.a.rx()

    """

    def __init__(self, reactive):
        self._reactive = reactive

    def _as_rx(self):
        return self._reactive if isinstance(self._reactive, rx) else self()

    def __call__(self):
        """Creates a reactive expression."""
        rxi = self._reactive
        return rxi if isinstance(rx, rx) else rx(rxi)

    def and_(self, other):
        """Replacement for the ``and`` statement."""
        return self._as_rx()._apply_operator(lambda obj, other: obj and other, other)

    def bool(self):
        """__bool__ cannot be implemented so it is provided as a method."""
        return self._as_rx()._apply_operator(bool)

    def buffer(self, n):
        """Collects the last n items that were emitted."""
        items = []
        def collect(new, n):
            items.append(new)
            while len(items) > n:
                items.pop(0)
            return items
        return self._as_rx()._apply_operator(collect, n)

    def in_(self, other):
        """Replacement for the ``in`` statement."""
        return self._as_rx()._apply_operator(operator.contains, other, reverse=True)

    def is_(self, other):
        """Replacement for the ``is`` statement."""
        return self._as_rx()._apply_operator(operator.is_, other)

    def is_not(self, other):
        """Replacement for the ``is not`` statement."""
        return self._as_rx()._apply_operator(operator.is_not, other)

    def len(self):
        """__len__ cannot be implemented so it is provided as a method."""
        return self._as_rx()._apply_operator(len)

    def map(self, func, /, *args, **kwargs):
        """
        Apply a function to each item.

        Arguments:
        ---------
        func: function
          Function to apply.
        args: iterable, optional
          Positional arguments to pass to `func`.
        kwargs: mapping, optional
          A dictionary of keywords to pass to `func`.

        """
        if inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
            raise TypeError(
                "Cannot map a generator function. Only regular function "
                "or coroutine functions are permitted."
            )
        if inspect.iscoroutinefunction(func):
            async def apply(vs, *args, **kwargs):
                return list(await asyncio.gather(*(func(v, *args, **kwargs) for v in vs)))
        else:
            def apply(vs, *args, **kwargs):
                return [func(v, *args, **kwargs) for v in vs]
        return self._as_rx()._apply_operator(apply, *args, **kwargs)

    def not_(self):
        """__bool__ cannot be implemented so not has to be provided as a method."""
        return self._as_rx()._apply_operator(operator.not_)

    def or_(self, other):
        """Replacement for the ``or`` statement."""
        return self._as_rx()._apply_operator(lambda obj, other: obj or other, other)

    def pipe(self, func, /, *args, **kwargs):
        """
        Apply chainable functions.

        Arguments:
        ---------
        func: function
          Function to apply.
        args: iterable, optional
          Positional arguments to pass to `func`.
        kwargs: mapping, optional
          A dictionary of keywords to pass to `func`.

        """
        return self._as_rx()._apply_operator(func, *args, **kwargs)

    def resolve(self, nested=True, recursive=False):
        """
        Resolves references held by the expression.

        As an example if the expression returns a list of parameters
        this operation will return a list of the parameter values.

        Arguments:
        ---------
        nested: bool
          Whether to resolve references contained within nested objects,
          i.e. tuples, lists, sets and dictionaries.
        recursive: bool
          Whether to recursively resolve references, i.e. if a reference
          itself returns a reference we recurse into it until no more
          references can be resolved.

        """
        resolver_type = NestedResolver if nested else Resolver
        resolver = resolver_type(object=self._reactive, recursive=recursive)
        return resolver.param.value.rx()

    def updating(self):
        """Returns a new expression that is True while the expression is updating."""
        wrapper = Wrapper(object=False)
        self._watch(lambda e: wrapper.param.update(object=True), precedence=-999)
        self._watch(lambda e: wrapper.param.update(object=False), precedence=999)
        return wrapper.param.object.rx()

    def when(self, *dependencies, initial=Undefined):
        """
        Returns a reactive expression that emits the contents of this
        expression only when the dependencies change. If initial value
        is provided and the dependencies are all param.Event types the
        expression will not be evaluated until the first event is
        triggered.

        Arguments:
        ---------
        dependencies: param.Parameter | rx
          A dependency that will trigger an update in the output.
        initial: object
          Object that will stand in for the actual value until the
          first time a param.Event in the dependencies is triggered.

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
        return bind(eval, *deps).rx()

    def where(self, x, y):
        """
        Returns either x or y depending on the current state of the
        expression, i.e. replaces a ternary if statement.

        Arguments:
        ---------
        x: object
          The value to return if the expression evaluates to True.
        y: object
          The value to return if the expression evaluates to False.

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
                if self.value:
                    trigger.param.trigger('value')
            bind(trigger_x, *xrefs, watch=True)
        if yrefs:
            def trigger_y(*args):
                if not self.value:
                    trigger.param.trigger('value')
            bind(trigger_y, *yrefs, watch=True)

        def ternary(condition, _):
            return resolve_value(x) if condition else resolve_value(y)
        return bind(ternary, self._reactive, trigger.param.value)

    # Operations to get the output and set the input of an expression

    @property
    def value(self):
        """
        Returns the current state of the reactive expression by
        evaluating the pipeline.
        """
        if isinstance(self._reactive, rx):
            return self._reactive._resolve()
        elif isinstance(self._reactive, Parameter):
            return getattr(self._reactive.owner, self._reactive.name)
        else:
            return self._reactive()

    @value.setter
    def value(self, new):
        """Allows overriding the original input to the pipeline."""
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
        Adds a callable that observes the output of the pipeline.
        If no callable is provided this simply causes the expression
        to be eagerly evaluated.
        """
        if precedence < 0:
            raise ValueError("User-defined watch callbacks must declare "
                             "a positive precedence. Negative precedences "
                             "are reserved for internal Watchers.")
        self._watch(fn, onlychanged=onlychanged, queued=queued, precedence=precedence)

    def _watch(self, fn=None, onlychanged=True, queued=False, precedence=0):
        def cb(value):
            from .parameterized import async_executor
            if iscoroutinefunction(fn):
                async_executor(partial(fn, value))
            elif fn is not None:
                fn(value)
        bind(cb, self._reactive, watch=True)


def bind(function, *args, watch=False, **kwargs):
    """
    Given a function, returns a wrapper function that binds the values
    of some or all arguments to Parameter values and expresses Param
    dependencies on those values, so that the function can be invoked
    whenever the underlying values change and the output will reflect
    those updated values.

    As for functools.partial, arguments can also be bound to constants,
    which allows all of the arguments to be bound, leaving a simple
    callable object.

    Arguments:
    ---------
    function: callable
        The function to bind constant or dynamic args and kwargs to.
    args: object, param.Parameter
        Positional arguments to bind to the function.
    watch: boolean
        Whether to evaluate the function automatically whenever one of
        the bound parameters changes.
    kwargs: object, param.Parameter
        Keyword arguments to bind to the function.

    Returns
    -------
    Returns a new function with the args and kwargs bound to it and
    annotated with all dependencies.

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
                arg = eval_function_with_deps(arg)
            elif isinstance(arg, Parameter):
                arg = getattr(arg.owner, arg.name)
            combined_args.append(arg)
        combined_args += list(wargs)

        combined_kwargs = {}
        for kw, arg in kwargs.items():
            if hasattr(arg, '_dinfo'):
                arg = eval_function_with_deps(arg)
            elif isinstance(arg, Parameter):
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
                fn = getattr(p.owner, p.name)
            else:
                fn = eval_function_with_deps(p)
        return fn

    if inspect.isgeneratorfunction(function):
        def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            evaled = eval_fn()(*combined_args, **combined_kwargs)
            for val in evaled:
                yield val
        wrapper_fn = depends(**dependencies, watch=watch)(wrapped)
        wrapped._dinfo = wrapper_fn._dinfo
    elif inspect.isasyncgenfunction(function):
        async def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            evaled = eval_fn()(*combined_args, **combined_kwargs)
            async for val in evaled:
                yield val
        wrapper_fn = depends(**dependencies, watch=watch)(wrapped)
        wrapped._dinfo = wrapper_fn._dinfo
    elif iscoroutinefunction(function):
        @depends(**dependencies, watch=watch)
        async def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            evaled = eval_fn()(*combined_args, **combined_kwargs)
            return await evaled
    else:
        @depends(**dependencies, watch=watch)
        def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(wargs, wkwargs)
            return eval_fn()(*combined_args, **combined_kwargs)
    wrapped.__bound_function__ = function
    wrapped.rx = reactive_ops(wrapped)
    _reactive_display_objs.add(wrapped)
    for name, accessor in _display_accessors.items():
        setattr(wrapped, name, accessor(wrapped))
    return wrapped


class rx:
    """
    `rx` allows wrapping objects and then operating on them
    interactively while recording any operations applied to them. By
    recording all arguments or operands in the operations the recorded
    pipeline can be replayed if an operand represents a dynamic value.

    Parameters
    ----------
    obj: any
        A supported data structure object

    Examples
    --------
    Instantiate it from an object:

    >>> ifloat = rx(3.14)
    >>> ifloat * 2
    6.28

    Then update the original value and see the new result:
    >>> ifloat.value = 1
    2

    """

    _accessors: dict[str, Callable[[rx], Any]] = {}

    _display_options: tuple[str] = ()

    _display_handlers: dict[type, tuple[Any, dict[str, Any]]] = {}

    _method_handlers: dict[str, Callable] = {}

    @classmethod
    def register_accessor(
        cls, name: str, accessor: Callable[[rx], Any],
        predicate: Optional[Callable[[Any], bool]] = None
    ):
        """
        Registers an accessor that extends rx with custom behavior.

        Arguments:
        ---------
        name: str
          The name of the accessor will be attribute-accessible under.
        accessor: Callable[[rx], any]
          A callable that will return the accessor namespace object
          given the rx object it is registered on.
        predicate: Callable[[Any], bool] | None

        """
        cls._accessors[name] = (accessor, predicate)

    @classmethod
    def register_display_handler(cls, obj_type, handler, **kwargs):
        """
        Registers a display handler for a specific type of object,
        making it possible to define custom display options for
        specific objects.

        Arguments:
        ---------
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
        Registers a handler that is called when a specific method on
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
            wrapper = GenWrapper(object=obj)
            fn = bind(lambda obj: obj, wrapper.param.object)
            obj = Undefined
        elif isinstance(obj, (FunctionType, MethodType)) and hasattr(obj, '_dinfo'):
            # Bound functions and methods are resolved on access
            fn = obj
            obj = None
        elif isinstance(obj, Parameter):
            fn = bind(lambda obj: obj, obj)
            obj = getattr(obj.owner, obj.name)
        else:
            # For all other objects wrap them so they can be updated
            # via .rx.value property
            wrapper = Wrapper(object=obj)
            fn = bind(lambda obj: obj, wrapper.param.object)
        inst = super(rx, cls).__new__(cls)
        inst._fn = fn
        inst._shared_obj = kwargs.get('_shared_obj', None if obj is None else [obj])
        inst._wrapper = wrapper
        return inst

    def __init__(
        self, obj=None, operation=None, fn=None, depth=0, method=None, prev=None,
        _shared_obj=None, _current=None, _wrapper=None, **kwargs
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
        self._method = method
        self._operation = operation
        self._depth = depth
        self._dirty = _current is None
        self._dirty_obj = False
        self._current_task = None
        self._error_state = None
        self._current_ = _current
        if isinstance(obj, rx) and not prev:
            self._prev = obj
        else:
            self._prev = prev

        # Define special trigger parameter if operation has to be lazily evaluated
        if operation and (iscoroutinefunction(operation['fn']) or inspect.isgeneratorfunction(operation['fn'])):
            self._trigger = Trigger(internal=True)
            self._current_ = Undefined
        else:
            self._trigger = None
        self._root = self._compute_root()
        self._fn_params = self._compute_fn_params()
        self._internal_params = self._compute_params()
        # Filter params that external objects depend on, ensuring
        # that Trigger parameters do not cause double execution
        self._params = [
            p for p in self._internal_params if (not isinstance(p.owner, Trigger) or p.owner.internal)
            or any (p not in self._internal_params for p in p.owner.parameters)
        ]
        self._setup_invalidations(depth)
        self._kwargs = kwargs
        self._rx = reactive_ops(self)
        self._init = True
        for name, accessor in _display_accessors.items():
            setattr(self, name, accessor(self))
        for name, (accessor, predicate) in rx._accessors.items():
            if predicate is None or predicate(self._current):
                setattr(self, name, accessor(self))

    @property
    def rx(self) -> reactive_ops:
        """
        The reactive namespace.

        Provides reactive versions of operations that cannot be made reactive through operator overloading, such as
        `.rx.and_` and `.rx.bool`. Calling this namespace (`()`) returns a reactive expression.

        Returns
        -------
        Reactive expression
            The result of calling the reactive namespace is a reactive expression.

        User Guide
        ----------
        https://param.holoviz.org/user_guide/Reactive_Expressions.html#special-methods-on-rx

        Examples
        --------
        Create a Parameterized instance:

        >>> import param
        >>> class P(param.Parameterized):
        ...     a = param.Number()
        >>> p = P(a=1)

        Get the current value:

        >>> a = p.param.a.rx.value

        Call it to get a reactive expression:

        >>> rx_value = p.param.a.rx()

        """
        return self._rx

    @property
    def _obj(self):
        if self._shared_obj is None:
            self._obj = eval_function_with_deps(self._fn)
        elif self._root._dirty_obj:
            root = self._root
            root._shared_obj[0] = eval_function_with_deps(root._fn)
            root._dirty_obj = False
        return self._shared_obj[0]

    @_obj.setter
    def _obj(self, obj):
        if self._shared_obj is None:
            self._shared_obj = [obj]
        else:
            self._shared_obj[0] = obj

    @property
    def _current(self):
        if self._error_state:
            raise self._error_state
        elif self._dirty or self._root._dirty_obj:
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
        for arg in list(self._operation['args'])+list(self._operation['kwargs'].values()):
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
                    params[0].owner.param._watch(self._invalidate_obj, fps, precedence=-1)
        for _, params in full_groupby(self._internal_params, lambda x: id(x.owner)):
            params[0].owner.param._watch(self._invalidate_current, [p.name for p in params], precedence=-1)

    def _invalidate_current(self, *events):
        if all(event.obj is self._trigger for event in events):
            return
        self._dirty = True
        self._error_state = None

    def _invalidate_obj(self, *events):
        self._root._dirty_obj = True
        self._error_state = None

    async def _resolve_async(self, obj):
        self._current_task = task = asyncio.current_task()
        if inspect.isasyncgen(obj):
            async for val in obj:
                if self._current_task is not task:
                    break
                self._current_ = val
                self._trigger.param.trigger('value')
        else:
            value = await obj
            if self._current_task is task:
                self._current_ = value
                self._trigger.param.trigger('value')

    def _lazy_resolve(self, obj):
        from .parameterized import async_executor
        if inspect.isgenerator(obj):
            obj = _to_async_gen(obj)
        async_executor(partial(self._resolve_async, obj))

    def _resolve(self):
        if self._error_state:
            raise self._error_state
        elif self._dirty or self._root._dirty_obj:
            try:
                obj = self._obj if self._prev is None else self._prev._resolve()
                if obj is Skip or obj is Undefined:
                    self._current_ = Undefined
                    raise Skip
                operation = self._operation
                if operation:
                    obj = self._eval_operation(obj, operation)
                    if inspect.isasyncgen(obj) or inspect.iscoroutine(obj) or inspect.isgenerator(obj):
                        self._lazy_resolve(obj)
                        obj = Skip
                    if obj is Skip:
                        raise Skip
            except Skip:
                self._dirty = False
                return self._current_
            except Exception as e:
                self._error_state = e
                raise e
            self._current_ = current = obj
        else:
            current = self._current_
        self._dirty = False
        if self._method:
            # E.g. `pi = dfi.A` leads to `pi._method` equal to `'A'`.
            current = getattr(current, self._method, current)
        if hasattr(current, '__call__'):
            self.__call__.__func__.__doc__ = self.__call__.__doc__
        return current

    def _transform_output(self, obj):
        """Applies custom display handlers before their output."""
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
    def _callback(self):
        params = self._params
        def evaluate(*args, **kwargs):
            out = self._current
            if self._method:
                out = getattr(out, self._method)
            return self._transform_output(out)
        if params:
            return bind(evaluate, *params)
        return evaluate

    def _clone(self, operation=None, copy=False, **kwargs):
        operation = operation or self._operation
        depth = self._depth + 1
        if copy:
            kwargs = dict(
                self._kwargs, _current=self._current, method=self._method,
                prev=self._prev, **kwargs
            )
        else:
            kwargs = dict(prev=self, **dict(self._kwargs, **kwargs))
        kwargs = dict(self._display_opts, **kwargs)
        return type(self)(
            self._obj, operation=operation, depth=depth, fn=self._fn,
            _shared_obj=self._shared_obj, _wrapper=self._wrapper,
            **kwargs
        )

    def __dir__(self):
        current = self._current
        if self._method:
            current = getattr(current, self._method)
        extras = {attr for attr in dir(current) if not attr.startswith('_')}
        try:
            return sorted(set(super().__dir__()) | extras)
        except Exception:
            return sorted(set(dir(type(self))) | set(self.__dict__) | extras)

    def _resolve_accessor(self):
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

        current = self_dict['_current_']
        dirty = self_dict['_dirty']
        if dirty:
            self._resolve()
            current = self_dict['_current_']

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
        if method == '__call__' and self._depth == 0 and not hasattr(self._current, '__call__'):
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

    def __array_ufunc__(self, ufunc, method, *args, **kwargs):
        new = self._resolve_accessor()
        operation = {
            'fn': getattr(ufunc, method),
            'args': args[1:],
            'kwargs': kwargs,
            'reverse': False
        }
        return new._clone(operation)

    def _apply_operator(self, operator, *args, reverse=False, **kwargs):
        new = self._resolve_accessor()
        operation = {
            'fn': operator,
            'args': args,
            'kwargs': kwargs,
            'reverse': reverse
        }
        return new._clone(operation)

    # Builtin functions

    def __abs__(self):
        return self._apply_operator(abs)

    def __str__(self):
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
    def __eq__(self, other):
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
    def __ne__(self, other):
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
        return self._apply_operator(operator.div, other, reverse=True)
    def __rdivmod__(self, other):
        return self._apply_operator(divmod, other, reverse=True)
    def __rfloordiv__(self, other):
        return self._apply_operator(operator.floordiv, other, reverse=True)
    def __rlshift__(self, other):
        return self._apply_operator(operator.rlshift, other)
    def __rmod__(self, other):
        return self._apply_operator(operator.mod, other, reverse=True)
    def __rmul__(self, other):
        return self._apply_operator(operator.mul, other, reverse=True)
    def __ror__(self, other):
        return self._apply_operator(operator.or_, other, reverse=True)
    def __rpow__(self, other):
        return self._apply_operator(operator.pow, other, reverse=True)
    def __rrshift__(self, other):
        return self._apply_operator(operator.rrshift, other)
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
            raise TypeError(f'cannot unpack non-iterable {type(self._current).__name__} object.')
        items = self._apply_operator(list)
        for i in range(len(self._current)):
            yield items[i]

    def _eval_operation(self, obj, operation):
        fn, args, kwargs = operation['fn'], operation['args'], operation['kwargs']
        resolved_args = []
        for arg in args:
            val = resolve_value(arg)
            if val is Skip or val is Undefined:
                raise Skip
            resolved_args.append(val)
        resolved_kwargs = {}
        for k, arg in kwargs.items():
            val = resolve_value(arg)
            if val is Skip or val is Undefined:
                raise Skip
            resolved_kwargs[k] = val
        if isinstance(fn, str):
            obj = getattr(obj, fn)(*resolved_args, **resolved_kwargs)
        elif operation.get('reverse'):
            obj = fn(resolved_args[0], obj, *resolved_args[1:], **resolved_kwargs)
        else:
            obj = fn(obj, *resolved_args, **resolved_kwargs)
        return obj


def _rx_transform(obj):
    if not isinstance(obj, rx):
        return obj
    return bind(lambda *_: obj.rx.value, *obj._params)

register_reference_transform(_rx_transform)
