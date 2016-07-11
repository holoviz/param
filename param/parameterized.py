"""
Generic support for objects with full-featured Parameters and
messaging.
"""

import copy
import re
import sys
import inspect
import random

from operator import itemgetter,attrgetter
from types import FunctionType
from functools import partial, wraps

import logging
from contextlib import contextmanager
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

try:
    # In case the optional ipython module is unavailable
    from .ipython import ParamPager
    param_pager = ParamPager(metaclass=True)  # Generates param description
except:
    param_pager = None


VERBOSE = INFO - 1
logging.addLevelName(VERBOSE, "VERBOSE")

# Logger instance to use for param; if "logger" is set to None, the root logger
# will be used.
logger = None
def get_logger():
    if logger is None:
        # If it was not configured before, do default initialization
        if not logging.getLogger().handlers:
            logging.basicConfig(level=INFO)
        return logging.getLogger()
    else:
        return logger

# Indicates whether warnings should be raised as errors, stopping
# processing.
warnings_as_exceptions = False

docstring_signature = True        # Add signature to class docstrings
docstring_describe_params = True  # Add parameter description to class
                                  # docstrings (requires ipython module)
object_count = 0
warning_count = 0


@contextmanager
def logging_level(level):
    """
    Temporarily modify param's logging level.
    """
    level = level.upper()
    levels = [DEBUG, INFO, WARNING, ERROR, CRITICAL, VERBOSE]
    level_names = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'VERBOSE']

    if level not in level_names:
        raise Exception("Level %r not in %r" % (level, levels))

    param_logger = get_logger()
    logging_level = param_logger.getEffectiveLevel()
    param_logger.setLevel(levels[level_names.index(level)])
    try:
        yield None
    finally:
        param_logger.setLevel(logging_level)


def classlist(class_):
    """
    Return a list of the class hierarchy above (and including) the given class.

    Same as inspect.getmro(class_)[::-1]
    """
    return inspect.getmro(class_)[::-1]


def descendents(class_):
    """
    Return a list of the class hierarchy below (and including) the given class.

    The list is ordered from least- to most-specific.  Can be useful for
    printing the contents of an entire class hierarchy.
    """
    assert isinstance(class_,type)
    q = [class_]
    out = []
    while len(q):
        x = q.pop(0)
        out.insert(0,x)
        for b in x.__subclasses__():
            if b not in q and b not in out:
                q.append(b)
    return out[::-1]


def get_all_slots(class_):
    """
    Return a list of slot names for slots defined in class_ and its
    superclasses.
    """
    # A subclass's __slots__ attribute does not contain slots defined
    # in its superclass (the superclass' __slots__ end up as
    # attributes of the subclass).
    all_slots = []
    parent_param_classes = [c for c in classlist(class_)[1::]]
    for c in parent_param_classes:
        if hasattr(c,'__slots__'):
            all_slots+=c.__slots__
    return all_slots


def get_occupied_slots(instance):
    """
    Return a list of slots for which values have been set.

    (While a slot might be defined, if a value for that slot hasn't
    been set, then it's an AttributeError to request the slot's
    value.)
    """
    return [slot for slot in get_all_slots(type(instance))
            if hasattr(instance,slot)]


def all_equal(arg1,arg2):
    """
    Return a single boolean for arg1==arg2, even for numpy arrays
    using element-wise comparison.

    Uses all(arg1==arg2) for sequences, and arg1==arg2 otherwise.

    If both objects have an '_infinitely_iterable' attribute, they are
    not be zipped together and are compared directly instead.
    """
    if all(hasattr(el, '_infinitely_iterable') for el in [arg1,arg2]):
        return arg1==arg2
    try:
        return all(a1 == a2 for a1, a2 in zip(arg1, arg2))
    except TypeError:
        return arg1==arg2



# For Python 2 compatibility.
#
# The syntax to use a metaclass changed incompatibly between 2 and
# 3. The add_metaclass() class decorator below creates a class using a
# specified metaclass in a way that works on both 2 and 3. For 3, can
# remove this decorator and specify metaclasses in a simpler way
# (https://docs.python.org/3/reference/datamodel.html#customizing-class-creation)
#
# Code from six (https://bitbucket.org/gutworth/six; version 1.4.1).
def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        for slots_var in orig_vars.get('__slots__', ()):
            orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


class bothmethod(object): # pylint: disable-msg=R0903
    """
    'optional @classmethod'

    A decorator that allows a method to receive either the class
    object (if called on the class) or the instance object
    (if called on the instance) as its first argument.

    Code (but not documentation) copied from:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/523033.
    """
    # pylint: disable-msg=R0903

    def __init__(self, func):
        self.func = func

    # i.e. this is also a non-data descriptor
    def __get__(self, obj, type_=None):
        if obj is None:
            return wraps(self.func)(partial(self.func, type_))
        else:
            return wraps(self.func)(partial(self.func, obj))


class ParameterMetaclass(type):
    """
    Metaclass allowing control over creation of Parameter classes.
    """
    def __new__(mcs,classname,bases,classdict):
        # store the class's docstring in __classdoc
        if '__doc__' in classdict:
            classdict['__classdoc']=classdict['__doc__']
        # when asking for help on Parameter *object*, return the doc
        # slot
        classdict['__doc__']=property(attrgetter('doc'))

        # To get the benefit of slots, subclasses must themselves define
        # __slots__, whether or not they define attributes not present in
        # the base Parameter class.  That's because a subclass will have
        # a __dict__ unless it also defines __slots__.
        if '__slots__' not in classdict:
            classdict['__slots__']=[]

        return type.__new__(mcs,classname,bases,classdict)

    def __getattribute__(mcs,name):
        if name=='__doc__':
            # when asking for help on Parameter *class*, return the
            # stored class docstring
            return type.__getattribute__(mcs,'__classdoc')
        else:
            return type.__getattribute__(mcs,name)



# CEBALERT: we break some aspects of slot handling for Parameter and
# Parameterized. The __new__ methods in the metaclasses for those two
# classes omit to handle the case where __dict__ is passed in
# __slots__ (and they possibly omit other things too). Additionally,
# various bits of code in the Parameterized class assumes that all
# Parameterized instances have a __dict__, but I'm not sure that's
# guaranteed to be true (although it's true at the moment).


