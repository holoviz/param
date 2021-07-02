"""
Generic support for objects with full-featured Parameters and
messaging.
"""

import copy
import re
import sys
import inspect
import random
import numbers
import operator

# Allow this file to be used standalone if desired, albeit without JSON serialization
try:
    from . import serializer
except ImportError:
    serializer = None


from collections import defaultdict, namedtuple, OrderedDict
from functools import partial, wraps, reduce
from operator import itemgetter,attrgetter
from types import FunctionType

import logging
from contextlib import contextmanager
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

try:
    # In case the optional ipython module is unavailable
    from .ipython import ParamPager
    param_pager = ParamPager(metaclass=True)  # Generates param description
except:
    param_pager = None

basestring = basestring if sys.version_info[0]==2 else str # noqa: it is defined

VERBOSE = INFO - 1
logging.addLevelName(VERBOSE, "VERBOSE")

# Get the appropriate logging.Logger instance. If `logger` is None, a
# logger named `"param"` will be instantiated. If `name` is set, a descendant
# logger with the name ``"param.<name>"`` is returned (or
# ``logger.name + ".<name>"``)
logger = None
def get_logger(name=None):
    if logger is None:
        root_logger = logging.getLogger('param')
        if not root_logger.handlers:
            root_logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                fmt='%(levelname)s:%(name)s: %(message)s')
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
    else:
        root_logger = logger
    if name is None:
        return root_logger
    else:
        return logging.getLogger(root_logger.name + '.' + name)


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


@contextmanager
def batch_watch(parameterized, enable=True, run=True):
    """
    Context manager to batch watcher events on a parameterized object.
    The context manager will queue any events triggered by setting a
    parameter on the supplied parameterized object and dispatch them
    all at once when the context manager exits. If run=False the
    queued events are not dispatched and should be processed manually.
    """
    BATCH_WATCH = parameterized.param._BATCH_WATCH
    parameterized.param._BATCH_WATCH = enable or parameterized.param._BATCH_WATCH
    try:
        yield
    finally:
        parameterized.param._BATCH_WATCH = BATCH_WATCH
        if run and not BATCH_WATCH:
            parameterized.param._batch_call_watchers()


@contextmanager
def edit_constant(parameterized):
    """
    Temporarily set parameters on Parameterized object to constant=False
    to allow editing them.
    """
    params = parameterized.param.objects('existing').values()
    constants = [p.constant for p in params]
    for p in params:
        p.constant = False
    try:
        yield
    except:
        raise
    finally:
        for (p, const) in zip(params, constants):
            p.constant = const


@contextmanager
def discard_events(parameterized):
    """
    Context manager that discards any events within its scope
    triggered on the supplied parameterized object.
    """
    batch_watch = parameterized.param._BATCH_WATCH
    parameterized.param._BATCH_WATCH = True
    watchers, events = (list(parameterized.param._watchers),
                        list(parameterized.param._events))
    try:
        yield
    except:
        raise
    finally:
        parameterized.param._BATCH_WATCH = batch_watch
        parameterized.param._watchers = watchers
        parameterized.param._events = events


# External components can register an async executor which will run
# async functions
async_executor = None


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


def _getattrr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return reduce(_getattr, [obj] + attr.split('.'))


# (thought I was going to have a few decorators following this pattern)
def accept_arguments(f):
    @wraps(f)
    def _f(*args, **kwargs):
        return lambda actual_f: f(actual_f, *args, **kwargs)
    return _f


def no_instance_params(cls):
    """
    Disables instance parameters on the class
    """
    cls._disable_instance__params = True
    return cls


def iscoroutinefunction(function):
    """
    Whether the function is an asynchronous coroutine function.
    """
    if not hasattr(inspect, 'iscoroutinefunction'):
        return False
    return inspect.iscoroutinefunction(function)


def instance_descriptor(f):
    # If parameter has an instance Parameter delegate setting
    def _f(self, obj, val):
        instance_param = getattr(obj, '_instance__params', {}).get(self.name)
        if instance_param is not None and self is not instance_param:
            instance_param.__set__(obj, val)
            return
        return f(self, obj, val)
    return _f


def get_method_owner(method):
    """
    Gets the instance that owns the supplied method
    """
    if not inspect.ismethod(method):
        return None
    if isinstance(method, partial):
        method = method.func
    return method.__self__ if sys.version_info.major >= 3 else method.im_self


@accept_arguments
def depends(func, *dependencies, **kw):
    """
    Annotates a function or Parameterized method to express its
    dependencies.  The specified dependencies can be either be
    Parameter instances or if a method is supplied they can be
    defined as strings referring to Parameters of the class,
    or Parameters of subobjects (Parameterized objects that are
    values of this object's parameters).  Dependencies can either be
    on Parameter values, or on other metadata about the Parameter.
    """

    # python3 would allow kw-only args
    # (i.e. "func,*dependencies,watch=False" rather than **kw and the check below)
    watch = kw.pop("watch",False)

    @wraps(func)
    def _depends(*args,**kw):
        return func(*args,**kw)

    deps = list(dependencies)+list(kw.values())
    string_specs = False
    for dep in deps:
        if isinstance(dep, basestring):
            string_specs = True
        elif not isinstance(dep, Parameter):
            raise ValueError('The depends decorator only accepts string '
                             'types referencing a parameter or parameter '
                             'instances, found %s type instead.' %
                             type(dep).__name__)
        elif not (isinstance(dep.owner, Parameterized) or
                  (isinstance(dep.owner, ParameterizedMetaclass))):
            owner = 'None' if dep.owner is None else '%s class' % type(dep.owner).__name__
            raise ValueError('Parameters supplied to the depends decorator, '
                             'must be bound to a Parameterized class or '
                             'instance not %s.' % owner)

    if (any(isinstance(dep, Parameter) for dep in deps) and
        any(isinstance(dep, basestring) for dep in deps)):
        raise ValueError('Dependencies must either be defined as strings '
                         'referencing parameters on the class defining '
                         'the decorated method or as parameter instances. '
                         'Mixing of string specs and parameter instances '
                         'is not supported.')
    elif string_specs and kw:
        raise AssertionError('Supplying keywords to the decorated method '
                             'or function is not supported when referencing '
                             'parameters by name.')

    if not string_specs and watch: # string_specs case handled elsewhere (later), in Parameterized.__init__
        def cb(*events):
            args = (getattr(dep.owner, dep.name) for dep in dependencies)
            dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw.items()}
            return func(*args, **dep_kwargs)

        grouped = defaultdict(list)
        for dep in deps:
            grouped[id(dep.owner)].append(dep)
        for group in grouped.values():
            group[0].owner.param.watch(cb, [dep.name for dep in group])

    _dinfo = getattr(func, '_dinfo', {})
    _dinfo.update({'dependencies': dependencies,
                   'kw': kw, 'watch': watch})

    _depends._dinfo = _dinfo

    return _depends


