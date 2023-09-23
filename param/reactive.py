"""
reactive API

`reactive` is a wrapper around a Python object that lets users create
reactive pipelines by calling existing APIs on an object with dynamic
parameters or widgets.

A `reactive` instance watches what operations are applied to the object
and records these on each instance, which are then strung together
into a chain.

The original input to a `reactive` is stored in a mutable list and can be
accessed via the `_obj` property. The shared mutable data structure
ensures that all `reactive` instances created from the same object can
hold a shared reference that can be updated, e.g. via the `.set`
method or because the input was itself a reference to some object that
can potentially be updated.

When an operation is applied to a `reactive` instance, it will
record the operation and create a new instance using `_clone` method,
e.g. `dfi.head()` first records that the `'head'` attribute is
accessed, which is achieved by overriding `__getattribute__`. A new
reactive object is returned, which will then record that it is
being called, and that new object will be itself called as
`reactive` implements `__call__`. `__call__` returns another
`reactive` instance. To be able to watch all the potential
operations that may be applied to an object, `reactive` implements:

- `__getattribute__`: Watching for attribute accesses
- `__call__`: Intercepting both actual calls or method calls if an
  attribute was previously accessed
- `__getitem__`: Intercepting indexing operations
- Operators: Implementing all valid operators `__gt__`, `__add__`, etc.
- `__array_ufunc__`: Intercepting numpy universal function calls

The `reactive` object evaluates operations lazily but whenever the
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
a new `reactive` instance is created part of a chain.  The root
instance in a reactive reactive has a `_depth` of 0. A reactive
expression can consist of multiple chains, such as `dfi[dfi.A > 1]`,
as the `reactive` instance is referenced twice in the reactive. As a
consequence `_depth` is not the total count of `reactive` instance
creations of a pipeline, it is the count of instances created in the
outer chain. In the example, that would be `dfi[]`. Each `reactive`
instance keeps a reference to the previous instance in the chain and
each instance tracks whether its current value is up-to-date via the
`_dirty` attribute, which is set to False if any dependency changes.

The `_method` attribute is a string that temporarily stores the
method/attr accessed on the object, e.g. `_method` is 'head' in
`dfi.head()`, until the `reactive` instance created in the pipeline
is called at which point `_method` is reset to None. In cases such as
`dfi.head` or `dfi.A`, `_method` is not (yet) reset to None. At this
stage the reactive instance returned has its `_current` attribute
not updated, e.g. `dfi.A._current` is still the original dataframe,
not the 'A' series. Keeping `_method` is thus useful for instance to
display `dfi.A`, as the evaluation of the object will check whether
`_method` is set or not, and if it's set it will use it to compute the
object returned, e.g. the series `df.A` or the method `df.head`, and
display its repr.
"""
from __future__ import annotations

import inspect
import math
import operator

from collections.abc import Iterable, Iterator
from types import FunctionType, MethodType
from typing import Any, Callable, Optional

from . import Event
from .depends import (
    _display_accessors, _reactive_display_objs, eval_function_with_deps,
    register_depends_transform, depends, resolve_ref, resolve_value,
    transform_dependency
)
from .parameterized import (
    Parameter, Parameterized, get_method_owner
)
from ._utils import iscoroutinefunction, full_groupby


class Wrapper(Parameterized):
    """
    Simple wrapper to allow updating literal values easily.
    """

    object = Parameter()


class Trigger(Parameterized):

    value = Event()