# CB: we could maybe reduce the complexity by doing something to allow
# a parameter to discover things about itself when created (would also
# allow things like checking a Parameter is owned by a
# Parameterized). I have some vague ideas about what to do.
@add_metaclass(ParameterMetaclass)
class Parameter(object):
    """
    An attribute descriptor for declaring parameters.

    Parameters are a special kind of class attribute.  Setting a
    Parameterized class attribute to be a Parameter instance causes
    that attribute of the class (and the class's instances) to be
    treated as a Parameter.  This allows special behavior, including
    dynamically generated parameter values, documentation strings,
    constant and read-only parameters, and type or range checking at
    assignment time.

    For example, suppose someone wants to define two new kinds of
    objects Foo and Bar, such that Bar has a parameter delta, Foo is a
    subclass of Bar, and Foo has parameters alpha, sigma, and gamma
    (and delta inherited from Bar).  She would begin her class
    definitions with something like this:

    class Bar(Parameterized):
        delta = Parameter(default=0.6, doc='The difference between steps.')
        ...

    class Foo(Bar):
        alpha = Parameter(default=0.1, doc='The starting value.')
        sigma = Parameter(default=0.5, doc='The standard deviation.',
                          constant=True)
        gamma = Parameter(default=1.0, doc='The ending value.')
        ...

    Class Foo would then have four parameters, with delta defaulting
    to 0.6.

    Parameters have several advantages over plain attributes:

    1. Parameters can be set automatically when an instance is
       constructed: The default constructor for Foo (and Bar) will
       accept arbitrary keyword arguments, each of which can be used
       to specify the value of a Parameter of Foo (or any of Foo's
       superclasses).  E.g., if a script does this:

           myfoo = Foo(alpha=0.5)

       myfoo.alpha will return 0.5, without the Foo constructor
       needing special code to set alpha.

       If Foo implements its own constructor, keyword arguments will
       still be accepted if the constructor accepts a dictionary of
       keyword arguments (as in ``def __init__(self,**params):``), and
       then each class calls its superclass (as in
       ``super(Foo,self).__init__(**params)``) so that the
       Parameterized constructor will process the keywords.

    2. A Parameterized class need specify only the attributes of a
       Parameter whose values differ from those declared in
       superclasses; the other values will be inherited.  E.g. if Foo
       declares

        delta = Parameter(default=0.2)

       the default value of 0.2 will override the 0.6 inherited from
       Bar, but the doc will be inherited from Bar.

    3. The Parameter descriptor class can be subclassed to provide
       more complex behavior, allowing special types of parameters
       that, for example, require their values to be numbers in
       certain ranges, generate their values dynamically from a random
       distribution, or read their values from a file or other
       external source.

    4. The attributes associated with Parameters provide enough
       information for automatically generating property sheets in
       graphical user interfaces, allowing Parameterized instances to
       be edited by users.

    Note that Parameters can only be used when set as class attributes
    of Parameterized classes. Parameters used as standalone objects,
    or as class attributes of non-Parameterized classes, will not have
    the behavior described here.
    """

    # Because they implement __get__ and __set__, Parameters are known
    # as 'descriptors' in Python; see "Implementing Descriptors" and
    # "Invoking Descriptors" in the 'Customizing attribute access'
    # section of the Python reference manual:
    # http://docs.python.org/ref/attribute-access.html
    #
    # Overview of Parameters for programmers
    # ======================================
    #
    # Consider the following code:
    #
    #
    # class A(Parameterized):
    #     p = Parameter(default=1)
    #
    # a1 = A()
    # a2 = A()
    #
    #
    # * a1 and a2 share one Parameter object (A.__dict__['p']).
    #
    # * The default (class) value of p is stored in this Parameter
    #   object (A.__dict__['p'].default).
    #
    # * If the value of p is set on a1 (e.g. a1.p=2), a1's value of p
    #   is stored in a1 itself (a1.__dict__['_p_param_value'])
    #
    # * When a1.p is requested, a1.__dict__['_p_param_value'] is
    #   returned. When a2.p is requested, '_p_param_value' is not
    #   found in a2.__dict__, so A.__dict__['p'].default (i.e. A.p) is
    #   returned instead.
    #
    #
    # Be careful when referring to the 'name' of a Parameter:
    #
    # * A Parameterized class has a name for the attribute which is
    #   being represented by the Parameter ('p' in the example above);
    #   in the code, this is called the 'attrib_name'.
    #
    # * When a Parameterized instance has its own local value for a
    #   parameter, it is stored as '_X_param_value' (where X is the
    #   attrib_name for the Parameter); in the code, this is called
    #   the internal_name.


    # So that the extra features of Parameters do not require a lot of
    # overhead, Parameters are implemented using __slots__ (see
    # http://www.python.org/doc/2.4/ref/slots.html).  Instead of having
    # a full Python dictionary associated with each Parameter instance,
    # Parameter instances have an enumerated list (named __slots__) of
    # attributes, and reserve just enough space to store these
    # attributes.  Using __slots__ requires special support for
    # operations to copy and restore Parameters (e.g. for Python
    # persistent storage pickling); see __getstate__ and __setstate__.
    __slots__ = ['_attrib_name','_internal_name','default','doc',
                 'precedence','instantiate','constant','readonly',
                 'pickle_default_value','allow_None']

    # When created, a Parameter does not know which
    # Parameterized class owns it. If a Parameter subclass needs
    # to know the owning class, it can declare an 'objtype' slot
    # (which will be filled in by ParameterizedMetaclass)

    def __init__(self,default=None,doc=None,precedence=None,  # pylint: disable-msg=R0913
                 instantiate=False,constant=False,readonly=False,
                 pickle_default_value=True, allow_None=False):
        """
        Initialize a new Parameter object: store the supplied attributes.

        default: the owning class's value for the attribute
        represented by this Parameter.

        precedence is a value, usually in the range 0.0 to 1.0, that
        allows the order of Parameters in a class to be defined (for
        e.g. in GUI menus). A negative precedence indicates a
        parameter that should be hidden in e.g. GUI menus.

        default, doc, and precedence default to None. This is to allow
        inheritance of Parameter slots (attributes) from the owning-class'
        class hierarchy (see ParameterizedMetaclass).

        In rare cases where the default value should not be pickled,
        set pickle_default_value=False (e.g. for file search paths).
        """
        self._attrib_name = None
        self._internal_name = None
        self.precedence = precedence
        self.default = default
        self.doc = doc
        self.constant = constant or readonly # readonly => constant
        self.readonly = readonly
        self._set_instantiate(instantiate)
        self.pickle_default_value = pickle_default_value
        self.allow_None = (default is None or allow_None)


    def _set_instantiate(self,instantiate):
        """Constant parameters must be instantiated."""
        # CB: instantiate doesn't actually matter for read-only
        # parameters, since they can't be set even on a class.  But
        # this avoids needless instantiation.
        if self.readonly:
            self.instantiate = False
        else:
            self.instantiate = instantiate or self.constant # pylint: disable-msg=W0201


    def __get__(self,obj,objtype): # pylint: disable-msg=W0613
        """
        Return the value for this Parameter.

        If called for a Parameterized class, produce that
        class's value (i.e. this Parameter object's 'default'
        attribute).

        If called for a Parameterized instance, produce that
        instance's value, if one has been set - otherwise produce the
        class's value (default).
        """
        # NB: obj can be None (when __get__ called for a
        # Parameterized class); objtype is never None

        if obj is None:
            result = self.default
        else:
            result = obj.__dict__.get(self._internal_name,self.default)
        return result


    def __set__(self,obj,val):
        """
        Set the value for this Parameter.

        If called for a Parameterized class, set that class's
        value (i.e. set this Parameter object's 'default' attribute).

        If called for a Parameterized instance, set the value of
        this Parameter on that instance (i.e. in the instance's
        __dict__, under the parameter's internal_name).


        If the Parameter's constant attribute is True, only allows
        the value to be set for a Parameterized class or on
        uninitialized Parameterized instances.

        If the Parameter's readonly attribute is True, only allows the
        value to be specified in the Parameter declaration inside the
        Parameterized source code. A read-only parameter also
        cannot be set on a Parameterized class.

        Note that until we support some form of read-only
        object, it is still possible to change the attributes of the
        object stored in a constant or read-only Parameter (e.g. the
        left bound of a BoundingBox).
        """
        # NB: obj can be None (when __set__ called for a
        # Parameterized class)
        if self.constant or self.readonly:
            if self.readonly:
                raise TypeError("Read-only parameter '%s' cannot be modified"%self._attrib_name)
            elif obj is None:  #not obj
                self.default = val
            elif not obj.initialized:
                obj.__dict__[self._internal_name] = val
            else:
                raise TypeError("Constant parameter '%s' cannot be modified"%self._attrib_name)

        else:
            if obj is None:
                self.default = val
            else:
                obj.__dict__[self._internal_name] = val


    def __delete__(self,obj):
        raise TypeError("Cannot delete '%s': Parameters deletion not allowed."%self._attrib_name)


    def _set_names(self,attrib_name):
        self._attrib_name = attrib_name
        self._internal_name = "_%s_param_value"%attrib_name


    def __getstate__(self):
        """
        All Parameters have slots, not a dict, so we have to support
        pickle and deepcopy ourselves.
        """
        state = {}
        for slot in get_occupied_slots(self):
            state[slot] = getattr(self,slot)
        return state

    def __setstate__(self,state):
        # set values of __slots__ (instead of in non-existent __dict__)
        for (k,v) in state.items():
            setattr(self,k,v)


