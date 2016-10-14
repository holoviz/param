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
import glob

from .parameterized import Parameterized, Parameter, String, \
     descendents, ParameterizedFunction, ParamOverrides

from .parameterized import logging_level # pyflakes:ignore (needed for eval)
from .parameterized import shared_parameters # pyflakes:ignore (needed for eval)

try: 
   from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
except ImportError as e:
    raise ImportError("Requires ordereddict package on Python 2.6")


# Determine up-to-date version information, if possible, but with a
# safe fallback to ensure that this file and parameterized.py are the
# only two required files.
try:
    from .version import Version
    __version__ = Version(release=(1,4,2), fpath=__file__,
                          commit="$Format:%h$", reponame="param")
except:
    __version__ = '1.4.2-unknown'


#: Top-level object to allow messaging not tied to a particular
#: Parameterized object, as in 'param.main.warning("Invalid option")'.
main=Parameterized(name="main")


# A global random seed (integer or rational) available for controlling
# the behaviour of parameterized objects with random state.
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

        Some potentially useful exact number classes::

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

    # For Python 2 compatibility; can be removed for Python 3.
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
            type_param = self.params('time_type')
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

    # CBENHANCEMENT: Add an 'epsilon' slot.
    # See email 'Re: simulation-time-controlled Dynamic parameters'
    # Dec 22, 2007 CB->JAB

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
        # CEBALERT: use a dictionary to hold these things.
        if hasattr(obj,"_Dynamic_time_fn"):
            gen._Dynamic_time_fn = obj._Dynamic_time_fn

        gen._Dynamic_last = None
        # CEB: I'd use None for this, except can't compare a fixedpoint
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
        if not obj: self._set_instantiate(dynamic)


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
    being dynamically generated, bounds are checked when a the value
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

    __slots__ = ['bounds','_softbounds','inclusive_bounds','set_hook']

    def __init__(self,default=0.0,bounds=None,softbounds=None,inclusive_bounds=(True,True),**params):
        """
        Initialize this parameter object and store the bounds.

        Non-dynamic default values are checked against the bounds.
        """
        super(Number,self).__init__(default=default,**params)

        self.set_hook = identity_hook
        self.bounds = bounds
        self.inclusive_bounds = inclusive_bounds
        self._softbounds = softbounds
        if not callable(default): self._check_value(default)


    def __get__(self,obj,objtype):
        """
        Same as the superclass's __get__, but if the value was
        dynamically generated, check the bounds.
        """
        result = super(Number,self).__get__(obj,objtype)
        # CEBALERT: results in extra lookups (_value_is_dynamic() is
        # also looking up 'result' - should just pass it in). Note
        # that this method is called often.
        if self._value_is_dynamic(obj,objtype): self._check_value(result)
        return result


    def __set__(self,obj,val):
        """
        Set to the given value raising an exception if out of bounds.
        Also applies set_hook, providing support for conversions
        and transformations of the value.
        """
        val = self.set_hook(obj,val)

        if not callable(val): self._check_value(val)
        super(Number,self).__set__(obj,val)


    # Allow softbounds to be used like a normal attribute, as it 
    # probably should have been already (not _softbounds)
    @property
    def softbounds(self): return self._softbounds

    @softbounds.setter
    def softbounds(self,value): self._softbounds = value


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
        super(Number,self).__set__(obj,bounded_val)


    # CEBERRORALERT: doesn't take account of exclusive bounds; see
    # https://github.com/ioam/param/issues/80.
    def crop_to_bounds(self,val):
        """
        Return the given value cropped to be within the hard bounds
        for this parameter.

        If a numeric value is passed in, check it is within the hard
        bounds. If it is larger than the high bound, return the high
        bound. If it's smaller, return the low bound. In either case, the
        returned value could be None.  If a non-numeric value is passed
        in, set to be the default value (which could be None).  In no
        case is an exception raised; all values are accepted.
        """
        # Currently, values outside the bounds are silently cropped to
        # be inside the bounds; it may be appropriate to add a warning
        # in such cases.
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
            return  self.default

        return val


    def _checkBounds(self, val):

        if self.bounds is not None:
            vmin,vmax = self.bounds
            incmin,incmax = self.inclusive_bounds

            # Could simplify: see https://github.com/ioam/param/issues/83
            if vmax is not None:
                if incmax is True:
                    if not val <= vmax:
                        raise ValueError("Parameter '%s' must be at most %s"%(self._attrib_name,vmax))
                else:
                    if not val < vmax:
                        raise ValueError("Parameter '%s' must be less than %s"%(self._attrib_name,vmax))

            if vmin is not None:
                if incmin is True:
                    if not val >= vmin:
                        raise ValueError("Parameter '%s' must be at least %s"%(self._attrib_name,vmin))
                else:
                    if not val > vmin:
                        raise ValueError("Parameter '%s' must be greater than %s"%(self._attrib_name,vmin))



    def _check_value(self,val):
        """
        Checks that the value is numeric and that it is within the hard
        bounds; if not, an exception is raised.
        """
        if self.allow_None and val is None:
            return

        if not _is_number(val):
            raise ValueError("Parameter '%s' only takes numeric values"%(self._attrib_name))

        self._checkBounds(val)


    def get_soft_bounds(self):
        """
        For each soft bound (upper and lower), if there is a defined bound (not equal to None)
        then it is returned, otherwise it defaults to the hard bound. The hard bound could still be None.
        """
        if self.bounds is None:
            hl,hu=(None,None)
        else:
            hl,hu=self.bounds

        if self._softbounds is None:
            sl,su=(None,None)
        else:
            sl,su=self._softbounds


        if sl is None: l = hl
        else:          l = sl

        if su is None: u = hu
        else:          u = su

        return (l,u)



