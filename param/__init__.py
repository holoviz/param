from __future__ import print_function
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

import os.path
import sys
import copy
import glob
import re
import datetime as dt
import collections

from .parameterized import (
    Parameterized, Parameter, String, ParameterizedFunction, ParamOverrides,
    descendents, get_logger, instance_descriptor, basestring, dt_types)

from .parameterized import (batch_watch, depends, output, script_repr, # noqa: api import
                            discard_events, edit_constant, instance_descriptor)
from .parameterized import shared_parameters # noqa: api import
from .parameterized import logging_level     # noqa: api import
from .parameterized import DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL # noqa: api import

from collections import OrderedDict
from numbers import Real

# Determine up-to-date version information, if possible, but with a
# safe fallback to ensure that this file and parameterized.py are the
# only two required files.
try:
    from .version import Version
    __version__ = str(Version(fpath=__file__, archive_commit="$Format:%h$", reponame="param"))
except:
    __version__ = "0.0.0+unknown"

try:
    import collections.abc as collections_abc
except ImportError:
    collections_abc = collections

if sys.version_info[0] >= 3:
    unicode = str

#: Top-level object to allow messaging not tied to a particular
#: Parameterized object, as in 'param.main.warning("Invalid option")'.
main=Parameterized(name="main")


# A global random seed (integer or rational) available for controlling
# the behaviour of Parameterized objects with random state.
random_seed = 42


def produce_value(value_obj):
    """
    A helper function that produces an actual parameter from a stored
    object: if the object is callable, call it, otherwise return the
    object.
    """
    if callable(value_obj):
        return value_obj()
    else:
        return value_obj


def as_unicode(obj):
    """
    Safely casts any object to unicode including regular string
    (i.e. bytes) types in python 2.
    """
    if sys.version_info.major < 3 and isinstance(obj, str):
        obj = obj.decode('utf-8')
    return unicode(obj)


def is_ordered_dict(d):
    """
    Predicate checking for ordered dictionaries. OrderedDict is always
    ordered, and vanilla Python dictionaries are ordered for Python 3.6+
    """
    py3_ordered_dicts = (sys.version_info.major == 3) and (sys.version_info.minor >= 6)
    vanilla_odicts = (sys.version_info.major > 3) or py3_ordered_dicts
    return isinstance(d, (OrderedDict))or (vanilla_odicts and isinstance(d, dict))


def hashable(x):
    """
    Return a hashable version of the given object x, with lists and
    dictionaries converted to tuples.  Allows mutable objects to be
    used as a lookup key in cases where the object has not actually
    been mutated. Lookup will fail (appropriately) in cases where some
    part of the object has changed.  Does not (currently) recursively
    replace mutable subobjects.
    """
    if isinstance(x, collections_abc.MutableSequence):
        return tuple(x)
    elif isinstance(x, collections_abc.MutableMapping):
        return tuple([(k,v) for k,v in x.items()])
    else:
        return x


def named_objs(objlist, namesdict=None):
    """
    Given a list of objects, returns a dictionary mapping from
    string name for the object to the object itself. Accepts
    an optional name,obj dictionary, which will override any other
    name if that item is present in the dictionary.
    """
    objs = OrderedDict()

    objtoname = {}
    unhashables = []
    if namesdict is not None:
        for k, v in namesdict.items():
            try:
                objtoname[hashable(v)] = k
            except TypeError:
                unhashables.append((k, v))

    for obj in objlist:
        if objtoname and hashable(obj) in objtoname:
            k = objtoname[hashable(obj)]
        elif any(obj is v for (_, v) in unhashables):
            k = [k for (k, v) in unhashables if v is obj][0]
        elif hasattr(obj, "name"):
            k = obj.name
        elif hasattr(obj, '__name__'):
            k = obj.__name__
        else:
            k = as_unicode(obj)
        objs[k] = obj
    return objs


def param_union(*parameterizeds, **kwargs):
    """
    Given a set of Parameterized objects, returns a dictionary
    with the union of all param name,value pairs across them.
    If warn is True (default), warns if the same parameter has
    been given multiple values; otherwise uses the last value
    """
    warn = kwargs.pop('warn', True)
    if len(kwargs):
        raise TypeError(
            "param_union() got an unexpected keyword argument '{}'".format(
                kwargs.popitem()[0]))
    d = dict()
    for o in parameterizeds:
        for k in o.param:
            if k != 'name':
                if k in d and warn:
                    get_logger().warning("overwriting parameter {}".format(k))
                d[k] = getattr(o, k)
    return d


def guess_param_types(**kwargs):
    """
    Given a set of keyword literals, promote to the appropriate
    parameter type based on some simple heuristics.
    """
    params = {}
    for k, v in kwargs.items():
        kws = dict(default=v, constant=True)
        if isinstance(v, Parameter):
            params[k] = v
        elif isinstance(v, dt_types):
            params[k] = Date(**kws)
        elif isinstance(v, bool):
            params[k] = Boolean(**kws)
        elif isinstance(v, int):
            params[k] = Integer(**kws)
        elif isinstance(v, float):
            params[k] = Number(**kws)
        elif isinstance(v, str):
            params[k] = String(**kws)
        elif isinstance(v, dict):
            params[k] = Dict(**kws)
        elif isinstance(v, tuple):
            if all(_is_number(el) for el in v):
                params[k] = NumericTuple(**kws)
            elif all(isinstance(el, dt_types) for el in v) and len(v)==2:
                params[k] = DateRange(**kws)
            else:
                params[k] = Tuple(**kws)
        elif isinstance(v, list):
            params[k] = List(**kws)
        else:
            if 'numpy' in sys.modules:
                from numpy import ndarray
                if isinstance(v, ndarray):
                    params[k] = Array(**kws)
                    continue
            if 'pandas' in sys.modules:
                from pandas import (
                    DataFrame as pdDFrame, Series as pdSeries
                )
                if isinstance(v, pdDFrame):
                    params[k] = DataFrame(**kws)
                    continue
                elif isinstance(v, pdSeries):
                    params[k] = Series(**kws)
                    continue
            params[k] = Parameter(**kws)

    return params


def parameterized_class(name, params, bases=Parameterized):
    """
    Dynamically create a parameterized class with the given name and the
    supplied parameters, inheriting from the specified base(s).
    """
    if not (isinstance(bases, list) or isinstance(bases, tuple)):
        bases=[bases]
    return type(name, tuple(bases), params)