# Define one particular type of Parameter that is used in this file
class String(Parameter):
    """
    A simple String parameter.
    """

    basestring = basestring if sys.version_info[0]==2 else str

    def __init__(self, default="", allow_None=False, **kwargs):
        super(String, self).__init__(default=default, allow_None=allow_None, **kwargs)
        self._check_value(default)
        self.allow_None = allow_None

    def _check_value(self,val):
        if not isinstance(val, self.basestring) and not (self.allow_None and val is None):
            raise ValueError("String '%s' only takes a string value."%self._attrib_name)

    def __set__(self,obj,val):
        self._check_value(val)
        super(String,self).__set__(obj,val)



class shared_parameters(object):
    """
    Context manager to share parameter instances when creating
    multiple Parameterized objects of the same type. Parameter default
    values are instantiated once and cached to be reused when another
    Parameterized object of the same type is instantiated.
    Can be useful to easily modify large collections of Parameterized
    objects at once and can provide a significant speedup.
    """

    _share = False
    _shared_cache = {}

    def __enter__(self):
        shared_parameters._share = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        shared_parameters._share = False
        shared_parameters._shared_cache = {}



class ParameterizedMetaclass(type):
    """
    The metaclass of Parameterized (and all its descendents).

    The metaclass overrides type.__setattr__ to allow us to set
    Parameter values on classes without overwriting the attribute
    descriptor.  That is, for a Parameterized class of type X with a
    Parameter y, the user can type X.y=3, which sets the default value
    of Parameter y to be 3, rather than overwriting y with the
    constant value 3 (and thereby losing all other info about that
    Parameter, such as the doc string, bounds, etc.).

    The __init__ method is used when defining a Parameterized class,
    usually when the module where that class is located is imported
    for the first time.  That is, the __init__ in this metaclass
    initializes the *class* object, while the __init__ method defined
    in each Parameterized class is called for each new instance of
    that class.

    Additionally, a class can declare itself abstract by having an
    attribute __abstract set to True. The 'abstract' attribute can be
    used to find out if a class is abstract or not.
    """
    def __init__(mcs,name,bases,dict_):
        """
        Initialize the class object (not an instance of the class, but
        the class itself).

        Initializes all the Parameters by looking up appropriate
        default values (see __param_inheritance()) and setting
        attrib_names (see _set_names()).
        """
        type.__init__(mcs,name,bases,dict_)

        # Give Parameterized classes a useful 'name' attribute.
        # (Could instead consider changing the instance Parameter
        # 'name' to '__name__'?)
        mcs.name = name

        # All objects (with their names) of type Parameter that are
        # defined in this class
        parameters = [(n,o) for (n,o) in dict_.items()
                      if isinstance(o,Parameter)]

        for param_name,param in parameters:
            mcs._initialize_parameter(param_name,param)

        if docstring_signature:
            mcs.__class_docstring_signature()

    def __class_docstring_signature(mcs, max_repr_len=15):
        """
        Autogenerate a keyword signature in the class docstring for
        all available parameters. This is particularly useful in the
        IPython Notebook as IPython will parse this signature to allow
        tab-completion of keywords.

        max_repr_len: Maximum length (in characters) of value reprs.
        """
        processed_kws, keyword_groups = set(), []
        for cls in reversed(mcs.mro()):
            keyword_group = []
            for (k,v) in sorted(cls.__dict__.items()):
                if isinstance(v, Parameter) and k not in processed_kws:
                    param_type = v.__class__.__name__
                    keyword_group.append("%s=%s" % (k, param_type))
                    processed_kws.add(k)
            keyword_groups.append(keyword_group)

        keywords = [el for grp in reversed(keyword_groups) for el in grp]
        class_docstr = "\n"+mcs.__doc__ if mcs.__doc__ else ''
        signature = "params(%s)" % (", ".join(keywords))
        description = param_pager(mcs) if (docstring_describe_params and param_pager) else ''
        mcs.__doc__ = signature + class_docstr + '\n' + description


    def _initialize_parameter(mcs,param_name,param):
        # parameter has no way to find out the name a
        # Parameterized class has for it
        param._set_names(param_name)
        mcs.__param_inheritance(param_name,param)


    # Python 2.6 added abstract base classes; see
    # https://github.com/ioam/param/issues/84
    def __is_abstract(mcs):
        """
        Return True if the class has an attribute __abstract set to True.
        Subclasses will return False unless they themselves have
        __abstract set to true.  This mechanism allows a class to
        declare itself to be abstract (e.g. to avoid it being offered
        as an option in a GUI), without the "abstract" property being
        inherited by its subclasses (at least one of which is
        presumably not abstract).
        """
        # Can't just do ".__abstract", because that is mangled to
        # _ParameterizedMetaclass__abstract before running, but
        # the actual class object will have an attribute
        # _ClassName__abstract.  So, we have to mangle it ourselves at
        # runtime.
        try:
            return getattr(mcs,'_%s__abstract'%mcs.__name__)
        except AttributeError:
            return False

    abstract = property(__is_abstract)



    def __setattr__(mcs,attribute_name,value):
        """
        Implements 'self.attribute_name=value' in a way that also supports Parameters.

        If there is already a descriptor named attribute_name, and
        that descriptor is a Parameter, and the new value is *not* a
        Parameter, then call that Parameter's __set__ method with the
        specified value.

        In all other cases set the attribute normally (i.e. overwrite
        the descriptor).  If the new value is a Parameter, once it has
        been set we make sure that the value is inherited from
        Parameterized superclasses as described in __param_inheritance().
        """
        # Find out if there's a Parameter called attribute_name as a
        # class attribute of this class - if not, parameter is None.
        parameter,owning_class = mcs.get_param_descriptor(attribute_name)

        if parameter and not isinstance(value,Parameter):
            if owning_class != mcs:
                type.__setattr__(mcs,attribute_name,copy.copy(parameter))
            mcs.__dict__[attribute_name].__set__(None,value)

        else:
            type.__setattr__(mcs,attribute_name,value)

            if isinstance(value,Parameter):
                mcs.__param_inheritance(attribute_name,value)
            else:
                # the purpose of the warning below is to catch
                # mistakes ("thinking you are setting a parameter, but
                # you're not"). There are legitimate times when
                # something needs be set on the class, and we don't
                # want to see a warning then. Such attributes should
                # presumably be prefixed by at least one underscore.
                # (For instance, python's own pickling mechanism
                # caches __slotnames__ on the class:
                # http://mail.python.org/pipermail/python-checkins/2003-February/033517.html.)
                # CEBALERT: this warning bypasses the usual
                # mechanisms, which has have consequences for warning
                # counts, warnings as exceptions, etc.
                if not attribute_name.startswith('_'):
                    get_logger().log(WARNING,
                                     "Setting non-Parameter class attribute %s.%s = %s ",
                                     mcs.__name__,attribute_name,repr(value))


    def __param_inheritance(mcs,param_name,param):
        """
        Look for Parameter values in superclasses of this
        Parameterized class.

        Ordinarily, when a Python object is instantiated, attributes
        not given values in the constructor will inherit the value
        given in the object's class, or in its superclasses.  For
        Parameters owned by Parameterized classes, we have implemented
        an additional level of default lookup, should this ordinary
        lookup return only None.

        In such a case, i.e. when no non-None value was found for a
        Parameter by the usual inheritance mechanisms, we explicitly
        look for Parameters with the same name in superclasses of this
        Parameterized class, and use the first such value that we
        find.

        The goal is to be able to set the default value (or other
        slots) of a Parameter within a Parameterized class, just as we
        can set values for non-Parameter objects in Parameterized
        classes, and have the values inherited through the
        Parameterized hierarchy as usual.

        Note that instantiate is handled differently: if there is a
        parameter with the same name in one of the superclasses with
        instantiate set to True, this parameter will inherit
        instatiate=True.
        """
        # get all relevant slots (i.e. slots defined in all
        # superclasses of this parameter)
        slots = {}
        for p_class in classlist(type(param))[1::]:
            slots.update(dict.fromkeys(p_class.__slots__))

        # Some Parameter classes need to know the owning Parameterized
        # class. Such classes can declare an 'objtype' slot, and the
        # owning class will be stored in it.
        if 'objtype' in slots:
            setattr(param,'objtype',mcs)
            del slots['objtype']

        # instantiate is handled specially
        for superclass in classlist(mcs)[::-1]:
            super_param = superclass.__dict__.get(param_name)
            if isinstance(super_param, Parameter) and super_param.instantiate is True:
                param.instantiate=True
        del slots['instantiate']


        for slot in slots.keys():
            superclasses = iter(classlist(mcs)[::-1])

            # Search up the hierarchy until param.slot (which has to
            # be obtained using getattr(param,slot)) is not None, or
            # we run out of classes to search.
            while getattr(param,slot) is None:
                try:
                    param_super_class = next(superclasses)
                except StopIteration:
                    break

                new_param = param_super_class.__dict__.get(param_name)
                if new_param is not None and hasattr(new_param,slot):
                    # (slot might not be there because could be a more
                    # general type of Parameter)
                    new_value = getattr(new_param,slot)
                    setattr(param,slot,new_value)


    def get_param_descriptor(mcs,param_name):
        """
        Goes up the class hierarchy (starting from the current class)
        looking for a Parameter class attribute param_name. As soon as
        one is found as a class attribute, that Parameter is returned
        along with the class in which it is declared.
        """
        classes = classlist(mcs)
        for c in classes[::-1]:
            attribute = c.__dict__.get(param_name)
            if isinstance(attribute,Parameter):
                return attribute,c
        return None,None