@accept_arguments
def output(func, *output, **kw):
    """
    output allows annotating a method on a Parameterized class to
    declare that it returns an output of a specific type. The outputs
    of a Parameterized class can be queried using the
    Parameterized.param.outputs method. By default the output will
    inherit the method name but a custom name can be declared by
    expressing the Parameter type using a keyword argument. Declaring
    multiple return types using keywords is only supported in Python >= 3.6.

    The simplest declaration simply declares the method returns an
    object without any type guarantees, e.g.:

      @output()

    If a specific parameter type is specified this is a declaration
    that the method will return a value of that type, e.g.:

      @output(param.Number())

    To override the default name of the output the type may be declared
    as a keyword argument, e.g.:

      @output(custom_name=param.Number())

    Multiple outputs may be declared using keywords mapping from
    output name to the type for Python >= 3.6 or using tuples of the
    same format, which is supported for earlier versions, i.e. these
    two declarations are equivalent:

      @output(number=param.Number(), string=param.String())

      @output(('number', param.Number()), ('string', param.String()))

    output also accepts Python object types which will be upgraded to
    a ClassSelector, e.g.:

      @output(int)
    """
    if output:
        outputs = []
        for i, out in enumerate(output):
            i = i if len(output) > 1 else None
            if isinstance(out, tuple) and len(out) == 2 and isinstance(out[0], str):
                outputs.append(out+(i,))
            elif isinstance(out, str):
                outputs.append((out, Parameter(), i))
            else:
                outputs.append((None, out, i))
    elif kw:
        py_major = sys.version_info.major
        py_minor = sys.version_info.minor
        if (py_major < 3 or (py_major == 3 and py_minor < 6)) and len(kw) > 1:
            raise ValueError('Multiple output declaration using keywords '
                             'only supported in Python >= 3.6.')
          # (requires keywords to be kept ordered, which was not true in previous versions)
        outputs = [(name, otype, i if len(kw) > 1 else None)
                   for i, (name, otype) in enumerate(kw.items())]
    else:
        outputs = [(None, Parameter(), None)]

    names, processed = [], []
    for name, otype, i in outputs:
        if isinstance(otype, type):
            if issubclass(otype, Parameter):
                otype = otype()
            else:
                from .import ClassSelector
                otype = ClassSelector(class_=otype)
        elif isinstance(otype, tuple) and all(isinstance(t, type) for t in otype):
            from .import ClassSelector
            otype = ClassSelector(class_=otype)
        if not isinstance(otype, Parameter):
            raise ValueError('output type must be declared with a Parameter class, '
                             'instance or a Python object type.')
        processed.append((name, otype, i))
        names.append(name)

    if len(set(names)) != len(names):
        raise ValueError('When declaring multiple outputs each value '
                         'must be unique.')

    _dinfo = getattr(func, '_dinfo', {})
    _dinfo.update({'outputs': processed})

    @wraps(func)
    def _output(*args,**kw):
        return func(*args,**kw)

    _output._dinfo = _dinfo

    return _output


def _params_depended_on(minfo):
    params = []
    dinfo = getattr(minfo.method,"_dinfo", {})
    for d in dinfo.get('dependencies', list(minfo.cls.param)):
        things = (minfo.inst or minfo.cls).param._spec_to_obj(d)
        for thing in things:
            if isinstance(thing,PInfo):
                params.append(thing)
            else:
                params += _params_depended_on(thing)
    return params


def _m_caller(self, n):
    function = getattr(self, n)
    if iscoroutinefunction(function):
        import asyncio
        @asyncio.coroutine
        def caller(*events):
            yield function()
    else:
        def caller(*events):
            return function()
    caller._watcher_name = n
    return caller


PInfo = namedtuple("PInfo","inst cls name pobj what")
MInfo = namedtuple("MInfo","inst cls name method")
Event = namedtuple("Event","what name obj cls old new type")
Watcher = namedtuple("Watcher","inst cls fn mode onlychanged parameter_names what queued")

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
    __slots__ = ['name', '_internal_name', 'default', 'doc',
                 'precedence', 'instantiate', 'constant', 'readonly',
                 'pickle_default_value', 'allow_None', 'per_instance',
                 'watchers', 'owner', '_label']

    # Note: When initially created, a Parameter does not know which
    # Parameterized class owns it, nor does it know its names
    # (attribute name, internal name). Once the owning Parameterized
    # class is created, owner, name, and _internal_name are
    # set.

    _serializers = {'json': serializer.JSONSerialization}

    def __init__(self,default=None, doc=None, label=None, precedence=None,  # pylint: disable-msg=R0913
                 instantiate=False, constant=False, readonly=False,
                 pickle_default_value=True, allow_None=False,
                 per_instance=True):

        """Initialize a new Parameter object and store the supplied attributes:

        default: the owning class's value for the attribute represented
        by this Parameter, which can be overridden in an instance.

        doc: docstring explaining what this parameter represents.

        label: optional text label to be used when this Parameter is
        shown in a listing. If no label is supplied, the attribute name
        for this parameter in the owning Parameterized object is used.

        precedence: a numeric value, usually in the range 0.0 to 1.0,
        which allows the order of Parameters in a class to be defined in
        a listing or e.g. in GUI menus. A negative precedence indicates
        a parameter that should be hidden in such listings.

        instantiate: controls whether the value of this Parameter will
        be deepcopied when a Parameterized object is instantiated (if
        True), or if the single default value will be shared by all
        Parameterized instances (if False). For an immutable Parameter
        value, it is best to leave instantiate at the default of
        False, so that a user can choose to change the value at the
        Parameterized instance level (affecting only that instance) or
        at the Parameterized class or superclass level (affecting all
        existing and future instances of that class or superclass). For
        a mutable Parameter value, the default of False is also appropriate
        if you want all instances to share the same value state, e.g. if
        they are each simply referring to a single global object like
        a singleton. If instead each Parameterized should have its own
        independently mutable value, instantiate should be set to
        True, but note that there is then no simple way to change the
        value of this Parameter at the class or superclass level,
        because each instance, once created, will then have an
        independently instantiated value.

        constant: if true, the Parameter value can be changed only at
        the class level or in a Parameterized constructor call. The
        value is otherwise constant on the Parameterized instance,
        once it has been constructed.

        readonly: if true, the Parameter value cannot ordinarily be
        changed by setting the attribute at the class or instance
        levels at all. The value can still be changed in code by
        temporarily overriding the value of this slot and then
        restoring it, which is useful for reporting values that the
        _user_ should never change but which do change during code
        execution.

        pickle_default_value: whether the default value should be
        pickled. Usually, you would want the default value to be pickled,
        but there are rare cases where that would not be the case (e.g.
        for file search paths that are specific to a certain system).

        per_instance: whether a separate Parameter instance will be
        created for every Parameterized instance. True by default.
        If False, all instances of a Parameterized class will share
        the same Parameter object, including all validation
        attributes (bounds, etc.). See also instantiate, which is
        conceptually similar but affects the Parameter value rather
        than the Parameter object.

        allow_None: if True, None is accepted as a valid value for
        this Parameter, in addition to any other values that are
        allowed. If the default value is defined as None, allow_None
        is set to True automatically.

        default, doc, and precedence all default to None, which allows
        inheritance of Parameter slots (attributes) from the owning-class'
        class hierarchy (see ParameterizedMetaclass).
        """

        self.name = None
        self.owner = None
        self.precedence = precedence
        self.default = default
        self.doc = doc
        self.constant = constant or readonly # readonly => constant
        self.readonly = readonly
        self._label = label
        self._internal_name = None
        self._set_instantiate(instantiate)
        self.pickle_default_value = pickle_default_value
        self.allow_None = (default is None or allow_None)
        self.watchers = {}
        self.per_instance = per_instance

    @classmethod
    def serialize(cls, value):
        "Given the parameter value, return a Python value suitable for serialization"
        return value

    @classmethod
    def deserialize(cls, value):
        "Given a serializable Python value, return a value that the parameter can be set to"
        return value

    def schema(self, safe=False, subset=None, mode='json'):
        if serializer is None:
            raise ImportError('Cannot import serializer.py needed to generate schema')
        if mode not in  self._serializers:
            raise KeyError('Mode %r not in available serialization formats %r'
                           % (mode, list(self._serializers.keys())))
        return self._serializers[mode].parameter_schema(self.__class__.__name__, self,
                                                        safe=safe, subset=subset)

    @property
    def label(self):
        if self.name and self._label is None:
            return label_formatter(self.name)
        else:
            return self._label

    @label.setter
    def label(self, val):
        self._label = val

    def _set_instantiate(self,instantiate):
        """Constant parameters must be instantiated."""
        # CB: instantiate doesn't actually matter for read-only
        # parameters, since they can't be set even on a class.  But
        # this avoids needless instantiation.
        if self.readonly:
            self.instantiate = False
        else:
            self.instantiate = instantiate or self.constant # pylint: disable-msg=W0201

    def __setattr__(self, attribute, value):
        implemented = (attribute != "default" and hasattr(self, 'watchers') and attribute in self.watchers)
        slot_attribute = attribute in self.__slots__
        try:
            old = getattr(self, attribute) if implemented else NotImplemented
            if slot_attribute:
                self._on_set(attribute, old, value)
        except AttributeError as e:
            if slot_attribute:
                # If Parameter slot is defined but an AttributeError was raised
                # we are in __setstate__ and watchers should not be triggered
                old = NotImplemented
            else:
                raise e

        super(Parameter, self).__setattr__(attribute, value)

        if old is NotImplemented:
            return

        event = Event(what=attribute,name=self.name, obj=None, cls=self.owner,
                      old=old, new=value, type=None)
        for watcher in self.watchers[attribute]:
            self.owner.param._call_watcher(watcher, event)
        if not self.owner.param._BATCH_WATCH:
            self.owner.param._batch_call_watchers()

    def _on_set(self, attribute, old, value):
        """
        Can be overridden on subclasses to handle changes when parameter
        attribute is set.
        """

    def __get__(self, obj, objtype): # pylint: disable-msg=W0613
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

    @instance_descriptor
    def __set__(self, obj, val):
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

        # ALERT: Deprecated Number set_hook called here to avoid duplicating
        #        setter, should be removed in 2.0
        if hasattr(self, 'set_hook'):
            val = self.set_hook(obj,val)

        self._validate(val)

        _old = NotImplemented
        # NB: obj can be None (when __set__ called for a
        # Parameterized class)
        if self.constant or self.readonly:
            if self.readonly:
                raise TypeError("Read-only parameter '%s' cannot be modified" % self.name)
            elif obj is None:
                _old = self.default
                self.default = val
            elif not obj.initialized:
                _old = obj.__dict__.get(self._internal_name, self.default)
                obj.__dict__[self._internal_name] = val
            else:
                _old = obj.__dict__.get(self._internal_name, self.default)
                if val is not _old:
                    raise TypeError("Constant parameter '%s' cannot be modified"%self.name)
        else:
            if obj is None:
                _old = self.default
                self.default = val
            else:
                _old = obj.__dict__.get(self._internal_name,self.default)
                obj.__dict__[self._internal_name] = val

        self._post_setter(obj, val)

        if obj is None:
            watchers = self.watchers.get("value")
        elif hasattr(obj, '_param_watchers') and self.name in obj._param_watchers:
            watchers = obj._param_watchers[self.name].get('value')
            if watchers is None:
                watchers = self.watchers.get("value")
        else:
            watchers = None

        obj = self.owner if obj is None else obj
        if obj is None or not watchers:
            return

        event = Event(what='value',name=self.name, obj=obj, cls=self.owner,
                      old=_old, new=val, type=None)
        for watcher in watchers:
            obj.param._call_watcher(watcher, event)
        if not obj.param._BATCH_WATCH:
            obj.param._batch_call_watchers()

    def _validate_value(self, value, allow_None):
        """Implements validation for parameter value"""

    def _validate(self, val):
        """Implements validation for the parameter value and attributes"""
        self._validate_value(val, self.allow_None)

    def _post_setter(self, obj, val):
        """Called after the parameter value has been validated and set"""

    def __delete__(self,obj):
        raise TypeError("Cannot delete '%s': Parameters deletion not allowed." % self.name)

    def _set_names(self, attrib_name):
        if None not in (self.owner, self.name) and attrib_name != self.name:
            raise AttributeError('The %s parameter %r has already been '
                                 'assigned a name by the %s class, '
                                 'could not assign new name %r. Parameters '
                                 'may not be shared by multiple classes; '
                                 'ensure that you create a new parameter '
                                 'instance for each new class.'
                                 % (type(self).__name__, self.name,
                                    self.owner.name, attrib_name))
        self.name = attrib_name
        self._internal_name = "_%s_param_value" % attrib_name

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

        # Handle renamed slots introduced for instance params
        if '_attrib_name' in state:
            state['name'] = state.pop('_attrib_name')
        if '_owner' in state:
            state['owner'] = state.pop('_owner')
        if 'watchers' not in state:
            state['watchers'] = {}
        if 'per_instance' not in state:
            state['per_instance'] = False
        if '_label' not in state:
            state['_label'] = None

        for (k,v) in state.items():
            setattr(self,k,v)