def guess_bounds(params, **overrides):
    """
    Given a dictionary of Parameter instances, return a corresponding
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


def _get_min_max_value(min, max, value=None, step=None):
    """Return min, max, value given input values with possible None."""
    # Either min and max need to be given, or value needs to be given
    if value is None:
        if min is None or max is None:
            raise ValueError('unable to infer range, value '
                             'from: ({0}, {1}, {2})'.format(min, max, value))
        diff = max - min
        value = min + (diff / 2)
        # Ensure that value has the same type as diff
        if not isinstance(value, type(diff)):
            value = min + (diff // 2)
    else:  # value is not None
        if not isinstance(value, Real):
            raise TypeError('expected a real number, got: %r' % value)
        # Infer min/max from value
        if value == 0:
            # This gives (0, 1) of the correct type
            vrange = (value, value + 1)
        elif value > 0:
            vrange = (-value, 3*value)
        else:
            vrange = (3*value, -value)
        if min is None:
            min = vrange[0]
        if max is None:
            max = vrange[1]
    if step is not None:
        # ensure value is on a step
        tick = int((value - min) / step)
        value = min + tick * step
    if not min <= value <= max:
        raise ValueError('value must be between min and max (min={0}, value={1}, max={2})'.format(min, value, max))
    return min, max, value


class Infinity(object):
    """
    An instance of this class represents an infinite value. Unlike
    Python's float('inf') value, this object can be safely compared
    with gmpy numeric types across different gmpy versions.

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
    def __iadd_ (self,other): return self
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

    label= String(default='Time', doc="""
         The label given to the Time object. Can be used to convey
         more specific notions of time as appropriate. For instance,
         the label could be 'Simulation Time' or 'Duration'.""")


    time_type = Parameter(default=int, constant=True, doc="""
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

         - gmpy.mpq: Allows a natural representation of times in
           decimal notation, and very fast because it uses the GNU
           Multi-Precision library, but needs to be installed
           separately and depends on a non-Python library.  gmpy.mpq
           is gmpy's rational type.
        """)

    timestep = Parameter(default=1.0,doc="""
        Stepsize to be used with the iterator interface.
        Time can be advanced or decremented by any value, not just
        those corresponding to the stepsize, and so this value is only
        a default.""")

    until = Parameter(default=forever,doc="""
         Declaration of an expected end to time values, if any.  When
         using the iterator interface, iteration will end before this
         value is exceeded.""")

    unit = String(default=None, doc="""
        The units of the time dimensions. The default of None is set
        as the global time function may on an arbitrary time base.

        Typical values for the parameter are 'seconds' (the SI unit
        for time) or subdivisions thereof (e.g. 'milliseconds').""")


    def __init__(self, **params):
        super(Time, self).__init__(**params)
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

    # PARAM2_DEPRECATION: For Python 2 compatibility; can be removed for Python 3.
    next = __next__

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



class Dynamic(Parameter):
    """
    Parameter whose value can be generated dynamically by a callable
    object.

    If a Parameter is declared as Dynamic, it can be set a callable
    object (such as a function or callable class), and getting the
    parameter's value will call that callable.

    Note that at present, the callable object must allow attributes
    to be set on itself.

    [Python 2.4 limitation: the callable object must be an instance of a
    callable class, rather than a named function or a lambda function,
    otherwise the object will not be picklable or deepcopyable.]

    If set as time_dependent, setting the Dynamic.time_fn allows the
    production of dynamic values to be controlled: a new value will be
    produced only if the current value of time_fn is different from
    what it was the last time the parameter value was requested.

    By default, the Dynamic parameters are not time_dependent so that
    new values are generated on every call regardless of the time. The
    default time_fn used when time_dependent is a single Time instance
    that allows general manipulations of time. It may be set to some
    other callable as required so long as a number is returned on each
    call.
    """

    time_fn = Time()
    time_dependent = False

    def __init__(self,**params):
        """
        Call the superclass's __init__ and set instantiate=True if the
        default is dynamic.
        """
        super(Dynamic,self).__init__(**params)

        if callable(self.default):
            self._set_instantiate(True)
            self._initialize_generator(self.default)


    def _initialize_generator(self,gen,obj=None):
        """
        Add 'last time' and 'last value' attributes to the generator.
        """
        # Could use a dictionary to hold these things.
        if hasattr(obj,"_Dynamic_time_fn"):
            gen._Dynamic_time_fn = obj._Dynamic_time_fn

        gen._Dynamic_last = None
        # Would have usede None for this, but can't compare a fixedpoint
        # number with None (e.g. 1>None but FixedPoint(1)>None can't be done)
        gen._Dynamic_time = -1

        gen._saved_Dynamic_last = []
        gen._saved_Dynamic_time = []


    def __get__(self,obj,objtype):
        """
        Call the superclass's __get__; if the result is not dynamic
        return that result, otherwise ask that result to produce a
        value and return it.
        """
        gen = super(Dynamic,self).__get__(obj,objtype)

        if not hasattr(gen,'_Dynamic_last'):
            return gen
        else:
            return self._produce_value(gen)


    @instance_descriptor
    def __set__(self,obj,val):
        """
        Call the superclass's set and keep this parameter's
        instantiate value up to date (dynamic parameters
        must be instantiated).

        If val is dynamic, initialize it as a generator.
        """
        super(Dynamic,self).__set__(obj,val)

        dynamic = callable(val)
        if dynamic: self._initialize_generator(val,obj)
        if obj is None: self._set_instantiate(dynamic)


    def _produce_value(self,gen,force=False):
        """
        Return a value from gen.

        If there is no time_fn, then a new value will be returned
        (i.e. gen will be asked to produce a new value).

        If force is True, or the value of time_fn() is different from
        what it was was last time produce_value was called, a new
        value will be produced and returned. Otherwise, the last value
        gen produced will be returned.
        """

        if hasattr(gen,"_Dynamic_time_fn"):
            time_fn = gen._Dynamic_time_fn
        else:
            time_fn = self.time_fn

        if (time_fn is None) or (not self.time_dependent):
            value = produce_value(gen)
            gen._Dynamic_last = value
        else:

            time = time_fn()

            if force or time!=gen._Dynamic_time:
                value = produce_value(gen)
                gen._Dynamic_last = value
                gen._Dynamic_time = time
            else:
                value = gen._Dynamic_last

        return value


    def _value_is_dynamic(self,obj,objtype=None):
        """
        Return True if the parameter is actually dynamic (i.e. the
        value is being generated).
        """
        return hasattr(super(Dynamic,self).__get__(obj,objtype),'_Dynamic_last')


    def _inspect(self,obj,objtype=None):
        """Return the last generated value for this parameter."""
        gen=super(Dynamic,self).__get__(obj,objtype)

        if hasattr(gen,'_Dynamic_last'):
            return gen._Dynamic_last
        else:
            return gen


    def _force(self,obj,objtype=None):
        """Force a new value to be generated, and return it."""
        gen=super(Dynamic,self).__get__(obj,objtype)

        if hasattr(gen,'_Dynamic_last'):
            return self._produce_value(gen,force=True)
        else:
            return gen