class reactive_ops:
    """
    Namespace for reactive operators.

    Implements operators that cannot be implemented using regular
    Python syntax.
    """

    def __init__(self, reactive):
        self._reactive = reactive

    def __call__(self):
        rx = self._reactive
        return rx if isinstance(rx, reactive) else reactive(rx)

    def bool(self):
        """
        __bool__ cannot be implemented so it is provided as a method.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(bool)

    def in_(self, other):
        """
        Replacement for the ``in`` statement.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(operator.contains, other, reverse=True)

    def is_(self, other):
        """
        Replacement for the ``is`` statement.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(operator.is_, other)

    def is_not(self, other):
        """
        Replacement for the ``is not`` statement.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(operator.is_not, other)

    def len(self):
        """
        __len__ cannot be implemented so it is provided as a method.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(len)

    def pipe(self, func, *args, **kwargs):
        """
        Apply chainable functions.

        Arguments
        ---------
        func: function
          Function to apply.
        args: iterable, optional
          Positional arguments to pass to `func`.
        kwargs: mapping, optional
          A dictionary of keywords to pass to `func`.
        """
        rx = self._reactive if isinstance(self._reactive, reactive) else self()
        return rx._apply_operator(func, *args, **kwargs)

    def when(self, *dependencies):
        """
        Returns a reactive object that emits the contents of this
        expression only when the condition changes.

        Arguments
        ---------
        dependencies: param.Parameter | reactive
          A dependency that will trigger an update in the output.
        """
        return bind(lambda *_: self.resolve(), *dependencies).rx()

    def where(self, x, y):
        """
        Returns either x or y depending on the current state of the
        expression, i.e. replaces a ternary if statement.

        Arguments
        ---------
        x: object
          The value to return if the expression evaluates to True.
        y: object
          The value to return if the expression evaluates to False.
        """
        xrefs = resolve_ref(x)
        yrefs = resolve_ref(y)
        trigger = Trigger()
        if xrefs:
            def trigger_x(*args):
                if self.resolve():
                    trigger.param.trigger('value')
            bind(trigger_x, *xrefs, watch=True)
        if yrefs:
            def trigger_y(*args):
                if not self.resolve():
                    trigger.param.trigger('value')
            bind(trigger_y, *yrefs, watch=True)

        def ternary(condition, event):
            return resolve_value(x) if condition else resolve_value(y)
        return self.pipe(ternary, trigger.param.value)

    # Operations to get the output and set the input of an expression

    def resolve(self):
        """
        Returns the current state of the reactive by evaluating the
        pipeline.
        """
        if isinstance(self._reactive, reactive):
            return self._reactive._resolve()
        elif isinstance(self._reactive, Parameter):
            return getattr(self._reactive.owner, self._reactive.name)
        else:
            return self._reactive()

    def set_input(self, new):
        """
        Allows overriding the original input to the pipeline.
        """
        if isinstance(self._reactive, Parameter):
            raise ValueError(
                "Parameter.rx.set_input() is not supported. Cannot override "
                "parameter value."
            )
        elif not isinstance(self._reactive, reactive):
            raise ValueError(
                "bind(...).rx.set_input() is not supported. Cannot override "
                "the output of a function."
            )
        if isinstance(new, reactive):
            new = new.resolve()
        prev = self._reactive
        while prev is not None:
            prev._dirty = True
            if prev._prev is not None:
                prev = prev._prev
                continue

            if prev._wrapper is None:
                raise ValueError(
                    'reactive.rx.set_input() is only supported if the '
                    'root object is a constant value. If the root is a '
                    'Parameter or another dynamic value it must reflect '
                    'the source and cannot be set.'
                )
            prev._invalidate_obj()
            prev._wrapper.object = new
            prev = None
        return self._reactive

    def watch(self, fn):
        """
        Adds a callback that observes the output of the pipeline.
        """
        def cb(*args):
            fn(self.resolve())

        if isinstance(self._reactive, reactive):
            params = self._reactive._params
        else:
            params = resolve_ref(self._reactive)
        for _, group in full_groupby(params, lambda x: id(x.owner)):
            group[0].owner.param.watch(cb, [dep.name for dep in group])


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

    Arguments
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
        tuple(transform_dependency(arg) for arg in args),
        {key: transform_dependency(arg) for key, arg in kwargs.items()}
    )
    dependencies = {}

    # If the wrapped function has a dependency add it
    fn_dep = transform_dependency(function)
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
                    combined_args[int(kw[5:])] = arg
                elif kw.startswith('__kwarg'):
                    combined_kwargs[kw[8:]] = arg
                continue
            elif kw.startswith('__arg') or kw.startswith('__kwarg') or kw.startswith('__fn'):
                continue
            combined_kwargs[kw] = arg
        return combined_args, combined_kwargs

    def eval_fn():
        if callable(function):
            fn = function
        else:
            p = transform_dependency(function)
            if isinstance(p, Parameter):
                fn = getattr(p.owner, p.name)
            else:
                fn = eval_function_with_deps(p)
        return fn

    if inspect.isasyncgenfunction(function):
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


class reactive:
    """
    `reactive` allows wrapping objects and then operating on them
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

    >>> ifloat = reactive(3.14)
    >>> ifloat * 2
    6.28

    Then update the original value and see the new result:
    >>> ifloat.set(1)
    2
    """

    _accessors: dict[str, Callable[[reactive], Any]] = {}

    _display_options: tuple[str] = ()

    _display_handlers: dict[type, tuple[Any, dict[str, Any]]] = {}

    _method_handlers: dict[str, Callable] = {}

    @classmethod
    def register_accessor(
        cls, name: str, accessor: Callable[[reactive], Any],
        predicate: Optional[Callable[[Any], bool]] = None
    ):
        """
        Registers an accessor that extends reactive with custom behavior.

        Arguments
        ---------
        name: str
          The name of the accessor will be attribute-accessible under.
        accessor: Callable[[reactive], any]
          A callable that will return the accessor namespace object
          given the reactive object it is registered on.
        predicate: Callable[[Any], bool] | None
        """
        cls._accessors[name] = (accessor, predicate)

    @classmethod
    def register_display_handler(cls, obj_type, handler, **kwargs):
        """
        Registers a display handler for a specific type of object,
        making it possible to define custom display options for
        specific objects.

        Arguments
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

    def __new__(cls, obj, **kwargs):
        wrapper = None
        obj = transform_dependency(obj)
        if kwargs.get('fn'):
            fn = kwargs.pop('fn')
            wrapper = kwargs.pop('_wrapper', None)
        elif isinstance(obj, (FunctionType, MethodType)) and hasattr(obj, '_dinfo'):
            fn = obj
            obj = eval_function_with_deps(obj)
        elif isinstance(obj, Parameter):
            fn = bind(lambda obj: obj, obj)
            obj = getattr(obj.owner, obj.name)
        else:
            wrapper = Wrapper(object=obj)
            fn = bind(lambda obj: obj, wrapper.param.object)
        inst = super(reactive, cls).__new__(cls)
        inst._fn = fn
        inst._shared_obj = kwargs.get('_shared_obj', None if obj is None else [obj])
        inst._wrapper = wrapper
        return inst

    def __init__(
        self, obj, operation=None, fn=None, depth=0, method=None, prev=None,
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
        self._dirty = True
        self._dirty_obj = False
        self._error_state = None
        self._current_ = None
        if isinstance(obj, reactive) and not prev:
            self._prev = obj
        else:
            self._prev = prev
        self._setup_invalidations(depth)
        self._kwargs = kwargs
        self.rx = reactive_ops(self)
        self._init = True
        for name, accessor in _display_accessors.items():
            setattr(self, name, accessor(self))
        for name, (accessor, predicate) in reactive._accessors.items():
            if predicate is None or predicate(self._current):
                setattr(self, name, accessor(self))

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
            self.rx.resolve()
        return self._current_

    @property
    def _fn_params(self) -> list[Parameter]:
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

    @property
    def _root(self):
        if self._prev is None:
            return self
        root = self
        while root._prev is not None:
            root = root._prev
        return root

    @property
    def _params(self) -> list[Parameter]:
        ps = self._fn_params

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
        ps += [
            ref for arg in self._operation['args']
            for ref in resolve_ref(arg)
        ]
        ps += [
            ref for arg in self._operation['kwargs'].values()
            for ref in resolve_ref(arg)
        ]
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
           is requested we then run and `.resolve()` pass that re-executes
           the pipeline.
        """
        if self._fn is not None:
            for _, params in full_groupby(self._fn_params, lambda x: id(x.owner)):
                params[0].owner.param.watch(self._invalidate_obj, [p.name for p in params])
        for _, params in full_groupby(self._params, lambda x: id(x.owner)):
            params[0].owner.param.watch(self._invalidate_current, [p.name for p in params])

    def _invalidate_current(self, *events):
        self._dirty = True
        self._error_state = None

    def _invalidate_obj(self, *events):
        self._root._dirty_obj = True
        self._error_state = None

    def _resolve(self):
        if self._error_state:
            raise self._error_state
        elif self._dirty or self._root._dirty_obj:
            try:
                obj = self._obj if self._prev is None else self._prev._resolve()
                operation = self._operation
                if operation:
                    obj = self._eval_operation(obj, operation)
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
        """
        Applies custom display handlers before their output.
        """
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
            return self._transform_output(self._current)
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
            self.rx.resolve()
            current = self_dict['_current_']

        method = self_dict['_method']
        if method:
            current = getattr(current, method)
        # Getting all the public attributes available on the current object,
        # e.g. `sum`, `head`, etc.
        extras = [d for d in dir(current) if not d.startswith('_')]
        if name in extras and name not in super().__dir__():
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

        if method in reactive._method_handlers:
            handler = reactive._method_handlers[method]
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
    # reactive pipeline APIs
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
    def __not__(self):
        return self._apply_operator(operator.not_)
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
                    new.rx.resolve()
                except RuntimeError:
                    break
                yield new
            return
        elif not isinstance(self._current, Iterable):
            raise TypeError('cannot unpack non-iterable {type(self._current).__name__} object.')
        iterator = []
        def iterate(value):
            if iterator:
                iterate = iterator[0]
            else:
                iterate = iter(value)
                iterator.append(iterate)
            try:
                yield next(iterate)
            except StopIteration as e:
                iterator.clear()
                raise e
        for item in self._apply_operator(iterate):
            yield item

    def _eval_operation(self, obj, operation):
        fn, args, kwargs = operation['fn'], operation['args'], operation['kwargs']
        resolved_args = []
        for arg in args:
            resolved_args.append(resolve_value(arg))
        resolved_kwargs = {}
        for k, arg in kwargs.items():
            resolved_kwargs[k] = resolve_value(arg)
        if isinstance(fn, str):
            obj = getattr(obj, fn)(*resolved_args, **resolved_kwargs)
        elif operation.get('reverse'):
            obj = fn(resolved_args[0], obj, *resolved_args[1:], **resolved_kwargs)
        else:
            obj = fn(obj, *resolved_args, **resolved_kwargs)
        return obj


def _reactive_transform(obj):
    if not isinstance(obj, reactive):
        return obj
    return bind(lambda *_: obj.rx.resolve(), *obj._params)

register_depends_transform(_reactive_transform)