# JABALERT: Only partially achieved so far -- objects of the same
# type and parameter values are treated as different, so anything
# for which instantiate == True is reported as being non-default.

# Whether script_repr should avoid reporting the values of parameters
# that are just inheriting their values from the class defaults.
script_repr_suppress_defaults=True


# CEBALERT: How about some defaults?
# Also, do we need an option to return repr without path, if desired?
# E.g. to get 'pre_plot_hooks()' instead of
# 'topo.command.analysis.pre_plot_hooks()' in the gui?
def script_repr(val,imports,prefix,settings):
    """
    Variant of repr() designed for generating a runnable script.

    Instances of types that require special handling can use the
    script_repr_reg dictionary. Using the type as a key, add a
    function that returns a suitable representation of instances of
    that type, and adds the required import statement.

    The repr of a parameter can be suppressed by returning None from
    the appropriate hook in script_repr_reg.
    """
    return pprint(val,imports,prefix,settings,unknown_value=None,
                  qualify=True,separator="\n")


# CB: when removing script_repr, merge its docstring here and improve.
# And the ALERT by script_repr about defaults can go.
# CEBALERT: remove settings, add default argument for imports
def pprint(val,imports, prefix="\n    ", settings=[],
           unknown_value='<?>', qualify=False, separator=''):
    """
    (Experimental) Pretty printed representation of a parameterized
    object that may be evaluated with eval.

    Similar to repr except introspection of the constructor (__init__)
    ensures a valid and succinct representation is generated.

    Only parameters are represented (whether specified as standard,
    positional, or keyword arguments). Parameters specified as
    positional arguments are always shown, followed by modified
    parameters specified as keyword arguments, sorted by precedence.

    unknown_value determines what to do where a representation cannot be
    generated for something required to recreate the object. Such things
    include non-parameter positional and keyword arguments, and certain
    values of parameters (e.g. some random state objects).

    Supplying an unknown_value of None causes unrepresentable things
    to be silently ignored. If unknown_value is a string, that
    string will appear in place of any unrepresentable things. If
    unknown_value is False, an Exception will be raised if an
    unrepresentable value is encountered.

    If supplied, imports should be a list, and it will be populated
    with the set of imports required for the object and all of its
    parameter values.

    If qualify is True, the class's path will be included (e.g. "a.b.C()"),
    otherwise only the class will appear ("C()").

    Parameters will be separated by a comma only by default, but the
    separator parameter allows an additional separator to be supplied
    (e.g. a newline could be supplied to have each Parameter appear on a
    separate line).

    NOTE: pprint will replace script_repr in a future version of
    param, but is not yet a complete replacement for script_repr.
    """
    # CB: doc prefix & settings or realize they don't need to be
    # passed around, etc.
    # JLS: The settings argument is not used anywhere. To be removed
    # in a separate PR.
    if isinstance(val,type):
        rep = type_script_repr(val,imports,prefix,settings)

    elif type(val) in script_repr_reg:
        rep = script_repr_reg[type(val)](val,imports,prefix,settings)

    # CEBALERT: remove with script_repr
    elif hasattr(val,'script_repr'):
        rep=val.script_repr(imports, prefix+"    ")

    elif hasattr(val,'pprint'):
        rep=val.pprint(imports=imports, prefix=prefix+"    ",
                       qualify=qualify, unknown_value=unknown_value,
                       separator=separator)

    else:
        rep=repr(val)

    return rep


#: see script_repr()
script_repr_reg = {}


# currently only handles list and tuple
def container_script_repr(container,imports,prefix,settings):
    result=[]
    for i in container:
        result.append(pprint(i,imports,prefix,settings))

    ## (hack to get container brackets)
    if isinstance(container,list):
        d1,d2='[',']'
    elif isinstance(container,tuple):
        d1,d2='(',')'
    else:
        raise NotImplementedError
    rep=d1+','.join(result)+d2

    # no imports to add for built-in types

    return rep


def empty_script_repr(*args): # pyflakes:ignore (unused arguments):
    return None

try:
    # Suppress scriptrepr for objects not yet having a useful string representation
    import numpy
    script_repr_reg[random.Random] = empty_script_repr
    script_repr_reg[numpy.random.RandomState] = empty_script_repr

except ImportError:
    pass # Support added only if those libraries are available


# why I have to type prefix and settings?
def function_script_repr(fn,imports,prefix,settings):
    name = fn.__name__
    module = fn.__module__
    imports.append('import %s'%module)
    return module+'.'+name

def type_script_repr(type_,imports,prefix,settings):
    module = type_.__module__
    if module!='__builtin__':
        imports.append('import %s'%module)
    return module+'.'+type_.__name__

script_repr_reg[list]=container_script_repr
script_repr_reg[tuple]=container_script_repr
script_repr_reg[FunctionType]=function_script_repr


#: If not None, the value of this Parameter will be called (using '()')
#: before every call to __db_print, and is expected to evaluate to a
#: string that is suitable for prefixing messages and warnings (such
#: as some indicator of the global state).
dbprint_prefix=None