import numbers
def _is_number(obj):
    if isinstance(obj, numbers.Number): return True
    # The extra check is for classes that behave like numbers, such as those
    # found in numpy, gmpy, etc.
    elif (hasattr(obj, '__int__') and hasattr(obj, '__add__')): return True
    # This is for older versions of gmpy
    elif hasattr(obj, 'qdiv'): return True
    else: return False


def identity_hook(obj,val): return val

def get_soft_bounds(bounds, softbounds):
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


class Bytes(Parameter):
    """
    A Bytes Parameter, with a default value and optional regular
    expression (regex) matching.

    Similar to the String parameter, but instead of type basestring
    this parameter only allows objects of type bytes (e.g. b'bytes').
    """

    __slots__ = ['regex']

    def __init__(self, default=b"", regex=None, allow_None=False, **kwargs):
        super(Bytes, self).__init__(default=default, allow_None=allow_None, **kwargs)
        self.regex = regex
        self.allow_None = (default is None or allow_None)
        self._validate(default)

    def _validate_regex(self, val, regex):
        if (val is None and self.allow_None):
            return
        if regex is not None and re.match(regex, val) is None:
            raise ValueError("Bytes parameter %r value %r does not match regex %r."
                             % (self.name, val, regex))

    def _validate_value(self, val, allow_None):
        if allow_None and val is None:
            return
        if not isinstance(val, bytes):
            raise ValueError("Bytes parameter %r only takes a byte string value, "
                             "not value of type %s." % (self.name, type(val)))

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_regex(val, self.regex)


