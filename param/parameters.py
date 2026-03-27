"""
Parameters are a kind of class attribute allowing special behavior,
including dynamically generated parameter values, documentation
strings, constant and read-only parameters, and type or range checking
at assignment time.

Potentially useful for any large Python program that needs
user-modifiable object attributes; see the Parameter and Parameterized
classes for more information.  If you do not want to add a dependency
on external code by importing from a separately installed param
package, you can simply save this file as param.py and copy it and
parameterized.py directly into your own package.

This file contains subclasses of Parameter, implementing specific
parameter types (e.g. Number), and also imports the definition of
Parameters and Parameterized classes.
"""
from __future__ import annotations

import copy
import datetime as dt
import glob
import importlib
import inspect
import numbers
import os.path
import pathlib
import re
import sys
import typing as t
import warnings

from collections import OrderedDict
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from os import PathLike


from .parameterized import (
    T, Parameterized, Parameter, ParameterizedFunction, ParameterKwargs, ParamOverrides,
    String, Undefined, get_logger, instance_descriptor, _dt_types,
    _int_types
)
from ._utils import (
    ParamDeprecationWarning as _ParamDeprecationWarning,
    _find_stack_level,
    _validate_error_prefix,
    _deserialize_from_path,
    _named_objs,
    _produce_value,
    _get_min_max_value,
    _is_number,
    concrete_descendents,  # noqa: F401
    descendents as _descendents,
    _abbreviate_paths,
    _to_datetime,
)

#-----------------------------------------------------------------------------
# Utilities
#-----------------------------------------------------------------------------

if t.TYPE_CHECKING:
    if sys.version_info < (3, 11):
        from typing_extensions import Unpack
    else:
        from typing import Unpack

    import numpy as np
    import pandas as pd


    LT = t.TypeVar("LT")
    CT = t.TypeVar("CT")
    IT = t.TypeVar("IT")


def param_union(*parameterizeds, warn=True):
    """
    Given a set of :class:`Parameterized` objects, returns a dictionary
    with the union of all param name,value pairs across them.

    Parameters
    ----------
    warn : bool, optional
        Wether to warn if the same parameter have been given multiple values,
        otherwise use the last value, by default True

    Returns
    -------
    dict
        Union of all param name,value pairs

    """
    d = {}
    for o in parameterizeds:
        for k in o.param:
            if k != 'name':
                if k in d and warn:
                    get_logger().warning(f"overwriting parameter {k}")
                d[k] = getattr(o, k)
    return d


def guess_param_types(**kwargs) -> dict[str, Parameter]:
    """
    Given a set of keyword literals, promote to the appropriate
    parameter type based on some simple heuristics.
    """
    params: dict[str, Parameter] = {}
    for k, v in kwargs.items():
        if isinstance(v, Parameter):
            params[k] = v
        elif isinstance(v, _dt_types):
            params[k] = Date(default=v, constant=True)
        elif isinstance(v, bool):
            params[k] = Boolean(default=v, constant=True)
        elif isinstance(v, int):
            params[k] = Integer(default=v, constant=True)
        elif isinstance(v, float):
            params[k] = Number(default=v, constant=True)
        elif isinstance(v, str):
            params[k] = String(default=v, constant=True)
        elif isinstance(v, dict):
            params[k] = Dict(default=v, constant=True)
        elif isinstance(v, tuple):
            if all(_is_number(el) for el in v):
                params[k] = NumericTuple(default=v, constant=True)
            elif len(v) == 2 and all(isinstance(el, _dt_types) for el in v):
                params[k] = DateRange(default=v, constant=True)
            else:
                params[k] = Tuple(default=v, constant=True)
        elif isinstance(v, list):
            params[k] = List(default=v, constant=True)
        else:
            if 'numpy' in sys.modules:
                numpy_mod = sys.modules['numpy']
                ndarray = numpy_mod.ndarray  # type: ignore[unresolved-attribute]
                if isinstance(v, ndarray):
                    params[k] = Array(default=v, constant=True)
                    continue
            if 'pandas' in sys.modules:
                pandas_mod = sys.modules['pandas']
                pdDFrame = pandas_mod.DataFrame  # type: ignore[unresolved-attribute]
                pdSeries = pandas_mod.Series  # type: ignore[unresolved-attribute]
                if isinstance(v, pdDFrame):
                    params[k] = DataFrame(default=v, constant=True)
                    continue
                elif isinstance(v, pdSeries):
                    params[k] = Series(default=v, constant=True)
                    continue
            params[k] = Parameter(default=v, constant=True)

    return params


def parameterized_class(
    name: str,
    params: dict[str, Parameter],
    bases: type[Parameterized] | tuple[type[Parameterized], ...] = Parameterized
) -> type[Parameterized]:
    """
    Dynamically create a parameterized class with the given name and the
    supplied parameters, inheriting from the specified base(s).
    """
    if isinstance(bases, type):
        basecls: tuple[type[Parameterized], ...] = (bases,)
    else:
        basecls = tuple(bases)
    return t.cast("type[Parameterized]", type(name, basecls, params))


def guess_bounds(params: dict[str, Parameter], **overrides: tuple[t.Any, t.Any]):
    """
    Given a dictionary of :class:`Parameter` instances, return a corresponding
    set of copies with the bounds appropriately set.


    If given a set of override keywords, use those numeric tuple bounds.
    """
    guessed = {}
    for name, p in params.items():
        new_param = copy.copy(p)
        if isinstance(p, (Integer, Number)):
            if name in overrides:
                minv,maxv = overrides[name]
            else:
                minv, maxv, _ = _get_min_max_value(None, None, value=p.default)
            new_param.bounds = (minv, maxv)
        guessed[name] = new_param
    return guessed


def get_soft_bounds(
    bounds: tuple[t.Any | None, t.Any | None] | None,
    softbounds: tuple[t.Any | None, t.Any | None] | None
) -> tuple[t.Any | None, t.Any | None]:
    """
    For each soft bound (upper and lower), if there is a defined bound
    (not equal to None) and does not exceed the hard bound, then it is
    returned. Otherwise it defaults to the hard bound. The hard bound
    could still be None.
    """
    if bounds is None:
        hl, hu = (None, None)
    else:
        hl, hu = bounds

    if softbounds is None:
        sl, su = (None, None)
    else:
        sl, su = softbounds

    if sl is None or (hl is not None and sl<hl):
        l = hl
    else:
        l = sl

    if su is None or (hu is not None and su>hu):
        u = hu
    else:
        u = su

    return (l, u)


class Infinity:
    """
    An instance of this class represents an infinite value. Unlike
    Python's float('inf') value, this object can be safely compared
    with gmpy2 numeric types across different gmpy2 versions.

    All operators on Infinity() return Infinity(), apart from the
    comparison and equality operators. Equality works by checking
    whether the two objects are both instances of this class.
    """

    def __eq__  (self,other): return isinstance(other,self.__class__)
    def __ne__  (self,other): return not self==other
    def __lt__  (self,other): return False
    def __le__  (self,other): return False
    def __gt__  (self,other): return True
    def __ge__  (self,other): return True
    def __add__ (self,other): return self
    def __radd__(self,other): return self
    def __ladd__(self,other): return self
    def __sub__ (self,other): return self
    def __iadd__ (self,other): return self
    def __isub__(self,other): return self
    def __repr__(self):       return "Infinity()"
    def __str__ (self):       return repr(self)



class Time(Parameterized):
    """
    A callable object returning a number for the current time.

    Here 'time' is an abstract concept that can be interpreted in any
    useful way.  For instance, in a simulation, it would be the
    current simulation time, while in a turn-taking game it could be
    the number of moves so far.  The key intended usage is to allow
    independent Parameterized objects with Dynamic parameters to
    remain consistent with a global reference.

    The time datatype (time_type) is configurable, but should
    typically be an exact numeric type like an integer or a rational,
    so that small floating-point errors do not accumulate as time is
    incremented repeatedly.

    When used as a context manager using the 'with' statement
    (implemented by the __enter__ and __exit__ special methods), entry
    into a context pushes the state of the Time object, allowing the
    effect of changes to the time value to be explored by setting,
    incrementing or decrementing time as desired. This allows the
    state of time-dependent objects to be modified temporarily as a
    function of time, within the context's block. For instance, you
    could use the context manager to "see into the future" to collect
    data over multiple times, without affecting the global time state
    once exiting the context. Of course, you need to be careful not to
    do anything while in context that would affect the lasting state
    of your other objects, if you want things to return to their
    starting state when exiting the context.

    The starting time value of a new Time object is 0, converted to
    the chosen time type. Here is an illustration of how time can be
    manipulated using a Time object:

    >>> time = Time(until=20, timestep=1)
    >>> 'The initial time is %s' % time()
    'The initial time is 0'
    >>> 'Setting the time to %s' % time(5)
    'Setting the time to 5'
    >>> time += 5
    >>> 'After incrementing by 5, the time is %s' % time()
    'After incrementing by 5, the time is 10'
    >>> with time as t:  # Entering a context
    ...     'Time before iteration: %s' % t()
    ...     'Iteration: %s' % [val for val in t]
    ...     'Time after iteration: %s' % t()
    ...     t += 2
    ...     'The until parameter may be exceeded outside iteration: %s' % t()
    'Time before iteration: 10'
    'Iteration: [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]'
    'Time after iteration: 20'
    'The until parameter may be exceeded outside iteration: 22'
    >>> 'After exiting the context the time is back to %s' % time()
    'After exiting the context the time is back to 10'
    """

    _infinitely_iterable = True

    forever = Infinity()

    label = String(default='Time', doc="""
         The label given to the Time object. Can be used to convey
         more specific notions of time as appropriate. For instance,
         the label could be 'Simulation Time' or 'Duration'.""")

    time_type: t.Any = Parameter(default=int, constant=True, doc="""
        Callable that Time will use to convert user-specified time
        values into the current time; all times will be of the resulting
        numeric type.

        By default, time is of integer type, but you can supply any
        arbitrary-precision type like a fixed-point decimal or a
        rational, to allow fractional times.  Floating-point times are
        also allowed, but are not recommended because they will suffer
        from accumulated rounding errors.  For instance, incrementing
        a floating-point value 0.0 by 0.05, 20 times, will not reach
        1.0 exactly.  Instead, it will be slightly higher than 1.0,
        because 0.05 cannot be represented exactly in a standard
        floating point numeric type. Fixed-point or rational types
        should be able to handle such computations exactly, avoiding
        accumulation issues over long time intervals.

        Some potentially useful exact number classes:

         - int: Suitable if all times can be expressed as integers.

         - Python's decimal.Decimal and fractions.Fraction classes:
           widely available but slow and also awkward to specify times
           (e.g. cannot simply type 0.05, but have to use a special
           constructor or a string).

         - fixedpoint.FixedPoint: Allows a natural representation of
           times in decimal notation, but very slow and needs to be
           installed separately.

         - gmpy2.mpq: Allows a natural representation of times in
           decimal notation, and very fast because it uses the GNU
           Multi-Precision library, but needs to be installed
           separately and depends on a non-Python library.  gmpy2.mpq
           is gmpy2's rational type.
        """)

    timestep: t.Any = Parameter(default=1.0,doc="""
        Stepsize to be used with the iterator interface.
        Time can be advanced or decremented by any value, not just
        those corresponding to the stepsize, and so this value is only
        a default.""")

    until: t.Any = Parameter(default=forever,doc="""
         Declaration of an expected end to time values, if any.  When
         using the iterator interface, iteration will end before this
         value is exceeded.""")

    unit = String(default=None, doc="""
        The units of the time dimensions. The default of None is set
        as the global time function may on an arbitrary time base.

        Typical values for the parameter are 'seconds' (the SI unit
        for time) or subdivisions thereof (e.g. 'milliseconds').""")

    def __init__(self, **params):
        super().__init__(**params)
        self._time = self.time_type(0)
        self._exhausted = None
        self._pushed_state = []

    def __eq__(self, other):
        if not isinstance(other, Time):
            return False
        self_params = (self.timestep,self.until)
        other_params = (other.timestep,other.until)
        if self_params != other_params:
            return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self): return self

    def __next__(self):
        timestep = self.time_type(self.timestep)

        if self._exhausted is None:
            self._exhausted = False
        elif (self._time + timestep) <= self.until:
            self._time += timestep
        else:
            self._exhausted = None
            raise StopIteration
        return self._time

    def __call__(self, val=None, time_type=None):
        """
        When called with no arguments, returns the current time value.

        When called with a specified val, sets the time to it.

        When called with a specified time_type, changes the time_type
        and sets the current time to the given val (which *must* be
        specified) converted to that time type.  To ensure that
        the current state remains consistent, this is normally the only
        way to change the time_type of an existing Time instance.
        """
        if time_type and val is None:
            raise Exception("Please specify a value for the new time_type.")
        if time_type:
            type_param = self.param.objects('existing').get('time_type')
            if type_param is None:
                raise ValueError("time_type parameter not found")
            type_param.constant = False
            self.time_type = time_type
            type_param.constant = True
        if val is not None:
            self._time = self.time_type(val)

        return self._time

    def advance(self, val):
        self += val

    def __iadd__(self, other):
        self._time = self._time + self.time_type(other)
        return self

    def __isub__(self, other):
        self._time = self._time - self.time_type(other)
        return self

    def __enter__(self):
        """Enter the context and push the current state."""
        self._pushed_state.append((self._time, self.timestep, self.until))
        self.in_context = True
        return self

    def __exit__(self, exc, *args):
        """
        Exit from the current context, restoring the previous state.
        The StopIteration exception raised in context will force the
        context to exit. Any other exception exc that is raised in the
        block will not be caught.
        """
        (self._time, self.timestep, self.until) = self._pushed_state.pop()
        self.in_context = len(self._pushed_state) != 0
        if exc is StopIteration:
            return True