def as_uninitialized(fn):
    """
    Decorator: call fn with the parameterized_instance's
    initialization flag set to False, then revert the flag.

    (Used to decorate Parameterized methods that must alter
    a constant Parameter.)
    """
    @wraps(fn)
    def override_initialization(parameterized_instance,*args,**kw):
        original_initialized=parameterized_instance.initialized
        parameterized_instance.initialized=False
        fn(parameterized_instance,*args,**kw)
        parameterized_instance.initialized=original_initialized
    return override_initialization



@add_metaclass(ParameterizedMetaclass)
class Parameterized(object):
    """
    Base class for named objects that support Parameters and message
    formatting.

    Automatic object naming: Every Parameterized instance has a name
    parameter.  If the user doesn't designate a name=<str> argument
    when constructing the object, the object will be given a name
    consisting of its class name followed by a unique 5-digit number.

    Automatic parameter setting: The Parameterized __init__ method
    will automatically read the list of keyword parameters.  If any
    keyword matches the name of a Parameter (see Parameter class)
    defined in the object's class or any of its superclasses, that
    parameter in the instance will get the value given as a keyword
    argument.  For example:

      class Foo(Parameterized):
         xx = Parameter(default=1)

      foo = Foo(xx=20)

    in this case foo.xx gets the value 20.

    When initializing a Parameterized instance ('foo' in the example
    above), the values of parameters can be supplied as keyword
    arguments to the constructor (using parametername=parametervalue);
    these values will override the class default values for this one
    instance.

    If no 'name' parameter is supplied, self.name defaults to the
    object's class name with a unique number appended to it.

    Message formatting: Each Parameterized instance has several
    methods for optionally printing output. This functionality is
    based on the standard Python 'logging' module; using the methods
    provided here, wraps calls to the 'logging' module's root logger
    and prepends each message with information about the instance
    from which the call was made. For more information on how to set
    the global logging level and change the default message prefix,
    see documentation for the 'logging' module.
    """

    name           = String(default=None,constant=True,doc="""
    String identifier for this object.""")


    def __init__(self,**params):
        global object_count

        # Flag that can be tested to see if e.g. constant Parameters
        # can still be set
        self.initialized=False

        self.__generate_name()

        self._setup_params(**params)
        object_count += 1

        self.initialized=True


    @classmethod
    def _add_parameter(cls, param_name,param_obj):
        """
        Add a new Parameter object into this object's class.

        Supposed to result in a Parameter equivalent to one declared
        in the class's source code.
        """
        # CEBALERT: can't we just do
        # setattr(cls,param_name,param_obj)?  The metaclass's
        # __setattr__ is actually written to handle that.  (Would also
        # need to do something about the params() cache.  That cache
        # is a pain, but it definitely improved the startup time; it
        # would be worthwhile making sure no method except for one
        # "add_param()" method has to deal with it (plus any future
        # remove_param() method.)
        type.__setattr__(cls,param_name,param_obj)
        ParameterizedMetaclass._initialize_parameter(cls,param_name,param_obj)
        # delete cached params()
        try:
            delattr(cls,'_%s__params'%cls.__name__)
        except AttributeError:
            pass


    @bothmethod
    def set_param(self_or_cls,*args,**kwargs):
        """
        For each param=value keyword argument, sets the corresponding
        parameter of this object or class to the given value.

        For backwards compatibility, also accepts
        set_param("param",value) for a single parameter value using
        positional arguments, but the keyword interface is preferred
        because it is more compact and can set multiple values.
        """

        if args:
            if len(args)==2 and not args[0] in kwargs and not kwargs:
                kwargs[args[0]]=args[1]
            else:
                raise ValueError("Invalid positional arguments for %s.set_param" %
                                 (self_or_cls.name))

        for (k,v) in kwargs.items():
            if k not in self_or_cls.params():
                raise ValueError("'%s' is not a parameter of %s"%(k,self_or_cls.name))
            setattr(self_or_cls,k,v)



    # CEBALERT: I think I've noted elsewhere the fact that we
    # sometimes have a method on Parameter that requires passing the
    # owning Parameterized instance or class, and other times we have
    # the method on Parameterized itself.  In case I haven't written
    # that down elsewhere, here it is again.  We should clean that up
    # (at least we should be consistent).

    # cebalert: it's really time to stop and clean up this bothmethod
    # stuff and repeated code in methods using it.

    # CEBALERT: note there's no state_push method on the class, so
    # dynamic parameters set on a class can't have state saved. This
    # is because, to do this, state_push() would need to be a
    # @bothmethod, but that complicates inheritance in cases where we
    # already have a state_push() method. I need to decide what to do
    # about that. (isinstance(g,Parameterized) below is used to exclude classes.)
    def state_push(self):
        """
        Save this instance's state.

        For Parameterized instances, this includes the state of
        dynamically generated values.

        Subclasses that maintain short-term state should additionally
        save and restore that state using state_push() and
        state_pop().

        Generally, this method is used by operations that need to test
        something without permanently altering the objects' state.
        """
        for pname,p in self.params().items():
            g = self.get_value_generator(pname)
            if hasattr(g,'_Dynamic_last'):
                g._saved_Dynamic_last.append(g._Dynamic_last)
                g._saved_Dynamic_time.append(g._Dynamic_time)
                # CB: not storing the time_fn: assuming that doesn't
                # change.
            elif hasattr(g,'state_push') and isinstance(g,Parameterized):
                g.state_push()

    def state_pop(self):
        """
        Restore the most recently saved state.

        See state_push() for more details.
        """
        for pname,p in self.params().items():
            g = self.get_value_generator(pname)
            if hasattr(g,'_Dynamic_last'):
                g._Dynamic_last = g._saved_Dynamic_last.pop()
                g._Dynamic_time = g._saved_Dynamic_time.pop()
            elif hasattr(g,'state_pop') and isinstance(g,Parameterized):
                g.state_pop()


    @classmethod
    def set_default(cls,param_name,value):
        """
        Set the default value of param_name.

        Equivalent to setting param_name on the class.
        """
        setattr(cls,param_name,value)


    @bothmethod
    def set_dynamic_time_fn(self_or_cls,time_fn,sublistattr=None):
        """
        Set time_fn for all Dynamic Parameters of this class or
        instance object that are currently being dynamically
        generated.

        Additionally, sets _Dynamic_time_fn=time_fn on this class or
        instance object, so that any future changes to Dynamic
        Parmeters can inherit time_fn (e.g. if a Number is changed
        from a float to a number generator, the number generator will
        inherit time_fn).

        If specified, sublistattr is the name of an attribute of this
        class or instance that contains an iterable collection of
        subobjects on which set_dynamic_time_fn should be called.  If
        the attribute sublistattr is present on any of the subobjects,
        set_dynamic_time_fn() will be called for those, too.
        """
        self_or_cls._Dynamic_time_fn = time_fn

        if isinstance(self_or_cls,type):
            a = (None,self_or_cls)
        else:
            a = (self_or_cls,)

        for n,p in self_or_cls.params().items():
            if hasattr(p,'_value_is_dynamic'):
                if p._value_is_dynamic(*a):
                    g = self_or_cls.get_value_generator(n)
                    g._Dynamic_time_fn = time_fn

        if sublistattr:
            try:
                sublist = getattr(self_or_cls,sublistattr)
            except AttributeError:
                sublist = []

            for obj in sublist:
                obj.set_dynamic_time_fn(time_fn,sublistattr)


    @as_uninitialized
    def _set_name(self,name):
        self.name=name


    @as_uninitialized
    def __generate_name(self):
        """
        Set name to a gensym formed from the object's type name and
        the object_count.
        """
        self._set_name('%s%05d' % (self.__class__.__name__ ,object_count))


    def __repr__(self):
        """
        Provide a nearly valid Python representation that could be used to recreate
        the item with its parameters, if executed in the appropriate environment.

        Returns 'classname(parameter1=x,parameter2=y,...)', listing
        all the parameters of this object.
        """
        settings = ['%s=%s' % (name,repr(val))
                    for name,val in self.get_param_values()]
        return self.__class__.__name__ + "(" + ", ".join(settings) + ")"


    def script_repr(self,imports=[],prefix="    "):
        """
        Variant of __repr__ designed for generating a runnable script.
        """
        return self.pprint(imports,prefix, unknown_value=None, qualify=True,
                           separator="\n")


    # CEBALERT: not yet properly documented
    def pprint(self, imports=None, prefix=" ", unknown_value='<?>',
               qualify=False, separator=""):
        """
        (Experimental) Pretty printed representation that may be
        evaluated with eval. See pprint() function for more details.
        """
        if imports is None:
            imports = []

        # CEBALERT: imports should just be a set rather than a list;
        # change in next release?
        imports[:] = list(set(imports))
        # Generate import statement
        mod = self.__module__
        bits = mod.split('.')
        imports.append("import %s"%mod)
        imports.append("import %s"%bits[0])

        changed_params = dict(self.get_param_values(onlychanged=script_repr_suppress_defaults))
        values = dict(self.get_param_values())
        spec = inspect.getargspec(self.__init__)
        args = spec.args[1:] if spec.args[0] == 'self' else spec.args

        if spec.defaults is not None:
            posargs = spec.args[:-len(spec.defaults)]
            kwargs = dict(zip(spec.args[-len(spec.defaults):], spec.defaults))
        else:
            posargs, kwargs = args, []

        ordering = sorted(
            sorted(changed_params.keys()), # alphanumeric tie-breaker
            key=lambda k: (- float('inf')  # No precedence is lowest possible precendence
                           if self.params(k).precedence is None
                           else self.params(k).precedence))

        arglist, keywords, processed = [], [], []
        for k in args + ordering:
            if k in processed: continue

            # Suppresses automatically generated names.
            if k == 'name' and (values[k] is not None and
                                re.match('^'+self.__class__.__name__+'[0-9]+$', values[k])):
                continue

            value = pprint(values[k], imports, prefix=prefix,settings=[],
                           unknown_value=unknown_value,
                           qualify=qualify) if k in values else None

            if value is None:
                if unknown_value is False:
                    raise Exception("%s: unknown value of %r" % (self.name,k))
                elif unknown_value is None:
                    # i.e. suppress repr
                    continue
                else:
                    value = unknown_value

            # Explicit kwarg (unchanged, known value)
            if (k in kwargs) and (k in values) and kwargs[k] == values[k]: continue

            if k in posargs:
                # value will be unknown_value unless k is a parameter
                arglist.append(value)
            elif k in kwargs or (spec.keywords is not None):
                # Explicit modified keywords or parameters in
                # precendence order (if **kwargs present)
                keywords.append('%s=%s' % (k, value))

            processed.append(k)

        qualifier = mod + '.'  if qualify else ''
        arguments = arglist + keywords + (['**%s' % spec.varargs] if spec.varargs else [])
        return qualifier + '%s(%s)' % (self.__class__.__name__,  (','+separator+prefix).join(arguments))


    def __str__(self):
        """Return a short representation of the name and class of this object."""
        return "<%s %s>" % (self.__class__.__name__,self.name)


    # CEBALERT: designed to avoid any processing unless the print
    # level is high enough, but not all callers of message(),
    # verbose(), debug(), etc are taking advantage of this. Need to
    # document, and also check other ioam projects.
    def __db_print(self,level,msg,*args,**kw):
        """
        Calls the logger returned by the get_logger() function,
        prepending the result of calling dbprint_prefix() (if any).

        See python's logging module for details.
        """
        if get_logger().isEnabledFor(level):

            if dbprint_prefix and callable(dbprint_prefix):
                prefix=dbprint_prefix() # pylint: disable-msg=E1102
            else:
                prefix=""

            get_logger().log(level, '%s%s: '+msg, prefix, self.name, *args, **kw)

    def warning(self,msg,*args,**kw):
        """
        Print msg merged with args as a warning, unless module variable
        warnings_as_exceptions is True, then raise an Exception
        containing the arguments.

        See Python's logging module for details of message formatting.
        """
        if not warnings_as_exceptions:
            global warning_count
            warning_count+=1
            self.__db_print(WARNING,msg,*args,**kw)
        else:
            raise Exception(' '.join(["Warning:",]+[str(x) for x in args]))


    def message(self,msg,*args,**kw):
        """
        Print msg merged with args as a message.

        See Python's logging module for details of message formatting.
        """
        self.__db_print(INFO,msg,*args,**kw)

    def verbose(self,msg,*args,**kw):
        """
        Print msg merged with args as a verbose message.

        See Python's logging module for details of message formatting.
        """
        self.__db_print(VERBOSE,msg,*args,**kw)

    def debug(self,msg,*args,**kw):
        """
        Print msg merged with args as a debugging statement.

        See Python's logging module for details of message formatting.
        """
        self.__db_print(DEBUG,msg,*args,**kw)

    # CEBALERT: this is a bit ugly
    def _instantiate_param(self,param_obj,dict_=None,key=None):
        # deepcopy param_obj.default into self.__dict__ (or dict_ if supplied)
        # under the parameter's _internal_name (or key if supplied)
        dict_ = dict_ or self.__dict__
        key = key or param_obj._internal_name
        param_key = (str(type(self)), param_obj._attrib_name)
        if shared_parameters._share:
            if param_key in shared_parameters._shared_cache:
                new_object = shared_parameters._shared_cache[param_key]
            else:
                new_object = copy.deepcopy(param_obj.default)
                shared_parameters._shared_cache[param_key] = new_object
        else:
            new_object = copy.deepcopy(param_obj.default)
        dict_[key]=new_object

        if isinstance(new_object,Parameterized):
            global object_count
            object_count+=1
            # CB: writes over name given to the original object;
            # should it instead keep the same name?
            new_object.__generate_name()


    @as_uninitialized
    def _setup_params(self,**params):
        """
        Initialize default and keyword parameter values.

        First, ensures that all Parameters with 'instantiate=True'
        (typically used for mutable Parameters) are copied directly
        into each object, to ensure that there is an independent copy
        (to avoid suprising aliasing errors).  Then sets each of the
        keyword arguments, warning when any of them are not defined as
        parameters.

        Constant Parameters can be set during calls to this method.
        """
        ## Deepcopy all 'instantiate=True' parameters
        # (build a set of names first to avoid redundantly instantiating
        #  a later-overridden parent class's parameter)
        params_to_instantiate = {}
        for class_ in classlist(type(self)):
            if not issubclass(class_, Parameterized):
                continue
            for (k,v) in class_.__dict__.items():
                # (avoid replacing name with the default of None)
                if isinstance(v,Parameter) and v.instantiate and k!="name":
                    params_to_instantiate[k]=v

        for p in params_to_instantiate.values():
            self._instantiate_param(p)

        ## keyword arg setting
        for name,val in params.items():
            desc = self.__class__.get_param_descriptor(name)[0] # pylint: disable-msg=E1101
            if not desc:
                self.warning("Setting non-parameter attribute %s=%s using a mechanism intended only for parameters",name,val)
            # i.e. if not desc it's setting an attribute in __dict__, not a Parameter
            setattr(self,name,val)


    def get_param_values(self,onlychanged=False):
        """
        Return a list of name,value pairs for all Parameters of this
        object.

        If onlychanged is True, will only return values that are not
        equal to the default value.
        """
        # CEB: we'd actually like to know whether a value has been
        # explicitly set on the instance, but I'm not sure that's easy
        # (would need to distinguish instantiation of default from
        # user setting of value).
        vals = []
        for name,val in self.params().items():
            value = self.get_value_generator(name)
            if not onlychanged or not all_equal(value,val.default):
                vals.append((name,value))

        vals.sort(key=itemgetter(0))
        return vals

    # CB: is there a more obvious solution than making these
    # 'bothmethod's?
    # An alternative would be to lose these methods completely and
    # make users do things via the Parameter object directly.

    # CB: is there a performance hit for doing this decoration? It
    # would show up in lissom_oo_or because separated composite uses
    # this method.
    @bothmethod
    def force_new_dynamic_value(cls_or_slf,name): # pylint: disable-msg=E0213
        """
        Force a new value to be generated for the dynamic attribute
        name, and return it.

        If name is not dynamic, its current value is returned
        (i.e. equivalent to getattr(name).
        """
        param_obj = cls_or_slf.params().get(name)

        if not param_obj:
            return getattr(cls_or_slf,name)

        cls,slf=None,None
        if isinstance(cls_or_slf,type):
            cls = cls_or_slf
        else:
            slf = cls_or_slf

        if not hasattr(param_obj,'_force'):
            return param_obj.__get__(slf,cls)
        else:
            return param_obj._force(slf,cls)


    @bothmethod
    def get_value_generator(cls_or_slf,name): # pylint: disable-msg=E0213
        """
        Return the value or value-generating object of the named
        attribute.

        For most parameters, this is simply the parameter's value
        (i.e. the same as getattr()), but Dynamic parameters have
        their value-generating object returned.
        """
        param_obj = cls_or_slf.params().get(name)

        if not param_obj:
            value = getattr(cls_or_slf,name)

        # CompositeParameter detected by being a Parameter and having 'attribs'
        elif hasattr(param_obj,'attribs'):
            value = [cls_or_slf.get_value_generator(a) for a in param_obj.attribs]

        # not a Dynamic Parameter
        elif not hasattr(param_obj,'_value_is_dynamic'):
            value = getattr(cls_or_slf,name)

        # Dynamic Parameter...
        else:
            internal_name = "_%s_param_value"%name
            if hasattr(cls_or_slf,internal_name):
                # dealing with object and it's been set on this object
                value = getattr(cls_or_slf,internal_name)
            else:
                # dealing with class or isn't set on the object
                value = param_obj.default

        return value


    @bothmethod
    def inspect_value(cls_or_slf,name): # pylint: disable-msg=E0213
        """
        Return the current value of the named attribute without modifying it.

        Same as getattr() except for Dynamic parameters, which have their
        last generated value returned.
        """
        param_obj = cls_or_slf.params().get(name)

        if not param_obj:
            value = getattr(cls_or_slf,name)
        elif hasattr(param_obj,'attribs'):
            value = [cls_or_slf.inspect_value(a) for a in param_obj.attribs]
        elif not hasattr(param_obj,'_inspect'):
            value = getattr(cls_or_slf,name)
        else:
            if isinstance(cls_or_slf,type):
                value = param_obj._inspect(None,cls_or_slf)
            else:
                value = param_obj._inspect(cls_or_slf,None)

        return value



    def print_param_values(self):
        """Print the values of all this object's Parameters."""
        for name,val in self.get_param_values():
            print('%s.%s = %s' % (self.name,name,val))


    def __getstate__(self):
        """
        Save the object's state: return a dictionary that is a shallow
        copy of the object's __dict__ and that also includes the
        object's __slots__ (if it has any).
        """
        # remind me, why is it a copy? why not just state.update(self.__dict__)?
        state = self.__dict__.copy()

        for slot in get_occupied_slots(self):
            state[slot] = getattr(self,slot)

        # Note that Parameterized object pickling assumes that
        # attributes to be saved are only in __dict__ or __slots__
        # (the standard Python places to store attributes, so that's a
        # reasonable assumption). (Additionally, class attributes that
        # are Parameters are also handled, even when they haven't been
        # instantiated - see PickleableClassAttributes.)

        return state


    def __setstate__(self,state):
        """
        Restore objects from the state dictionary to this object.

        During this process the object is considered uninitialized.
        """
        self.initialized=False
        for name,value in state.items():
            setattr(self,name,value)
        self.initialized=True


    @classmethod
    def params(cls,parameter_name=None):
        """
        Return the Parameters of this class as the
        dictionary {name: parameter_object}

        Includes Parameters from this class and its
        superclasses.
        """
        # CB: we cache the parameters because this method is called often,
        # and parameters are rarely added (and cannot be deleted)
        try:
            pdict=getattr(cls,'_%s__params'%cls.__name__)
        except AttributeError:
            paramdict = {}
            for class_ in classlist(cls):
                for name,val in class_.__dict__.items():
                    if isinstance(val,Parameter):
                        paramdict[name] = val

            # We only want the cache to be visible to the cls on which
            # params() is called, so we mangle the name ourselves at
            # runtime (if we were to mangle it now, it would be
            # _Parameterized.__params for all classes).
            setattr(cls,'_%s__params'%cls.__name__,paramdict)
            pdict= paramdict

        if parameter_name is None:
            return pdict
        else:
            return pdict[parameter_name]



    @classmethod
    def print_param_defaults(cls):
        """Print the default values of all cls's Parameters."""
        for key,val in cls.__dict__.items():
            if isinstance(val,Parameter):
                print(cls.__name__+'.'+key+ '='+ repr(val.default))


    def defaults(self):
        """
        Return {parameter_name:parameter.default} for all non-constant
        Parameters.

        Note that a Parameter for which instantiate==True has its default
        instantiated.
        """
        d = {}
        for param_name,param in self.params().items():
            if param.constant:
                pass
            elif param.instantiate:
                self._instantiate_param(param,dict_=d,key=param_name)
            else:
                d[param_name]=param.default
        return d