class Number(Dynamic):
    """
    A numeric Dynamic Parameter, with a default value and optional bounds.

    There are two types of bounds: ``bounds`` and
    ``softbounds``.  ``bounds`` are hard bounds: the parameter must
    have a value within the specified range.  The default bounds are
    (None,None), meaning there are actually no hard bounds.  One or
    both bounds can be set by specifying a value
    (e.g. bounds=(None,10) means there is no lower bound, and an upper
    bound of 10). Bounds are inclusive by default, but exclusivity
    can be specified for each bound by setting inclusive_bounds
    (e.g. inclusive_bounds=(True,False) specifies an exclusive upper
    bound).

    Number is also a type of Dynamic parameter, so its value
    can be set to a callable to get a dynamically generated
    number (see Dynamic).

    When not being dynamically generated, bounds are checked when a
    Number is created or set. Using a default value outside the hard
    bounds, or one that is not numeric, results in an exception. When
    being dynamically generated, bounds are checked when the value
    of a Number is requested. A generated value that is not numeric,
    or is outside the hard bounds, results in an exception.

    As a special case, if allow_None=True (which is true by default if
    the parameter has a default of None when declared) then a value
    of None is also allowed.

    A separate function set_in_bounds() is provided that will
    silently crop the given value into the legal range, for use
    in, for instance, a GUI.

    ``softbounds`` are present to indicate the typical range of
    the parameter, but are not enforced. Setting the soft bounds
    allows, for instance, a GUI to know what values to display on
    sliders for the Number.

    Example of creating a Number::

      AB = Number(default=0.5, bounds=(None,10), softbounds=(0,1), doc='Distance from A to B.')

    """

    __slots__ = ['bounds', 'softbounds', 'inclusive_bounds', 'set_hook', 'step']

    def __init__(self, default=0.0, bounds=None, softbounds=None,
                 inclusive_bounds=(True,True), step=None, **params):
        """
        Initialize this parameter object and store the bounds.

        Non-dynamic default values are checked against the bounds.
        """
        super(Number,self).__init__(default=default, **params)

        self.set_hook = identity_hook
        self.bounds = bounds
        self.inclusive_bounds = inclusive_bounds
        self.softbounds = softbounds
        self.step = step
        self._validate(default)

    def __get__(self, obj, objtype):
        """
        Same as the superclass's __get__, but if the value was
        dynamically generated, check the bounds.
        """
        result = super(Number, self).__get__(obj, objtype)
        # Should be able to optimize this commonly used method by
        # avoiding extra lookups (e.g. _value_is_dynamic() is also
        # looking up 'result' - should just pass it in).
        if self._value_is_dynamic(obj, objtype):
            self._validate(result)
        return result

    def set_in_bounds(self,obj,val):
        """
        Set to the given value, but cropped to be within the legal bounds.
        All objects are accepted, and no exceptions will be raised.  See
        crop_to_bounds for details on how cropping is done.
        """
        if not callable(val):
            bounded_val = self.crop_to_bounds(val)
        else:
            bounded_val = val
        super(Number, self).__set__(obj, bounded_val)

    def crop_to_bounds(self, val):
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

    def _validate_bounds(self, val, bounds, inclusive_bounds):
        if bounds is None or (val is None and self.allow_None) or callable(val):
            return
        vmin, vmax = bounds
        incmin, incmax = inclusive_bounds
        if vmax is not None:
            if incmax is True:
                if not val <= vmax:
                    raise ValueError("Parameter %r must be at most %s, "
                                     "not %s." % (self.name, vmax, val))
            else:
                if not val < vmax:
                    raise ValueError("Parameter %r must be less than %s, "
                                     "not %s." % (self.name, vmax, val))

        if vmin is not None:
            if incmin is True:
                if not val >= vmin:
                    raise ValueError("Parameter %r must be at least %s, "
                                     "not %s." % (self.name, vmin, val))
            else:
                if not val > vmin:
                    raise ValueError("Parameter %r must be greater than %s, "
                                     "not %s." % (self.name, vmin, val))

    def _validate_value(self, val, allow_None):
        if (allow_None and val is None) or callable(val):
            return

        if not _is_number(val):
            raise ValueError("Parameter %r only takes numeric values, "
                             "not type %r." % (self.name, type(val)))

    def _validate_step(self, val, step):
        if step is not None and not _is_number(step):
            raise ValueError("Step can only be None or a "
                             "numeric value, not type %r." % type(step))

    def _validate(self, val):
        """
        Checks that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        self._validate_value(val, self.allow_None)
        self._validate_step(val, self.step)
        self._validate_bounds(val, self.bounds, self.inclusive_bounds)

    def get_soft_bounds(self):
        return get_soft_bounds(self.bounds, self.softbounds)

    def __setstate__(self,state):
        if 'step' not in state:
            state['step'] = None

        super(Number, self).__setstate__(state)



class Integer(Number):
    """Numeric Parameter required to be an Integer"""

    def __init__(self, default=0, **params):
        Number.__init__(self, default=default, **params)

    def _validate_value(self, val, allow_None):
        if callable(val):
            return

        if allow_None and val is None:
            return

        if not isinstance(val, int):
            raise ValueError("Integer parameter %r must be an integer, "
                             "not type %r." % (self.name, type(val)))

    def _validate_step(self, val, step):
        if step is not None and not isinstance(step, int):
            raise ValueError("Step can only be None or an "
                             "integer value, not type %r" % type(step))



class Magnitude(Number):
    """Numeric Parameter required to be in the range [0.0-1.0]."""

    def __init__(self, default=1.0, softbounds=None, **params):
        Number.__init__(self, default=default, bounds=(0.0,1.0), softbounds=softbounds, **params)



class Boolean(Parameter):
    """Binary or tristate Boolean Parameter."""

    __slots__ = ['bounds']

    # Bounds are set for consistency and are arguably accurate, but have
    # no effect since values are either False, True, or None (if allowed).
    def __init__(self, default=False, bounds=(0,1), **params):
        self.bounds = bounds
        super(Boolean, self).__init__(default=default, **params)

    def _validate_value(self, val, allow_None):
        if allow_None:
            if not isinstance(val, bool) and val is not None:
                raise ValueError("Boolean parameter %r only takes a "
                                 "Boolean value or None, not %s."
                                 % (self.name, val))
        elif not isinstance(val, bool):
            raise ValueError("Boolean parameter %r must be True or False, "
                             "not %s." % (self.name, val))



class Tuple(Parameter):
    """A tuple Parameter (e.g. ('a',7.6,[3,5])) with a fixed tuple length."""

    __slots__ = ['length']

    def __init__(self, default=(0,0), length=None, **params):
        """
        Initialize a tuple parameter with a fixed length (number of
        elements).  The length is determined by the initial default
        value, if any, and must be supplied explicitly otherwise.  The
        length is not allowed to change after instantiation.
        """
        super(Tuple,self).__init__(default=default, **params)
        if length is None and default is not None:
            self.length = len(default)
        elif length is None and default is None:
            raise ValueError("%s: length must be specified if no default is supplied." %
                             (self.name))
        else:
            self.length = length
        self._validate(default)

    def _validate_value(self, val, allow_None):
        if val is None and allow_None:
            return

        if not isinstance(val, tuple):
            raise ValueError("Tuple parameter %r only takes a tuple value, "
                             "not %r." % (self.name, type(val)))

    def _validate_length(self, val, length):
        if val is None and self.allow_None:
            return

        if not len(val) == length:
            raise ValueError("Tuple parameter %r is not of the correct "
                             "length (%d instead of %d)." %
                             (self.name, len(val), length))

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


class NumericTuple(Tuple):
    """A numeric tuple Parameter (e.g. (4.5,7.6,3)) with a fixed tuple length."""

    def _validate_value(self, val, allow_None):
        super(NumericTuple, self)._validate_value(val, allow_None)
        if allow_None and val is None:
            return
        for n in val:
            if _is_number(n):
                continue
            raise ValueError("NumericTuple parameter %r only takes numeric "
                             "values, not type %r." % (self.name, type(n)))


class XYCoordinates(NumericTuple):
    """A NumericTuple for an X,Y coordinate."""

    def __init__(self, default=(0.0, 0.0), **params):
        super(XYCoordinates,self).__init__(default=default, length=2, **params)


class Callable(Parameter):
    """
    Parameter holding a value that is a callable object, such as a function.

    A keyword argument instantiate=True should be provided when a
    function object is used that might have state.  On the other hand,
    regular standalone functions cannot be deepcopied as of Python
    2.4, so instantiate must be False for those values.
    """

    def _validate_value(self, val, allow_None):
        if (allow_None and val is None) or callable(val):
            return

        raise ValueError("Callable parameter %r only takes a callable object, "
                         "not objects of type %r." % (self.name, type(val)))


class Action(Callable):
    """
    A user-provided function that can be invoked like a class or object method using ().
    In a GUI, this might be mapped to a button, but it can be invoked directly as well.
    """
# Currently same implementation as Callable, but kept separate to allow different handling in GUIs


def _is_abstract(class_):
    try:
        return class_.abstract
    except AttributeError:
        return False


# Could be a method of ClassSelector.
def concrete_descendents(parentclass):
    """
    Return a dictionary containing all subclasses of the specified
    parentclass, including the parentclass.  Only classes that are
    defined in scripts that have been run or modules that have been
    imported are included, so the caller will usually first do ``from
    package import *``.

    Only non-abstract classes will be included.
    """
    return dict((c.__name__,c) for c in descendents(parentclass)
                if not _is_abstract(c))


class Composite(Parameter):
    """
    A Parameter that is a composite of a set of other attributes of the class.

    The constructor argument 'attribs' takes a list of attribute
    names, which may or may not be Parameters.  Getting the parameter
    returns a list of the values of the constituents of the composite,
    in the order specified.  Likewise, setting the parameter takes a
    sequence of values and sets the value of the constituent
    attributes.

    This Parameter type has not been tested with watchers and
    dependencies, and may not support them properly.
    """

    __slots__ = ['attribs', 'objtype']

    def __init__(self, attribs=None, **kw):
        if attribs is None:
            attribs = []
        super(Composite, self).__init__(default=None, **kw)
        self.attribs = attribs

    def __get__(self, obj, objtype):
        """
        Return the values of all the attribs, as a list.
        """
        if obj is None:
            return [getattr(objtype, a) for a in self.attribs]
        else:
            return [getattr(obj, a) for a in self.attribs]

    def _validate_attribs(self, val, attribs):
        if len(val) == len(attribs):
            return
        raise ValueError("Compound parameter %r got the wrong number "
                         "of values (needed %d, but got %d)." %
                         (self.name, len(attribs), len(val)))

    def _validate(self, val):
        self._validate_attribs(val, self.attribs)

    def _post_setter(self, obj, val):
        if obj is None:
            for a, v in zip(self.attribs, val):
                setattr(self.objtype, a, v)
        else:
            for a, v in zip(self.attribs, val):
                setattr(obj, a, v)


class SelectorBase(Parameter):
    """
    Parameter whose value must be chosen from a list of possibilities.

    Subclasses must implement get_range().
    """

    __abstract = True

    def get_range(self):
        raise NotImplementedError("get_range() must be implemented in subclasses.")


class Selector(SelectorBase):
    """
    Parameter whose value must be one object from a list of possible objects.

    By default, if no default is specified, picks the first object from
    the provided set of objects, as long as the objects are in an
    ordered data collection.

    check_on_set restricts the value to be among the current list of
    objects. By default, if objects are initially supplied,
    check_on_set is True, whereas if no objects are initially
    supplied, check_on_set is False. This can be overridden by
    explicitly specifying check_on_set initially.

    If check_on_set is True (either because objects are supplied
    initially, or because it is explicitly specified), the default
    (initial) value must be among the list of objects (unless the
    default value is None).

    The list of objects can be supplied as a list (appropriate for
    selecting among a set of strings, or among a set of objects with a
    "name" parameter), or as a (preferably ordered) dictionary from
    names to objects.  If a dictionary is supplied, the objects
    will need to be hashable so that their names can be looked
    up from the object value.
    """

    __slots__ = ['objects', 'compute_default_fn', 'check_on_set', 'names']

    # Selector is usually used to allow selection from a list of
    # existing objects, therefore instantiate is False by default.
    def __init__(self, objects=None, default=None, instantiate=False,
                 compute_default_fn=None, check_on_set=None,
                 allow_None=None, empty_default=False, **params):

        autodefault = None
        if objects:
            if is_ordered_dict(objects):
                autodefault = list(objects.values())[0]
            elif isinstance(objects, dict):
                main.param.warning("Parameter default value is arbitrary due to "
                                   "dictionaries prior to Python 3.6 not being "
                                   "ordered; should use an ordered dict or "
                                   "supply an explicit default value.")
                autodefault = list(objects.values())[0]
            elif isinstance(objects, list):
                autodefault = objects[0]

        default = autodefault if (not empty_default and default is None) else default

        if objects is None:
            objects = []
        if isinstance(objects, collections_abc.Mapping):
            self.names = objects
            self.objects = list(objects.values())
        else:
            self.names = None
            self.objects = objects
        self.compute_default_fn = compute_default_fn

        if check_on_set is not None:
            self.check_on_set = check_on_set
        elif len(objects) == 0:
            self.check_on_set = False
        else:
            self.check_on_set = True

        super(Selector,self).__init__(
            default=default, instantiate=instantiate, **params)
        # Required as Parameter sets allow_None=True if default is None
        self.allow_None = allow_None
        if default is not None and self.check_on_set is True:
            self._validate(default)

    # Note that if the list of objects is changed, the current value for
    # this parameter in existing POs could be outside of the new range.

    def compute_default(self):
        """
        If this parameter's compute_default_fn is callable, call it
        and store the result in self.default.

        Also removes None from the list of objects (if the default is
        no longer None).
        """
        if self.default is None and callable(self.compute_default_fn):
            self.default = self.compute_default_fn()
            if self.default not in self.objects:
                self.objects.append(self.default)

    def _validate(self, val):
        """
        val must be None or one of the objects in self.objects.
        """
        if not self.check_on_set:
            self._ensure_value_is_in_objects(val)
            return

        if not (val in self.objects or (self.allow_None and val is None)):
            # This method can be called before __init__ has called
            # super's __init__, so there may not be any name set yet.
            if (hasattr(self, "name") and self.name):
                attrib_name = " " + self.name
            else:
                attrib_name = ""

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
            raise ValueError("%s not in parameter%s's list of possible objects, "
                             "valid options include %s" % (val, attrib_name, items))

    def _ensure_value_is_in_objects(self,val):
        """
        Make sure that the provided value is present on the objects list.
        Subclasses can override if they support multiple items on a list,
        to check each item instead.
        """
        if not (val in self.objects):
            self.objects.append(val)

    def get_range(self):
        """
        Return the possible objects to which this parameter could be set.

        (Returns the dictionary {object.name:object}.)
        """
        return named_objs(self.objects, self.names)


class ObjectSelector(Selector):
    """
    Deprecated. Same as Selector, but with a different constructor for
    historical reasons.
    """
    def __init__(self, default=None, objects=None, **kwargs):
        super(ObjectSelector,self).__init__(objects=objects, default=default,
                                            empty_default=True, **kwargs)


class ClassSelector(SelectorBase):
    """
    Parameter allowing selection of either a subclass or an instance of a given set of classes.
    By default, requires an instance, but if is_instance=False, accepts a class instead.
    Both class and instance values respect the instantiate slot, though it matters only
    for is_instance=True.
    """

    __slots__ = ['class_', 'is_instance']

    def __init__(self,class_,default=None,instantiate=True,is_instance=True,**params):
        self.class_ = class_
        self.is_instance = is_instance
        super(ClassSelector,self).__init__(default=default,instantiate=instantiate,**params)
        self._validate(default)

    def _validate(self, val):
        super(ClassSelector, self)._validate(val)
        self._validate_class_(val, self.class_, self.is_instance)

    def _validate_class_(self, val, class_, is_instance):
        if (val is None and self.allow_None):
            return
        if isinstance(class_, tuple):
            class_name = ('(%s)' % ', '.join(cl.__name__ for cl in class_))
        else:
            class_name = class_.__name__
        param_cls = self.__class__.__name__
        if is_instance:
            if not (isinstance(val, class_)):
                raise ValueError(
                    "%s parameter %r value must be an instance of %s, not %r." %
                    (param_cls, self.name, class_name, val))
        else:
            if not (issubclass(val, class_)):
                raise ValueError(
                    "%s parameter %r must be a subclass of %s, not %r." %
                    (param_cls, self.name, class_name, val.__name__))

    def get_range(self):
        """
        Return the possible types for this parameter's value.

        (I.e. return `{name: <class>}` for all classes that are
        concrete_descendents() of `self.class_`.)

        Only classes from modules that have been imported are added
        (see concrete_descendents()).
        """
        classes = self.class_ if isinstance(self.class_, tuple) else (self.class_,)
        all_classes = {}
        for cls in classes:
            all_classes.update(concrete_descendents(cls))
        d = OrderedDict((name, class_) for name,class_ in all_classes.items())
        if self.allow_None:
            d['None'] = None
        return d


class List(Parameter):
    """
    Parameter whose value is a list of objects, usually of a specified type.

    The bounds allow a minimum and/or maximum length of
    list to be enforced.  If the item_type is non-None, all
    items in the list are checked to be of that type.

    `class_` is accepted as an alias for `item_type`, but is
    deprecated due to conflict with how the `class_` slot is
    used in Selector classes.
    """

    __slots__ = ['bounds', 'item_type', 'class_']

    def __init__(self, default=[], class_=None, item_type=None,
                 instantiate=True, bounds=(0, None), **params):
        self.item_type = item_type or class_
        self.class_ = self.item_type
        self.bounds = bounds
        Parameter.__init__(self, default=default, instantiate=instantiate,
                           **params)
        self._validate(default)

    def _validate(self, val):
        """
        Checks that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        self._validate_value(val, self.allow_None)
        self._validate_bounds(val, self.bounds)
        self._validate_item_type(val, self.item_type)

    def _validate_bounds(self, val, bounds):
        "Checks that the list is of the right length and has the right contents."
        if bounds is None or (val is None and self.allow_None):
            return
        min_length, max_length = bounds
        l = len(val)
        if min_length is not None and max_length is not None:
            if not (min_length <= l <= max_length):
                raise ValueError("%s: list length must be between %s and %s (inclusive)"%(self.name,min_length,max_length))
        elif min_length is not None:
            if not min_length <= l:
                raise ValueError("%s: list length must be at least %s."
                                 % (self.name, min_length))
        elif max_length is not None:
            if not l <= max_length:
                raise ValueError("%s: list length must be at most %s."
                                 % (self.name, max_length))

    def _validate_value(self, val, allow_None):
        if allow_None and val is None:
            return
        if not isinstance(val, list):
            raise ValueError("List parameter %r must be a list, not an object of type %s."
                             % (self.name, type(val)))

    def _validate_item_type(self, val, item_type):
        if item_type is None or (self.allow_None and val is None):
            return
        for v in val:
            if isinstance(v, item_type):
                continue
            raise TypeError("List parameter %r items must be instances "
                            "of type %r, not %r." % (self.name, item_type, val))