class Integer(Number):
    """Numeric Parameter required to be an Integer"""

    def _check_value(self,val):
        if self.allow_None and val is None:
            return

        if not isinstance(val,int):
            raise ValueError("Parameter '%s' must be an integer."%self._attrib_name)

        self._checkBounds(val)



class Magnitude(Number):
    """Numeric Parameter required to be in the range [0.0-1.0]."""

    def __init__(self,default=1.0,softbounds=None,**params):
        Number.__init__(self,default=default,bounds=(0.0,1.0),softbounds=softbounds,**params)



class Boolean(Parameter):
    """Binary or tristate Boolean Parameter."""

    __slots__ = ['bounds']

    # CB: bounds have no effect; see https://github.com/ioam/param/issues/82
    def __init__(self,default=False,bounds=(0,1),**params):
        self.bounds = bounds
        super(Boolean, self).__init__(default=default,**params)

    def __set__(self,obj,val):
        if self.allow_None:
            if not isinstance(val,bool) and val is not None:
                raise ValueError("Boolean '%s' only takes a Boolean value or None."
                                 %self._attrib_name)

            if val is not True and val is not False and val is not None:
                raise ValueError("Boolean '%s' must be True, False, or None."%self._attrib_name)
        else:
            if not isinstance(val,bool):
                raise ValueError("Boolean '%s' only takes a Boolean value."%self._attrib_name)

            if val is not True and val is not False:
                raise ValueError("Boolean '%s' must be True or False."%self._attrib_name)

        super(Boolean,self).__set__(obj,val)


class Tuple(Parameter):
    """A tuple Parameter (e.g. ('a',7.6,[3,5])) with a fixed tuple length."""

    __slots__ = ['length']

    def __init__(self,default=(0,0),length=None,**params):
        """
        Initialize a tuple parameter with a fixed length (number of
        elements).  The length is determined by the initial default
        value, if any, and must be supplied explicitly otherwise.  The
        length is not allowed to change after instantiation.
        """
        super(Tuple,self).__init__(default=default,**params)
        if length is None and default is not None:
            self.length = len(default)
        elif length is None and default is None:
            raise ValueError("%s: length must be specified if no default is supplied." %
                             (self._attrib_name))
        else:
            self.length = length
        self._check(default)



    def _check(self,val):
        if val is None and self.allow_None:
            return

        if not isinstance(val,tuple):
            raise ValueError("Tuple '%s' only takes a tuple value."%self._attrib_name)

        if not len(val)==self.length:
            raise ValueError("%s: tuple is not of the correct length (%d instead of %d)." %
                             (self._attrib_name,len(val),self.length))


    def __set__(self,obj,val):
        self._check(val)
        super(Tuple,self).__set__(obj,val)



class NumericTuple(Tuple):
    """A numeric tuple Parameter (e.g. (4.5,7.6,3)) with a fixed tuple length."""

    def _check(self,val):
        super(NumericTuple, self)._check(val)
        if not (self.allow_None and val is None):
            for n in val:
                if not _is_number(n):
                    raise ValueError("%s: tuple element is not numeric: %s." %
                                     (self._attrib_name,str(n)))