# CB: seems to work, but conflicts with (hides)
# Simulation(OptionalSingleton)'s __deepcopy__ method. Guess it's
# finally time to clean up that inheritance mess...

##     def __deepcopy__(self,memo=None):
##         # Deepcopy all attributes in __slots__ and __dict__, except
##         # for attributes which are ObjectSelector parameters (which
##         # are not copied at all).
##         #
##         # Should be equivalent to copy.deepcopy(self), but without copying
##         # ObjectSelector parameters.

##         if memo is None:
##             memo = {}

##         class_ = self.__class__
##         new_instance = class_.__new__(class_)

##         memo[id(self)]=new_instance

##         ## attributes are in __dict__ and __slots__
##         all_attributes = []
##         if hasattr(self,'__dict__'):
##             all_attributes+=self.__dict__.keys()
##         if hasattr(self,'__slots__'):
##             all_attributes+=self.__slots__
##         attributes_to_copy = all_attributes[:]

##         ## remove ObjectSelector parameters from list to be copied
##         for param_name,param_obj in self.params().items():
##             internal_param_name = "_%s_param_value"%param_name
##             # (if param_obj has 'objects' slot, it's assumed to be an ObjectSelector)
##             if hasattr(param_obj,'objects') and internal_param_name in attributes_to_copy:
##                 attributes_to_copy.remove(internal_param_name)