class HookList(List):
    """
    Parameter whose value is a list of callable objects.

    This type of List Parameter is typically used to provide a place
    for users to register a set of commands to be called at a
    specified place in some sequence of processing steps.
    """
    __slots__ = ['class_', 'bounds']

    def _validate_value(self, val, allow_None):
        super(HookList, self)._validate_value(val, allow_None)
        if allow_None and val is None:
            return
        for v in val:
            if callable(v):
                continue
            raise ValueError("HookList parameter %r items must be callable, "
                             "not %r." % (self.name, v))


class Dict(ClassSelector):
    """
    Parameter whose value is a dictionary.
    """

    def __init__(self, default=None, **params):
        super(Dict, self).__init__(dict, default=default, **params)


class Array(ClassSelector):
    """
    Parameter whose value is a numpy array.
    """

    def __init__(self, default=None, **params):
        from numpy import ndarray
        super(Array, self).__init__(ndarray, allow_None=True, default=default, **params)

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return value.tolist()

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        from numpy import asarray
        return asarray(value)


class DataFrame(ClassSelector):
    """
    Parameter whose value is a pandas DataFrame.

    The structure of the DataFrame can be constrained by the rows and
    columns arguments:

    rows: If specified, may be a number or an integer bounds tuple to
    constrain the allowable number of rows.

    columns: If specified, may be a number, an integer bounds tuple, a
    list or a set. If the argument is numeric, constrains the number of
    columns using the same semantics as used for rows. If either a list
    or set of strings, the column names will be validated. If a set is
    used, the supplied DataFrame must contain the specified columns and
    if a list is given, the supplied DataFrame must contain exactly the
    same columns and in the same order and no other columns.
    """

    __slots__ = ['rows', 'columns', 'ordered']

    def __init__(self, default=None, rows=None, columns=None, ordered=None, **params):
        from pandas import DataFrame as pdDFrame
        self.rows = rows
        self.columns = columns
        self.ordered = ordered
        super(DataFrame,self).__init__(pdDFrame, default=default, **params)
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = '{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(message.format(name=name, length=length, bounds=bounds))
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(message.format(name=name,length=length, bounds=bounds))

    def _validate(self, val):
        super(DataFrame, self)._validate(val)

        if isinstance(self.columns, set) and self.ordered is True:
            raise ValueError('Columns cannot be ordered when specified as a set')

        if self.allow_None and val is None:
            return

        if self.columns is None:
            pass
        elif (isinstance(self.columns, tuple) and len(self.columns)==2
              and all(isinstance(v, (type(None), numbers.Number)) for v in self.columns)): # Numeric bounds tuple
            self._length_bounds_check(self.columns, len(val.columns), 'Columns')
        elif isinstance(self.columns, (list, set)):
            self.ordered = isinstance(self.columns, list) if self.ordered is None else self.ordered
            difference = set(self.columns) - set([str(el) for el in val.columns])
            if difference:
                msg = 'Provided DataFrame columns {found} does not contain required columns {expected}'
                raise ValueError(msg.format(found=list(val.columns), expected=sorted(self.columns)))
        else:
            self._length_bounds_check(self.columns, len(val.columns), 'Column')

        if self.ordered:
            if list(val.columns) != list(self.columns):
                msg = 'Provided DataFrame columns {found} must exactly match {expected}'
                raise ValueError(msg.format(found=list(val.columns), expected=self.columns))

        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'Row')

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return value.to_dict('records')

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        from pandas import DataFrame as pdDFrame
        return pdDFrame(value)


