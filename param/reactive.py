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

When an operation is applied to an `reactive` instance, it will
record the operation and create a new instance using `_clone` method,
e.g. `dfi.head()` first records that the `'head'` attribute is
accessed, this is achieved by overriding `__getattribute__`. A new
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
useful in Notebook sessions, as this allows to inspect the transformed
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
instance in an reactive has a `_depth` of 0. An reactive can
consist of multiple chains, such as `dfi[dfi.A > 1]`, as the
`reactive` instance is referenced twice in the reactive. As a
consequence `_depth` is not the total count of `reactive` instance
creations of a pipeline, it is the count of instances created in the
outer chain. In the example, that would be `dfi[]`. Each `reactive`
instance keeps a reference to the previous instance in the chain and
each instance tracks whether its current value is up-to-date via the
`_dirty` attribute which is set to False if any dependency changes.

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

import math
import operator

from types import FunctionType, MethodType
from typing import Any, Callable, Optional

import param

from .depends import (
    _display_accessors, bind, depends, eval_function_with_deps,
    register_depends_transform, resolve_ref, resolve_value,
    transform_dependency
)
from .parameterized import Parameter, get_method_owner
from ._utils import full_groupby


class Wrapper(param.Parameterized):

    object = param.Parameter()


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
        if isinstance(obj, reactive) and not prev:
            self._prev = obj
        else:
            self._prev = prev
        self._kwargs = kwargs
        self._init = True
        self._dirty = True
        self._current_ = None
        self._setup_invalidations(depth)
        for name, accessor in _display_accessors.items():
            setattr(self, name, accessor(self))
        for name, (accessor, predicate) in reactive._accessors.items():
            if predicate is None or predicate(self._current):
                setattr(self, name, accessor(self))

    @property
    def _obj(self):
        if self._shared_obj is None:
            self._obj = eval_function_with_deps(self._fn)
        return self._shared_obj[0]

    @_obj.setter
    def _obj(self, obj):
        if self._shared_obj is None:
            self._shared_obj = [obj]
        else:
            self._shared_obj[0] = obj

    @property
    def _current(self):
        if self._dirty:
            self.eval()
        return self._current_

    @property
    def _fn_params(self) -> list[param.Parameter]:
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
    def _params(self) -> list[param.Parameter]:
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
           is requested we then run and `.eval()` pass that re-executes
           the pipeline.
        """
        if self._fn is not None and depth == 0:
            for _, params in full_groupby(self._fn_params, lambda x: id(x.owner)):
                params[0].owner.param.watch(self._update_obj, [p.name for p in params])
        for _, params in full_groupby(self._params, lambda x: id(x.owner)):
            params[0].owner.param.watch(self._invalidate_current, [p.name for p in params])

    def _invalidate_current(self, *events):
        self._dirty = True

    def _update_obj(self, *args):
        self._obj = eval_function_with_deps(self._fn)

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
        def evaluate_inner():
            obj = self.eval()
            return self._transform_output(obj)
        params = self._params
        if params:
            @depends(*params)
            def evaluate(*args, **kwargs):
                return evaluate_inner()
        else:
            def evaluate():
                return evaluate_inner()
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
        no_lookup = (
            'eval', '_dirty', '_prev', '_operation', '_obj', '_shared_obj',
            '_method', '_eval_operation', '_display_opts', '_fn', '_resolve_accessor',
            '_clone', '_setup_invalidations', '_params', '_fn_params',
            '_invalidate_current', '_depth', '_current', '_kwargs',
            '_wrapper',
        )
        if not self_dict.get('_init') or name in no_lookup:
            return super().__getattribute__(name)

        current = self_dict['_current_']
        dirty = self_dict['_dirty']
        if dirty:
            self.eval()
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

    def len(self):
        """
        __len__ cannot be implemented so we alternative helper.
        """
        return self._apply_operator(len)

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
        return self._apply_operator(func, *args, **kwargs)

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

    #----------------------------------------------------------------
    # Public API
    #----------------------------------------------------------------

    def eval(self):
        """
        Returns the current state of the reactive by evaluating the
        pipeline.
        """
        if self._dirty:
            obj = self._obj if self._prev is None else self._prev.eval()
            operation = self._operation
            if operation:
                obj = self._eval_operation(obj, operation)
            self._current_ = current = obj
        else:
            current = self._current_
        self._dirty = False
        if self._method:
            # E.g. `pi = dfi.A` leads to `pi._method` equal to `'A'`.
            current = getattr(current, self._method, current)
        if hasattr(current, '__call__'):
            self.__call__.__func__.__doc__ = current.__call__.__doc__
        return current

    def set_display(self, **kwargs):
        """
        Overrides the display options for this reactive object.
        """
        self._display_opts = dict(self._display_opts, **kwargs)
        return self

    def set(self, new):
        """
        Allows overriding the original input to the pipeline.
        """
        prev = self
        while prev is not None:
            prev._dirty = True
            if prev._prev is not None:
                prev = prev._prev
                continue

            if prev._wrapper is None:
                raise ValueError(
                    f'{type(self).__name__}.set is only supported if the '
                    'root object is a constant value. If the root is a '
                    'Parameter or another dynamic value it must reflect '
                    'the source and cannot be set.'
                )
            prev._wrapper.object = new
            prev = None
        return self


def _reactive_transform(obj):
    if not isinstance(obj, reactive):
        return obj
    return bind(lambda *_: obj.eval(), *obj._params)

register_depends_transform(_reactive_transform)