# Define one particular type of Parameter that is used in this file
class String(Parameter):
    """
    A String Parameter, with a default value and optional regular expression (regex) matching.

    Example of using a regex to implement IPv4 address matching::

      class IPAddress(String):
        '''IPv4 address as a string (dotted decimal notation)'''
       def __init__(self, default="0.0.0.0", allow_None=False, **kwargs):
           ip_regex = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
           super(IPAddress, self).__init__(default=default, regex=ip_regex, **kwargs)

    """

    __slots__ = ['regex']

    def __init__(self, default="", regex=None, allow_None=False, **kwargs):
        super(String, self).__init__(default=default, allow_None=allow_None, **kwargs)
        self.regex = regex
        self.allow_None = (default is None or allow_None)
        self._validate(default)

    def _validate_regex(self, val, regex):
        if (val is None and self.allow_None):
            return
        if regex is not None and re.match(regex, val) is None:
            raise ValueError("String parameter %r value %r does not match regex %r."
                             % (self.name, val, regex))

    def _validate_value(self, val, allow_None):
        if allow_None and val is None:
            return
        if not isinstance(val, basestring):
            raise ValueError("String parameter %r only takes a string value, "
                             "not value of type %s." % (self.name, type(val)))

    def _validate(self, val):
        self._validate_value(val, self.allow_None)
        self._validate_regex(val, self.regex)


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


def as_uninitialized(fn):
    """
    Decorator: call fn with the parameterized_instance's
    initialization flag set to False, then revert the flag.

    (Used to decorate Parameterized methods that must alter
    a constant Parameter.)
    """
    @wraps(fn)
    def override_initialization(self_,*args,**kw):
        parameterized_instance = self_.self
        original_initialized = parameterized_instance.initialized
        parameterized_instance.initialized = False
        fn(parameterized_instance, *args, **kw)
        parameterized_instance.initialized = original_initialized
    return override_initialization


class Comparator(object):
    """
    Comparator defines methods for determining whether two objects
    should be considered equal. It works by registering custom
    comparison functions, which may either be registed by type or with
    a predicate function. If no matching comparison can be found for
    the two objects the comparison will return False.

    If registered by type the Comparator will check whether both
    objects are of that type and apply the comparison. If the equality
    function is instead registered with a function it will call the
    function with each object individually to check if the comparison
    applies. This is useful for defining comparisons for objects
    without explicitly importing them.

    To use the Comparator simply call the is_equal function.
    """

    equalities = {
        numbers.Number: operator.eq,
        basestring: operator.eq,
        bytes: operator.eq,
        type(None): operator.eq
    }

    @classmethod
    def is_equal(cls, obj1, obj2):
        for eq_type, eq in cls.equalities.items():
            if ((isinstance(eq_type, FunctionType)
                 and eq_type(obj1) and eq_type(obj2))
                or (isinstance(obj1, eq_type) and isinstance(obj2, eq_type))):
                return eq(obj1, obj2)
        if isinstance(obj2, (list, set, tuple)):
            return cls.compare_iterator(obj1, obj2)
        elif isinstance(obj2, dict):
            return cls.compare_mapping(obj1, obj2)
        return False

    @classmethod
    def compare_iterator(cls, obj1, obj2):
        if type(obj1) != type(obj2) or len(obj1) != len(obj2):
            return False
        for o1, o2 in zip(obj1, obj2):
            if not cls.is_equal(o1, o2):
                return False
        return True

    @classmethod
    def compare_mapping(cls, obj1, obj2):
        if type(obj1) != type(obj2) or len(obj1) != len(obj2): return False
        for k in obj1:
            if k in obj2:
                if not cls.is_equal(obj1[k], obj2[k]):
                    return False
            else:
                return False
        return True