class Series(ClassSelector):
    """
    Parameter whose value is a pandas Series.

    The structure of the Series can be constrained by the rows argument
    which may be a number or an integer bounds tuple to constrain the
    allowable number of rows.
    """

    __slots__ = ['rows']

    def __init__(self, default=None, rows=None, allow_None=False, **params):
        from pandas import Series as pdSeries
        self.rows = rows
        super(Series,self).__init__(pdSeries, default=default, allow_None=allow_None,
                                    **params)
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = '{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(message.format(name=name, length=length, bounds=bounds))
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(message.format(name=name,length=length, bounds=bounds))

    def _validate(self, val):
        super(Series, self)._validate(val)

        if self.allow_None and val is None:
            return

        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'Row')



# For portable code:
#   - specify paths in unix (rather than Windows) style;
#   - use resolve_path(path_to_file=True) for paths to existing files to be read,
#   - use resolve_path(path_to_file=False) for paths to existing folders to be read,
#     and normalize_path() for paths to new files to be written.

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

    search_paths = List(default=[os.getcwd()], pickle_default_value=False, doc="""
        Prepended to a non-relative path, in order, until a file is
        found.""")

    path_to_file = Boolean(default=True, pickle_default_value=False,
                           allow_None=True, doc="""
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
            raise IOError("%s '%s' not found." % (ftype,path))

        else:
            paths_tried = []
            for prefix in p.search_paths:
                try_path = os.path.join(os.path.normpath(prefix), path)

                if ((p.path_to_file is None  and os.path.exists(try_path)) or
                    (p.path_to_file is True  and os.path.isfile(try_path)) or
                    (p.path_to_file is False and os.path.isdir( try_path))):
                    return try_path

                paths_tried.append(try_path)

            raise IOError(ftype + " " + os.path.split(path)[1] + " was not found in the following place(s): " + str(paths_tried) + ".")


class normalize_path(ParameterizedFunction):
    """
    Convert a UNIX-style path to the current OS's format,
    typically for creating a new file or directory.

    If the path is not already absolute, it will be made absolute
    (using the prefix parameter).

    Should do the same as Python's os.path.abspath(), except using
    prefix rather than os.getcwd).
    """

    prefix = String(default=os.getcwd(),pickle_default_value=False,doc="""
        Prepended to the specified path, if that path is not
        absolute.""")

    def __call__(self,path="",**params):
        p = ParamOverrides(self,params)

        if not os.path.isabs(path):
            path = os.path.join(os.path.normpath(p.prefix),path)

        return os.path.normpath(path)



class Path(Parameter):
    """
    Parameter that can be set to a string specifying the path of a file or folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system. Please use
    the Filename or Foldername classes if you require discrimination
    between the two possibilities.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
       search_paths is not None);

    or

    * any of the paths searched by resolve_path() (if search_paths
      is None).
    """

    __slots__ = ['search_paths']

    def __init__(self, default=None, search_paths=None, **params):
        if search_paths is None:
            search_paths = []

        self.search_paths = search_paths
        super(Path,self).__init__(default,**params)

    def _resolve(self, path):
        return resolve_path(path, path_to_file=None, search_paths=self.search_paths)

    def _validate(self, val):
        if val is None:
            if not self.allow_None:
                Parameterized(name="%s.%s"%(self.owner.name,self.name)).param.warning('None is not allowed')
        else:
            try:
                self._resolve(val)
            except IOError as e:
                Parameterized(name="%s.%s"%(self.owner.name,self.name)).param.warning('%s',e.args[0])

    def __get__(self, obj, objtype):
        """
        Return an absolute, normalized path (see resolve_path).
        """
        raw_path = super(Path,self).__get__(obj,objtype)
        return None if raw_path is None else self._resolve(raw_path)

    def __getstate__(self):
        # don't want to pickle the search_paths
        state = super(Path,self).__getstate__()

        if 'search_paths' in state:
            state['search_paths'] = []

        return state



class Filename(Path):
    """
    Parameter that can be set to a string specifying the path of a file.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
      search_paths is not None);

    or

    * any of the paths searched by resolve_path() (if search_paths
      is None).
    """

    def _resolve(self, path):
        return resolve_path(path, path_to_file=True, search_paths=self.search_paths)


class Foldername(Path):
    """
    Parameter that can be set to a string specifying the path of a folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
      search_paths is not None);

    or

    * any of the paths searched by resolve_dir_path() (if search_paths
      is None).
    """

    def _resolve(self, path):
        return resolve_path(path, path_to_file=False, search_paths=self.search_paths)



def abbreviate_paths(pathspec,named_paths):
    """
    Given a dict of (pathname,path) pairs, removes any prefix shared by all pathnames.
    Helps keep menu items short yet unambiguous.
    """
    from os.path import commonprefix, dirname, sep

    prefix = commonprefix([dirname(name)+sep for name in named_paths.keys()]+[pathspec])
    return OrderedDict([(name[len(prefix):],path) for name,path in named_paths.items()])



class FileSelector(Selector):
    """
    Given a path glob, allows one file to be selected from those matching.
    """
    __slots__ = ['path']

    def __init__(self, default=None, path="", **kwargs):
        self.default = default
        self.path = path
        self.update()
        super(FileSelector, self).__init__(default=default, objects=self.objects,
                                           empty_default=True, **kwargs)

    def _on_set(self, attribute, old, new):
        super(FileSelector, self)._on_set(attribute, new, old)
        if attribute == 'path':
            self.update()

    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default in self.objects:
            return
        self.default = self.objects[0] if self.objects else None

    def get_range(self):
        return abbreviate_paths(self.path,super(FileSelector, self).get_range())


class ListSelector(Selector):
    """
    Variant of Selector where the value can be multiple objects from
    a list of possible objects.
    """

    def __init__(self, default=None, objects=None, **kwargs):
        super(ListSelector,self).__init__(
            objects=objects, default=default, empty_default=True, **kwargs)

    def compute_default(self):
        if self.default is None and callable(self.compute_default_fn):
            self.default = self.compute_default_fn()
            for o in self.default:
                if o not in self.objects:
                    self.objects.append(o)

    def _validate(self, val):
        if (val is None and self.allow_None):
            return
        if not isinstance(val, list):
            raise ValueError("ListSelector parameter %r only takes list "
                             "types, not %r." % (self.name, val))
        for o in val:
            super(ListSelector, self)._validate(o)



class MultiFileSelector(ListSelector):
    """
    Given a path glob, allows multiple files to be selected from the list of matches.
    """
    __slots__ = ['path']

    def __init__(self, default=None, path="", **kwargs):
        self.default = default
        self.path = path
        self.update()
        super(MultiFileSelector, self).__init__(default=default, objects=self.objects, **kwargs)

    def _on_set(self, attribute, old, new):
        super(MultiFileSelector, self)._on_set(attribute, new, old)
        if attribute == 'path':
            self.update()

    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default and all([o in self.objects for o in self.default]):
            return
        self.default = self.objects

    def get_range(self):
        return abbreviate_paths(self.path,super(MultiFileSelector, self).get_range())


class Date(Number):
    """
    Date parameter of datetime or date type.
    """

    def __init__(self, default=None, **kwargs):
        super(Date, self).__init__(default=default, **kwargs)

    def _validate_value(self, val, allow_None):
        """
        Checks that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        if self.allow_None and val is None:
            return

        if not isinstance(val, dt_types) and not (allow_None and val is None):
            raise ValueError(
                "Date parameter %r only takes datetime and date types, "
                "not type %r." % (self.name, type(val))
            )

    def _validate_step(self, val, step):
        if step is not None and not isinstance(step, dt_types):
            raise ValueError(
                "Step can only be None, a datetime "
                "or datetime type, not type %r." % type(val)
            )

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        if not isinstance(value, (dt.datetime, dt.date)): # i.e np.datetime64
            value = value.astype(dt.datetime)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")