#-----------------------------------------------------------------------------
# Parameters
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Dynamic/Number
#-----------------------------------------------------------------------------


class Dynamic(Parameter[T]):
    """
    Parameter whose value can be generated dynamically by a callable
    object.

    If a Parameter is declared as Dynamic, it can be set a callable
    object (such as a function or callable class), and getting the
    parameter's value will call that callable.

    Note that at present, the callable object must allow attributes
    to be set on itself.

    If set as ``time_dependent``, setting the ``Dynamic.time_fn`` allows the
    production of dynamic values to be controlled: a new value will be
    produced only if the current value of ``time_fn`` is different from
    what it was the last time the parameter value was requested.

    By default, the Dynamic parameters are not ``time_dependent`` so that
    new values are generated on every call regardless of the time. The
    default ``time_fn`` used when ``time_dependent`` is a single :class:`Time` instance
    that allows general manipulations of time. It may be set to some
    other callable as required so long as a number is returned on each
    call.
    """

    time_fn = Time()
    time_dependent = False

    if t.TYPE_CHECKING:
        @t.overload
        def __init__(self) -> None:
            ...

        @t.overload
        def __init__(
            self: Dynamic[t.Any],
            default: t.Any = None,
            *,
            allow_None: bool = False,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default=Undefined,
        *,
        allow_None=t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        """
        Call the superclass's __init__ and set instantiate=True if the
        default is dynamic.
        """
        super().__init__(default=default, allow_None=allow_None, **params)

        if callable(self.default):
            self._set_instantiate(True)
            self._initialize_generator(self.default)

    def _initialize_generator(self, gen, obj=None):
        """Add 'last time' and 'last value' attributes to the generator."""
        # Could use a dictionary to hold these things.
        if obj is not None and hasattr(obj, "_Dynamic_time_fn"):
            gen._Dynamic_time_fn = obj._Dynamic_time_fn

        gen._Dynamic_last = None
        # Would have usede None for this, but can't compare a fixedpoint
        # number with None (e.g. 1>None but FixedPoint(1)>None can't be done)
        gen._Dynamic_time = -1

        gen._saved_Dynamic_last = []
        gen._saved_Dynamic_time = []

    def __get__(
        self, obj: Parameterized | None, objtype: type[Parameterized] | None = None
    ) -> T:
        """
        Call the superclass's __get__; if the result is not dynamic
        return that result, otherwise ask that result to produce a
        value and return it.
        """
        gen = super().__get__(obj, objtype)

        if not hasattr(gen,'_Dynamic_last'):
            return gen
        else:
            return t.cast("T", self._produce_value(gen))

    @instance_descriptor
    def __set__(self, obj: Parameterized, val: T):
        """
        Call the superclass's set and keep this parameter's
        instantiate value up to date (dynamic parameters
        must be instantiated).

        If val is dynamic, initialize it as a generator.
        """
        super().__set__(obj, val)

        dynamic = callable(val)
        if dynamic: self._initialize_generator(val,obj)
        if obj is None: self._set_instantiate(dynamic)

    def _produce_value(self, gen, force: bool = False):
        """
        Return a value from gen.

        If there is no time_fn, then a new value will be returned
        (i.e. gen will be asked to produce a new value).

        If force is True, or the value of time_fn() is different from
        what it was was last time _produce_value was called, a new
        value will be produced and returned. Otherwise, the last value
        gen produced will be returned.
        """
        if hasattr(gen, "_Dynamic_time_fn"):
            time_fn = gen._Dynamic_time_fn
        else:
            time_fn = self.time_fn

        if (time_fn is None) or (not self.time_dependent):
            value = _produce_value(gen)
            gen._Dynamic_last = value
        else:

            time = time_fn()

            if force or time != gen._Dynamic_time:
                value = _produce_value(gen)
                gen._Dynamic_last = value
                gen._Dynamic_time = time
            else:
                value = gen._Dynamic_last

        return value

    def _value_is_dynamic(
        self,
        obj: Parameterized | type[Parameterized] | None,
        objtype: type[Parameterized] | None = None
    ) -> bool:
        """
        Return True if the parameter is actually dynamic (i.e. the
        value is being generated).
        """
        return hasattr(t.cast("t.Any", super()).__get__(obj, objtype), '_Dynamic_last')

    def _inspect(
        self,
        obj: Parameterized | type[Parameterized],
        objtype: type[Parameterized] | None = None
    ) -> t.Any:
        """Return the last generated value for this parameter."""
        gen = t.cast("t.Any", super()).__get__(obj, objtype)

        if hasattr(gen,'_Dynamic_last'):
            return gen._Dynamic_last
        else:
            return gen

    def _force(
        self,
        obj: Parameterized | type[Parameterized],
        objtype: type[Parameterized] | None = None
    ) -> t.Any:
        """Force a new value to be generated, and return it."""
        gen = t.cast("t.Any", super()).__get__(obj, objtype)

        if hasattr(gen,'_Dynamic_last'):
            return self._produce_value(gen, force=True)
        else:
            return gen


class NumberInitKwargs(ParameterKwargs, total=False):
    bounds: tuple[t.Any | None, t.Any | None] | None
    softbounds: tuple[t.Any | None, t.Any | None] | None
    inclusive_bounds: tuple[bool, bool]
    step: t.Any | None
    set_hook: t.Callable[..., t.Any] | None


class NumberKwargs(NumberInitKwargs, total=False):
    allow_None: bool


class Number(Dynamic[T]):
    """
    A numeric :class:`Dynamic` Parameter, with a default value and optional bounds.

    There are two types of bounds: ``bounds`` and
    ``softbounds``.  ``bounds`` are hard bounds: the parameter must
    have a value within the specified range.  The default bounds are
    ``(None, None)``, meaning there are actually no hard bounds. One or
    both bounds can be set by specifying a value
    (e.g. ``bounds=(None, 10)`` means there is no lower bound, and an upper
    bound of 10). Bounds are inclusive by default, but exclusivity
    can be specified for each bound by setting inclusive_bounds
    (e.g. ``inclusive_bounds=(True, False)`` specifies an exclusive upper
    bound).

    Number is also a type of :class:`Dynamic` parameter, so its value
    can be set to a callable to get a dynamically generated
    number.

    When not being dynamically generated, bounds are checked when a
    Number is created or set. Using a default value outside the hard
    bounds, or one that is not numeric, results in an exception. When
    being dynamically generated, bounds are checked when the value
    of a Number is requested. A generated value that is not numeric,
    or is outside the hard bounds, results in an exception.

    As a special case, if ``allow_None=True`` (which is true by default if
    the parameter has a default of ``None`` when declared) then a value
    of ``None`` is also allowed.

    A separate method :meth:`set_in_bounds` is provided that will
    silently crop the given value into the legal range, for use
    in, for instance, a GUI.

    ``softbounds`` are present to indicate the typical range of
    the parameter, but are not enforced. Setting the soft bounds
    allows, for instance, a GUI to know what values to display on
    sliders for the Number.

    Example of creating a Number::

      AB = Number(default=0.5, bounds=(None,10), softbounds=(0,1), doc='Distance from A to B.')

    """

    __slots__ = ['bounds', 'softbounds', 'inclusive_bounds', 'step']

    _slot_defaults = dict(
        Dynamic._slot_defaults, default=0.0, bounds=None, softbounds=None,
        inclusive_bounds=(True,True), step=None,
    )

    bounds: tuple[float | int | None, float | int | None] | None
    softbounds: tuple[float | int | None, float | int | None] | None
    inclusive_bounds: tuple[bool, bool]
    step: float | int | None

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Number[float | int],
            default: float | int = 0.0,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Number[float | int | None],
            default: float | int = 0.0,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Number[float | int | None],
            default: None = None,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Number[float | int | None],
            default: float | int | None = None,
            *,
            allow_None: bool = False,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: float | int | None = t.cast("float | int | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        bounds: tuple[float | int | None, float | int | None] | None = t.cast(  # pyrefly: ignore[bad-argument-type]
            "tuple[float | int | None, float | int | None] | None", Undefined
        ),
        softbounds: tuple[float | int | None, float | int | None] | None = t.cast(  # pyrefly: ignore[bad-argument-type]
            "tuple[float | int | None, float | int | None] | None", Undefined
        ),
        inclusive_bounds: tuple[bool, bool] = t.cast("tuple[bool, bool]", Undefined),  # pyrefly: ignore[bad-argument-type]
        step: float | int | None = t.cast("float | int | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        set_hook: t.Callable[..., t.Any] | None = t.cast("t.Callable[..., t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        """
        Initialize this parameter object and store the bounds.

        Non-dynamic default values are checked against the bounds.
        """
        super().__init__(default=default, allow_None=allow_None, **params)
        self.bounds = bounds
        self.inclusive_bounds = inclusive_bounds
        self.softbounds = softbounds
        self.step = step
        self._validate(self.default)

    def __get__(
        self, obj: Parameterized | None, objtype: type[Parameterized] | None = None
    ) -> T:
        """Retrieve the value of the attribute, checking bounds if dynamically generated.

        Parameters
        ----------
        obj: Parameterized | None
            The instance the attribute is accessed on, or `None` for class access.
        objtype: type[Parameterized]
            The class that owns the attribute.

        Returns
        -------
        The value of the attribute, potentially after applying bounds checks.
        """
        result = super().__get__(obj, objtype)

        # Should be able to optimize this commonly used method by
        # avoiding extra lookups (e.g. _value_is_dynamic() is also
        # looking up 'result' - should just pass it in).
        if self._value_is_dynamic(obj, objtype):
            self._validate(result)
        return result

    def set_in_bounds(self, obj: Parameterized, val: t.Any) -> None:
        """
        Set to the given value, but cropped to be within the legal bounds.
        All objects are accepted, and no exceptions will be raised.  See
        crop_to_bounds for details on how cropping is done.
        """
        if not callable(val):
            bounded_val = self.crop_to_bounds(val)
        else:
            bounded_val = val
        super().__set__(obj, t.cast("t.Any", bounded_val))

    def crop_to_bounds(self, val: t.Any) -> t.Any:
        """
        Return the given value cropped to be within the hard bounds
        for this parameter.

        If a numeric value is passed in, check it is within the hard
        bounds. If it is larger than the high bound, return the high
        bound. If it's smaller, return the low bound. In either case, the
        returned value could be None.  If a non-numeric value is passed
        in, set to be the default value (which could be None).  In no
        case is an exception raised; all values are accepted.

        As documented in https://github.com/holoviz/param/issues/80,
        currently does not respect exclusive bounds, which would
        strictly require setting to one less for integer values or
        an epsilon less for floats.
        """
        # Values outside the bounds are silently cropped to
        # be inside the bounds.
        if _is_number(val):
            if self.bounds is None:
                return val
            vmin, vmax = self.bounds
            if vmin is not None:
                if val < vmin:
                    return  vmin

            if vmax is not None:
                if val > vmax:
                    return vmax

        elif self.allow_None and val is None:
            return val

        else:
            # non-numeric value sent in: reverts to default value
            return self.default

        return val

    def _validate_bounds(
        self,
        val: t.Any,
        bounds: tuple[t.Any | None, t.Any | None] | None,
        inclusive_bounds: tuple[bool, bool]
    ) -> None:
        if bounds is None or (val is None and self.allow_None) or callable(val):
            return
        vmin, vmax = bounds
        incmin, incmax = inclusive_bounds
        if vmax is not None:
            if incmax is True:
                if not val <= vmax:
                    raise ValueError(
                        f"{_validate_error_prefix(self)} must be at most "
                        f"{vmax}, not {val}."
                    )
            else:
                if not val < vmax:
                    raise ValueError(
                        f"{_validate_error_prefix(self)} must be less than "
                        f"{vmax}, not {val}."
                    )

        if vmin is not None:
            if incmin is True:
                if not val >= vmin:
                    raise ValueError(
                        f"{_validate_error_prefix(self)} must be at least "
                        f"{vmin}, not {val}."
                    )
            else:
                if not val > vmin:
                    raise ValueError(
                        f"{_validate_error_prefix(self)} must be greater than "
                        f"{vmin}, not {val}."
                    )

    def _validate_value(self, value: t.Any, allow_None: bool) -> None:
        if (allow_None and value is None) or (callable(value) and not inspect.isgeneratorfunction(value)):
            return

        if not _is_number(value):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes numeric values, "
                f"not {type(value)}."
            )

    def _validate_step(self, val: t.Any, step: t.Any) -> None:
        if step is not None and not _is_number(step):
            raise ValueError(
                f"{_validate_error_prefix(self, 'step')} can only be "
                f"None or a numeric value, not {type(step)}."
            )

    def _validate(self, val: t.Any) -> None:
        """
        Check that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        self._validate_value(val, self.allow_None)
        self._validate_step(val, self.step)
        self._validate_bounds(val, self.bounds, self.inclusive_bounds)

    def get_soft_bounds(self):
        return get_soft_bounds(self.bounds, self.softbounds)

    def __setstate__(self, state: dict[str, t.Any]) -> None:
        # Pickling backward compatibility
        if 'step' not in state:
            state['step'] = None

        super().__setstate__(state)


class IntegerInitKwargs(ParameterKwargs, total=False):
    bounds: tuple[int | None, int | None] | None
    softbounds: tuple[int | None, int | None] | None
    inclusive_bounds: tuple[bool, bool]
    step: int | None
    set_hook: t.Callable[..., t.Any] | None


class Integer(Number[T]):
    """Numeric Parameter required to be an Integer."""

    _slot_defaults = {**Number._slot_defaults, 'default': 0}

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Integer[int]):
            ...

        @t.overload
        def __init__(
            self: Integer[int],
            default: int = 0,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Integer[int | None],
            default: int = 0,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Integer[int | None],
            default: None = None,
            *,
            allow_None: bool = False,
            **kwargs: Unpack[NumberInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: int | None = t.cast("int | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[IntegerInitKwargs]
    ) -> None:
        super().__init__(default=default, allow_None=allow_None, **kwargs)  # type: ignore[misc]

    def _validate_value(self, value: t.Any, allow_None: bool) -> None:
        if callable(value):
            return

        if allow_None and value is None:
            return

        if not isinstance(value, _int_types):
            raise ValueError(
                f"{_validate_error_prefix(self)} must be an integer, "
                f"not {type(value)}."
            )

    def _validate_step(self, val: t.Any, step: t.Any) -> None:
        if step is not None and not isinstance(step, int):
            raise ValueError(
                f"{_validate_error_prefix(self, 'step')} can only be "
                f"None or an integer value, not {type(step)}."
            )


class Magnitude(Number[T]):
    """Numeric Parameter required to be in the range [0.0-1.0]."""

    _slot_defaults = {**Number._slot_defaults, 'default': 1.0, 'bounds': (0.0, 1.0)}


class DateInitKwargs(ParameterKwargs, total=False):
    bounds: tuple[t.Any | None, t.Any | None] | None
    softbounds: tuple[t.Any | None, t.Any | None] | None
    inclusive_bounds: tuple[bool, bool]
    step: int | None
    set_hook: t.Callable[..., t.Any] | None


class Date(Number[T]):
    """Date parameter of datetime or date type."""

    _slot_defaults = {**Number._slot_defaults, 'default': None}

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(  # type: ignore[inconsistent-overload]
            self: Date[dt.datetime | dt.date],
            default: dt.datetime | dt.date | None = None,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[DateInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(  # type: ignore[inconsistent-overload]
            self: Date[dt.datetime | dt.date | None],
            default: dt.datetime | dt.date | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[DateInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default=None,
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[DateInitKwargs]
    ) -> None:
        t.cast("t.Any", Number.__init__)(
            self, default=default, allow_None=allow_None, **kwargs
        )

    def _validate_value(self, value: t.Any, allow_None: bool) -> None:
        """
        Check that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        if self.allow_None and value is None:
            return

        if not isinstance(value, _dt_types) and not (allow_None and value is None):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes datetime and "
                f"date types, not {type(value)}."
            )

    def _validate_step(self, val: t.Any, step: t.Any) -> None:
        if step is not None and not isinstance(step, _dt_types):
            raise ValueError(
                f"{_validate_error_prefix(self, 'step')} can only be None, "
                f"a datetime or date type, not {type(step)}."
            )

    def _validate_bounds(self, val: t.Any, bounds: tuple[t.Any | None, t.Any | None] | None, inclusive_bounds: tuple[bool, bool]) -> None:
        val = _to_datetime(val)
        bounds = None if bounds is None else t.cast(
            "tuple[t.Any | None, t.Any | None]",
            tuple(map(_to_datetime, bounds)),
        )
        return super()._validate_bounds(val, bounds, inclusive_bounds)

    @classmethod
    def serialize(cls, value: dt.datetime | dt.date | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, (dt.datetime, dt.date)): # i.e np.datetime64
            value = value.astype(dt.datetime)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")

    @classmethod
    def deserialize(cls, value: str | None) -> dt.datetime | None:
        if value == 'null' or value is None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")


class CalendarDateInitKwargs(ParameterKwargs, total=False):
    bounds: tuple[dt.date | None, dt.date | None] | None
    softbounds: tuple[dt.date | None, dt.date | None] | None
    inclusive_bounds: tuple[bool, bool]
    step: int | None
    set_hook: t.Callable[..., t.Any] | None


class CalendarDate(Number[T]):
    """Parameter specifically allowing dates (not datetimes)."""

    _slot_defaults = {**Number._slot_defaults, 'default': None}

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(  # type: ignore[inconsistent-overload]
            self: CalendarDate[dt.date],
            default: dt.date | None = None,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[CalendarDateInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(  # type: ignore[inconsistent-overload]
            self: CalendarDate[dt.date | None],
            default: dt.date | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[CalendarDateInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: dt.date | None = t.cast("dt.date | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[CalendarDateInitKwargs]
    ) -> None:
        super().__init__( # type: ignore[misc, call-overload]
            self, default=default, allow_None=allow_None, **kwargs
        )

    def _validate_value(self, value, allow_None):
        """
        Check that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        if self.allow_None and value is None:
            return

        if (not isinstance(value, dt.date) or isinstance(value, dt.datetime)) and not (allow_None and value is None):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes date types."
            )

    def _validate_step(self, val: t.Any, step: t.Any) -> None:
        if step is not None and not isinstance(step, dt.date):
            raise ValueError(
                f"{_validate_error_prefix(self, 'step')} can only be None or "
                f"a date type, not {type(step)}."
            )

    @classmethod
    def serialize(cls, value: dt.date | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")

    @classmethod
    def deserialize(cls, value: str | None) -> dt.date | None:
        if value == 'null' or value is None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%d").date()

#-----------------------------------------------------------------------------
# Boolean
#-----------------------------------------------------------------------------

class Boolean(Parameter[T]):
    """Binary or tristate Boolean Parameter."""

    _slot_defaults = dict(Parameter._slot_defaults, default=False)

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Boolean[bool],
            default: bool = False,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Boolean[bool | None],
            default: bool | None = False,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Boolean[bool | None],
            default: None = None,
            *,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: bool | None = t.cast("bool | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__(default=default, allow_None=allow_None, **params)
        self._validate(self.default)

    def _validate_value(self, value: t.Any, allow_None: bool) -> None:
        if allow_None:
            if not isinstance(value, bool) and value is not None:
                raise ValueError(
                    f"{_validate_error_prefix(self)} only takes a "
                    f"boolean value or None, not {value!r}."
                )
        elif not isinstance(value, bool):
            raise ValueError(
                f"{_validate_error_prefix(self)} must be True or False, "
                f"not {value!r}."
            )

    def _validate(self, val: t.Any) -> None:
        self._validate_value(val, self.allow_None)


class Event(Boolean):
    """
    An Event Parameter is one whose value is intimately linked to the
    triggering of events for watchers to consume. Event has a boolean
    value, which when set to ``True`` triggers the associated watchers (as
    any Parameter does) and then is automatically set back to
    ``False``. Conversely, if events are triggered directly via
    :meth:`~parameterized.Parameters.trigger`, the value is transiently set
    to ``True`` (so that it's clear which of
    many parameters being watched may have changed), then restored to
    ``False`` when the triggering completes. An Event parameter is thus like
    a momentary switch or pushbutton with a transient ``True`` value that
    serves only to launch some other action (e.g. via a :func:`depends`
    decorator), rather than encapsulating the action itself as
    :class:`param.Action` does.
    """

    # _autotrigger_value specifies the value used to set the parameter
    # to when the parameter is supplied to the trigger method. This
    # value change is then what triggers the watcher callbacks.
    __slots__ = ['_autotrigger_value', '_mode', '_autotrigger_reset_value']

    def __init__(self, default=False, **params):
        self._autotrigger_value = True
        self._autotrigger_reset_value = False
        self._mode = 'set-reset'
        # Mode can be one of 'set', 'set-reset' or 'reset'

        # 'set' is normal Boolean parameter behavior when set with a value.
        # 'set-reset' temporarily sets the parameter (which triggers
        # watching callbacks) but immediately resets the value back to
        # False.
        # 'reset' applies the reset from True to False without
        # triggering watched callbacks

        # This _mode attribute is one of the few places where a specific
        # parameter has a special behavior that is relied upon by the
        # core functionality implemented in
        # parameterized.py. Specifically, the ``update`` method
        # temporarily sets this attribute in order to disable resetting
        # back to False while triggered callbacks are executing
        super().__init__(default=default,**params)

    def _reset_event(self, obj, val):
        val = False
        if obj is None:
            self.default = val
        else:
            obj._param__private.values[self.name] = val
        self._post_setter(obj, val)

    @instance_descriptor
    def __set__(self, obj, val):
        if self._mode in ['set-reset', 'set']:
            super().__set__(obj, val)
        if self._mode in ['set-reset', 'reset']:
            self._reset_event(obj, val)

#-----------------------------------------------------------------------------
# Tuple
#-----------------------------------------------------------------------------

class __compute_length_of_default:
    def __call__(self, p):
        return len(p.default)

    def __repr__(self):
        return repr(self.sig)

    @property
    def sig(self):
        return None


_compute_length_of_default = __compute_length_of_default()


class Tuple(Parameter[T]):
    """A tuple Parameter (e.g. ('a',7.6,[3,5])) with a fixed tuple length."""

    __slots__ = ['length']

    _slot_defaults = dict(Parameter._slot_defaults, default=(0,0), length=_compute_length_of_default)

    length: int | None

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Tuple[tuple[t.Any, ...]],
            *,
            length: int | None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Tuple[tuple[t.Any, ...]],
            default: tuple[t.Any, ...] = (0, 0),
            *,
            length: int | None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Tuple[tuple[t.Any, ...] | None],
            default: tuple[t.Any, ...] | None = (0, 0),
            *,
            length: int | None = None,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Tuple[tuple[t.Any, ...] | None],
            default: None,
            *,
            length: int | None = None,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Tuple[tuple[t.Any, ...] | None],
            default: tuple[t.Any, ...] | None = None,
            *,
            length: int | None = None,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default=t.cast("tuple[t.Any, ...] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        length: int | None = t.cast("int | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        """
        Initialize a tuple parameter with a fixed length (number of
        elements).  The length is determined by the initial default
        value, if any, and must be supplied explicitly otherwise.  The
        length is not allowed to change after instantiation.
        """
        super().__init__(default=default, allow_None=allow_None, **params)
        if length is Undefined and self.default is None:
            raise ValueError(
                f"{_validate_error_prefix(self, 'length')} must be "
                "specified if no default is supplied."
            )
        elif default is not Undefined and default:
            self.length = len(default)
        else:
            self.length = length
        self._validate(self.default)

    def _validate_value(self, value, allow_None):
        if value is None and allow_None:
            return

        if not isinstance(value, tuple):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes a tuple value, "
                f"not {type(value)}."
            )

    def _validate_length(self, val, length):
        if val is None and self.allow_None:
            return

        if not len(val) == length:
            raise ValueError(
                f"{_validate_error_prefix(self, 'length')} is not "
                f"of the correct length ({len(val)} instead of {length})."
            )

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_length(val, self.length)

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return list(value) # As JSON has no tuple representation

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        return tuple(value) # As JSON has no tuple representation


class NumericTuple(Tuple[T]):
    """A numeric tuple Parameter (e.g. (4.5,7.6,3)) with a fixed tuple length."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: NumericTuple[tuple[float, ...]]) -> None:
            ...

        @t.overload
        def __init__(
            self: NumericTuple[tuple[float, ...] | None],
            default: tuple[float, ...] = (0.0, 0.0),
            *,
            length: int | None = None,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: NumericTuple[tuple[float, ...] | None],
            default: None = None,
            *,
            length: int | None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: NumericTuple[tuple[float, ...] | None],
            default: tuple[float, ...] | None = None,
            *,
            length: int | None = None,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: tuple[float, ...] | None = t.cast("tuple[float, ...] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        length: int | None = t.cast("int | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__( # type: ignore[misc]
            default=default, length=length, allow_None=allow_None, **params
        )

    def _validate_value(self, value, allow_None):
        super()._validate_value(value, allow_None)
        if allow_None and value is None:
            return
        for n in value:
            if _is_number(n):
                continue
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes numeric "
                f"values, not {type(n)}."
            )


class XYCoordinates(NumericTuple[T]):
    """A NumericTuple for an X,Y coordinate."""

    _slot_defaults = {**NumericTuple._slot_defaults, 'default': (0.0, 0.0)}

    if t.TYPE_CHECKING:
        @t.overload
        def __init__(self: XYCoordinates[tuple[float, float] | None]) -> None:
            ...

        @t.overload
        def __init__(
            self: XYCoordinates[tuple[float, float]],
            default: tuple[float, float] = (0.0, 0.0),
            *,
            allow_None: t.Literal[False] = False,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: XYCoordinates[tuple[float, float] | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: XYCoordinates[tuple[float, float] | None],
            default: tuple[float, float] | None = None,
            *,
            allow_None: bool = False,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: tuple[float, float] | None = t.cast("tuple[float, float] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__( # type: ignore[misc]
            default=default,
            length=2,
            allow_None=allow_None,
            **params
        )


class RangeInitKwargs(ParameterKwargs, total=False):
    bounds: tuple[float, float] | None
    softbounds: tuple[float, float] | None
    inclusive_bounds: tuple[bool, bool]
    step: float | None
    set_hook: t.Callable[..., t.Any] | None


class Range(NumericTuple[T]):
    """A numeric range with optional bounds and softbounds."""

    __slots__ = ['bounds', 'inclusive_bounds', 'softbounds', 'step']

    _slot_defaults = {
        **NumericTuple._slot_defaults,
        'default': None,
        'bounds': None,
        'inclusive_bounds': (True, True),
        'softbounds': None,
        'step': None,
    }

    bounds: tuple[float, float] | None
    inclusive_bounds: tuple[bool, bool]
    softbounds: tuple[float, float] | None
    step: float | None

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Range[tuple[float, float]]) -> None:
            ...

        @t.overload
        def __init__(
            self: Range[tuple[float, float]],
            default: tuple[float, float] = (0.0, 0.0),
            *,
            allow_None: t.Literal[False] = False,
            **params: Unpack[RangeInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Range[tuple[float, float] | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **params: Unpack[RangeInitKwargs]
        ) -> None:
            ...

    def __init__(  # type: ignore[call-overload, misc]
        self,
        default: tuple[float, float] | None = t.cast("tuple[float, float] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        bounds: tuple[float, float] | None = t.cast("tuple[float, float] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        softbounds: tuple[float, float] | None = t.cast("tuple[float, float] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        inclusive_bounds: tuple[bool, bool] = t.cast("tuple[bool, bool]", Undefined),  # pyrefly: ignore[bad-argument-type]
        step: float | None = t.cast("float | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ):
        self.bounds = bounds
        self.inclusive_bounds = inclusive_bounds
        self.softbounds = softbounds
        self.step = step
        super().__init__(default=default, length=2, allow_None=allow_None, **params) # type: ignore[misc, call-overload]

    def _validate(self, val):
        super()._validate(val)
        self._validate_bounds(val, self.bounds, self.inclusive_bounds, 'bound')
        self._validate_bounds(val, self.softbounds, self.inclusive_bounds, 'softbound')
        self._validate_step(val, self.step)
        self._validate_order(val, self.step, allow_None=self.allow_None)

    def _validate_step(self, val, step):
        if step is not None:
            if not _is_number(step):
                raise ValueError(
                    f"{_validate_error_prefix(self, 'step')} can only be None "
                    f"or a numeric value, not {type(step)}."
                )
            elif step == 0:
                raise ValueError(
                    f"{_validate_error_prefix(self, 'step')} cannot be 0."
                )

    def _validate_order(self, val, step, allow_None):
        if val is None and allow_None:
            return
        if val is None:
            return
        elif val is not None and (val[0] is None or val[1] is None):
            return

        start, end = t.cast("tuple[t.Any, t.Any]", val)
        if step is not None and step > 0 and not start <= end:
            raise ValueError(
                f"{_validate_error_prefix(self)} end {end} is less than its "
                f"start {start} with positive step {step}."
            )
        elif step is not None and step < 0 and not start >= end:
            raise ValueError(
                f"{_validate_error_prefix(self)} start {start} is less than its "
                f"start {end} with negative step {step}."
            )

    def _validate_bound_type(self, value, position, kind):
        if not _is_number(value):
            raise ValueError(
                f"{_validate_error_prefix(self)} {position} {kind} can only be "
                f"None or a numerical value, not {type(value)}."
            )

    def _validate_bounds(self, val, bounds, inclusive_bounds, kind):
        if bounds is not None:
            for pos, v in zip(['lower', 'upper'], bounds):
                if v is None:
                    continue
                self._validate_bound_type(v, pos, kind)
        if kind == 'softbound':
            return

        if bounds is None or (val is None and self.allow_None):
            return
        vmin, vmax = bounds
        incmin, incmax = inclusive_bounds
        for bound, v in zip(['lower', 'upper'], val):
            too_low = (vmin is not None) and (v < vmin if incmin else v <= vmin)
            too_high = (vmax is not None) and (v > vmax if incmax else v >= vmax)
            if too_low or too_high:
                raise ValueError(
                    f"{_validate_error_prefix(self)} {bound} bound must be in "
                    f"range {self.rangestr()}, not {v}."
                )

    def get_soft_bounds(self):
        return get_soft_bounds(self.bounds, self.softbounds)

    def rangestr(self) -> str | tuple[str, str]:
        if self.bounds is None:
            return "(-inf, inf)"
        vmin, vmax = self.bounds
        incmin, incmax = self.inclusive_bounds
        min_delim = '[' if incmin else '('
        max_delim = ']' if incmax else ')'
        return f'{min_delim}{vmin}, {vmax}{max_delim}'


class DateRange(Range[T]):
    """
    A datetime or date range specified as ``(start, end)``.

    Bounds must be specified as datetime or date types (see ``param._dt_types``).
    """

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: DateRange[tuple[dt.datetime | dt.date, dt.datetime | dt.date] | None]) -> None:
            ...

        @t.overload
        def __init__(
            self: DateRange[tuple[dt.datetime | dt.date, dt.datetime | dt.date]],
            default: tuple[dt.datetime | dt.date, dt.datetime | dt.date] = (dt.datetime.now(), dt.datetime.now()),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[DateInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: DateRange[tuple[dt.datetime | dt.date, dt.datetime | dt.date] | None],
            default: tuple[dt.datetime | dt.date, dt.datetime | dt.date] | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[DateInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: tuple[dt.datetime | dt.date, dt.datetime | dt.date] | None = t.cast("tuple[dt.datetime | dt.date, dt.datetime | dt.date] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[DateInitKwargs]
    ) -> None:
        super().__init__(default=default, allow_None=allow_None, **kwargs)  # type: ignore[misc, call-overload]

    def _validate_bound_type(self, value, position, kind):
        if not isinstance(value, _dt_types):
            raise ValueError(
                f"{_validate_error_prefix(self)} {position} {kind} can only be "
                f"None or a date/datetime value, not {type(value)}."
            )

    def _validate_bounds(self, val, bounds, inclusive_bounds, kind):
        val = None if val is None else tuple(map(_to_datetime, val))
        bounds = None if bounds is None else tuple(map(_to_datetime, bounds))
        super()._validate_bounds(val, bounds, inclusive_bounds, kind)

    def _validate_value(self, value, allow_None):
        # Cannot use super()._validate_value as DateRange inherits from
        # NumericTuple which check that the tuple values are numbers and
        # datetime objects aren't numbers.
        if allow_None and value is None:
            return

        if not isinstance(value, tuple):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes a tuple value, "
                f"not {type(value)}."
            )
        for n in value:
            if isinstance(n, _dt_types):
                continue
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes date/datetime "
                f"values, not {type(n)}."
            )

        start, end = value
        if not end >= start:
            raise ValueError(
                f"{_validate_error_prefix(self)} end datetime {value[1]} "
                f"is before start datetime {value[0]}."
            )

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        # List as JSON has no tuple representation
        serialized = []
        for v in value:
            if not isinstance(v, (dt.datetime, dt.date)): # i.e np.datetime64
                v = v.astype(dt.datetime)
            # Separate date and datetime to deserialize to the right type.
            if type(v) is dt.date:
                v = v.strftime("%Y-%m-%d")
            else:
                v = v.strftime("%Y-%m-%dT%H:%M:%S.%f")
            serialized.append(v)
        return serialized

    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        deserialized = []
        for v in value:
            # Date
            if len(v) == 10:
                v = dt.datetime.strptime(v, "%Y-%m-%d").date()
            # Datetime
            else:
                v = dt.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%f")
            deserialized.append(v)
        # As JSON has no tuple representation
        return tuple(deserialized)


class CalendarDateRange(Range[T]):
    """A date range specified as ``(start_date, end_date)``."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: CalendarDateRange[tuple[dt.date, dt.date] | None]) -> None:
            ...

        @t.overload
        def __init__(
            self: CalendarDateRange[tuple[dt.date, dt.date]],
            default: tuple[dt.date, dt.date] = (dt.date(2024, 1, 1), dt.date(2024, 1, 2)),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[DateInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: CalendarDateRange[tuple[dt.date, dt.date] | None],
            default: tuple[dt.date, dt.date] | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[CalendarDateInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: tuple[dt.date, dt.date] | None = t.cast("tuple[dt.date, dt.date] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[CalendarDateInitKwargs]
    ) -> None:
        super().__init__(default=default, allow_None=allow_None, **kwargs)  # type: ignore[misc, call-overload]

    def _validate_value(self, value, allow_None):
        if allow_None and value is None:
            return

        for n in value:
            if not isinstance(n, dt.date):
                raise ValueError(
                    f"{_validate_error_prefix(self)} only takes date types, "
                    f"not {value}."
                )

        start, end = value
        if not end >= start:
            raise ValueError(
                f"{_validate_error_prefix(self)} end date {value[1]} is before "
                f"start date {value[0]}."
            )

    def _validate_bound_type(self, value, position, kind):
        if not isinstance(value, dt.date):
            raise ValueError(
                f"{_validate_error_prefix(self)} {position} {kind} can only be "
                f"None or a date value, not {type(value)}."
            )

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        # As JSON has no tuple representation
        return [v.strftime("%Y-%m-%d") for v in value]

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        # As JSON has no tuple representation
        return tuple([dt.datetime.strptime(v, "%Y-%m-%d").date() for v in value])

#-----------------------------------------------------------------------------
# Callable
#-----------------------------------------------------------------------------

class Callable(Parameter[T]):
    """
    Parameter holding a value that is a callable object, such as a function.

    A keyword argument ``instantiate=True`` should be provided when a
    function object is used that might have state.  On the other hand,
    regular standalone functions cannot be deepcopied as of Python
    2.4, so instantiate must be False for those values.
    """

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Callable[t.Callable[..., t.Any]]) -> None:
            ...

        @t.overload
        def __init__(
            self: Callable[t.Callable[..., t.Any]],
            default: t.Callable[..., t.Any] = lambda: None,
            *,
            allow_None: t.Literal[False] = False,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Callable[t.Callable[..., t.Any] | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **params: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(self,
        default: t.Callable[..., t.Any] | None = t.cast("t.Callable[..., t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__(default=default, **params)
        self._validate(self.default)

    def _validate_value(self, value, allow_None):
        if (allow_None and value is None) or callable(value):
            return
        raise ValueError(
            f"{_validate_error_prefix(self)} only takes a callable object, "
            f"not objects of {type(value)}."
        )

    def _validate(self, val):
        self._validate_value(val, self.allow_None)


class Action(Callable):
    """
    A user-provided function that can be invoked like a class or object method using ().
    In a GUI, this might be mapped to a button, but it can be invoked directly as well.
    """
# Currently same implementation as Callable, but kept separate to allow different handling in GUIs

#-----------------------------------------------------------------------------
# Composite
#-----------------------------------------------------------------------------

class Composite(Parameter):
    """
    A Parameter that is a composite of a set of other attributes of the class.

    The constructor argument ``attribs`` takes a list of attribute
    names, which may or may not be Parameters.  Getting the parameter
    returns a list of the values of the constituents of the composite,
    in the order specified.  Likewise, setting the parameter takes a
    sequence of values and sets the value of the constituent
    attributes.

    This Parameter type has not been tested with watchers and
    dependencies, and may not support them properly.
    """

    __slots__ = ['attribs', 'objtype']

    attribs: list[str]
    objtype: type[Parameterized]

    @t.overload
    def __init__(self) -> None:
        ...

    @t.overload
    def __init__(
        self,
        *,
        attribs: list[str] | None = None,
        doc: str | None = None,
        label: str | None = None,
        precedence: float | None = None,
        instantiate: bool = False,
        constant: bool = False,
        readonly: bool = False,
        pickle_default_value: bool = True,
        allow_None: bool = False,
        per_instance: bool = True,
        allow_refs: bool = False,
        nested_refs: bool = False,
        default_factory: t.Callable[..., t.Any] | None = None,
        metadata: dict[str, t.Any] | None = None
    ) -> None:
        ...

    def __init__(self, *, attribs=Undefined, **kw):
        if attribs is Undefined:
            attribs = []
        super().__init__(default=Undefined, **kw)
        self.attribs = attribs  # type: ignore[attr-defined, ty:invalid-assignment]

    def __get__(
        self, obj: Parameterized | None, objtype: type[Parameterized] | None = None
    ) -> list[t.Any]:
        """Return the values of all the attribs, as a list."""
        if objtype is None:
            objtype = self.objtype
        if obj is None:
            return [getattr(objtype, a) for a in self.attribs]
        else:
            return [getattr(obj, a) for a in self.attribs]

    def _validate_attribs(self, val, attribs):
        if len(val) == len(attribs):
            return
        raise ValueError(
            f"{_validate_error_prefix(self)} got the wrong number "
            f"of values (needed {len(attribs)}, but got {len(val)})."
        )

    def _validate(self, val):
        self._validate_attribs(val, self.attribs)

    def _post_setter(self, obj, val):
        if obj is None:
            for a, v in zip(self.attribs, val):
                setattr(self.objtype, a, v)
        else:
            for a, v in zip(self.attribs, val):
                setattr(obj, a, v)

#-----------------------------------------------------------------------------
# Selector
#-----------------------------------------------------------------------------

class SelectorBase(Parameter[T]):
    """
    Parameter whose value must be chosen from a list of possibilities.

    Subclasses must implement get_range().
    """

    def get_range(self):
        raise NotImplementedError("get_range() must be implemented in subclasses.")


class ListProxy(list):
    """
    Container that supports both list-style and dictionary-style
    updates. Useful for replacing code that originally accepted lists
    but needs to support dictionary access (typically for naming
    items).
    """

    def __init__(self, iterable, parameter: Selector):
        super().__init__(iterable)
        self._parameter = parameter

    def _warn(self, method):
        clsname = type(self._parameter).__name__
        get_logger().warning(
            '{clsname}.objects{method} is deprecated if objects attribute '
            'was declared as a dictionary. Use `{clsname}.objects[label] '
            '= value` instead.'.format(clsname=clsname, method=method)
        )

    @contextmanager
    def _trigger(self, trigger=True):
        trigger = 'objects' in self._parameter.watchers and trigger
        old = dict(self._parameter.names) or list(self._parameter._objects)
        yield
        if trigger:
            value = self._parameter.names or self._parameter._objects
            self._parameter._trigger_event('objects', old, value)

    def __getitem__(self, index):
        if self._parameter.names:
            return self._parameter.names[index]
        return super().__getitem__(index)

    def __setitem__(self, index, object, trigger=True):
        if isinstance(index, (int, slice)):
            if self._parameter.names:
                self._warn('[index] = object')
            with self._trigger():
                super().__setitem__(index, object)
                self._parameter._objects[index] = object
            return
        if self and not self._parameter.names:
            self._parameter.names = _named_objs(self)
        with self._trigger(trigger):
            if index in self._parameter.names:
                old = self._parameter.names[index]
                idx = self.index(old)
                super().__setitem__(idx, object)
                self._parameter._objects[idx] = object
            else:
                super().append(object)
                self._parameter._objects.append(object)
            self._parameter.names[index] = object

    def __eq__(self, other):
        eq = super().__eq__(other)
        if self._parameter.names and eq is NotImplemented:
            return dict(zip(self._parameter.names, self)) == other
        return eq

    def __ne__(self, other):
        return not self.__eq__(other)

    def append(self, object):
        if self._parameter.names:
            self._warn('.append')
        with self._trigger():
            super().append(object)
            self._parameter._objects.append(object)

    def copy(self):  # type: ignore[override]
        if self._parameter.names:
            return self._parameter.names.copy()
        return list(self)

    def clear(self):
        with self._trigger():
            super().clear()
            self._parameter._objects.clear()
            self._parameter.names.clear()

    def extend(self, objects):
        if self._parameter.names:
            self._warn('.append')
        with self._trigger():
            super().extend(objects)
            self._parameter._objects.extend(objects)

    def get(self, key, default=None):
        if self._parameter.names:
            return self._parameter.names.get(key, default)
        return _named_objs(self).get(key, default)

    def insert(self, index, object):
        if self._parameter.names:
            self._warn('.insert')
        with self._trigger():
            super().insert(index, object)
            self._parameter._objects.insert(index, object)

    def items(self):
        if self._parameter.names:
            return self._parameter.names.items()
        return _named_objs(self).items()

    def keys(self):
        if self._parameter.names:
            return self._parameter.names.keys()
        return _named_objs(self).keys()

    def pop(self, *args):
        index = args[0] if args else -1
        if isinstance(index, int):
            with self._trigger():
                super().pop(index)
                object = self._parameter._objects.pop(index)
                if self._parameter.names:
                    self._parameter.names = {
                        k: v for k, v in self._parameter.names.items()
                        if v is object
                    }
            return
        if self and not self._parameter.names:
            raise ValueError(
                'Cannot pop an object from {clsname}.objects if '
                'objects was not declared as a dictionary.'
            )
        with self._trigger():
            object = self._parameter.names.pop(*args)
            super().remove(object)
            self._parameter._objects.remove(object)
        return object

    def remove(self, object):
        with self._trigger():
            super().remove(object)
            self._parameter._objects.remove(object)
            if self._parameter.names:
                copy = self._parameter.names.copy()
                self._parameter.names.clear()
                self._parameter.names.update({
                    k: v for k, v in copy.items() if v is not object
                })

    def update(self, objects, **items):
        if not self._parameter.names:
            self._parameter.names = _named_objs(self)
        objects = objects.items() if isinstance(objects, dict) else objects
        with self._trigger():
            for i, o in enumerate(objects):
                if not isinstance(o, Sequence):
                    raise TypeError(
                        f'cannot convert dictionary update sequence element #{i} to a sequence'
                    )
                o = tuple(o)
                n = len(o)
                if n != 2:
                    raise ValueError(
                        f'dictionary update sequence element #{i} has length {n}; 2 is required'
                    )
                k, v = o
                self.__setitem__(k, v, trigger=False)
            for k, v in items.items():
                self.__setitem__(k, v, trigger=False)

    def values(self):
        if self._parameter.names:
            return self._parameter.names.values()
        return _named_objs(self).values()


class __compute_selector_default:
    """
    Using a function instead of setting default to [] in _slot_defaults, as
    if it were modified in place later, which would happen with check_on_set set to False,
    then the object in _slot_defaults would itself be updated and the next Selector
    instance created wouldn't have [] as the default but a populated list.
    """

    def __call__(self, p):
        return []

    def __repr__(self):
        return repr(self.sig)

    @property
    def sig(self):
        return []

_compute_selector_default = __compute_selector_default()


class __compute_selector_checking_default:
    def __call__(self, p):
        return len(p.objects) != 0

    def __repr__(self):
        return repr(self.sig)

    @property
    def sig(self):
        return None

_compute_selector_checking_default = __compute_selector_checking_default()


class _SignatureSelector(Parameter[T]):
    # Needs docstring; why is this a separate mixin?
    _slot_defaults = dict(
        SelectorBase._slot_defaults, _objects=_compute_selector_default,
        compute_default_fn=None, check_on_set=_compute_selector_checking_default,
        allow_None=None, instantiate=False, default=None,
    )

    @classmethod
    def _modified_slots_defaults(cls):
        defaults = super()._modified_slots_defaults()
        defaults['objects'] = defaults.pop('_objects')
        return defaults


class SelectorInitKwargs(ParameterKwargs, total=False):
    objects: list[t.Any] | dict[str, t.Any] | None
    compute_default_fn: t.Callable[[], t.Any] | None
    check_on_set: bool
    empty_default: bool


class Selector(SelectorBase, _SignatureSelector[T]):
    """
    Parameter whose value must be one object from a list of possible objects.

    By default, if no default is specified, picks the first object from
    the provided set of objects, as long as the objects are in an
    ordered data collection.

    ``check_on_set`` restricts the value to be among the current list of
    objects. By default, if objects are initially supplied,
    ``check_on_set`` is ``True``, whereas if no objects are initially
    supplied, ``check_on_set`` is ``False``. This can be overridden by
    explicitly specifying check_on_set initially.

    If ``check_on_set`` is ``True`` (either because objects are supplied
    initially, or because it is explicitly specified), the default
    (initial) value must be among the list of objects (unless the
    default value is ``None``).

    The list of objects can be supplied as a list (appropriate for
    selecting among a set of strings, or among a set of objects with a
    ``name`` parameter), or as a (preferably ordered) dictionary from
    names to objects.  If a dictionary is supplied, the objects
    will need to be hashable so that their names can be looked
    up from the object value.

    ``empty_default`` is an internal argument that does not have a slot.
    """

    __slots__ = ['_objects', 'compute_default_fn', 'check_on_set', 'names']

    _objects: list[t.Any]
    compute_default_fn: t.Callable[[], t.Any] | None
    check_on_set: bool
    names: dict[str, t.Any]

    # Selector is usually used to allow selection from a list of
    # existing objects, therefore instantiate is False by default.
    def __init__(
        self,
        *,
        objects: list[t.Any] | dict[str, t.Any] | None = t.cast("list[t.Any] | dict[str, t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        default: t.Any = t.cast("t.Any", Undefined),  # pyrefly: ignore[bad-argument-type]
        compute_default_fn: t.Callable[[], t.Any] | None = t.cast("t.Callable[[], t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        check_on_set: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        empty_default: bool = False,
        **params: Unpack[ParameterKwargs]
    ) -> None:

        if compute_default_fn is not Undefined:
            warnings.warn(
                'compute_default_fn has been deprecated and will be removed in a future version.',
                _ParamDeprecationWarning,
                stacklevel=_find_stack_level(),
            )

        autodefault = Undefined
        if objects is not Undefined and objects:
            if isinstance(objects, dict):
                autodefault = list(objects.values())[0]
            elif isinstance(objects, list):
                autodefault = objects[0]

        default = autodefault if (not empty_default and default is Undefined) else default

        self.objects = objects
        self.compute_default_fn = compute_default_fn
        self.check_on_set = check_on_set

        instantiate = params.pop("instantiate", Undefined)
        params["instantiate"] = False if instantiate is Undefined else instantiate
        super().__init__(default=default, **params)
        # Required as Parameter sets allow_None=True if default is None
        self.allow_None = allow_None
        if self.default is not None:
            self._validate_value(self.default)
        self._update_state()

    def _update_state(self):
        if self.check_on_set is False and self.default is not None:
            self._ensure_value_is_in_objects(self.default)

    @property
    def objects(self):
        return ListProxy(self._objects, self)

    @objects.setter
    def objects(self, objects):
        if isinstance(objects, Mapping):
            self.names = dict(objects)
            self._objects = list(objects.values())
        else:
            self.names = {}
            self._objects = objects

    # Note that if the list of objects is changed, the current value for
    # this parameter in existing POs could be outside of the new range.

    def compute_default(self):
        """
        If this parameter's compute_default_fn is callable, call it
        and store the result in self.default.

        Also removes None from the list of objects (if the default is
        no longer None).

        .. deprecated:: 2.3.0
        """
        warnings.warn(
            'compute_default() has been deprecated and will be removed in a future version.',
            _ParamDeprecationWarning,
            stacklevel=_find_stack_level(),
        )

        if self.default is None and callable(self.compute_default_fn):
            self.default = self.compute_default_fn()
            self._ensure_value_is_in_objects(self.default)

    def _validate(self, val):
        if not self.check_on_set:
            self._ensure_value_is_in_objects(val)
            return

        self._validate_value(val)

    def _validate_value(self, value, allow_None=None):
        if allow_None is None:
            allow_None = self.allow_None
        if self.check_on_set and not (allow_None and value is None) and value not in self.objects:
            items = []
            limiter = ']'
            length = 0
            for item in self.objects:
                string = str(item)
                length += len(string)
                if length < 200:
                    items.append(string)
                else:
                    limiter = ', ...]'
                    break
            items = '[' + ', '.join(items) + limiter
            raise ValueError(
                f"{_validate_error_prefix(self)} does not accept {value!r}; "
                f"valid options include: {items!r}"
            )

    def _ensure_value_is_in_objects(self, val):
        """
        Make sure that the provided value is present on the objects list.
        Subclasses can override if they support multiple items on a list,
        to check each item instead.
        """
        if val not in self.objects:
            self._objects.append(val)

    def get_range(self) -> dict[str, t.Any]:
        """
        Return the possible objects to which this parameter could be set.

        (Returns the dictionary {object.name: object}.)
        """
        return _named_objs(self._objects, self.names)


class ObjectSelector(Selector):
    """
    Deprecated. Same as Selector, but with a different constructor for
    historical reasons.
    """

    def __init__(
        self,
        default: t.Any = t.cast("t.Any", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[SelectorInitKwargs]
    ) -> None:
        kwargs["empty_default"] = True
        super().__init__(default=default, **kwargs) # type: ignore[misc, call-overload]


class FileSelectorInitKwargs(ParameterKwargs, total=False):
    path: str | PathLike


class FileSelector(Selector[T]):
    """Given a path glob, allows one file to be selected from those matching."""

    __slots__ = ['path']

    _slot_defaults = {**Selector._slot_defaults, 'path': ""}

    path: str | PathLike

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: FileSelector[PathLike | str | None]) -> None:
            ...

        @t.overload
        def __init__(
            self: FileSelector[PathLike | str],
            default: PathLike | str = pathlib.Path(""),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[FileSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: FileSelector[PathLike | str | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[FileSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: FileSelector[PathLike | str | None],
            default: PathLike | str = pathlib.Path(""),
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[FileSelectorInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: PathLike | str | None = t.cast("PathLike | str", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        path: str | PathLike = t.cast("str | PathLike", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", False),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[ParameterKwargs]
    ) -> None:
        self.path = path
        self.update(path=path)
        super().__init__(default=default, objects=self._objects, **kwargs) # type: ignore[misc, call-overload]

    def _on_set(self, attribute: str, old: t.Any, value: t.Any):
        super()._on_set(attribute, old, value)
        if attribute == 'path':
            self.update(path=value)

    def update(self, path: str | PathLike[str] = t.cast("str | PathLike[str]", Undefined)):  # pyrefly: ignore[bad-argument-type]
        resolved = self.path if path is Undefined else path
        if resolved is Undefined or resolved == "":
            self.objects = []
        else:
            # Convert using os.fspath and pathlib.Path to handle ensure
            # the path separators are consistent (on Windows in particular)
            pathpattern = os.fspath(pathlib.Path(t.cast("str | PathLike[str]", resolved)))  # type: ignore[redundant-cast]
            self.objects = sorted(glob.glob(pathpattern))
        if self.default in self.objects:
            return
        self.default = self.objects[0] if self.objects else None

    def get_range(self) -> dict[str, str | PathLike]:
        return _abbreviate_paths(self.path,super().get_range())


class ListSelector(Selector):
    """
    Variant of :class:`Selector` where the value can be multiple objects from
    a list of possible objects.
    """

    def __init__(
        self,
        default: list[t.Any] | None = t.cast("list[t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", False),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[SelectorInitKwargs]
    ) -> None:
        kwargs["empty_default"] = True
        super().__init__(default=default, allow_None=allow_None, **kwargs) # type: ignore[misc, call-overload]

    def compute_default(self):
        warnings.warn(
            'compute_default() has been deprecated and will be removed in a future version.',
            _ParamDeprecationWarning,
            stacklevel=_find_stack_level(),
        )
        if self.default is None and callable(self.compute_default_fn):
            self.default = self.compute_default_fn()
            for o in self.default:
                if o not in self.objects:
                    self.objects.append(o)

    def _validate(self, val):
        if (val is None and self.allow_None):
            return
        self._validate_type(val)

        if self.check_on_set:
            self._validate_value(val)
        else:
            for v in val:
                self._ensure_value_is_in_objects(v)

    def _validate_type(self, val):
        if not isinstance(val, list):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes list types, "
                f"not {val!r}."
            )

    def _validate_value(self, value, allow_None=None):
        if allow_None is None:
            allow_None = self.allow_None
        self._validate_type(value)
        if allow_None and value is None:
            return
        if value is not None:
            for o in value:
                super()._validate_value(o)

    def _update_state(self):
        if self.check_on_set is False and self.default is not None:
            for o in self.default:
                self._ensure_value_is_in_objects(o)


class MultiFileSelector(ListSelector):
    """Given a path glob, allows multiple files to be selected from the list of matches."""

    __slots__ = ['path']

    _slot_defaults = {**Selector._slot_defaults, 'path': ""}

    def __init__(
        self,
        default: list[PathLike | str] | None = t.cast("list[PathLike | str] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        path: str | PathLike = t.cast("str | PathLike", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[SelectorInitKwargs]
    ) -> None:
        self.default = default
        self.path = path
        self.update(path=path)
        kwargs["objects"] = self._objects
        super().__init__(default=default, **kwargs)

    def _on_set(self, attribute: str, old: t.Any, value: t.Any):
        super()._on_set(attribute, old, value)
        if attribute == 'path':
            self.update(path=value)

    def update(self, path=Undefined):
        if path is Undefined:
            path = self.path
        self.objects = sorted(glob.glob(t.cast("str", path)))
        if self.default and all([o in self.objects for o in self.default]):
            return
        elif not self.default:
            return
        self.default = self.objects

    def get_range(self) -> dict[str, str | PathLike]:
        return _abbreviate_paths(self.path,super().get_range())


class ClassSelectorInitKwargs(t.TypedDict, total=False):
    doc: str | None
    label: str | None
    precedence: float | None
    constant: bool
    readonly: bool
    pickle_default_value: bool
    per_instance: bool
    allow_refs: bool
    nested_refs: bool
    default_factory: t.Callable[..., t.Any] | None
    metadata: dict[str, t.Any] | None


class ClassSelector(SelectorBase[T]):
    """
    Parameter allowing selection of either a subclass or an instance of a class
    or tuple of classes.

    By default, requires an instance, but if ``is_instance=False``, accepts a
    class instead. Both class and instance values respect the ``instantiate``
    slot, though it matters only for ``is_instance=True``.
    """

    __slots__ = ['class_', 'is_instance']

    _slot_defaults = {**SelectorBase._slot_defaults, 'instantiate': True, 'is_instance': True}

    instantiate: bool
    is_instance: bool
    class_: type | tuple[type, ...]

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: ClassSelector[type[CT]],
            *,
            class_: type[CT] | tuple[type[CT], ...],
            default: type[CT] | None = None,
            instantiate: bool = True,
            is_instance: t.Literal[False],
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ClassSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: ClassSelector[type[CT] | None],
            *,
            class_: type[CT] | tuple[type[CT], ...],
            default: type[CT] | None = None,
            instantiate: bool = True,
            is_instance: t.Literal[False],
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ClassSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: ClassSelector[IT],
            *,
            class_: type[IT] | tuple[type[IT], ...],
            default: IT | None = None,
            instantiate: bool = True,
            is_instance: t.Literal[True] = True,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ClassSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: ClassSelector[IT | None],
            *,
            class_: type[IT] | tuple[type[IT], ...],
            default: IT | None = None,
            instantiate: bool = True,
            is_instance: t.Literal[True] = True,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ClassSelectorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: ClassSelector[IT | CT | None],
            *,
            class_: type[IT] | type[CT] | tuple[type[IT] | type[CT], ...],
            default: IT | type[CT] | None = None,
            instantiate: bool = True,
            is_instance: bool = True,
            allow_None: bool = False,
            **kwargs: Unpack[ClassSelectorInitKwargs]
        ) -> None:
            ...

    def __init__(
        self, *,
        class_: type | tuple[type, ...] = t.cast("type | tuple[type, ...]", Undefined),  # pyrefly: ignore[bad-argument-type]
        default: t.Any | None = t.cast("t.Any | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        instantiate: bool = True,
        is_instance: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ClassSelectorInitKwargs]
    ) -> None:
        self.class_ = class_
        self.is_instance = is_instance  # type: ignore
        super().__init__(  # type: ignore[misc, call-overload]
            default=default, allow_None=allow_None, **params
        )
        self._validate(self.default)

    def _validate(self, val):
        super()._validate(val)
        self._validate_class_(val, self.class_, self.is_instance)

    def _validate_class_(self, val: t.Any, class_: type | tuple[type, ...], is_instance: bool):
        if (val is None and self.allow_None):
            return
        if (is_instance and isinstance(val, class_)) or (not is_instance and issubclass(val, class_)):
            return

        if isinstance(class_, tuple):
            class_name = ('({})'.format(', '.join(cl.__name__ for cl in class_)))
        else:
            class_name = class_.__name__

        raise ValueError(
            f"{_validate_error_prefix(self)} value must be "
            f"{'an instance' if is_instance else 'a subclass'} of {class_name}, not {val!r}."
        )

    def get_range(self):
        """
        Return the possible types for this parameter's value.

        (I.e. return ``{name: <class>}`` for all classes that are
        :func:`param.parameterized.descendents` of ``self.class_``.)

        Only classes from modules that have been imported are added
        (see :func:`param.parameterized.descendents`).
        """
        classes = self.class_ if isinstance(self.class_, tuple) else (self.class_,)
        all_classes = {}
        for cls in classes:
            desc = _descendents(cls, concrete=True)
            # This will clobber separate classes with identical names.
            # Known historical issue, see https://github.com/holoviz/param/pull/1035
            all_classes.update({c.__name__: c for c in desc})
        d = OrderedDict((name, class_) for name,class_ in all_classes.items())
        if self.allow_None:
            d['None'] = None
        return d


class Dict(ClassSelector[T]):
    """Parameter whose value is a dictionary."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Dict[dict[t.Any, t.Any] | None],
        ):
            ...

        @t.overload
        def __init__(
            self: Dict[dict[t.Any, t.Any]],
            default: dict[t.Any, t.Any] = {},
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Dict[dict[t.Any, t.Any] | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Dict[dict[t.Any, t.Any] | None],
            default: dict[t.Any, t.Any] | None = None,
            *,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: dict[t.Any, t.Any] | None = t.cast("dict[t.Any, t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__(default=default, class_=dict, allow_None=allow_None, **params) # type: ignore[misc, call-overload]


class Array(ClassSelector[T]):
    """Parameter whose value is a numpy array."""

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Array[np.ndarray | None],
        ):
            ...

        @t.overload
        def __init__(
            self: Array[np.ndarray],
            default: np.ndarray = np.array([]),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Array[np.ndarray | None],
            default: None = None,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(self, default=Undefined, **params):
        ndarray = importlib.import_module('numpy').ndarray  # type: ignore[unresolved-attribute]
        t.cast("t.Any", super().__init__)(default=default, class_=ndarray, **params)

    @classmethod
    def serialize(cls, value: np.ndarray | None) -> list | None:
        if value is None:
            return None
        return value.tolist()

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        numpy = t.cast("t.Any", importlib.import_module('numpy'))
        if isinstance(value, str):
            return _deserialize_from_path(
                {'.npy': numpy.load, '.txt': lambda x: numpy.loadtxt(str(x))},
                value, 'Array'
            )
        else:
            return numpy.asarray(value)


class DataFrameInitKwargs(ParameterKwargs, total=False):
    rows: int | tuple[int | None, int | None] | None
    columns: int | tuple[int | None, int | None] | list[str] | set[str] | None
    ordered: bool | None


class DataFrame(ClassSelector[T]):
    """
    Parameter whose value is a pandas ``DataFrame``.

    The structure of the DataFrame can be constrained by the rows and
    columns arguments:

    ``rows``: If specified, may be a number or an integer bounds tuple to
    constrain the allowable number of rows.

    ``columns``: If specified, may be a number, an integer bounds tuple, a
    list or a set. If the argument is numeric, constrains the number of
    columns using the same semantics as used for rows. If either a list
    or set of strings, the column names will be validated. If a set is
    used, the supplied DataFrame must contain the specified columns and
    if a list is given, the supplied DataFrame must contain exactly the
    same columns and in the same order and no other columns.
    """

    __slots__ = ['rows', 'columns', 'ordered']

    _slot_defaults = {
        **ClassSelector._slot_defaults,
        'rows': None,
        'columns': None,
        'ordered': None,
    }

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: DataFrame[pd.DataFrame | None],
        ):
            ...

        @t.overload
        def __init__(
            self: DataFrame[pd.DataFrame],
            default: pd.DataFrame = pd.DataFrame([]),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[DataFrameInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: DataFrame[pd.DataFrame | None],
            default: pd.DataFrame | None = None,
            *,
            rows: int | tuple[int | None, int | None] | None = None,
            columns: int | tuple[int | None, int | None] | list[str] | set[str] | None = None,
            ordered: bool | None = None,
            allow_None: bool = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: pd.DataFrame | None = t.cast("pd.DataFrame | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        rows: int | tuple[int | None, int | None] | None = t.cast("int | tuple[int | None, int | None] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        columns: int | tuple[int | None, int | None] | list[str] | set[str] | None = t.cast("int | tuple[int | None, int | None] | list[str] | set[str] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        ordered: bool | None = t.cast("bool | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        pdDFrame = importlib.import_module('pandas').DataFrame  # type: ignore[unresolved-attribute]
        self.rows = rows
        self.columns = columns
        self.ordered = ordered
        super().__init__(default=default, class_=pdDFrame, **params)
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = f'{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(f"{_validate_error_prefix(self)}: {message}")
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(f"{_validate_error_prefix(self)}: {message}")

    def _validate(self, val):
        super()._validate(val)

        if isinstance(self.columns, set) and self.ordered is True:
            raise ValueError(
                f'{_validate_error_prefix(self)}: columns cannot be ordered '
                f'when specified as a set'
            )

        if self.allow_None and val is None:
            return

        if self.columns is None:
            pass
        elif (isinstance(self.columns, tuple) and len(self.columns)==2
              and all(isinstance(v, (type(None), numbers.Number)) for v in self.columns)): # Numeric bounds tuple
            self._length_bounds_check(self.columns, len(val.columns), 'columns')
        elif isinstance(self.columns, (list, set)):
            self.ordered = isinstance(self.columns, list) if self.ordered is None else self.ordered
            difference = set(self.columns) - {str(el) for el in val.columns}
            if difference:
                raise ValueError(
                    f"{_validate_error_prefix(self)}: provided columns "
                    f"{list(val.columns)} does not contain required "
                    f"columns {sorted(self.columns)}"
                )
        else:
            self._length_bounds_check(self.columns, len(val.columns), 'column')

        if self.ordered and isinstance(self.columns, Iterable):
            if list(val.columns) != list(self.columns):
                raise ValueError(
                    f"{_validate_error_prefix(self)}: provided columns "
                    f"{list(val.columns)} must exactly match {self.columns}"
                )
        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'row')

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return value.to_dict('records')

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        pandas = t.cast("t.Any", importlib.import_module('pandas'))
        if isinstance(value, str):
            return _deserialize_from_path(
                {
                    '.csv': pandas.read_csv,
                    '.dta': pandas.read_stata,
                    '.feather': pandas.read_feather,
                    '.h5': pandas.read_hdf,
                    '.hdf5': pandas.read_hdf,
                    '.json': pandas.read_json,
                    '.ods': pandas.read_excel,
                    '.parquet': pandas.read_parquet,
                    '.pkl': pandas.read_pickle,
                    '.tsv': lambda x: pandas.read_csv(x, sep='\t'),
                    '.xlsm': pandas.read_excel,
                    '.xlsx': pandas.read_excel,
                }, value, 'DataFrame')
        else:
            return pandas.DataFrame(value)


class Series(ClassSelector[T]):
    """
    Parameter whose value is a pandas ``Series``.

    The structure of the Series can be constrained by the rows argument
    which may be a number or an integer bounds tuple to constrain the
    allowable number of rows.
    """

    __slots__ = ['rows']

    _slot_defaults = dict(
        ClassSelector._slot_defaults, rows=None, allow_None=False
    )

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(
            self: Series[pd.Series | None],
        ):
            ...

        @t.overload
        def __init__(
            self: Series[pd.Series],
            default: pd.Series = pd.Series([]),
            *,
            rows: int | tuple[int | None, int | None] | None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Series[pd.Series | None],
            default: None = None,
            *,
            rows: int | tuple[int | None, int | None] | None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Series[pd.Series | None],
            default: pd.Series | None = None,
            *,
            rows: int | tuple[int | None, int | None] | None = None,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Series[pd.Series | None],
            default: pd.Series | None = None,
            *,
            rows: int | tuple[int | None, int | None] | None = None,
            allow_None: bool = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: pd.Series | None = t.cast("pd.Series | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        rows: int | tuple[int | None, int | None] | None = t.cast("int | tuple[int | None, int | None] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ):
        pdSeries = t.cast("t.Any", importlib.import_module('pandas')).Series
        self.rows = rows
        super().__init__(
            default=default, class_=pdSeries, allow_None=allow_None, **params
        )
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = f'{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(f"{_validate_error_prefix(self)}: {message}")
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(f"{_validate_error_prefix(self)}: {message}")

    def _validate(self, val):
        super()._validate(val)

        if self.allow_None and val is None:
            return

        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'row')

#-----------------------------------------------------------------------------
# List
#-----------------------------------------------------------------------------

class List(Parameter[T]):
    """
    Parameter whose value is a list of objects, usually of a specified type.

    The bounds allow a minimum and/or maximum length of
    list to be enforced.  If the ``item_type`` is non-None, all
    items in the list are checked to be instances of that type if
    ``is_instance`` is ``True`` (default) or subclasses of that type when False.
    """

    __slots__ = ['bounds', 'item_type', 'is_instance']

    _slot_defaults = dict(
        Parameter._slot_defaults, item_type=None, bounds=(0, None),
        instantiate=True, default=[], is_instance=True,
    )

    bounds: tuple[int, int | None] | None
    item_type: type | tuple[type, ...] | None

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: List[list[t.Any]]):
            ...

        @t.overload
        def __init__(
            self: List[list[LT]],
            default: list[LT] = [],
            *,
            item_type: type[LT] | tuple[type[LT], ...],
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: List[list[LT] | None],
            default: list[LT] | None = None,
            *,
            item_type: type[LT] | tuple[type[LT], ...],
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: List[list[t.Any] | None],
            default: list[t.Any] | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: List[list[t.Any]],
            default: list[t.Any] = [],
            *,
            item_type: None = None,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ParameterKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: list[t.Any] | None = t.cast("list[t.Any] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        item_type: type[t.Any] | tuple[type[t.Any], ...] | None = t.cast(  # pyrefly: ignore[bad-argument-type]
            "type[t.Any] | tuple[type[t.Any], ...] | None", Undefined
        ),
        bounds: tuple[int, int | None] | None = t.cast("tuple[int, int | None] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        is_instance: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        self.item_type = item_type
        self.is_instance = is_instance
        self.bounds = bounds
        Parameter.__init__(self, default=default, allow_None=allow_None, **params) # type: ignore[misc, call-overload]
        self._validate(self.default)

    def _validate(self, val):
        """
        Check that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        self._validate_value(val, self.allow_None)
        self._validate_bounds(val, self.bounds)
        self._validate_item_type(val, self.item_type, self.is_instance)

    def _validate_bounds(self, val, bounds):
        """Check that the list is of the right length and has the right contents."""
        if bounds is None or (val is None and self.allow_None):
            return
        min_length, max_length = bounds
        l = len(val)
        if min_length is not None and max_length is not None:
            if not (min_length <= l <= max_length):
                raise ValueError(
                    f"{_validate_error_prefix(self)} length must be between "
                    f"{min_length} and {max_length} (inclusive), not {l}."
                )
        elif min_length is not None:
            if not min_length <= l:
                raise ValueError(
                    f"{_validate_error_prefix(self)} length must be at "
                    f"least {min_length}, not {l}."
                )
        elif max_length is not None:
            if not l <= max_length:
                raise ValueError(
                    f"{_validate_error_prefix(self)} length must be at "
                    f"most {max_length}, not {l}."
                )

    def _validate_value(self, value, allow_None):
        if allow_None and value is None:
            return
        if not isinstance(value, list):
            raise ValueError(
                f"{_validate_error_prefix(self)} must be a list, not an "
                f"object of {type(value)}."
            )

    def _validate_item_type(self, val, item_type, is_instance):
        if item_type is None or (self.allow_None and val is None):
            return
        err_kind = None
        for v in val:
            obj_display = lambda v: v
            if is_instance and not isinstance(v, item_type):
                err_kind = "instances"
                obj_display = lambda v: type(v)
            elif not is_instance and (type(v) is not type or not issubclass(v, item_type)):
                err_kind = "subclasses"
            if err_kind:
                raise TypeError(
                    f"{_validate_error_prefix(self)} items must be {err_kind} "
                    f"of {item_type!r}, not {obj_display(v)}."
                )


class HookList(List):
    """
    Parameter whose value is a list of callable objects.

    This type of :class:`List` Parameter is typically used to provide a place
    for users to register a set of commands to be called at a
    specified place in some sequence of processing steps.
    """

    def _validate_value(self, value, allow_None):
        super()._validate_value(value, allow_None)
        if allow_None and value is None:
            return
        for v in value:
            if callable(v):
                continue
            raise ValueError(
                f"{_validate_error_prefix(self)} items must be callable, "
                f"not {v!r}."
            )

#-----------------------------------------------------------------------------
# Path
#-----------------------------------------------------------------------------

# For portable code:
#   - specify paths in unix (rather than Windows) style;
#   - use resolve_path(path_to_file=True) for paths to existing files to be read,
#   - use resolve_path(path_to_file=False) for paths to existing folders to be read.

class resolve_path(ParameterizedFunction):
    """
    Find the path to an existing file, searching the paths specified
    in the search_paths parameter if the filename is not absolute, and
    converting a UNIX-style path to the current OS's format if
    necessary.

    To turn a supplied relative path into an absolute one, the path is
    appended to paths in the search_paths parameter, in order, until
    the file is found.

    An IOError is raised if the file is not found.

    Similar to Python's os.path.abspath(), except more search paths
    than just os.getcwd() can be used, and the file must exist.
    """

    search_paths = List(default=[os.getcwd()], doc="""
        Prepended to a non-relative path, in order, until a file is
        found.""")

    path_to_file = Boolean(default=True, allow_None=True, doc="""
        String specifying whether the path refers to a 'File' or a
        'Folder'. If None, the path may point to *either* a 'File' *or*
        a 'Folder'.""")

    def __call__(self, path, **params):
        p = ParamOverrides(self, params)
        path = os.path.normpath(path)
        ftype = "File" if p.path_to_file is True \
            else "Folder" if p.path_to_file is False else "Path"

        if not p.search_paths:
            p.search_paths = [os.getcwd()]

        if os.path.isabs(path):
            if ((p.path_to_file is None  and os.path.exists(path)) or
                (p.path_to_file is True  and os.path.isfile(path)) or
                (p.path_to_file is False and os.path.isdir( path))):
                return path
            raise OSError(f"{ftype} '{path}' not found.")

        else:
            paths_tried = []
            for prefix in p.search_paths:
                try_path = os.path.join(os.path.normpath(prefix), path)

                if ((p.path_to_file is None  and os.path.exists(try_path)) or
                    (p.path_to_file is True  and os.path.isfile(try_path)) or
                    (p.path_to_file is False and os.path.isdir( try_path))):
                    return try_path

                paths_tried.append(try_path)

            raise OSError(ftype + " " + os.path.split(path)[1] + " was not found in the following place(s): " + str(paths_tried) + ".")


class PathInitKwargs(ParameterKwargs, total=False):
    search_paths: list[str | PathLike] | None
    check_exists: bool


class Path(Parameter[T]):
    """
    Parameter that can be set to a string specifying the path of a file or folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system. Please use
    the :class:`Filename` or :class:`Foldername` Parameters if you require discrimination
    between the two possibilities.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the ``search_paths`` attribute (if
      ``search_paths`` is not ``None``);
    * any of the paths searched by :func:`resolve_path` (if ``search_paths``
      is ``None``).

    Parameters
    ----------
    search_paths : list, default=[os.getcwd()]
        List of paths to search the path from
    check_exists: boolean, default=True
        If True (default) the path must exist on instantiation and set,
        otherwise the path can optionally exist.
    """

    __slots__ = ['search_paths', 'check_exists']

    _slot_defaults = dict(
        Parameter._slot_defaults, check_exists=True,
    )

    search_paths: list[str | PathLike] | None
    check_exists: bool

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Path[PathLike | str | None]) -> None:
            ...

        @t.overload
        def __init__(
            self: Path[PathLike | str],
            default: PathLike | str = pathlib.Path(""),
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[PathInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Path[PathLike | str | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[PathInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Path[PathLike | str | None],
            default: PathLike | str = pathlib.Path(""),
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[PathInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: str | PathLike | None = t.cast("str | PathLike | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        search_paths: list[str | PathLike] | None = t.cast("list[str | PathLike] | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        check_exists: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **params: Unpack[ParameterKwargs]
    ) -> None:
        if search_paths is Undefined:
            search_paths = []
        self.search_paths = t.cast("list[str | PathLike] | None", search_paths)
        if check_exists is not Undefined and not isinstance(check_exists, bool):
            raise ValueError("'check_exists' attribute value must be a boolean")
        self.check_exists = check_exists
        super().__init__(default=default, allow_None=allow_None, **params) # type: ignore[misc, call-overload]
        self._validate(self.default)

    def _resolve(self, path):
        return resolve_path(path=path, path_to_file=None, search_paths=self.search_paths)

    def _validate(self, val):
        if val is None:
            if not self.allow_None:
                raise ValueError(f'{_validate_error_prefix(self)} does not accept None')
        else:
            if not isinstance(val, (str, pathlib.Path)):
                raise ValueError(f'{_validate_error_prefix(self)} only take str or pathlib.Path types')
            try:
                self._resolve(val)
            except OSError as e:
                if self.check_exists:
                    raise OSError(e.args[0]) from None

    def __get__(
        self, obj: Parameterized | None, objtype: type[Parameterized] | None = None
    ) -> T:
        """Return an absolute, normalized path (see resolve_path)."""
        raw_path = super().__get__(obj, objtype)
        if raw_path is None:
            path = None
        else:
            try:
                path = self._resolve(raw_path)
            except OSError:
                if self.check_exists:
                    raise
                else:
                    path = raw_path
        return t.cast("T", path)

    def __getstate__(self):
        # don't want to pickle the search_paths
        state = super().__getstate__()

        if 'search_paths' in state:
            state['search_paths'] = []

        return state



class Filename(Path):
    """
    Parameter that can be set to a string specifying the path of a file.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the ``search_paths`` attribute (if
      ``search_paths`` is not ``None``);
    * any of the paths searched by :func:`resolve_path` (if ``search_paths``
      is ``None``).
    """

    def _resolve(self, path):
        return resolve_path(path=path, path_to_file=True, search_paths=self.search_paths)


class Foldername(Path):
    """
    Parameter that can be set to a string specifying the path of a folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the ``search_paths`` attribute (if
      ``search_paths`` is not ``None``);
    * any of the paths searched by resolve_dir_path() (if ``search_paths``
      is ``None``).
    """

    def _resolve(self, path):
        return resolve_path(path=path, path_to_file=False, search_paths=self.search_paths)

#-----------------------------------------------------------------------------
# Color
#-----------------------------------------------------------------------------

class ColorInitKwargs(ParameterKwargs, total=False):
    allow_named: bool


class Color(Parameter[T]):
    """
    Color parameter defined as a hex RGB string with an optional ``#``
    prefix or (optionally) as a CSS3 color name.
    """

    # CSS3 color specification https://www.w3.org/TR/css-color-3/#svg-color
    _named_colors = [ 'aliceblue', 'antiquewhite', 'aqua',
        'aquamarine', 'azure', 'beige', 'bisque', 'black',
        'blanchedalmond', 'blue', 'blueviolet', 'brown', 'burlywood',
        'cadetblue', 'chartreuse', 'chocolate', 'coral',
        'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'darkblue',
        'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey',
        'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen',
        'darkorange', 'darkorchid', 'darkred', 'darksalmon',
        'darkseagreen', 'darkslateblue', 'darkslategray',
        'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink',
        'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue',
        'firebrick', 'floralwhite', 'forestgreen', 'fuchsia',
        'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray',
        'grey', 'green', 'greenyellow', 'honeydew', 'hotpink',
        'indianred', 'indigo', 'ivory', 'khaki', 'lavender',
        'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue',
        'lightcoral', 'lightcyan', 'lightgoldenrodyellow',
        'lightgray', 'lightgrey', 'lightgreen', 'lightpink',
        'lightsalmon', 'lightseagreen', 'lightskyblue',
        'lightslategray', 'lightslategrey', 'lightsteelblue',
        'lightyellow', 'lime', 'limegreen', 'linen', 'magenta',
        'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid',
        'mediumpurple', 'mediumseagreen', 'mediumslateblue',
        'mediumspringgreen', 'mediumturquoise', 'mediumvioletred',
        'midnightblue', 'mintcream', 'mistyrose', 'moccasin',
        'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab',
        'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen',
        'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff',
        'peru', 'pink', 'plum', 'powderblue', 'purple', 'red',
        'rosybrown', 'royalblue', 'saddlebrown', 'salmon',
        'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
        'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow',
        'springgreen', 'steelblue', 'tan', 'teal', 'thistle',
        'tomato', 'turquoise', 'violet', 'wheat', 'white',
        'whitesmoke', 'yellow', 'yellowgreen']

    __slots__ = ['allow_named']

    _slot_defaults = dict(Parameter._slot_defaults, allow_named=True)

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Color[str]) -> None:
            ...

        @t.overload
        def __init__(
            self: Color[str],
            default: str = "#ffffff",
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ColorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Color[str | None],
            default: None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[ColorInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Color[str | None],
            default: None = None,
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[ColorInitKwargs]
        ) -> None:
            ...

    def __init__(self,
        default: str | None = t.cast("str | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        allow_named: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__(default=default, **kwargs)
        self.allow_named = allow_named
        self._validate(self.default)

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_allow_named(val, self.allow_named)

    def _validate_value(self, value, allow_None):
        if (allow_None and value is None):
            return
        if not isinstance(value, str):
            raise ValueError(
                f"{_validate_error_prefix(self)} expects a string value, "
                f"not an object of {type(value)}."
            )

    def _validate_allow_named(self, val, allow_named):
        if (val is None and self.allow_None):
            return
        is_hex = re.match('^#?(([0-9a-fA-F]{2}){3}|([0-9a-fA-F]){3})$', val)
        if self.allow_named:
            if not is_hex and val.lower() not in self._named_colors:
                raise ValueError(
                    f"{_validate_error_prefix(self)} only takes RGB hex codes "
                    f"or named colors, received '{val}'."
                )
        elif not is_hex:
            raise ValueError(
                f"{_validate_error_prefix(self)} only accepts valid RGB hex "
                f"codes, received {val!r}."
            )

#-----------------------------------------------------------------------------
# Bytes
#-----------------------------------------------------------------------------

class BytesInitKwargs(ParameterKwargs, total=False):
    regex: bytes | str | None


class Bytes(Parameter[T]):
    """
    A Bytes Parameter, with a default value and optional regular
    expression (regex) matching.

    Similar to the :class:`String` parameter, but instead of type string
    this parameter only allows objects of type bytes (e.g. ``b'bytes'``).
    """

    __slots__ = ['regex']

    _slot_defaults = dict(
        Parameter._slot_defaults, default=b"", regex=None, allow_None=False,
    )

    if t.TYPE_CHECKING:

        @t.overload
        def __init__(self: Bytes[bytes]) -> None:
            ...

        @t.overload
        def __init__(
            self: Bytes[bytes],
            default: bytes = b"",
            *,
            allow_None: t.Literal[False] = False,
            **kwargs: Unpack[BytesInitKwargs]
        ) -> None:
            ...

        @t.overload
        def __init__(
            self: Bytes[bytes | None],
            default: bytes | None = None,
            *,
            allow_None: t.Literal[True] = True,
            **kwargs: Unpack[BytesInitKwargs]
        ) -> None:
            ...

    def __init__(
        self,
        default: bytes | str | None = t.cast("bytes | str | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        *,
        regex: bytes | str | None = t.cast("bytes | str | None", Undefined),  # pyrefly: ignore[bad-argument-type]
        allow_None: bool = t.cast("bool", Undefined),  # pyrefly: ignore[bad-argument-type]
        **kwargs: Unpack[ParameterKwargs]
    ) -> None:
        super().__init__(default=default, allow_None=allow_None, **kwargs)
        self.regex = regex
        self._validate(self.default)

    def _validate_regex(self, val, regex):
        if (val is None and self.allow_None):
            return
        if regex is not None and re.match(regex, val) is None:
            raise ValueError(
                f"{_validate_error_prefix(self)} value {val!r} "
                f"does not match regex {regex!r}."
            )

    def _validate_value(self, value, allow_None):
        if allow_None and value is None:
            return
        if not isinstance(value, bytes):
            raise ValueError(
                f"{_validate_error_prefix(self)} only takes a byte string value, "
                f"not value of {type(value)}."
            )

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_regex(val, self.regex)