class Parameters(object):
    """Object that holds the namespace and implementation of Parameterized
    methods as well as any state that is not in __slots__ or the
    Parameters themselves.

    Exists at both the metaclass level (instantiated by the metaclass)
    and at the instance level. Can contain state specific to either the
    class or the instance as necessary.
    """

    _disable_stubs = False # Flag used to disable stubs in the API1 tests
                          # None for no action, True to raise and False to warn.

    def __init__(self_, cls, self=None):
        """
        cls is the Parameterized class which is always set.
        self is the instance if set.
        """
        self_.cls = cls
        self_.self = self

    @property
    def _BATCH_WATCH(self_):
        return self_.self_or_cls._parameters_state['BATCH_WATCH']

    @_BATCH_WATCH.setter
    def _BATCH_WATCH(self_, value):
        self_.self_or_cls._parameters_state['BATCH_WATCH'] = value

    @property
    def _TRIGGER(self_):
        return self_.self_or_cls._parameters_state['TRIGGER']

    @_TRIGGER.setter
    def _TRIGGER(self_, value):
        self_.self_or_cls._parameters_state['TRIGGER'] = value

    @property
    def _events(self_):
        return self_.self_or_cls._parameters_state['events']

    @_events.setter
    def _events(self_, value):
        self_.self_or_cls._parameters_state['events'] = value

    @property
    def _watchers(self_):
        return self_.self_or_cls._parameters_state['watchers']

    @_watchers.setter
    def _watchers(self_, value):
        self_.self_or_cls._parameters_state['watchers'] = value

    @property
    def self_or_cls(self_):
        return self_.cls if self_.self is None else self_.self

    def __setstate__(self, state):
        # Set old parameters state on Parameterized._parameters_state
        self_or_cls = state.get('self', state.get('cls'))
        for k in self_or_cls._parameters_state:
            key = '_'+k
            if key in state:
                self_or_cls._parameters_state[k] = state.pop(key)
        for k, v in state.items():
            setattr(self, k, v)

    def __getitem__(self_, key):
        """
        Returns the class or instance parameter
        """
        inst = self_.self
        parameters = self_.objects(False) if inst is None else inst.param.objects(False)
        p = parameters[key]
        if (inst is not None and getattr(inst, 'initialized', False) and p.per_instance and
            not getattr(inst, '_disable_instance__params', False)):
            if key not in inst._instance__params:
                try:
                    # Do not copy watchers on class parameter
                    watchers = p.watchers
                    p.watchers = {}
                    p = copy.copy(p)
                except:
                    raise
                finally:
                    p.watchers = {k: list(v) for k, v in watchers.items()}
                p.owner = inst
                inst._instance__params[key] = p
            else:
                p = inst._instance__params[key]
        return p


    def __dir__(self_):
        """
        Adds parameters to dir
        """
        return super(Parameters, self_).__dir__() + list(self_)


    def __iter__(self_):
        """
        Iterates over the parameters on this object.
        """
        for p in self_.objects(instance=False):
            yield p


    def __contains__(self_, param):
        return param in list(self_)


    def __getattr__(self_, attr):
        """
        Extends attribute access to parameter objects.
        """
        cls = self_.__dict__.get('cls')
        if cls is None: # Class not initialized
            raise AttributeError

        try:
            params = list(getattr(cls, '_%s__params' % cls.__name__))
        except AttributeError:
            params = [n for class_ in classlist(cls) for n, v in class_.__dict__.items()
                      if isinstance(v, Parameter)]

        if attr in params:
            return self_.__getitem__(attr)
        elif self_.self is None:
            raise AttributeError("type object '%s.param' has no attribute %r" %
                                 (self_.cls.__name__, attr))
        else:
            raise AttributeError("'%s.param' object has no attribute %r" %
                                 (self_.cls.__name__, attr))


    @as_uninitialized
    def _set_name(self_, name):
        self = self_.param.self
        self.name=name


    @as_uninitialized
    def _generate_name(self_):
        self = self_.param.self
        self.param._set_name('%s%05d' % (self.__class__.__name__ ,object_count))


    @as_uninitialized
    def _setup_params(self_,**params):
        """
        Initialize default and keyword parameter values.

        First, ensures that all Parameters with 'instantiate=True'
        (typically used for mutable Parameters) are copied directly
        into each object, to ensure that there is an independent copy
        (to avoid surprising aliasing errors).  Then sets each of the
        keyword arguments, warning when any of them are not defined as
        parameters.

        Constant Parameters can be set during calls to this method.
        """
        self = self_.param.self
        ## Deepcopy all 'instantiate=True' parameters
        # (build a set of names first to avoid redundantly instantiating
        #  a later-overridden parent class's parameter)
        params_to_instantiate = {}
        for class_ in classlist(type(self)):
            if not issubclass(class_, Parameterized):
                continue
            for (k, v) in class_.param._parameters.items():
                # (avoid replacing name with the default of None)
                if v.instantiate and k != "name":
                    params_to_instantiate[k] = v

        for p in params_to_instantiate.values():
            self.param._instantiate_param(p)

        ## keyword arg setting
        for name, val in params.items():
            desc = self.__class__.get_param_descriptor(name)[0] # pylint: disable-msg=E1101
            if not desc:
                self.param.warning("Setting non-parameter attribute %s=%s using a mechanism intended only for parameters", name, val)
            # i.e. if not desc it's setting an attribute in __dict__, not a Parameter
            setattr(self, name, val)

    @classmethod
    def deprecate(cls, fn):
        """
        Decorator to issue warnings for API moving onto the param
        namespace and to add a docstring directing people to the
        appropriate method.
        """
        def inner(*args, **kwargs):
            if cls._disable_stubs:
                raise AssertionError('Stubs supporting old API disabled')
            elif cls._disable_stubs is None:
                pass
            elif cls._disable_stubs is False:
                get_logger(name=args[0].__class__.__name__).log(
                    WARNING, 'Use method %r via param namespace ' % fn.__name__)
            return fn(*args, **kwargs)

        inner.__doc__= "Inspect .param.%s method for the full docstring"  % fn.__name__
        return inner


    @classmethod
    def _changed(cls, event):
        """
        Predicate that determines whether a Event object has actually
        changed such that old != new.
        """
        return not Comparator.is_equal(event.old, event.new)


    # CEBALERT: this is a bit ugly
    def _instantiate_param(self_, param_obj, dict_=None, key=None):
        # deepcopy param_obj.default into self.__dict__ (or dict_ if supplied)
        # under the parameter's _internal_name (or key if supplied)
        self = self_.self
        dict_ = dict_ or self.__dict__
        key = key or param_obj._internal_name
        if shared_parameters._share:
            param_key = (str(type(self)), param_obj.name)
            if param_key in shared_parameters._shared_cache:
                new_object = shared_parameters._shared_cache[param_key]
            else:
                new_object = copy.deepcopy(param_obj.default)
                shared_parameters._shared_cache[param_key] = new_object
        else:
            new_object = copy.deepcopy(param_obj.default)

        dict_[key] = new_object

        if isinstance(new_object, Parameterized):
            global object_count
            object_count += 1
            # CB: writes over name given to the original object;
            # should it instead keep the same name?
            new_object.param._generate_name()

    # Classmethods

    def print_param_defaults(self_):
        """Print the default values of all cls's Parameters."""
        cls = self_.cls
        for key,val in cls.__dict__.items():
            if isinstance(val,Parameter):
                print(cls.__name__+'.'+key+ '='+ repr(val.default))


    def set_default(self_,param_name,value):
        """
        Set the default value of param_name.

        Equivalent to setting param_name on the class.
        """
        cls = self_.cls
        setattr(cls,param_name,value)


    def _add_parameter(self_, param_name,param_obj):
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
        cls = self_.cls
        type.__setattr__(cls,param_name,param_obj)
        ParameterizedMetaclass._initialize_parameter(cls,param_name,param_obj)
        # delete cached params()
        try:
            delattr(cls,'_%s__params'%cls.__name__)
        except AttributeError:
            pass


    def params(self_, parameter_name=None):
        """
        Return the Parameters of this class as the
        dictionary {name: parameter_object}

        Includes Parameters from this class and its
        superclasses.
        """
        pdict = self_.objects(instance='existing')
        if parameter_name is None:
            return pdict
        else:
            return pdict[parameter_name]

    # Bothmethods

    def set_param(self_, *args,**kwargs):
        """
        For each param=value keyword argument, sets the corresponding
        parameter of this object or class to the given value.

        For backwards compatibility, also accepts
        set_param("param",value) for a single parameter value using
        positional arguments, but the keyword interface is preferred
        because it is more compact and can set multiple values.
        """
        BATCH_WATCH = self_.self_or_cls.param._BATCH_WATCH
        self_.self_or_cls.param._BATCH_WATCH = True
        self_or_cls = self_.self_or_cls
        if args:
            if len(args) == 2 and not args[0] in kwargs and not kwargs:
                kwargs[args[0]] = args[1]
            else:
                self_.self_or_cls.param._BATCH_WATCH = False
                raise ValueError("Invalid positional arguments for %s.set_param" %
                                 (self_or_cls.name))

        trigger_params = [k for k in kwargs
                          if ((k in self_.self_or_cls.param) and
                              hasattr(self_.self_or_cls.param[k], '_autotrigger_value'))]

        for tp in trigger_params:
            self_.self_or_cls.param[tp]._mode = 'set'

        for (k, v) in kwargs.items():
            if k not in self_or_cls.param:
                self_.self_or_cls.param._BATCH_WATCH = False
                raise ValueError("'%s' is not a parameter of %s" % (k, self_or_cls.name))
            try:
                setattr(self_or_cls, k, v)
            except:
                self_.self_or_cls.param._BATCH_WATCH = False
                raise

        self_.self_or_cls.param._BATCH_WATCH = BATCH_WATCH
        if not BATCH_WATCH:
            self_._batch_call_watchers()

        for tp in trigger_params:
            p = self_.self_or_cls.param[tp]
            p._mode = 'reset'
            setattr(self_or_cls, tp, p._autotrigger_reset_value)
            p._mode = 'set-reset'

    def objects(self_, instance=True):
        """
        Returns the Parameters of this instance or class

        If instance=True and called on a Parameterized instance it
        will create instance parameters for all Parameters defined on
        the class. To force class parameters to be returned use
        instance=False. Since classes avoid creating instance
        parameters unless necessary you may also request only existing
        instance parameters to be returned by setting
        instance='existing'.
        """
        cls = self_.cls
        # CB: we cache the parameters because this method is called often,
        # and parameters are rarely added (and cannot be deleted)
        try:
            pdict = getattr(cls, '_%s__params' % cls.__name__)
        except AttributeError:
            paramdict = {}
            for class_ in classlist(cls):
                for name, val in class_.__dict__.items():
                    if isinstance(val, Parameter):
                        paramdict[name] = val

            # We only want the cache to be visible to the cls on which
            # params() is called, so we mangle the name ourselves at
            # runtime (if we were to mangle it now, it would be
            # _Parameterized.__params for all classes).
            setattr(cls, '_%s__params' % cls.__name__, paramdict)
            pdict = paramdict

        if instance and self_.self is not None:
            if instance == 'existing':
                if getattr(self_.self, 'initialized', False) and self_.self._instance__params:
                    return dict(pdict, **self_.self._instance__params)
                return pdict
            else:
                return {k: self_.self.param[k] for k in pdict}
        return pdict


    def trigger(self_, *param_names):
        """
        Trigger watchers for the given set of parameter names. Watchers
        will be triggered whether or not the parameter values have
        actually changed. As a special case, the value will actually be
        changed for a Parameter of type Event, setting it to True so
        that it is clear which Event parameter has been triggered.
        """
        trigger_params = [p for p in self_.self_or_cls.param
                          if hasattr(self_.self_or_cls.param[p], '_autotrigger_value')]
        triggers = {p:self_.self_or_cls.param[p]._autotrigger_value
                    for p in trigger_params if p in param_names}

        events = self_.self_or_cls.param._events
        watchers = self_.self_or_cls.param._watchers
        self_.self_or_cls.param._events  = []
        self_.self_or_cls.param._watchers = []
        param_values = dict(self_.get_param_values())
        params = {name: param_values[name] for name in param_names}
        self_.self_or_cls.param._TRIGGER = True
        self_.set_param(**dict(params, **triggers))
        self_.self_or_cls.param._TRIGGER = False
        self_.self_or_cls.param._events += events
        self_.self_or_cls.param._watchers += watchers


    def _update_event_type(self_, watcher, event, triggered):
        """
        Returns an updated Event object with the type field set appropriately.
        """
        if triggered:
            event_type = 'triggered'
        else:
            event_type = 'changed' if watcher.onlychanged else 'set'
        return Event(what=event.what, name=event.name, obj=event.obj, cls=event.cls,
                     old=event.old, new=event.new, type=event_type)

    def _execute_watcher(self, watcher, events):
        if watcher.mode == 'args':
            args, kwargs = events, {}
        else:
            args, kwargs = (), {event.name: event.new for event in events}

        if iscoroutinefunction(watcher.fn):
            if async_executor is None:
                raise RuntimeError("Could not execute %s coroutine function. "
                                   "Please register a asynchronous executor on "
                                   "param.parameterized.async_executor, which "
                                   "schedules the function on an event loop." %
                                   watcher.fn)
            async_executor(partial(watcher.fn, *args, **kwargs))
        else:
            watcher.fn(*args, **kwargs)

    def _call_watcher(self_, watcher, event):
        """
        Invoke the given the watcher appropriately given a Event object.
        """
        if self_.self_or_cls.param._TRIGGER:
            pass
        elif watcher.onlychanged and (not self_._changed(event)):
            return

        if self_.self_or_cls.param._BATCH_WATCH:
            self_._events.append(event)
            if watcher not in self_._watchers:
                self_._watchers.append(watcher)
        else:
            event = self_._update_event_type(watcher, event, self_.self_or_cls.param._TRIGGER)
            with batch_watch(self_.self_or_cls, enable=watcher.queued, run=False):
                self_._execute_watcher(watcher, (event,))

    def _batch_call_watchers(self_):
        """
        Batch call a set of watchers based on the parameter value
        settings in kwargs using the queued Event and watcher objects.
        """
        while self_.self_or_cls.param._events:
            event_dict = OrderedDict([((event.name, event.what), event)
                                      for event in self_.self_or_cls.param._events])
            watchers = self_.self_or_cls.param._watchers[:]
            self_.self_or_cls.param._events = []
            self_.self_or_cls.param._watchers = []

            for watcher in watchers:
                events = [self_._update_event_type(watcher, event_dict[(name, watcher.what)],
                                                   self_.self_or_cls.param._TRIGGER)
                          for name in watcher.parameter_names
                          if (name, watcher.what) in event_dict]
                with batch_watch(self_.self_or_cls, enable=watcher.queued, run=False):
                    self_._execute_watcher(watcher, events)

    def set_dynamic_time_fn(self_,time_fn,sublistattr=None):
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
        self_or_cls = self_.self_or_cls
        self_or_cls._Dynamic_time_fn = time_fn

        if isinstance(self_or_cls,type):
            a = (None,self_or_cls)
        else:
            a = (self_or_cls,)

        for n,p in self_or_cls.param.objects('existing').items():
            if hasattr(p, '_value_is_dynamic'):
                if p._value_is_dynamic(*a):
                    g = self_or_cls.param.get_value_generator(n)
                    g._Dynamic_time_fn = time_fn

        if sublistattr:
            try:
                sublist = getattr(self_or_cls,sublistattr)
            except AttributeError:
                sublist = []

            for obj in sublist:
                obj.param.set_dynamic_time_fn(time_fn,sublistattr)

    def serialize_parameters(self_, subset=None, mode='json'):
        self_or_cls = self_.self_or_cls
        if mode not in Parameter._serializers:
            raise ValueError('Mode %r not in available serialization formats %r'
                             % (mode, list(Parameter._serializers.keys())))
        serializer = Parameter._serializers[mode]
        return serializer.serialize_parameters(self_or_cls, subset=subset)

    def serialize_value(self_, pname, mode='json'):
        self_or_cls = self_.self_or_cls
        if mode not in Parameter._serializers:
            raise ValueError('Mode %r not in available serialization formats %r'
                             % (mode, list(Parameter._serializers.keys())))
        serializer = Parameter._serializers[mode]
        return serializer.serialize_parameter_value(self_or_cls, pname)

    def deserialize_parameters(self_, serialization, subset=None, mode='json'):
        self_or_cls = self_.self_or_cls
        serializer = Parameter._serializers[mode]
        return serializer.deserialize_parameters(self_or_cls, serialization, subset=subset)

    def deserialize_value(self_, pname, value, mode='json'):
        self_or_cls = self_.self_or_cls
        if mode not in Parameter._serializers:
            raise ValueError('Mode %r not in available serialization formats %r'
                             % (mode, list(Parameter._serializers.keys())))
        serializer = Parameter._serializers[mode]
        return serializer.deserialize_parameter_value(self_or_cls, pname, value)

    def schema(self_, safe=False, subset=None, mode='json'):
        """
        Returns a schema for the parameters on this Parameterized object.
        """
        self_or_cls = self_.self_or_cls
        if mode not in Parameter._serializers:
            raise ValueError('Mode %r not in available serialization formats %r'
                             % (mode, list(Parameter._serializers.keys())))
        serializer = Parameter._serializers[mode]
        return serializer.schema(self_or_cls, safe=safe, subset=subset)

    def get_param_values(self_, onlychanged=False):
        """
        Return a list of name,value pairs for all Parameters of this
        object.

        When called on an instance with onlychanged set to True, will
        only return values that are not equal to the default value
        (onlychanged has no effect when called on a class).
        """
        self_or_cls = self_.self_or_cls
        # CEB: we'd actually like to know whether a value has been
        # explicitly set on the instance, but I'm not sure that's easy
        # (would need to distinguish instantiation of default from
        # user setting of value).
        vals = []
        for name, val in self_or_cls.param.objects('existing').items():
            value = self_or_cls.param.get_value_generator(name)
            # (this is pointless for cls)
            if not onlychanged or not all_equal(value, val.default):
                vals.append((name, value))

        vals.sort(key=itemgetter(0))
        return vals


    def force_new_dynamic_value(self_, name): # pylint: disable-msg=E0213
        """
        Force a new value to be generated for the dynamic attribute
        name, and return it.

        If name is not dynamic, its current value is returned
        (i.e. equivalent to getattr(name).
        """
        cls_or_slf = self_.self_or_cls
        param_obj = cls_or_slf.param.objects('existing').get(name)

        if not param_obj:
            return getattr(cls_or_slf, name)

        cls, slf = None, None
        if isinstance(cls_or_slf,type):
            cls = cls_or_slf
        else:
            slf = cls_or_slf

        if not hasattr(param_obj,'_force'):
            return param_obj.__get__(slf, cls)
        else:
            return param_obj._force(slf, cls)


    def get_value_generator(self_,name): # pylint: disable-msg=E0213
        """
        Return the value or value-generating object of the named
        attribute.

        For most parameters, this is simply the parameter's value
        (i.e. the same as getattr()), but Dynamic parameters have
        their value-generating object returned.
        """
        cls_or_slf = self_.self_or_cls
        param_obj = cls_or_slf.param.objects('existing').get(name)

        if not param_obj:
            value = getattr(cls_or_slf,name)

        # CompositeParameter detected by being a Parameter and having 'attribs'
        elif hasattr(param_obj,'attribs'):
            value = [cls_or_slf.param.get_value_generator(a) for a in param_obj.attribs]

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

    def inspect_value(self_,name): # pylint: disable-msg=E0213
        """
        Return the current value of the named attribute without modifying it.

        Same as getattr() except for Dynamic parameters, which have their
        last generated value returned.
        """
        cls_or_slf = self_.self_or_cls
        param_obj = cls_or_slf.param.objects('existing').get(name)

        if not param_obj:
            value = getattr(cls_or_slf,name)
        elif hasattr(param_obj,'attribs'):
            value = [cls_or_slf.param.inspect_value(a) for a in param_obj.attribs]
        elif not hasattr(param_obj,'_inspect'):
            value = getattr(cls_or_slf,name)
        else:
            if isinstance(cls_or_slf,type):
                value = param_obj._inspect(None,cls_or_slf)
            else:
                value = param_obj._inspect(cls_or_slf,None)

        return value


    def params_depended_on(self_,name):
        return _params_depended_on(MInfo(cls=self_.cls,inst=self_.self,name=name,method=getattr(self_.self_or_cls,name)))


    def outputs(self_):
        """
        Returns a mapping between any declared outputs and a tuple
        of the declared Parameter type, the output method, and the
        index into the output if multiple outputs are returned.
        """
        outputs = {}
        for cls in classlist(self_.cls):
            for name in dir(cls):
                method = getattr(self_.self_or_cls, name)
                dinfo = getattr(method, '_dinfo', {})
                if 'outputs' not in dinfo:
                    continue
                for override, otype, idx in dinfo['outputs']:
                    if override is not None:
                        name = override
                    outputs[name] = (otype, method, idx)
        return outputs


    def _spec_to_obj(self_,spec):
        # TODO: when we decide on spec, this method should be
        # rewritten

        if isinstance(spec, Parameter):
            inst = spec.owner if isinstance(spec.owner, Parameterized) else None
            cls = spec.owner if inst is None else type(inst)
            info = PInfo(inst=inst, cls=cls, name=spec.name,
                         pobj=spec, what='value')
            return [info]

        assert spec.count(":")<=1

        spec = spec.strip()
        m = re.match("(?P<path>[^:]*):?(?P<what>.*)", spec)
        what = m.group('what')
        path = "."+m.group('path')
        m = re.match(r"(?P<obj>.*)(\.)(?P<attr>.*)",path)
        obj = m.group('obj')
        attr = m.group("attr")

        src = self_.self_or_cls if obj=='' else _getattrr(self_.self_or_cls,obj[1::])
        cls,inst = (src, None) if isinstance(src, type) else (type(src), src)

        if attr == 'param':
            dependencies = self_._spec_to_obj(obj[1:])
            for p in src.param:
                dependencies += src.param._spec_to_obj(p)
            return dependencies
        elif attr in src.param:
            what = what if what != '' else 'value'
            info = PInfo(inst=inst, cls=cls, name=attr,
                         pobj=src.param[attr], what=what)
        else:
            info = MInfo(inst=inst, cls=cls, name=attr,
                         method=getattr(src,attr))
        return [info]


    def _watch(self_, action, watcher, what='value', operation='add'): #'add' | 'remove'
        parameter_names = watcher.parameter_names
        for parameter_name in parameter_names:
            if parameter_name not in self_.cls.param:
                raise ValueError("%s parameter was not found in list of "
                                 "parameters of class %s" %
                                 (parameter_name, self_.cls.__name__))

            if self_.self is not None and what == "value":
                watchers = self_.self._param_watchers
                if parameter_name not in watchers:
                    watchers[parameter_name] = {}
                if what not in watchers[parameter_name]:
                    watchers[parameter_name][what] = []
                getattr(watchers[parameter_name][what], action)(watcher)
            else:
                watchers = self_[parameter_name].watchers
                if what not in watchers:
                    watchers[what] = []
                getattr(watchers[what], action)(watcher)

    def watch(self_,fn,parameter_names, what='value', onlychanged=True, queued=False):
        parameter_names = tuple(parameter_names) if isinstance(parameter_names, list) else (parameter_names,)
        watcher = Watcher(inst=self_.self, cls=self_.cls, fn=fn, mode='args',
                          onlychanged=onlychanged, parameter_names=parameter_names,
                          what=what, queued=queued)
        self_._watch('append', watcher, what)
        return watcher

    def unwatch(self_,watcher):
        """
        Unwatch watchers set either with watch or watch_values.
        """
        try:
            self_._watch('remove',watcher)
        except:
            self_.warning('No such watcher {watcher} to remove.'.format(watcher=watcher))


    def watch_values(self_, fn, parameter_names, what='value', onlychanged=True, queued=False):
        parameter_names = tuple(parameter_names) if isinstance(parameter_names, list) else (parameter_names,)
        watcher = Watcher(inst=self_.self, cls=self_.cls, fn=fn,
                          mode='kwargs', onlychanged=onlychanged,
                          parameter_names=parameter_names, what='value',
                          queued=queued)
        self_._watch('append', watcher, what)
        return watcher


    # Instance methods


    def defaults(self_):
        """
        Return {parameter_name:parameter.default} for all non-constant
        Parameters.

        Note that a Parameter for which instantiate==True has its default
        instantiated.
        """
        self = self_.self
        d = {}
        for param_name, param in self.param.objects('existing').items():
            if param.constant:
                pass
            if param.instantiate:
                self.param._instantiate_param(param, dict_=d, key=param_name)
            d[param_name] = param.default
        return d

    # CEBALERT: designed to avoid any processing unless the print
    # level is high enough, but not all callers of message(),
    # verbose(), debug(), etc are taking advantage of this. Need to
    # document, and also check other ioam projects.
    def __db_print(self_,level,msg,*args,**kw):
        """
        Calls the logger returned by the get_logger() function,
        prepending the result of calling dbprint_prefix() (if any).

        See python's logging module for details.
        """
        self_or_cls = self_.self_or_cls
        if get_logger(name=self_or_cls.name).isEnabledFor(level):

            if dbprint_prefix and callable(dbprint_prefix):
                msg = dbprint_prefix() + ": " + msg  # pylint: disable-msg=E1102

            get_logger(name=self_or_cls.name).log(level, msg, *args, **kw)

    def print_param_values(self_):
        """Print the values of all this object's Parameters."""
        self = self_.self
        for name,val in self.param.get_param_values():
            print('%s.%s = %s' % (self.name,name,val))

    def warning(self_, msg,*args,**kw):
        """
        Print msg merged with args as a warning, unless module variable
        warnings_as_exceptions is True, then raise an Exception
        containing the arguments.

        See Python's logging module for details of message formatting.
        """
        if not warnings_as_exceptions:
            global warning_count
            warning_count+=1
            self_.__db_print(WARNING,msg,*args,**kw)
        else:
            raise Exception("Warning: " + msg % args)

    def message(self_,msg,*args,**kw):
        """
        Print msg merged with args as a message.

        See Python's logging module for details of message formatting.
        """
        self_.__db_print(INFO,msg,*args,**kw)

    def verbose(self_,msg,*args,**kw):
        """
        Print msg merged with args as a verbose message.

        See Python's logging module for details of message formatting.
        """
        self_.__db_print(VERBOSE,msg,*args,**kw)

    def debug(self_,msg,*args,**kw):
        """
        Print msg merged with args as a debugging statement.

        See Python's logging module for details of message formatting.
        """
        self_.__db_print(DEBUG,msg,*args,**kw)


    # CEBALERT: I think I've noted elsewhere the fact that we
    # sometimes have a method on Parameter that requires passing the
    # owning Parameterized instance or class, and other times we have
    # the method on Parameterized itself.  In case I haven't written
    # that down elsewhere, here it is again.  We should clean that up
    # (at least we should be consistent).

    # cebalert: it's really time to stop and clean up this bothmethod
    # stuff and repeated code in methods using it.



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

        mcs._parameters_state = {
            "BATCH_WATCH": False, # If true, Event and watcher objects are queued.
            "TRIGGER": False,
            "events": [], # Queue of batched events
            "watchers": [] # Queue of batched watchers
        }
        mcs._param = Parameters(mcs)

        # All objects (with their names) of type Parameter that are
        # defined in this class
        parameters = [(n,o) for (n,o) in dict_.items()
                      if isinstance(o, Parameter)]

        mcs._param._parameters = dict(parameters)

        for param_name,param in parameters:
            mcs._initialize_parameter(param_name,param)

        # retrieve depends info from methods and store more conveniently
        dependers = [(n,m._dinfo) for (n,m) in dict_.items()
                     if hasattr(m,'_dinfo')]

        _watch = []
        # TODO: probably copy dependencies here too and have
        # everything else access from here rather than from method
        # object
        for n,dinfo in dependers:
            watch = dinfo.get('watch', False)
            if watch:
                _watch.append((n, watch == 'queued'))

        mcs.param._depends = {'watch': _watch}

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
        # runtime. Mangling follows description in https://docs.python.org/2/tutorial/classes.html#private-variables-and-class-local-references
        try:
            return getattr(mcs,'_%s__abstract'%mcs.__name__.lstrip("_"))
        except AttributeError:
            return False

    abstract = property(__is_abstract)

    def _get_param(mcs):
        return mcs._param

    param = property(_get_param)

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
                parameter = copy.copy(parameter)
                parameter.owner = mcs
                type.__setattr__(mcs,attribute_name,parameter)
            mcs.__dict__[attribute_name].__set__(None,value)

        else:
            type.__setattr__(mcs,attribute_name,value)

            if isinstance(value,Parameter):
                mcs.__param_inheritance(attribute_name,value)
            elif isinstance(value,Parameters):
                pass
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
        instantiate=True.
        """
        # get all relevant slots (i.e. slots defined in all
        # superclasses of this parameter)
        slots = {}
        for p_class in classlist(type(param))[1::]:
            slots.update(dict.fromkeys(p_class.__slots__))


        # note for some eventual future: python 3.6+ descriptors grew
        # __set_name__, which could replace this and _set_names
        setattr(param,'owner',mcs)
        del slots['owner']

        # backwards compatibility (see Composite parameter)
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


# Copy of Python 3.2 reprlib's recursive_repr but allowing extra arguments
if sys.version_info.major >= 3:
    from threading import get_ident
    def recursive_repr(fillvalue='...'):
        'Decorator to make a repr function return fillvalue for a recursive call'

        def decorating_function(user_function):
            repr_running = set()

            def wrapper(self, *args, **kwargs):
                key = id(self), get_ident()
                if key in repr_running:
                    return fillvalue
                repr_running.add(key)
                try:
                    result = user_function(self, *args, **kwargs)
                finally:
                    repr_running.discard(key)
                return result
            return wrapper

        return decorating_function
else:
    def recursive_repr(fillvalue='...'):
        def decorating_function(user_function):
            return user_function
        return decorating_function


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

    name = String(default=None, constant=True, doc="""
        String identifier for this object.""")

    def __init__(self, **params):
        global object_count

        # Flag that can be tested to see if e.g. constant Parameters
        # can still be set
        self.initialized = False
        self._parameters_state = {
            "BATCH_WATCH": False, # If true, Event and watcher objects are queued.
            "TRIGGER": False,
            "events": [], # Queue of batched events
            "watchers": [] # Queue of batched watchers
        }
        self._instance__params = {}
        self._param_watchers = {}

        self.param._generate_name()
        self.param._setup_params(**params)
        object_count += 1

        # add watched dependencies
        for cls in classlist(self.__class__):
            if not issubclass(cls, Parameterized):
                continue
            for n, queued in cls.param._depends['watch']:
                # TODO: should improve this - will happen for every
                # instantiation of Parameterized with watched deps. Will
                # probably store expanded deps on class - see metaclass
                # 'dependers'.
                grouped = defaultdict(list)
                for dep in self.param.params_depended_on(n):
                    grouped[(id(dep.inst),id(dep.cls),dep.what)].append(dep)
                for group in grouped.values():
                    # TODO: can't remember why not just pass m (rather than _m_caller) here
                    gdep = group[0] # Need to grab representative dep from this group
                    (gdep.inst or gdep.cls).param.watch(_m_caller(self, n), [d.name for d in group], gdep.what, queued=queued)

        self.initialized = True

    @property
    def param(self):
        return Parameters(self.__class__, self=self)

    # 'Special' methods

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

    def __setstate__(self, state):
        """
        Restore objects from the state dictionary to this object.

        During this process the object is considered uninitialized.
        """
        self.initialized=False

        # When making a copy the internal watchers have to be
        # recreated and point to the new instance
        if '_param_watchers' in state:
            param_watchers = state['_param_watchers']
            for p, attrs in param_watchers.items():
                for attr, watchers in attrs.items():
                    new_watchers = []
                    for watcher in watchers:
                        watcher_args = list(watcher)
                        if watcher.inst is not None:
                            watcher_args[0] = self
                        fn = watcher.fn
                        if hasattr(fn, '_watcher_name'):
                            watcher_args[2] = _m_caller(self, fn._watcher_name)
                        elif get_method_owner(fn) is watcher.inst:
                            watcher_args[2] = getattr(self, fn.__name__)
                        new_watchers.append(Watcher(*watcher_args))
                    param_watchers[p][attr] = new_watchers

        if '_instance__params' not in state:
            state['_instance__params'] = {}
        if '_param_watchers' not in state:
            state['_param_watchers'] = {}
        state.pop('param', None)

        for name,value in state.items():
            setattr(self,name,value)
        self.initialized=True

    @recursive_repr()
    def __repr__(self):
        """
        Provide a nearly valid Python representation that could be used to recreate
        the item with its parameters, if executed in the appropriate environment.

        Returns 'classname(parameter1=x,parameter2=y,...)', listing
        all the parameters of this object.
        """
        try:
            settings = ['%s=%s' % (name, repr(val))
                        for name,val in self.param.get_param_values()]
        except RuntimeError: # Handle recursion in parameter depth
            settings = []
        return self.__class__.__name__ + "(" + ", ".join(settings) + ")"

    def __str__(self):
        """Return a short representation of the name and class of this object."""
        return "<%s %s>" % (self.__class__.__name__,self.name)


    def script_repr(self,imports=[],prefix="    "):
        """
        Variant of __repr__ designed for generating a runnable script.
        """
        return self.pprint(imports,prefix, unknown_value=None, qualify=True,
                           separator="\n")

    @recursive_repr()
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

        changed_params = dict(self.param.get_param_values(onlychanged=script_repr_suppress_defaults))
        values = dict(self.param.get_param_values())
        spec = inspect.getargspec(self.__init__)
        args = spec.args[1:] if spec.args[0] == 'self' else spec.args

        if spec.defaults is not None:
            posargs = spec.args[:-len(spec.defaults)]
            kwargs = dict(zip(spec.args[-len(spec.defaults):], spec.defaults))
        else:
            posargs, kwargs = args, []

        parameters = self.param.objects('existing')
        ordering = sorted(
            sorted(changed_params), # alphanumeric tie-breaker
            key=lambda k: (- float('inf')  # No precedence is lowest possible precendence
                           if parameters[k].precedence is None else
                           parameters[k].precedence))

        arglist, keywords, processed = [], [], []
        for k in args + ordering:
            if k in processed: continue

            # Suppresses automatically generated names.
            if k == 'name' and (values[k] is not None
                                and re.match('^'+self.__class__.__name__+'[0-9]+$', values[k])):
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
        for pname, p in self.param.objects('existing').items():
            g = self.param.get_value_generator(pname)
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
        for pname, p in self.param.objects('existing').items():
            g = self.param.get_value_generator(pname)
            if hasattr(g,'_Dynamic_last'):
                g._Dynamic_last = g._saved_Dynamic_last.pop()
                g._Dynamic_time = g._saved_Dynamic_time.pop()
            elif hasattr(g,'state_pop') and isinstance(g,Parameterized):
                g.state_pop()


    # API to be accessed via param namespace

    @classmethod
    @Parameters.deprecate
    def _add_parameter(cls, param_name,param_obj):
        return cls.param._add_parameter(param_name,param_obj)

    @bothmethod
    @Parameters.deprecate
    def params(cls,parameter_name=None):
        return cls.param.params(parameter_name=parameter_name)

    @classmethod
    @Parameters.deprecate
    def set_default(cls,param_name,value):
        return cls.param.set_default(param_name,value)

    @classmethod
    @Parameters.deprecate
    def print_param_defaults(cls):
        return cls.param.print_param_defaults()

    @bothmethod
    @Parameters.deprecate
    def set_param(self_or_cls,*args,**kwargs):
        return self_or_cls.param.set_param(*args,**kwargs)

    @bothmethod
    @Parameters.deprecate
    def set_dynamic_time_fn(self_or_cls,time_fn,sublistattr=None):
        return self_or_cls.param.set_dynamic_time_fn(time_fn,sublistattr=sublistattr)

    @bothmethod
    @Parameters.deprecate
    def get_param_values(self_or_cls,onlychanged=False):
        return self_or_cls.param.get_param_values(onlychanged=onlychanged)

    @bothmethod
    @Parameters.deprecate
    def force_new_dynamic_value(cls_or_slf,name): # pylint: disable-msg=E0213
        return cls_or_slf.param.force_new_dynamic_value(name)

    @bothmethod
    @Parameters.deprecate
    def get_value_generator(cls_or_slf,name): # pylint: disable-msg=E0213
        return cls_or_slf.param.get_value_generator(name)

    @bothmethod
    @Parameters.deprecate
    def inspect_value(cls_or_slf,name): # pylint: disable-msg=E0213
        return cls_or_slf.param.inspect_value(name)

    @Parameters.deprecate
    def _set_name(self,name):
        return self.param._set_name(name)

    @Parameters.deprecate
    def __db_print(self,level,msg,*args,**kw):
        return self.param.__db_print(level,msg,*args,**kw)

    @Parameters.deprecate
    def warning(self,msg,*args,**kw):
        return self.param.warning(msg,*args,**kw)

    @Parameters.deprecate
    def message(self,msg,*args,**kw):
        return self.param.message(msg,*args,**kw)

    @Parameters.deprecate
    def verbose(self,msg,*args,**kw):
        return self.param.verbose(msg,*args,**kw)

    @Parameters.deprecate
    def debug(self,msg,*args,**kw):
        return self.param.debug(msg,*args,**kw)

    @Parameters.deprecate
    def print_param_values(self):
        return self.param.print_param_values()

    @Parameters.deprecate
    def defaults(self):
        return self.param.defaults()



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

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self.__dict__ or key in self._overridden.param

    def _check_params(self,params):
        """
        Print a warning if params contains something that is not a
        Parameter of the overridden object.
        """
        overridden_object_params = list(self._overridden.param)
        for item in params:
            if item not in overridden_object_params:
                self.param.warning("'%s' will be ignored (not a Parameter).",item)

    def _extract_extra_keywords(self,params):
        """
        Return any items in params that are not also
        parameters of the overridden object.
        """
        extra_keywords = {}
        overridden_object_params = list(self._overridden.param)
        for name, val in params.items():
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
            params = dict(self_or_cls.param.get_param_values())
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
        inst.param._set_name(class_.__name__)
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



class default_label_formatter(ParameterizedFunction):
    "Default formatter to turn parameter names into appropriate widget labels."

    capitalize = Parameter(default=True, doc="""
        Whether or not the label should be capitalized.""")

    replace_underscores = Parameter(default=True, doc="""
        Whether or not underscores should be replaced with spaces.""")

    overrides = Parameter(default={}, doc="""
        Allows custom labels to be specified for specific parameter
        names using a dictionary where key is the parameter name and the
        value is the desired label.""")

    def __call__(self, pname):
        if pname in self.overrides:
            return self.overrides[pname]
        if self.replace_underscores:
            pname = pname.replace('_',' ')
        if self.capitalize:
            pname = pname[:1].upper() + pname[1:]
        return pname


label_formatter = default_label_formatter


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