class CalendarDate(Number):
    """
    Parameter specifically allowing dates (not datetimes).
    """

    def __init__(self, default=None, **kwargs):
        super(CalendarDate, self).__init__(default=default, **kwargs)

    def _validate_value(self, val, allow_None):
        """
        Checks that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        if self.allow_None and val is None:
            return

        if (not isinstance(val, dt.date) or isinstance(val, dt.datetime)) and not (allow_None and val is None):
            raise ValueError("CalendarDate parameter %r only takes date types." % self.name)

    def _validate_step(self, val, step):
        if step is not None and not isinstance(step, dt.date):
            raise ValueError("Step can only be None or a date type.")

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%d").date()


class Color(Parameter):
    """
    Color parameter defined as a hex RGB string with an optional #
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

    def __init__(self, default=None, allow_named=True, **kwargs):
        super(Color, self).__init__(default=default, **kwargs)
        self.allow_named = allow_named
        self._validate(default)

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_allow_named(val, self.allow_named)

    def _validate_value(self, val, allow_None):
        if (allow_None and val is None):
            return
        if not isinstance(val, basestring):
            raise ValueError("Color parameter %r expects a string value, "
                             "not an object of type %s." % (self.name, type(val)))

    def _validate_allow_named(self, val, allow_named):
        if (val is None and self.allow_None):
            return
        is_hex = re.match('^#?(([0-9a-fA-F]{2}){3}|([0-9a-fA-F]){3})$', val)
        if self.allow_named:
            if not is_hex and val.lower() not in self._named_colors:
                raise ValueError("Color '%s' only takes RGB hex codes "
                                 "or named colors, received '%s'." % (self.name, val))
        elif not is_hex:
            raise ValueError("Color '%s' only accepts valid RGB hex "
                             "codes, received '%s'." % (self.name, val))