##         for attr in all_attributes:
##             if attr in attributes_to_copy:
##                 obj = copy.deepcopy(getattr(self,attr),memo)
##             else:
##                 obj = getattr(self,attr)
##             setattr(new_instance,attr,obj)

##         return new_instance




def print_all_param_defaults():
    """Print the default values for all imported Parameters."""
    print("_______________________________________________________________________________")
    print("")
    print("                           Parameter Default Values")
    print("")
    classes = descendents(Parameterized)
    classes.sort(key=lambda x:x.__name__)
    for c in classes:
        c.print_param_defaults()
    print("_______________________________________________________________________________")




# Note that with Python 2.6, a fn's **args no longer has to be a
# dictionary. This might allow us to use a decorator to simplify using
# ParamOverrides (if that does indeed make them simpler to use).
# http://docs.python.org/whatsnew/2.6.html
class ParamOverrides(dict):
    """
    A dictionary that returns the attribute of a specified object if
    that attribute is not present in itself.

    Used to override the parameters of an object.
    """

    # NOTE: Attribute names of this object block parameters of the
    # same name, so all attributes of this object should have names
    # starting with an underscore (_).

    def __init__(self,overridden,dict_,allow_extra_keywords=False):
        """

        If allow_extra_keywords is False, then all keys in the
        supplied dict_ must match parameter names on the overridden
        object (otherwise a warning will be printed).

        If allow_extra_keywords is True, then any items in the
        supplied dict_ that are not also parameters of the overridden
        object will be available via the extra_keywords() method.
        """
        # we'd like __init__ to be fast because it's going to be
        # called a lot. What's the fastest way to move the existing
        # params dictionary into this one? Would
        #  def __init__(self,overridden,**kw):
        #      ...
        #      dict.__init__(self,**kw)
        # be faster/easier to use?
        self._overridden = overridden
        dict.__init__(self,dict_)

        if allow_extra_keywords:
            self._extra_keywords=self._extract_extra_keywords(dict_)
        else:
            self._check_params(dict_)

    def extra_keywords(self):
        """
        Return a dictionary containing items from the originally
        supplied dict_ whose names are not parameters of the
        overridden object.
        """
        return self._extra_keywords

    def param_keywords(self):
        """
        Return a dictionary containing items from the originally
        supplied dict_ whose names are parameters of the
        overridden object (i.e. not extra keywords/parameters).
        """
        return dict((key, self[key]) for key in self if key not in self.extra_keywords())

    def __missing__(self,name):
        # Return 'name' from the overridden object
        return getattr(self._overridden,name)

    def __repr__(self):
        # As dict.__repr__, but indicate the overridden object
        return dict.__repr__(self)+" overriding params from %s"%repr(self._overridden)

    def __getattr__(self,name):
        # Provide 'dot' access to entries in the dictionary.
        # (This __getattr__ method is called only if 'name' isn't an
        # attribute of self.)
        return self.__getitem__(name)

    def __setattr__(self,name,val):
        # Attributes whose name starts with _ are set on self (as
        # normal), but all other attributes are inserted into the
        # dictionary.
        if not name.startswith('_'):
            self.__setitem__(name,val)
        else:
            dict.__setattr__(self,name,val)

    def _check_params(self,params):
        """
        Print a warning if params contains something that is not a
        Parameter of the overridden object.
        """
        overridden_object_params = list(self._overridden.params().keys())
        for item in params:
            if item not in overridden_object_params:
                self.warning("'%s' will be ignored (not a Parameter).",item)

    def _extract_extra_keywords(self,params):
        """
        Return any items in params that are not also
        parameters of the overridden object.
        """
        extra_keywords = {}
        overridden_object_params = self._overridden.params()
        for name,val in params.items():
            if name not in overridden_object_params:
                extra_keywords[name]=val
                # CEBALERT: should we remove name from params
                # (i.e. del params[name]) so that it's only available
                # via extra_keywords()?
        return extra_keywords