class XYCoordinates(NumericTuple):
    """A NumericTuple for an X,Y coordinate."""

    def __init__(self,default=(0.0,0.0),**params):
        super(XYCoordinates,self).__init__(default=default,length=2,**params)



class Callable(Parameter):
    """
    Parameter holding a value that is a callable object, such as a function.

    A keyword argument instantiate=True should be provided when a
    function object is used that might have state.  On the other hand,
    regular standalone functions cannot be deepcopied as of Python
    2.4, so instantiate must be False for those values.
    """

    def __set__(self,obj,val):
        if not (self.allow_None and val is None) and (not callable(val)):
            raise ValueError("Callable '%s' only takes a callable object."%self._attrib_name)
        super(Callable,self).__set__(obj,val)



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



# CEBALERT: this should be a method of ClassSelector.
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
    """

    __slots__=['attribs','objtype']

    def __init__(self,attribs=None,**kw):
        if attribs is None:
            attribs = []
        super(Composite,self).__init__(default=None,**kw)
        self.attribs = attribs

    def __get__(self,obj,objtype):
        """
        Return the values of all the attribs, as a list.
        """
        if not obj:
            return [getattr(objtype,a) for a in self.attribs]
        else:
            return [getattr(obj,a) for a in self.attribs]

    def __set__(self,obj,val):
        """
        Set the values of all the attribs.
        """
        assert len(val) == len(self.attribs),"Compound parameter '%s' got the wrong number of values (needed %d, but got %d)." % (self._attrib_name,len(self.attribs),len(val))

        if not obj:
            for a,v in zip(self.attribs,val):
                setattr(self.objtype,a,v)
        else:
            for a,v in zip(self.attribs,val):
                setattr(obj,a,v)


class Selector(Parameter):
    """
    Parameter whose value must be chosen from a list of possibilities.

    Subclasses must implement get_range().
    """

    __abstract = True

    def get_range(self):
        raise NotImplementedError("get_range() must be implemented in subclasses.")


class ObjectSelector(Selector):
    """
    Parameter whose value must be one object from a list of possible objects.

    check_on_set restricts the value to be among the current list of
    objects. By default, if objects are initially supplied,
    check_on_set is True, whereas if no objects are initially
    supplied, check_on_set is False. This can be overridden by
    explicitly specifying check_on_set initially.

    If check_on_set is True (either because objects are supplied
    initially, or because it is explicitly specified), the default
    (initial) value must be among the list of objects (unless the
    default value is None).
    """

    __slots__ = ['objects','compute_default_fn','check_on_set']

    # ObjectSelector is usually used to allow selection from a list of
    # existing objects, therefore instantiate is False by default.
    def __init__(self,default=None,objects=None,instantiate=False,
                 compute_default_fn=None,check_on_set=None,allow_None=None,**params):
        if objects is None:
            objects = []
        self.objects = objects
        self.compute_default_fn = compute_default_fn

        if check_on_set is not None:
            self.check_on_set=check_on_set
        elif len(objects)==0:
            self.check_on_set=False
        else:
            self.check_on_set=True

        super(ObjectSelector,self).__init__(default=default,instantiate=instantiate,
                                            **params)
        # Required as Parameter sets allow_None=True if default is None
        self.allow_None = allow_None
        if default is not None and self.check_on_set is True:
            self._check_value(default)


    # CBNOTE: if the list of objects is changed, the current value for
    # this parameter in existing POs could be out of the new range.

    def compute_default(self):
        """
        If this parameter's compute_default_fn is callable, call it
        and store the result in self.default.

        Also removes None from the list of objects (if the default is
        no longer None).
        """
        if self.default is None and callable(self.compute_default_fn):
            self.default=self.compute_default_fn()
            if self.default not in self.objects:
                self.objects.append(self.default)


    def _check_value(self,val,obj=None):
        """
        val must be None or one of the objects in self.objects.
        """
        if not (val in self.objects or (self.allow_None and val is None)):
            # CEBALERT: can be called before __init__ has called
            # super's __init__, i.e. before attrib_name has been set.
            try:
                attrib_name = self._attrib_name
            except AttributeError:
                attrib_name = ""
            raise ValueError("%s not in Parameter %s's list of possible objects" \
                             %(val,attrib_name))

    def __set__(self,obj,val):
        if self.check_on_set:
            self._check_value(val,obj)
        elif not (val in self.objects):
            self.objects.append(val)
        super(ObjectSelector,self).__set__(obj,val)


    def get_range(self):
        """
        Return the possible objects to which this parameter could be set.

        (Returns the dictionary {object.name:object}.)
        """
        return OrderedDict((obj.name if hasattr(obj,"name") \
                     else obj.__name__ if hasattr(obj,"__name__") \
                     else str(obj), obj) for obj in self.objects)


class ClassSelector(Selector):
    """
    Parameter whose value is a specified class or an instance of that class.
    By default, requires an instance, but if is_instance=False, accepts a class instead.
    Both class and instance values respect the instantiate slot, though it matters only
    for is_instance=True.
    """

    __slots__ = ['class_','is_instance']

    def __init__(self,class_,default=None,instantiate=True,is_instance=True,**params):
        self.class_ = class_
        self.is_instance = is_instance
        super(ClassSelector,self).__init__(default=default,instantiate=instantiate,**params)
        self._check_value(default)


    def _check_value(self,val,obj=None):
        """val must be None, an instance of self.class_ if self.is_instance=True or a subclass of self_class if self.is_instance=False"""
        if self.is_instance:
            if not (isinstance(val,self.class_)) and not (val is None and self.allow_None):
                raise ValueError(
                    "Parameter '%s' value must be an instance of %s, not '%s'" %
                    (self._attrib_name, self.class_.__name__, val))
        else:
            if not (val is None and self.allow_None) and not (issubclass(val,self.class_)):
                raise ValueError(
                    "Parameter '%s' must be a subclass of %s, not '%s'" %
                    (val.__name__, self.class_.__name__, val.__class__.__name__))


    def __set__(self,obj,val):
        self._check_value(val,obj)
        super(ClassSelector,self).__set__(obj,val)


    def get_range(self):
        """
        Return the possible types for this parameter's value.

        (I.e. return {name: <class>} for all classes that are
        concrete_descendents() of self.class_.)

        Only classes from modules that have been imported are added
        (see concrete_descendents()).
        """
        classes = concrete_descendents(self.class_)
        d=OrderedDict((name,class_) for name,class_ in classes.items())
        if self.allow_None:
            d['None']=None
        return d


class List(Parameter):
    """
    Parameter whose value is a list of objects, usually of a specified type.

    The bounds allow a minimum and/or maximum length of
    list to be enforced.  If the class is non-None, all
    items in the list are checked to be of that type.
    """

    __slots__ = ['class_','bounds']

    def __init__(self,default=[],class_=None,instantiate=True,
                 bounds=(0,None),**params):
        self.class_ = class_
        self.bounds = bounds
        Parameter.__init__(self,default=default,instantiate=instantiate,
                           **params)
        self._check_bounds(default)

    # Could add range() method from ClassSelector, to allow
    # list to be populated in the GUI

    def __set__(self,obj,val):
        """Set to the given value, raising an exception if out of bounds."""
        self._check_bounds(val)
        super(List,self).__set__(obj,val)

    def _check_bounds(self,val):
        """
        Checks that the list is of the right length and has the right contents.
        Otherwise, an exception is raised.
        """
        if self.allow_None and val is None:
            return

        if not isinstance(val, list):
            raise ValueError("List '%s' must be a list."%(self._attrib_name))

        if self.bounds is not None:
            min_length,max_length = self.bounds
            l=len(val)
            if min_length is not None and max_length is not None:
                if not (min_length <= l <= max_length):
                    raise ValueError("%s: list length must be between %s and %s (inclusive)"%(self._attrib_name,min_length,max_length))
            elif min_length is not None:
                if not min_length <= l:
                    raise ValueError("%s: list length must be at least %s."%(self._attrib_name,min_length))
            elif max_length is not None:
                if not l <= max_length:
                    raise ValueError("%s: list length must be at most %s."%(self._attrib_name,max_length))

        self._check_type(val)

    def _check_type(self,val):
        if self.class_ is not None:
            for v in val:
                assert isinstance(v,self.class_),repr(self._attrib_name)+": "+repr(v)+" is not an instance of " + repr(self.class_) + "."



class HookList(List):
    """
    Parameter whose value is a list of callable objects.

    This type of List Parameter is typically used to provide a place
    for users to register a set of commands to be called at a
    specified place in some sequence of processing steps.
    """
    __slots__ = ['class_','bounds']

    def _check_type(self,val):
        for v in val:
            assert callable(v),repr(self._attrib_name)+": "+repr(v)+" is not callable."



class Dict(ClassSelector):
    """
    Parameter whose value is a dictionary.
    """
    def __init__(self,**params):
        super(Dict,self).__init__(dict,**params)


class Array(ClassSelector):
    """
    Parameter whose value is a numpy array.
    """

    def __init__(self, **params):
        # CEBALERT: instead use python array as default?
        from numpy import ndarray
        super(Array,self).__init__(ndarray, allow_None=True, **params)


# For portable code:
#   - specify paths in unix (rather than Windows) style;
#   - use resolve_file_path() for paths to existing files to be read,
#   - use resolve_folder_path() for paths to existing folders to be read,
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

    path_to_file = Boolean(default=True, pickle_default_value=False, doc="""
        String specifying whether the path refers to a 'File' or a 'Folder'.""")

    def __call__(self, path, **params):
        p = ParamOverrides(self, params)

        path = os.path.normpath(path)

        if os.path.isabs(path):
            if p.path_to_file:
                if os.path.isfile(path):
                    return path
                else:
                    raise IOError("File '%s' not found." %path)
            elif not p.path_to_file:
                if os.path.isdir(path):
                    return path
                else:
                    raise IOError("Folder '%s' not found." %path)
            else:
                raise IOError("Type '%s' not recognised." %p.path_type)

        else:
            paths_tried = []
            for prefix in p.search_paths:
                try_path = os.path.join(os.path.normpath(prefix), path)

                if p.path_to_file:
                    if os.path.isfile(try_path):
                        return try_path
                elif not p.path_to_file:
                    if os.path.isdir(try_path):
                        return try_path
                else:
                    raise IOError("Type '%s' not recognised." %p.path_type)

                paths_tried.append(try_path)

            raise IOError(os.path.split(path)[1] + " was not found in the following place(s): " + str(paths_tried) + ".")


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
        if self.search_paths:
            return resolve_path(path, search_paths=self.search_paths)
        else:
            return resolve_path(path)

    def __set__(self, obj, val):
        """
        Call Parameter's __set__, but warn if the file cannot be found.
        """
        if val is None:
            if not self.allow_None:
                Parameterized(name="%s.%s"%(obj.name,self._attrib_name)).warning('None is not allowed')
        else:
            try:
                self._resolve(val)
            except IOError as e:
                Parameterized(name="%s.%s"%(obj.name,self._attrib_name)).warning('%s',e.args[0])
        super(Path,self).__set__(obj,val)

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
        if self.search_paths:
            return resolve_path(path, path_to_file=True, search_paths=self.search_paths)
        else:
            return resolve_path(path, path_to_file=True)


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
        if self.search_paths:
            return resolve_path(path, path_to_file=False, search_paths=self.search_paths)
        else:
            return resolve_path(path, path_to_file=False)



def abbreviate_paths(pathspec,named_paths):
    """
    Given a dict of (pathname,path) pairs, removes any prefix shared by all pathnames.
    Helps keep menu items short yet unambiguous.
    """
    from os.path import commonprefix, dirname, sep

    prefix = commonprefix([dirname(name)+sep for name in named_paths.keys()]+[pathspec])
    return OrderedDict([(name[len(prefix):],path) for name,path in named_paths.items()])



class FileSelector(ObjectSelector):
    """
    Given a path glob, allows one file to be selected from those matching.
    """
    __slots__ = ['path']

    def __init__(self, default=None, path="", **kwargs):
        super(FileSelector, self).__init__(default, **kwargs)
        self.path = path
        self.update()

    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default in self.objects:
            return
        self.default = self.objects[0] if self.objects else None

    def get_range(self):
        return abbreviate_paths(self.path,super(FileSelector, self).get_range())


class ListSelector(ObjectSelector):
    """
    Variant of ObjectSelector where the value can be multiple objects from
    a list of possible objects.
    """

    def compute_default(self):
        if self.default is None and callable(self.compute_default_fn):
            self.default = self.compute_default_fn()
            for o in self.default:
                if self.default not in self.objects:
                    self.objects.append(self.default)

    def _check_value(self, val, obj=None):
        for o in val:
            super(ListSelector, self)._check_value(o, obj)



class MultiFileSelector(ListSelector):
    """
    Given a path glob, allows multiple files to be selected from the list of matches.
    """
    __slots__ = ['path']

    def __init__(self, default=None, path="", **kwargs):
        super(MultiFileSelector, self).__init__(default, **kwargs)
        self.path = path
        self.update()

    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default and all([o in self.objects for o in self.default]):
            return
        self.default = self.objects

    def get_range(self):
        return abbreviate_paths(self.path,super(MultiFileSelector, self).get_range())