class Range(NumericTuple):
    """
    A numeric range with optional bounds and softbounds.
    """

    __slots__ = ['bounds', 'inclusive_bounds', 'softbounds', 'step']

    def __init__(self,default=None, bounds=None, softbounds=None,
                 inclusive_bounds=(True,True), step=None, **params):
        self.bounds = bounds
        self.inclusive_bounds = inclusive_bounds
        self.softbounds = softbounds
        self.step = step
        super(Range,self).__init__(default=default,length=2,**params)

    def _validate(self, val):
        super(Range, self)._validate(val)
        self._validate_bounds(val, self.bounds, self.inclusive_bounds)

    def _validate_bounds(self, val, bounds, inclusive_bounds):
        if bounds is None or (val is None and self.allow_None):
            return
        vmin, vmax = bounds
        incmin, incmax = inclusive_bounds
        for bound, v in zip(['lower', 'upper'], val):
            too_low = (vmin is not None) and (v < vmin if incmin else v <= vmin)
            too_high = (vmax is not None) and (v > vmax if incmax else v >= vmax)
            if too_low or too_high:
                raise ValueError("Range parameter %r's %s bound must be in range %s."
                                 % (self.name, bound, self.rangestr()))


    def get_soft_bounds(self):
        return get_soft_bounds(self.bounds, self.softbounds)


    def rangestr(self):
        vmin, vmax = self.bounds
        incmin, incmax = self.inclusive_bounds
        incmin = '[' if incmin else '('
        incmax = ']' if incmax else ')'
        return '%s%s, %s%s' % (incmin, vmin, vmax, incmax)


class DateRange(Range):
    """
    A datetime or date range specified as (start, end).

    Bounds must be specified as datetime or date types (see param.dt_types).
    """

    def _validate_value(self, val, allow_None):
        # Cannot use super()._validate_value as DateRange inherits from
        # NumericTuple which check that the tuple values are numbers and
        # datetime objects aren't numbers.
        if allow_None and val is None:
            return

        if not isinstance(val, tuple):
            raise ValueError("DateRange parameter %r only takes a tuple value, "
                             "not %s." % (self.name, type(val).__name__))
        for n in val:
            if isinstance(n, dt_types):
                continue
            raise ValueError("DateRange parameter %r only takes date/datetime "
                             "values, not type %s." % (self.name, type(n).__name__))

        start, end = val
        if not end >= start:
            raise ValueError("DateRange parameter %r's end datetime %s "
                             "is before start datetime %s." %
                             (self.name, val[1], val[0]))

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
            if type(v) == dt.date:
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

class CalendarDateRange(Range):
    """
    A date range specified as (start_date, end_date).
    """
    def _validate_value(self, val, allow_None):
        if allow_None and val is None:
            return

        for n in val:
            if not isinstance(n, dt.date):
                raise ValueError("CalendarDateRange parameter %r only "
                                 "takes date types, not %s." % (self.name, val))

        start, end = val
        if not end >= start:
            raise ValueError("CalendarDateRange parameter %r's end date "
                             "%s is before start date %s." %
                             (self.name, val[1], val[0]))

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


class Event(Boolean):
    """
    An Event Parameter is one whose value is intimately linked to the
    triggering of events for watchers to consume. Event has a Boolean
    value, which when set to True triggers the associated watchers (as
    any Parameter does) and then is automatically set back to
    False. Conversely, if events are triggered directly via `.trigger`,
    the value is transiently set to True (so that it's clear which of
    many parameters being watched may have changed), then restored to
    False when the triggering completes. An Event parameter is thus like
    a momentary switch or pushbutton with a transient True value that
    serves only to launch some other action (e.g. via a param.depends
    decorator), rather than encapsulating the action itself as
    param.Action does.
    """

    # _autotrigger_value specifies the value used to set the parameter
    # to when the parameter is supplied to the trigger method. This
    # value change is then what triggers the watcher callbacks.
    __slots__ = ['_autotrigger_value', '_mode', '_autotrigger_reset_value']

    def __init__(self,default=False,bounds=(0,1),**params):
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
        # parameterized.py. Specifically, the set_param method
        # temporarily sets this attribute in order to disable resetting
        # back to False while triggered callbacks are executing
        super(Event, self).__init__(default=default,**params)

    def _reset_event(self, obj, val):
        val = False
        if obj is None:
            self.default = val
        else:
            obj.__dict__[self._internal_name] = val
        self._post_setter(obj, val)

    @instance_descriptor
    def __set__(self, obj, val):
        if self._mode in ['set-reset', 'set']:
            super(Event, self).__set__(obj, val)
        if self._mode in ['set-reset', 'reset']:
            self._reset_event(obj, val)


from contextlib import contextmanager
@contextmanager
def exceptions_summarized():
    """Useful utility for writing docs that need to show expected errors.
    Shows exception only, concisely, without a traceback.
    """
    try:
        yield
    except Exception:
        import sys
        etype, value, tb = sys.exc_info()
        print("{}: {}".format(etype.__name__,value), file=sys.stderr)