# Helper function required by ParameterizedFunction.__reduce__
def _new_parameterized(cls):
    return Parameterized.__new__(cls)


class ParameterizedFunction(Parameterized):
    """
    Acts like a Python function, but with arguments that are Parameters.

    Implemented as a subclass of Parameterized that, when instantiated,
    automatically invokes __call__ and returns the result, instead of
    returning an instance of the class.

    To obtain an instance of this class, call instance().
    """
    __abstract = True

    # CEBALERT: shouldn't this have come from a parent class
    # somewhere?
    def __str__(self):
        return self.__class__.__name__+"()"

    @bothmethod
    def instance(self_or_cls,**params):
        """
        Return an instance of this class, copying parameters from any
        existing instance provided.
        """

        if isinstance (self_or_cls,ParameterizedMetaclass):
            cls = self_or_cls
        else:
            p = params
            params = dict(self_or_cls.get_param_values())
            params.update(p)
            params.pop('name')
            cls = self_or_cls.__class__

        inst=Parameterized.__new__(cls)
        Parameterized.__init__(inst,**params)
        if 'name' in params:  inst.__name__ = params['name']
        else:                 inst.__name__ = self_or_cls.name
        return inst

    def __new__(class_,*args,**params):
        # Create and __call__() an instance of this class.
        inst = class_.instance()
        inst._set_name(class_.__name__)
        return inst.__call__(*args,**params)

    def __call__(self,*args,**kw):
        raise NotImplementedError("Subclasses must implement __call__.")

    def __reduce__(self):
        # Control reconstruction (during unpickling and copying):
        # ensure that ParameterizedFunction.__new__ is skipped
        state = ParameterizedFunction.__getstate__(self)
        # CB: here it's necessary to use a function defined at the
        # module level rather than Parameterized.__new__ directly
        # because otherwise pickle will find .__new__'s module to be
        # __main__. Pretty obscure aspect of pickle.py, or a bug?
        return (_new_parameterized,(self.__class__,),state)

    def script_repr(self,imports=[],prefix="    "):
        """
        Same as Parameterized.script_repr, except that X.classname(Y
        is replaced with X.classname.instance(Y
        """
        return self.pprint(imports,prefix,unknown_value='',qualify=True,
                           separator="\n")


    def pprint(self, imports=None, prefix="\n    ",unknown_value='<?>',
               qualify=False, separator=""):
        """
        Same as Parameterized.pprint, except that X.classname(Y
        is replaced with X.classname.instance(Y
        """
        r = Parameterized.pprint(self,imports,prefix,
                                 unknown_value=unknown_value,
                                 qualify=qualify,separator=separator)
        classname=self.__class__.__name__
        return r.replace(".%s("%classname,".%s.instance("%classname)




# CBENHANCEMENT: should be able to remove overridable_property when we
# switch to Python 2.6:
# "Properties now have three attributes, getter, setter and deleter,
# that are decorators providing useful shortcuts for adding a getter,
# setter or deleter function to an existing property."
# http://docs.python.org/whatsnew/2.6.html

# Renamed & documented version of OProperty from
# infinitesque.net/articles/2005/enhancing%20Python's%20property.xhtml
class overridable_property(object):
    """
    The same as Python's "property" attribute, but allows the accessor
    methods to be overridden in subclasses.
    """
    # Delays looking up the accessors until they're needed, rather
    # than finding them when the class is first created.

    # Based on the emulation of PyProperty_Type() in Objects/descrobject.c

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        if self.fget.__name__ == '<lambda>' or not self.fget.__name__:
            return self.fget(obj)
        else:
            return getattr(obj, self.fget.__name__)()

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        if self.fset.__name__ == '<lambda>' or not self.fset.__name__:
            self.fset(obj, value)
        else:
            getattr(obj, self.fset.__name__)(value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        if self.fdel.__name__ == '<lambda>' or not self.fdel.__name__:
            self.fdel(obj)
        else:
            getattr(obj, self.fdel.__name__)()
