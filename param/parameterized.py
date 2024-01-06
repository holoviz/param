"""
Generic support for objects with full-featured Parameters and
messaging.

This file comes from the Param library (https://github.com/holoviz/param)
but can be taken out of the param module and used on its own if desired,
either alone (providing basic Parameter support) or with param's
__init__.py (providing specialized Parameter types).
"""

import copy
import datetime
import re
import numbers
import operator
import inspect
import threading
import typing
from types import FunctionType, TracebackType
from enum import Enum
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from functools import partial, wraps
from operator import itemgetter, attrgetter
from contextlib import contextmanager

from .utils import *
from .exceptions import *
from .serializer import serializers

try:
    # In case the optional ipython module is unavailable
    from .ipython import ParamPager
    param_pager = ParamPager(metaclass=True)  # Generates param description
except:
    param_pager = None

dt_types = (datetime.datetime, datetime.date)

try:
    import numpy as np
    dt_types = dt_types + (np.datetime64,)
except:
    pass

# External components can register an async executor which will run
# async functions
async_executor = None

Undefined = NotImplemented


def instance_descriptor(f :  typing.Callable[['Parameter', 'Parameterized', typing.Any], None]) -> typing.Callable[[
                'Parameter', 'Parameterized', typing.Any], None]:
    # If parameter has an instance Parameter, delegate setting
    def fset(self : 'Parameter', obj : 'Parameterized', val : typing.Any) -> None:
        if hasattr(obj, 'parameters'):
            if hasattr(obj.parameters, '_instance_params'):
                instance_param = obj.parameters._instance_params.get(self.name, None)
                if instance_param is not None and self is not instance_param:
                    instance_param.__set__(obj, val)
                    return
        return f(self, obj, val)
    return fset



class ParameterMetaclass(type):
    """
    Metaclass allowing control over creation of Parameter classes.
    """
    def __new__(mcs, classname : str, bases : typing.Tuple[typing.Any], 
                                    classdict : typing.Dict[str, typing.Any]) -> 'ParameterMetaclass':

        # store the class's docstring in __classdoc
        if '__doc__' in classdict:
            classdict['__classdoc'] = classdict['__doc__']

        # when asking for help on Parameter *object*, return the doc slot
        classdict['__doc__'] = property(attrgetter('doc'))

        # To get the benefit of slots, subclasses must themselves define
        # __slots__, whether or not they define attributes not present in
        # the base Parameter class.  That's because a subclass will have
        # a __dict__ unless it also defines __slots__.
        if '__slots__' not in classdict:
            classdict['__slots__'] = []
        if '__parent_slots__' not in classdict:
            classdict['__parent_slots__'] = []
        
        for base in bases: # there will almost always only one base because slots dont support multiple inheritance
            for base_ in inspect.getmro(base):
                if hasattr(base_, '__slots__'):
                # check _post_slot_set in Parameter to understand the requirement
                    classdict['__parent_slots__'].extend(base_.__slots__) # type: ignore
        
        # No special handling for a __dict__ slot; should there be?
        return type.__new__(mcs, classname, bases, classdict)

    def __getattribute__(mcs, name : str) -> typing.Any:
        if name == '__doc__':
            # when asking for help on Parameter *class*, return the
            # stored class docstring
            return type.__getattribute__(mcs, '__classdoc')
        else:
            return type.__getattribute__(mcs, name)



class Parameter(metaclass=ParameterMetaclass):
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
    definitions with something like this::

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
       superclasses).  E.g., if a script does this::

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
       declares::

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

    # Be careful when referring to the 'name' of a Parameter:
    #
    # * A Parameterized class has a name for the attribute which is
    #   being represented by the Parameter in the code, 
    #   this is called the 'attrib_name'.
    #
    # * When a Parameterized instance has its own local value for a
    #   parameter, it is stored as '_X_param_value' (where X is the
    #   attrib_name for the Parameter); in the code, this is called
    #   the internal_name.


    # So that the extra features of Parameters do not require a lot of
    # overhead, Parameters are implemented using __slots__ (see
    # http://www.python.org/doc/2.4/ref/slots.html). 

    __slots__ = ['default', 'doc', 'constant', 'readonly', 'allow_None',
                'per_instance_descriptor', 'deepcopy_default', 'class_member', 'precedence', 
                'owner', 'name', '_internal_name', 'watchers', 'overloads',
                '_disable_post_slot_set']

    # Note: When initially created, a Parameter does not know which
    # Parameterized class owns it. Once the owning Parameterized
    # class is created, owner, name, and _internal_name are
    # set.

    def __init__(self, default : typing.Any, *, doc : typing.Optional[str] = None,
                constant : bool = False, readonly : bool = False, allow_None : bool = False,
                per_instance_descriptor : bool = False, deepcopy_default : bool = False, class_member : bool = False,
                fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None, 
                fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:  # pylint: disable-msg=R0913

        """Initialize a new Parameter object and store the supplied attributes:

        default: the owning class's value for the attribute represented
        by this Parameter, which can be overridden in an instance.

        doc: docstring explaining what this parameter represents.

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

        allow_None: if True, None is accepted as a valid value for
        this Parameter, in addition to any other values that are
        allowed. If the default value is defined as None, allow_None
        is set to True automatically.

        label: optional text label to be used when this Parameter is
        shown in a listing. If no label is supplied, the attribute name
        for this parameter in the owning Parameterized object is used.

        per_instance_descriptor: whether a separate Parameter instance will be
        created for every Parameterized instance. True by default.
        If False, all instances of a Parameterized class will share
        the same Parameter object, including all validation
        attributes (bounds, etc.). 

        deepcopy_default: controls whether the value of this Parameter will
        be deepcopied when a Parameterized object is instantiated (if
        True), or if the single default value will be shared by all
        Parameterized instances (if False). For an immutable Parameter
        value, it is best to leave deepcopy_default at the default of
        False, so that a user can choose to change the value at the
        Parameterized instance level (affecting only that instance) or
        at the Parameterized class or superclass level (affecting all
        existing and future instances of that class or superclass). For
        a mutable Parameter value, the default of False is also appropriate
        if you want all instances to share the same value state, e.g. if
        they are each simply referring to a single global object like
        a singleton. If instead each Parameterized should have its own
        independently mutable value, deepcopy_default should be set to
        True, but note that there is then no simple way to change the
        value of this Parameter at the class or superclass level,
        because each instance, once created, will then have an
        independently deepcopied value.

        class_member : To make a ... 

        precedence: a numeric value, usually in the range 0.0 to 1.0,
        which allows the order of Parameters in a class to be defined in
        a listing or e.g. in GUI menus. A negative precedence indicates
        a parameter that should be hidden in such listings.

        default, doc, and precedence all default to None, which allows
        inheritance of Parameter slots (attributes) from the owning-class'
        class hierarchy (see ParameterizedMetaclass).

        Note - parameter's own attributes are not type checked. if one sets
        allow_None = 45 instead of allow_None = True, allow_None will be taken to be True.
        """
        self._disable_post_slot_set = False
        # the above slot should better to stay at top of init for __setattr__ to work uniformly
        self.default = default
        self.doc = doc
        self.constant = constant # readonly is also constant however constants can be set once
        self.readonly = readonly
        self.allow_None = constant or allow_None
        self.per_instance_descriptor = per_instance_descriptor
        self.deepcopy_default = deepcopy_default
        self.class_member = class_member
        self.precedence = precedence
        self.watchers : typing.Dict[str, typing.List] = {}
        self.overloads : typing.Dict[str, typing.Union[typing.Callable, None]] = dict(fget=fget, 
                                                                                fset=fset, fdel=fdel)
        
    def __set_name__(self, owner : typing.Any, attrib_name : str) -> None:
        self._internal_name = f"_{attrib_name}_param_value"
        self.name  = attrib_name
        self.owner = owner
        # This particular order is generally important

    def __setattr__(self, attribute : str, value : typing.Any) -> None:
        if attribute == 'name' and getattr(self, 'name', None) and value != self.name:
            raise AttributeError("Parameter name cannot be modified after "
                                 "it has been bound to a Parameterized.")

        watched = (attribute != "default" and hasattr(self, 'watchers') and attribute in self.watchers)
        slot_attribute = attribute in self.__slots__ or attribute in self.__parent_slots__ # type: ignore
        try:
            old = getattr(self, attribute) if watched else NotImplemented
        except AttributeError as exc:
            if slot_attribute:
                # If Parameter slot is defined but an AttributeError was raised
                # we are in __setstate__ and watchers should not be triggered
                old = NotImplemented
            else:
                raise # exc , dont raise exc as it will cause multiple tracebacks

        super(Parameter, self).__setattr__(attribute, value)

        if slot_attribute and hasattr(self, '_disable_post_slot_set') and not self._disable_post_slot_set:
            self._post_slot_set(attribute, old, value)

        if old is NotImplemented or not isinstance(self.owner, Parameterized):
            return

        event_dispatcher = self.owner.parameters.event_dispatcher
        event = Event(what=attribute, name=self.name, obj=None, cls=self.owner,
                    old=old, new=value, type=None)
        for watcher in self.watchers[attribute]:
            event_dispatcher.call_watcher(watcher, event)
        if not event_dispatcher.state.BATCH_WATCH:
            event_dispatcher.batch_call_watchers()
        
    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        """
        Can be overridden on subclasses to handle changes when parameter
        attribute is set. Be very careful of circular calls. 
        """
        # __parent_slots__ attribute is needed for entry into this function correctly otherwise 
        # slot_attribute in __setattr__ will have wrong boolean flag
        if slot == 'owner' and self.owner is not None:
            with disable_post_slot_set(self):
                self.default = self.validate_and_adapt(self.default)
 
    def __get__(self, obj : typing.Union['Parameterized', typing.Any], 
                        objtype : typing.Union['ParameterizedMetaclass', typing.Any]) -> typing.Any: # pylint: disable-msg=W0613
        """
        Return the value for this Parameter.

        If called for a Parameterized class, produce that
        class's value (i.e. this Parameter object's 'default'
        attribute).

        If called for a Parameterized instance, produce that
        instance's value, if one has been set - otherwise produce the
        class's value (default).
        """        
        if obj is None:
            return self 
        fget = self.overloads['fget'] 
        if fget is not None:     
            return fget(obj) 
        return obj.__dict__.get(self._internal_name, self.default)
       
    @instance_descriptor
    def __set__(self, obj : typing.Union['Parameterized', typing.Any], value : typing.Any) -> None:
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
        object stored in a constant or read-only Parameter (e.g. one
        item in a list).
        """
        if self.readonly:
            raise_TypeError("Read-only parameter cannot be set/modified.", self)
        
        value = self.validate_and_adapt(value)

        obj = obj if not self.class_member else self.owner

        old = NotImplemented
        if self.constant:
            old = None
            if (obj.__dict__.get(self._internal_name, NotImplemented) != NotImplemented) or self.default is not None: 
                # Dont even entertain any type of setting, even if its the same value
                raise_TypeError("Constant parameter cannot be modified.", self)
        else:
            old = obj.__dict__.get(self._internal_name, self.default)

        # The following needs to be optimised, probably through lambda functions?
        fset = self.overloads['fset']
        if fset is not None:
            fset(obj, value) 
        else: 
            obj.__dict__[self._internal_name] = value
        
        self._post_value_set(obj, value) 

        if not isinstance(obj, (Parameterized, ParameterizedMetaclass)):
            """
            dont deal with events, watchers etc when object is not a Parameterized class child.
            Many variables like obj.param below will also raise AttributeError. 
            This will enable generic use of Parameters without adherence to Parameterized subclassing.
            """
            return           
        
        event_dispatcher = obj.parameters.event_dispatcher
        event_dispatcher.update_dynamic_dependencies(self.name)

        if self.name in event_dispatcher.all_watchers:
            watchers = event_dispatcher.all_watchers[self.name].get('value', None)
            if watchers is None:
                watchers = self.watchers.get('value', None)
            if watchers is None:
                return
        
            event = Event(what=parameter.VALUE, name=self.name, obj=obj, cls=self.owner,
                      old=old, new=value, type=None)

            # Copy watchers here since they may be modified inplace during iteration
            for watcher in sorted(watchers, key=lambda w: w.precedence):
                event_dispatcher.call_watcher(watcher, event)
            if not event_dispatcher.state.BATCH_WATCH:
                event_dispatcher.batch_call_watchers()
            
    def validate_and_adapt(self, value : typing.Any) -> typing.Any:
        """
        modify the given value if a proper logical reasoning can be given.
        returns modified value. Should not be mostly used unless the data stored is quite complex by structure.
        """
        # raise NotImplementedError("overload this function in child class to validate your value and adapt it if necessary.")
        return value
     
    def _post_value_set(self, obj : typing.Union['Parameterized', typing.Any], value : typing.Any) -> None:
        """Called after the parameter value has been validated and set"""

    def __getstate__(self):
        """
        All Parameters have slots, not a dict, so we have to support
        pickle and deepcopy ourselves.
        """
        
        state = {}
        for slot in self.__slots__ + self.__parent_slots__:
            state[slot] = getattr(self, slot)
        state.pop('_disable_post_slot_set')
        return state

    def __setstate__(self, state : typing.Dict[str, typing.Any]):
        """
        set values of __slots__ (instead of in non-existent __dict__)
        """
        # Handle renamed slots introduced for instance params
        # if '_attrib_name' in state:
        #     state['name'] = state.pop('_attrib_name')
        # if '_owner' in state:
        #     state['owner'] = state.pop('_owner')
        # if 'watchers' not in state:
        #     state['watchers'] = {}
        # if 'per_instance_descriptor' not in state:
        #     state['per_instance_descriptor'] = False
        # if '_label' not in state:
        #     state['_label'] = None
        with disable_post_slot_set(self):
            for (k,v) in state.items():
                setattr(self,k,v)
        
    def getter(self, func : typing.Callable) -> typing.Callable:
        self.overloads['fget'] = func 
        return func

    def setter(self, func : typing.Callable) -> typing.Callable: 
        self.overloads['fset'] = func
        return func
    
    def deleter(self, func : typing.Callable) -> typing.Callable: 
        self.overloads['fdel'] = func
        return func
    
    @classmethod
    def serialize(cls, value : typing.Any) -> typing.Any:
        "Given the parameter value, return a Python value suitable for serialization"
        return value

    @classmethod
    def deserialize(cls, value : typing.Any) -> typing.Any:
        "Given a serializable Python value, return a value that the parameter can be set to"
        return value

    def schema(self, safe : bool = False, subset : typing.Optional[typing.List] = None, 
                        mode : str = 'json') -> typing.Dict[str, typing.Any]:
        if mode not in serializers:
            raise KeyError(f"Mode {mode} not in available serialization formats {list(serializers.keys())}")
        return serializers[mode].param_schema(self.__class__.__name__, self, safe=safe, subset=subset)
    


class disable_post_slot_set:
    def __init__(self, parameter : 'Parameter'):
        self.parameter = parameter

    def __enter__(self):
        self.parameter._disable_post_slot_set = True 

    def __exit__(self, exc_type, exc_value, traceback):
        self.parameter._disable_post_slot_set = False


class parameter(Enum):
    VALUE = 'value'
    DOC = 'doc'
    CONSTANT = 'constant'
    READONLY = 'readonly'
    ALLOW_NONE = 'allow_None'
    PER_INSTANCE_DESCRIPTORS = 'per_instance_descriptor'
    DEEPCOPY_DEFAULT = 'deepcopy_default'
    CLASS_MEMBER = 'class_member'
    PRECEDENCE = 'precedence'
    OWNER = 'owner'
    NAME = 'name'
    WATCHERS = 'watchers'
    OVERLOADS = 'overload'
    # small letters creates clashes with name and value attribute


@dataclass
class Event:
    """
    Object representing an event that triggers a Watcher.
    what : What is being watched on the Parameter (either value or a slot name)
    name : Name of the Parameter that was set or triggered
    obj  : Parameterized instance owning the watched Parameter, or None
    cls  : Parameterized class owning the watched Parameter
    old  : Previous value of the item being watched
    new  : New value of the item being watched
    type : 'triggered' if this event was triggered explicitly, 'changed' if
    the item was set and watching for 'onlychanged', 'set' if the item was set,
    or  None if type not yet known
    """
    what :  typing.Union[str, Enum]
    name : str
    obj : typing.Optional[typing.Union["Parameterized", "ParameterizedMetaclass"]]
    cls : typing.Union["Parameterized", "ParameterizedMetaclass"]
    old : typing.Any
    new : typing.Any
    type: typing.Optional[str]


@contextmanager
def edit_constant(obj : typing.Union['Parameterized', 'Parameter']):
    """
    Temporarily set parameters on Parameterized object to constant=False
    to allow editing them.
    """
    if isinstance(obj, Parameterized):
        params = obj.parameters.descriptors.values()
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
    elif isinstance(obj, Parameter):
        constant = obj.constant 
        obj.constant = False
        try:
            yield
        except:
            raise
        finally:
            obj.constant = constant
    else:
        raise TypeError(f"argument to edit_constant must be a parameter or parameterized instance, given type : {type(obj)}")


@dataclass
class GeneralDependencyInfo:
    """
    Dependency info attached to a method of a Parameterized subclass. 
    """
    dependencies : typing.Tuple[typing.Union[str, Parameter]]
    queued : bool
    on_init : bool 
    invoke : bool 


@dataclass
class ParameterDependencyInfo:
    """
    Object describing something being watched about a Parameter.

    inst: Parameterized instance owning the Parameter, or None
    cls: Parameterized class owning the Parameter
    name: Name of the Parameter being watched    
    pobj: Parameter object being watched
    what: What is being watched on the Parameter (either 'value' or a slot name)
    """
    inst : typing.Optional["Parameterized"] # optional while being unbound
    cls : "ParameterizedMetaclass"
    name : str
    pobj : Parameter
    what : typing.Union[str, Enum]


@dataclass
class DynamicDependencyInfo:
    """
    Object describing dynamic dependencies.
    spec: Dependency specification to resolve
    """
    notation : str


@dataclass
class SortedDependencies:
    static : typing.List[ParameterDependencyInfo] = field(default_factory = list)
    dynamic : typing.List[DynamicDependencyInfo] = field(default_factory = list)

    def __iadd__(self, other : "SortedDependencies") -> "SortedDependencies":
        assert isinstance(other, SortedDependencies), wrap_error_text(
            f"Can only add other ResolvedDepedency types to iteself, given type {type(other)}") 
        self.static += other.static 
        self.dynamic += other.dynamic
        return self



def depends_on(*parameters, invoke : bool = True, on_init : bool = True, queued : bool = False) -> typing.Callable:
    """
    Annotates a function or Parameterized method to express its
    dependencies.  The specified dependencies can be either be
    Parameter instances or if a method is supplied they can be
    defined as strings referring to Parameters of the class,
    or Parameters of subobjects (Parameterized objects that are
    values of this object's parameters).  Dependencies can either be
    on Parameter values, or on other metadata about the Parameter.
    """
    def decorator(func):
        if not isinstance(parameters, tuple):
            deps = tuple(parameters)
        else:
            deps = parameters
        for dep in deps:
            if not isinstance(dep, (str, Parameter)):
                raise ValueError(wrap_error_text(
                    f"""The depends_on decorator only accepts string types referencing a parameter or parameter 
                        instances, found {type(dep).__name__} type instead."""))
            
        _dinfo = GeneralDependencyInfo(
                dependencies=deps,
                queued=queued, 
                on_init=on_init,
                invoke=invoke
            )
        if hasattr(func, 'param_dependency_info') and not isinstance(func.param_dependency_info, GeneralDependencyInfo):
            raise TypeError(f"attribute 'param_depency_info' reserved by param library, please use another name.")
        func.param_dependency_info = _dinfo
        return func
    return decorator



@dataclass
class Watcher:
    """
    Object declaring a callback function to invoke when an Event is
    triggered on a watched item.

    inst : Parameterized instance owning the watched Parameter, or
    None

    cls: Parameterized class owning the watched Parameter

    fn : Callback function to invoke when triggered by a watched
    Parameter

    mode: 'args' for param.watch (call fn with PInfo object
    positional args), or 'kwargs' for param.watch_values (call fn
    with <param_name>:<new_value> keywords)

    onlychanged: If True, only trigger for actual changes, not
    setting to the current value

    parameter_names: List of Parameters to watch, by name

    what: What to watch on the Parameters (either 'value' or a slot
    name)

    queued: Immediately invoke callbacks triggered during processing
            of an Event (if False), or queue them up for processing
            later, after this event has been handled (if True)

    precedence: A numeric value which determines the precedence of
                  the watcher. Lower precedence values are executed
                  with higher priority.
    """

    inst : "Parameterized"
    cls : "ParameterizedMetaclass"
    fn : typing.Callable
    mode : str
    onlychanged : bool 
    parameter_names : typing.Tuple[str]
    what : str 
    queued : bool
    precedence : typing.Union[float, int] = field(default=0)


@contextmanager
def _batch_call_watchers(parameterized : typing.Union['Parameterized', 'ParameterizedMetaclass'], 
                        queued : bool = True, run : bool = True):
    """
    Internal version of batch_call_watchers, adding control over queueing and running.
    Only actually batches events if enable=True; otherwise a no-op. Only actually
    calls the accumulated watchers on exit if run=True; otherwise they remain queued.
    """
    state = parameterized.parameters.event_dispatcher.state
    BATCH_WATCH = state.BATCH_WATCH
    state.BATCH_WATCH = queued or state.BATCH_WATCH
    try:
        yield
    finally:
        state.BATCH_WATCH = BATCH_WATCH
        if run and not BATCH_WATCH:
            parameterized.parameters.event_dispatcher.batch_call_watchers()


@contextmanager
def batch_call_watchers(parameterized : 'Parameterized'):
    """
    Context manager to batch events to provide to Watchers on a
    parameterized object.  This context manager queues any events
    triggered by setting a parameter on the supplied parameterized
    object, saving them up to dispatch them all at once when the
    context manager exits.
    """
    state = parameterized.parameters.event_dispatcher.state
    old_BATCH_WATCH = state.BATCH_WATCH 
    state.BATCH_WATCH = True
    try:
        yield
    finally:
        state.BATCH_WATCH = old_BATCH_WATCH
        if not old_BATCH_WATCH:
            parameterized.parameters.event_dispatcher.batch_call_watchers()


@contextmanager
def discard_events(parameterized : 'Parameterized'):
    """
    Context manager that discards any events within its scope
    triggered on the supplied parameterized object.
    """
    state = parameterized.parameters.event_dispatcher.state
    old_watchers = state.watchers
    old_events = state.events
    state.watchers = []
    state.events = []
    try:
        yield
    except:
        raise
    finally:
        state.watchers = old_watchers
        state.events = old_events


def _skip_event(*events : Event, **kwargs) -> bool:
    """
    Checks whether a subobject event should be skipped.
    Returns True if all the values on the new subobject
    match the values on the previous subobject.
    """
    what = kwargs.get('what', 'value')
    changed = kwargs.get('changed')
    if changed is None:
        return False
    for e in events:
        for p in changed:
            if what == 'value':
                old = NotImplemented if e.old is None else get_dot_resolved_attr(e.old, p, None)
                new = NotImplemented if e.new is None else get_dot_resolved_attr(e.new, p, None)
            else:
                old = NotImplemented if e.old is None else get_dot_resolved_attr(e.old.parameters[p], what, None)
                new = NotImplemented if e.new is None else get_dot_resolved_attr(e.new.parameters[p], what, None)
            if not Comparator.is_equal(old, new):
                return False
    return True



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
        str: operator.eq,
        bytes: operator.eq,
        type(None): operator.eq,
        type(NotImplemented) : operator.eq
    }
    equalities.update({ dtt : operator.eq for dtt in dt_types }) # type: ignore

    @classmethod    	
    def is_equal(cls, obj1 : typing.Any, obj2 : typing.Any) -> bool:
        for eq_type, eq in cls.equalities.items():
            if ((isinstance(eq_type, FunctionType) and eq_type(obj1) and eq_type(obj2))
                or (isinstance(obj1, eq_type) and isinstance(obj2, eq_type))):
                return eq(obj1, obj2)
        if isinstance(obj2, (list, set, tuple)):
            return cls.compare_iterator(obj1, obj2)
        elif isinstance(obj2, dict):
            return cls.compare_mapping(obj1, obj2)
        return False

    @classmethod
    def compare_iterator(cls, obj1 : typing.Any, obj2 : typing.Any) -> bool:
        if type(obj1) != type(obj2) or len(obj1) != len(obj2): return False
        for o1, o2 in zip(obj1, obj2):
            if not cls.is_equal(o1, o2):
                return False
        return True

    @classmethod
    def compare_mapping(cls, obj1 : typing.Any, obj2 : typing.Any) -> bool:
        if type(obj1) != type(obj2) or len(obj1) != len(obj2): return False
        for k in obj1:
            if k in obj2:
                if not cls.is_equal(obj1[k], obj2[k]):
                    return False
            else:
                return False
        return True



@dataclass
class UnresolvedWatcherInfo:
    method_name : str 
    invoke : bool 
    on_init : bool 
    static_dependencies : typing.List[ParameterDependencyInfo] 
    dynamic_dependencies : typing.List[DynamicDependencyInfo] 
    queued : bool = field(default = False)


class EventResolver:

    def __init__(self, owner_cls : 'ParameterizedMetaclass') -> None:
        self.owner_cls = owner_cls
        self._unresolved_watcher_info : typing.List[UnresolvedWatcherInfo] 

    def create_unresolved_watcher_info(self, owner_class_members : dict):
        # retrieve depends info from methods and store more conveniently
        dependers : typing.List[typing.Tuple[str, typing.Callable, GeneralDependencyInfo]] = [
            (name, method, method.param_dependency_info) for (name, method) in owner_class_members.items()
            if hasattr(method, 'param_dependency_info')]

        # Resolve dependencies of current class
        _watch : typing.List[UnresolvedWatcherInfo] = []
        for name, method, dinfo in dependers:
            if not dinfo.invoke:
                continue
            # No need MInfo
            sorted_dependencies = self.method_depends_on(method, dynamic=False)
            _watch.append(UnresolvedWatcherInfo(
                method_name=name, 
                invoke=dinfo.invoke, 
                on_init=dinfo.on_init, 
                queued=dinfo.queued,
                static_dependencies=sorted_dependencies.static, 
                dynamic_dependencies=sorted_dependencies.dynamic
            ))

        # Resolve dependencies in class hierarchy
        _inherited : typing.List[UnresolvedWatcherInfo] = []
        for mcs_super in classlist(self.owner_cls)[:-1][::-1]:
            if isinstance(mcs_super, ParameterizedMetaclass):
                for dep in mcs_super.parameters.event_resolver._unresolved_watcher_info: # type: ignore - why doesnt it work?
                    assert isinstance(dep, UnresolvedWatcherInfo),  wrap_error_text( # dummy assertion to check types
                        f"""Parameters._unresolved_watcher_info only accept UnresolvedWatcherInfo type, given type {type(dep)}""")
                    method = getattr(mcs_super, dep.method_name, None)
                    if method is not None and hasattr(method, 'param_dependency_info'): 
                        assert isinstance(method.param_dependency_info, GeneralDependencyInfo), wrap_error_text(
                            f"""attribute 'param_depency_info' reserved by param library, 
                            please use another name for your attributes of type {type(method.param_dependency_info)}."""
                        ) # dummy assertion to check types
                        dinfo : GeneralDependencyInfo = method.param_dependency_info
                        if (not any(dep.method_name == w.method_name for w in _watch+_inherited) and dinfo.invoke):
                            _inherited.append(dep)

        self._unresolved_watcher_info = _inherited + _watch
    

    def method_depends_on(self, method : typing.Callable, dynamic : bool = True, intermediate : bool = True) -> SortedDependencies:
        """
        Resolves dependencies declared on a method of Parameterized class.
        Dynamic dependencies, i.e. dependencies on sub-objects which may
        or may not yet be available, are only resolved if dynamic=True.
        By default intermediate dependencies, i.e. dependencies on the
        path to a sub-object are returned. For example for a dependency
        on 'a.b.c' dependencies on 'a' and 'b' are returned as long as
        intermediate=True.

        Returns lists of concrete dependencies on available parameters
        and dynamic dependencies specifications which have to resolved
        if the referenced sub-objects are defined.
        """
        dependencies = SortedDependencies()
        dinfo : GeneralDependencyInfo = method.param_dependency_info
        for d in dinfo.dependencies:
            _sorted_dependencies = self.convert_notation_to_dependency_info(d, dynamic, intermediate)
            dependencies.dynamic += _sorted_dependencies.dynamic
            for dep in _sorted_dependencies.static:
                if isinstance(dep, ParameterDependencyInfo):
                    dependencies.static.append(dep)
                else:
                    dependencies += self.method_depends_on(dep, dynamic, intermediate)
        return dependencies
    
           
    def convert_notation_to_dependency_info(self, depended_obj_notation : typing.Union[Parameter, str], 
                        owner_inst : typing.Optional["Parameterized"] = None, dynamic : bool = True, 
                        intermediate : bool = True) -> SortedDependencies:
        """
        Resolves a dependency specification into lists of explicit
        parameter dependencies and dynamic dependencies.

        Dynamic dependencies are specifications to be resolved when
        the sub-object whose parameters are being depended on is
        defined.

        During class creation set dynamic=False which means sub-object
        dependencies are not resolved. At instance creation and
        whenever a sub-object is set on an object this method will be
        invoked to determine whether the dependency is available.

        For sub-object dependencies we also return dependencies for
        every part of the path, e.g. for a dependency specification
        like "a.b.c" we return dependencies for sub-object "a" and the
        sub-sub-object "b" in addition to the dependency on the actual
        parameter "c" on object "b". This is to ensure that if a
        sub-object is swapped out we are notified and can update the
        dynamic dependency to the new object. Even if a sub-object
        dependency can only partially resolved, e.g. if object "a"
        does not yet have a sub-object "b" we must watch for changes
        to "b" on sub-object "a" in case such a subobject is put in "b".
        """
        if isinstance(depended_obj_notation, Parameter):
            if not intermediate:
                inst = depended_obj_notation.owner if isinstance(depended_obj_notation.owner, Parameterized) else None
                cls = depended_obj_notation.owner
                if not isinstance(cls, ParameterizedMetaclass):
                    raise TypeError(wrap_error_text("""Currently dependencies of a parameter from another class except a subclass 
                                    of parameterized is not supported"""))
                info = ParameterDependencyInfo(inst=inst, cls=cls, name=depended_obj_notation.name,
                            pobj=depended_obj_notation, what=parameter.VALUE)
                return SortedDependencies(static=[info])
            return SortedDependencies() 
        
        obj, attr, what = self.parse_notation(depended_obj_notation)
        if obj is None:
            src = owner_inst or self.owner_cls
        elif not dynamic:
            return SortedDependencies(dynamic=[DynamicDependencyInfo(notation=depended_obj_notation)])
        else:
            src = get_dot_resolved_attr(owner_inst or self.owner_cls, obj[1::], NotImplemented)
            if src == NotImplemented:
                path = obj[1:].split('.')
                static_deps = []
                # Attempt to partially resolve subobject path to ensure
                # that if a subobject is later updated making the full
                # subobject path available we have to be notified and
                # set up watchers
                if len(path) >= 1 and intermediate:
                    sub_src = None
                    subpath = path
                    while sub_src is None and subpath:
                        subpath = subpath[:-1]
                        sub_src = get_dot_resolved_attr(owner_inst or self.owner_cls, '.'.join(subpath), None)
                    if subpath:
                        static_deps += self.convert_notation_to_dependency_info(
                            '.'.join(path[:len(subpath)+1]), owner_inst, dynamic, intermediate).static
                return SortedDependencies(
                    static=static_deps,
                    dynamic=[] if intermediate else [DynamicDependencyInfo(notation=depended_obj_notation)]
                ) 
           
        cls =  (src, None) if isinstance(src, type) else (type(src), src)
        if attr == 'parameters':
            assert isinstance(obj, str), wrap_error_text("""object preceding parameters access (i.e. <name of obj>.parameters)
              in dependency resolution became None due to internal error.""")
            sorted_dependencies = self.convert_notation_to_dependency_info(obj[1:], 
                                                                           dynamic, intermediate)
            for p in src.parameters:
                sorted_dependencies += src.parameters.event_resolver.convert_notation_to_dependency_info(p, 
                                                                                            dynamic, intermediate)
            return sorted_dependencies
        elif attr in src.parameters:
            info = ParameterDependencyInfo(inst=owner_inst, cls=src, name=attr,
                         pobj=src.parameters[attr], what=what)
            if obj is None or not intermediate:
                return SortedDependencies(static=[info])
            sorted_dependencies = self.convert_notation_to_dependency_info(obj[1:], dynamic, intermediate)
            if not intermediate:
                sorted_dependencies.static.append(info)
            return sorted_dependencies
        elif hasattr(src, attr):
            attr_obj = getattr(src, attr)
            if isinstance(attr_obj, Parameterized):
                return SortedDependencies()
            elif isinstance(attr_obj, FunctionType):
                raise NotImplementedError(wrap_error_text(
                    f"""In this version of param, support for dependency on other callbacks is removed.
                    Please divide your methods with your own logic. 
                    """))
            else:
                raise AttributeError(wrap_error_text(
                    f"""Attribute {attr!r} could not be resolved on {src} or resolved attribute not supported 
                    for dependent events"""))
        else:
            raise AttributeError(f"Attribute {attr!r} could not be resolved on {src}.")

        
    @classmethod
    def parse_notation(cls, notation : str) -> typing.Tuple[typing.Union[str, None], str, str]:
        """
        Parses param.depends specifications into three components:

        1. The dotted path to the sub-object
        2. The attribute being depended on, i.e. either a parameter or method
        3. The parameter attribute being depended on
        """
        assert notation.count(":") <= 1, "argument '{notation}' for depends has more than one colon"
        notation = notation.strip()
        m = re.match(r"(?P<path>[^:]*):?(?P<what>.*)", notation)
        assert m is not None, f"could not parse object notation for finding dependecies {notation}"
        what = m.group('what')
        path = "."+m.group('path')
        m = re.match(r"(?P<obj>.*)(\.)(?P<attr>.*)", path)
        assert m is not None, f"could not parse object notation for finding dependecies {notation}"
        obj = m.group('obj')
        attr = m.group("attr")
        return obj or None, attr, what or 'value'
    

    def bind_static_dependencies(self, obj : "Parameterized", 
                    static_dependencies : typing.List[ParameterDependencyInfo] = []) -> typing.List["ParameterDependencyInfo"]:
        """
        Resolves constant and dynamic parameter dependencies previously
        obtained using the method_depends_on function. Existing resolved
        dependencies are updated with a supplied parameter instance while
        dynamic dependencies are resolved if possible.
        """
        dependencies = []
        for dep in static_dependencies:
            if not issubclass(type(obj), dep.cls):
                dependencies.append(dep)
                continue
            dep.inst = obj if dep.inst is None else dep.inst
            dep.pobj = dep.inst.parameters[dep.name]
            dependencies.append(dep)
        return dependencies


    def attempt_conversion_from_dynamic_to_static_dep(self, obj : "Parameterized",  
                            dynamic_dependencies : typing.List[DynamicDependencyInfo] = [],
                            intermediate : bool = True):
        dependencies = []
        for dep in dynamic_dependencies:
            subresolved = obj.parameters.event_resolver.convert_notation_to_dependency_info(dep.notation, 
                                                            intermediate=intermediate).static
            for subdep in subresolved:
                if isinstance(subdep, ParameterDependencyInfo):
                    subdep.inst = obj if subdep.inst is None else subdep.inst
                    subdep.pobj = subdep.inst.parameters[subdep.name]
                    dependencies.append(subdep)
                else:
                    dependencies += self.method_depends_on(subdep, intermediate=intermediate).static
        return dependencies
    

    def resolve_dynamic_dependencies(self, obj : 'Parameterized', dynamic_dep : DynamicDependencyInfo, 
                    param_dep : ParameterDependencyInfo, attribute : str) -> typing.Tuple:
        """
        If a subobject whose parameters are being depended on changes
        we should only trigger events if the actual parameter values
        of the new object differ from those on the old subobject,
        therefore we accumulate parameters to compare on a subobject
        change event.

        Additionally we need to make sure to notify the parent object
        if a subobject changes so the dependencies can be
        reinitialized so we return a callback which updates the
        dependencies.
        """
        subobj = obj
        subobjs : typing.List = [obj]
        for subpath in dynamic_dep.notation.split('.')[:-1]:
            subobj = getattr(subobj, subpath.split(':')[0], None)
            subobjs.append(subobj)

        dep_obj = param_dep.inst or param_dep.cls
        if dep_obj not in subobjs[:-1]:
            return None, None, param_dep.what

        depth = subobjs.index(dep_obj)
        callback = None
        if depth > 0:
            def callback(*events):
                """
                If a subobject changes, we need to notify the main
                object to update the dependencies.
                """
                obj.parameters.event_dispatcher.update_dynamic_dependencies(attribute)

        p = '.'.join(dynamic_dep.notation.split(':')[0].split('.')[depth+1:])
        if p == 'param':
            subparams = [sp for sp in list(subobjs[-1].parameters)]
        else:
            subparams = [p]

        if ':' in dynamic_dep.notation:
            what = dynamic_dep.notation.split(':')[-1]
        else:
            what = param_dep.what

        return subparams, callback, what
    


class EventDispatcherState:

    def __init__(self):
        self._BATCH_WATCH : typing.Dict[int, bool] = {} # If true, Event and watcher objects are queued.
        self._TRIGGER : typing.Dict[int, bool] = {}
        self._events : typing.Dict[int, typing.List[Event]] = {} # Queue of batched events
        self._watchers : typing.Dict[int, typing.List[Watcher]] = {} # Queue of batched watchers
        
    @property
    def BATCH_WATCH(self) -> bool:
        return self._BATCH_WATCH[threading.get_ident()]

    @BATCH_WATCH.setter
    def BATCH_WATCH(self, value : bool):
        self._BATCH_WATCH[threading.get_ident()] = value

    @property
    def TRIGGER(self):
        return self._TRIGGER[threading.get_ident()]

    @TRIGGER.setter
    def TRIGGER(self, value):
        self._TRIGGER[threading.get_ident()] = value

    @property
    def events(self) -> typing.List[Event]:
        thread_id = threading.get_ident()
        try:
            return self._events[thread_id]
        except KeyError:
            self._events[thread_id] = []
            return self._events[thread_id]
            
    @events.setter
    def events(self, value):
        self._events[threading.get_ident()] = value

    @property
    def watchers(self) -> typing.List[Watcher]:
        return self._watchers[threading.get_ident()]

    @watchers.setter
    def watchers(self, value):
        self._watchers[threading.get_ident()] = value



class EventDispatcher:

    # This entire class is supposed to be instantiated as a private variable, therefore we dont use underscores
    # for variables within this class 
     
    def __init__(self, owner_inst : typing.Union['Parameterized', 'ParameterizedMetaclass'], 
                    event_resolver : EventResolver) -> None:
        self.owner_inst = owner_inst 
        self.owner_class = event_resolver.owner_cls
        self.event_resolver = event_resolver
        self.all_watchers : typing.Dict[str, typing.Dict[str, typing.List[Watcher]]] = {}
        self.dynamic_watchers : typing.Dict[str, typing.List[Watcher]] = defaultdict(list)
        self.state : EventDispatcherState = EventDispatcherState()


    def prepare_instance_dependencies(self):
        init_methods = []
        for watcher_info in self.event_resolver._unresolved_watcher_info:
            static = defaultdict(list)
            for dep in self.event_resolver.bind_static_dependencies(self.owner_inst, watcher_info.static_dependencies):
                static[(id(dep.inst), id(dep.cls), dep.what)].append((dep, None))
            for group in static.values():
                self.watch_group(self.owner_inst, watcher_info.method_name, watcher_info.invoke, group)
            m = getattr(self.owner_inst, watcher_info.method_name)
            if watcher_info.on_init and m not in init_methods:
                init_methods.append(m)

        self.update_dynamic_dependencies()
        for m in init_methods:
            m()


    def update_dynamic_dependencies(self, attribute : typing.Optional[str] = None) -> None:
        for watcher_info in self.event_resolver._unresolved_watcher_info:
            # On initialization set up constant watchers; otherwise
            # clean up previous dynamic watchers for the updated attribute
            dynamic = [d for d in watcher_info.dynamic_dependencies if attribute is None or 
                        d.notation.split(".")[0] == attribute]
            if len(dynamic) > 0:
                for w in self.dynamic_watchers.pop(watcher_info.method_name, []):
                    (w.inst or w.cls).parameters.event_dispatcher.deregister_watcher(w)
                # Resolve dynamic dependencies one-by-one to be able to trace their watchers
                grouped = defaultdict(list)
                for ddep in dynamic:
                    for dep in self.event_resolver.attempt_conversion_from_dynamic_to_static_dep(self.owner_inst,
                                                            dynamic_dependencies=[ddep]):
                        grouped[(id(dep.inst), id(dep.cls), dep.what)].append((dep, ddep))

                for group in grouped.values():
                    watcher = self.watch_group(self.owner_inst, watcher_info.method_name, watcher_info.invoke, 
                                        group, attribute)
                    self.dynamic_watchers[watcher_info.method_name].append(watcher)
        

    def watch_group(self, obj : "Parameterized", name : str, queued : bool, group : typing.List[typing.Tuple], 
                     attribute : typing.Optional[str] = None):
        """
        Sets up a watcher for a group of dependencies. Ensures that
        if the dependency was dynamically generated we check whether
        a subobject change event actually causes a value change and
        that we update the existing watchers, i.e. clean up watchers
        on the old subobject and create watchers on the new subobject.
        """
        some_param_dep, dynamic_dep = group[0]
        dep_obj : typing.Union[ParameterizedMetaclass, Parameterized] = some_param_dep.inst or some_param_dep.cls
        params = []
        for p in group:
            if p.name not in params:
                params.append(p.name)

        if dynamic_dep is None or len(dynamic_dep) == 0:
            subparams, callback, what = None, None, some_param_dep.what
        else:
            subparams, callback, what = self.event_resolver.resolve_dynamic_dependencies(
                obj, dynamic_dep, some_param_dep, attribute)

        executor = self.create_method_caller(obj, name, what, subparams, callback)
        return dep_obj.parameters.event_dispatcher.watch(
            executor, params, some_param_dep.what, queued=queued, precedence=-1)
    

    def create_method_caller(self, bound_inst : typing.Union["ParameterizedMetaclass", "Parameterized"], 
                method_name : str, what : str = 'value', changed : typing.Optional[typing.List] = None, callback=None):
        """
        Wraps a method call adding support for scheduling a callback
        before it is executed and skipping events if a subobject has
        changed but its values have not.
        """
        function = getattr(bound_inst, method_name)
        if iscoroutinefunction(function):
            async def caller(*events): # type: ignore
                if callback: callback(*events)
                if not _skip_event(*events, what=what, changed=changed):
                    await function() 
        else:
            def caller(*events):
                if callback: callback(*events)
                if not _skip_event(*events, what=what, changed=changed):
                    return function()
        caller._watcher_name = method_name
        return caller
    

    def watch(self, fn : typing.Callable, parameter_names : typing.Union[typing.List[str], str], what : str = 'value', 
            onlychanged : bool = True, queued : bool = False, precedence : float = -1):
        parameter_names = tuple(parameter_names) if isinstance(parameter_names, list) else (parameter_names,) # type: ignore
        watcher = Watcher(inst=self.owner_inst, cls=self.owner_class, fn=fn, mode='args',
                          onlychanged=onlychanged, parameter_names=parameter_names, # type: ignore
                          what=what, queued=queued, precedence=precedence)
        self.register_watcher(watcher, what)
        return watcher
    

    def register_watcher(self, watcher : Watcher, what = 'value'):
        parameter_names = watcher.parameter_names
        for parameter_name in parameter_names:
            # Execution should never reach here if parameter is not found. 
            # this should be solved in resolution itself - TODO - make sure
            # if parameter_name not in self_.cls.param:
            #     raise ValueError("{} parameter was not found in list of "
            #                      "parameters of class {}".format(parameter_name, self_.cls.__name__))
            if self.owner_inst is not None and what == "value":  
                if parameter_name not in self.all_watchers:
                    self.all_watchers[parameter_name] = {}
                if what not in self.all_watchers[parameter_name]:
                    self.all_watchers[parameter_name][what] = []
                self.all_watchers[parameter_name][what].append(watcher)
            else:
                watchers = self.owner_inst.parameters[parameter_name].watchers
                if what not in watchers:
                    watchers[what] = []
                watchers[what].append(watcher)

    
    def deregister_watcher(self, watcher : Watcher, what = 'value'):
        parameter_names = watcher.parameter_names
        for parameter_name in parameter_names:
            if self.owner_inst is not None and what == "value":
                if parameter_name not in self.all_watchers or what not in self.all_watchers[parameter_name]:
                    return
                self.all_watchers[parameter_name][what].remove(watcher)
            else:
                watchers = self.owner_inst.parameters[parameter_name].watchers
                if what not in watchers:
                    return
                watchers[what].remove(watcher)


    def call_watcher(self, watcher : Watcher, event : Event) -> None:
        """
        Invoke the given watcher appropriately given an Event object.
        """
        if watcher.onlychanged and not Comparator.is_equal(event.old, event.new):
            return

        if self.state.BATCH_WATCH:
            self.state.events.append(event)
            if not any(watcher is w for w in self.state.watchers):
                self.state.watchers.append(watcher)
        else:
            with _batch_call_watchers(self.owner_inst or self.owner_class, 
                            queued=watcher.queued, run=False):
                self.execute_watcher(watcher, (event,))
                

    def batch_call_watchers(self):
        """
        Batch call a set of watchers based on the parameter value
        settings in kwargs using the queued Event and watcher objects.
        """
        watchers = self.state.watchers
        events = self.state.events 
        while len(events) > 0:
            event = events.pop(0)
            for watcher in sorted(watchers, key=lambda w: w.precedence):
                with _batch_call_watchers(self.owner_inst or self.owner_class, 
                                queued=watcher.queued, run=False):
                    self.execute_watcher(watcher, (event,))
        events.clear()
        watchers.clear()


    def execute_watcher(self, watcher : Watcher, events : typing.Tuple[Event]):
        if watcher.mode == 'args': 
            args, kwargs = events, {}
        else:
            args, kwargs = (), {event.name: event.new for event in events}

        if iscoroutinefunction(watcher.fn):
            if async_executor is None:
                raise RuntimeError(wrap_error_text(f"""Could not execute {watcher.fn} coroutine function. Please 
                    register a asynchronous executor on param.parameterized.async_executor, which 
                    schedules the function on an event loop."""))
            async_executor(partial(watcher.fn, *args, **kwargs))
        else:
            watcher.fn(*args, **kwargs)


    def trigger(self, *parameters : str) -> None:
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
        param_values = self_.values()
        params = {name: param_values[name] for name in param_names}
        self.self_or_cls.param._TRIGGER = True
        self.update(dict(params, **triggers))
        self.self_or_cls.param._TRIGGER = False
        self.self_or_cls.param._events += events
        self.self_or_cls.param._watchers += watchers
    
    

class ClassParameters(object):
    """
    Object that holds the namespace and implementation of Parameterized
    methods as well as any state that is not in __slots__ or the
    Parameters themselves.

    Exists at metaclass level (instantiated by the metaclass)
    and at the instance level. Contains state specific to the
    class.
    """

    def __init__(self, owner_cls : 'ParameterizedMetaclass', owner_class_members : typing.Optional[dict] = None) -> None:
        """
        cls is the Parameterized class which is always set.
        self is the instance if set.
        """
        self.owner_cls = owner_cls         
        self.owner_inst = None
        if owner_class_members is not None:
            self.event_resolver = EventResolver(owner_cls=owner_cls)
            self.event_dispatcher = EventDispatcher(owner_cls, self.event_resolver)
            self.event_resolver.create_unresolved_watcher_info(owner_class_members)
        
    def __getitem__(self, key : str) -> 'Parameter':
        """
        Returns the class or instance parameter like a dictionary dict[key] syntax lookup
        """
        # code change comment -
        # metaclass instance has a param attribute remember, no need to repeat logic of self_.self_or_cls
        # as we create only one instance of Parameters object 
        return self.descriptors[key] # if self.owner_inst is None else self.owner_inst.param.objects(False)
  
    def __dir__(self) -> typing.List[str]:
        """
        Adds parameters to dir
        """
        return super().__dir__() + self.descriptors().keys() # type: ignore

    def __iter__(self):
        """
        Iterates over the parameters on this object.
        """
        yield from self.descriptors

    def __contains__(self, param : 'Parameter') -> bool:
        return param in list(self) 
    
    @property
    def owner(self):
        return self.owner_inst if self.owner_inst is not None else self.owner_cls
    
    @property
    def descriptors(self) -> typing.Dict[str, 'Parameter']:
        try:
            paramdict = getattr(self.owner_cls, '__%s_params__' % self.owner_cls.__name__)
        except AttributeError:
            paramdict = {}
            for class_ in classlist(self.owner_cls):
                if class_ == object or class_ == type: 
                    continue
                for name, val in class_.__dict__.items():
                    if isinstance(val, Parameter):
                        paramdict[name] = val
            # We only want the cache to be visible to the cls on which
            # params() is called, so we mangle the name ourselves at
            # runtime (if we were to mangle it now, it would be
            # _Parameterized.__params for all classes).
            # print(self.owner_cls, '__%s_params__' % self.owner_cls.__name__, paramdict)
            setattr(self.owner_cls, '__%s_params__' % self.owner_cls.__name__, paramdict)
        return paramdict

    @property
    def names(self) -> typing.Iterable[str]:
        return self.descriptors.keys()

    @property
    def defaults(self):
        """Print the default values of all cls's Parameters."""
        defaults = {}
        for key, val in self.descriptors.items():
            defaults[key] = val.default
        return defaults
    
    @property
    def values(self, onlychanged : bool = False):
        """
        Return a dictionary of name,value pairs for the Parameters of this
        object.

        When called on an instance with onlychanged set to True, will
        only return values that are not equal to the default value
        (onlychanged has no effect when called on a class).
        """
        self_or_cls = self_.self_or_cls
        vals = []
        for name, val in self_or_cls.param.objects('existing').items():
            value = self_or_cls.param.get_value_generator(name)
            if not onlychanged or not all_equal(value, val.default):
                vals.append((name, value))

        vals.sort(key=itemgetter(0))
        return dict(vals)
    
    def serialize(self, subset : typing.Optional[typing.List[str]] = None, 
                                            mode : typing.Optional[str] = 'json') -> typing.Dict[str, str]:
        if mode not in serializers:
            raise ValueError(f'Mode {mode} not in available serialization formats {serializers.keys()}')
        serializer = serializers[mode]
        return serializer.serialize_parameters(self.owner, subset=subset)

    def serialize_value(self, parameter_name : str, mode : typing.Optional[str] = 'json') -> str:
        if mode not in serializers:
            raise ValueError(f'Mode {mode} not in available serialization formats {serializers.keys()}')
        serializer = serializers[mode]
        return serializer.serialize_parameter_value(self.owner, parameter_name)

    def deserialize(self, serialization : str, subset : typing.Optional[typing.List[str]] = None, 
                               mode : typing.Optional[str] = 'json') -> typing.Dict[str, typing.Any]:
        if mode not in serializers:
            raise ValueError(f'Mode {mode} not in available serialization formats {serializers.keys()}')
        serializer = serializers[mode]
        return serializer.deserialize_parameters(self.owner, serialization, subset=subset)

    def deserialize_value(self, parameter_name : str, value : str, mode : str = 'json'): 
        if mode not in serializers:
            raise ValueError(f'Mode {mode} not in available serialization formats {serializers.keys()}')
        serializer = serializers[mode]
        return serializer.deserialize_parameter_value(self.owner, parameter_name, value)

    def schema(self, safe : bool = False, subset : typing.Optional[typing.List[str]] = None, 
                               mode : typing.Optional[str] = 'json') -> typing.Dict[str, typing.Any]:
        """
        Returns a schema for the parameters on this Parameterized object.
        """
        if mode not in serializers:
            raise ValueError(f'Mode {mode} not in available serialization formats {serializers.keys()}')
        serializer = serializers[mode]
        return serializer.schema(self.owner, safe=safe, subset=subset)

     

class InstanceParameters(ClassParameters):

    def __init__(self, owner_cls : 'ParameterizedMetaclass', owner_inst : 'Parameterized') -> None:
        super().__init__(owner_cls=owner_cls, owner_class_members=None)
        self.owner_inst = owner_inst
        self._instance_params = {}
        self.event_resolver = self.owner_cls.parameters.event_resolver
        self.event_dispatcher = EventDispatcher(owner_inst, self.event_resolver)
        self.event_dispatcher.prepare_instance_dependencies()
                

    def _setup_parameters(self, **parameters):
        """
        Initialize default and keyword parameter values.

        First, ensures that all Parameters with 'deepcopy_default=True'
        (typically used for mutable Parameters) are copied directly
        into each object, to ensure that there is an independent copy
        (to avoid surprising aliasing errors).  Then sets each of the
        keyword arguments, warning when any of them are not defined as
        parameters.

        Constant Parameters can be set during calls to this method.
        """
        ## Deepcopy all 'deepcopy_default=True' parameters
        # (building a set of names first to avoid redundantly
        # instantiating a later-overridden parent class's parameter)
        param_default_values_to_deepcopy = {}
        param_descriptors_to_deepcopy = {}
        for (k, v) in self.owner_cls.parameters.descriptors.items():
            if v.deepcopy_default and k != "name":
                # (avoid replacing name with the default of None)
                param_default_values_to_deepcopy[k] = v
            if v.per_instance_descriptor and k != "name":
                param_descriptors_to_deepcopy[k] = v

        for p in param_default_values_to_deepcopy.values():
            self._deep_copy_param_default(p)
        for p in param_descriptors_to_deepcopy.values():
            self._deep_copy_param_descriptor(p)

        ## keyword arg setting
        if len(parameters) > 0:
            descs = self.descriptors
            for name, val in parameters.items():
                desc = descs.get(name, None) # pylint: disable-msg=E1101
                if desc:
                    setattr(self.owner_inst, name, val)
                # Its erroneous to set a non-descriptor (& non-param-descriptor) with a value from init. 
                # we dont know what that value even means, so we silently ignore


    def _deep_copy_param_default(self, param_obj : 'Parameter') -> None:
        # deepcopy param_obj.default into self.__dict__ (or dict_ if supplied)
        # under the parameter's _internal_name (or key if supplied)
        _old = self.owner_inst.__dict__.get(param_obj._internal_name, NotImplemented) 
        _old = _old if _old is not NotImplemented else param_obj.default
        new_object = copy.deepcopy(_old)
        # remember : simply setting in the dict does not activate post setter and remaining logic which is sometimes important
        self.owner_inst.__dict__[param_obj._internal_name] = new_object


    def _deep_copy_param_descriptor(self, param_obj : Parameter):
        param_obj_copy = copy.deepcopy(param_obj)
        self._instance_params[param_obj.name] = param_obj_copy


    def add_parameter(self, param_name: str, param_obj: Parameter) -> None:
        setattr(self.owner_inst, param_name, param_obj)
        if param_obj.deepcopy_default:
            self._deep_copy_param_default(param_obj)
        try:
            delattr(self.owner_cls, '__%s_params__'%self.owner_cls.__name__)
        except AttributeError:
            pass


    @property
    def descriptors(self) -> typing.Dict[str, 'Parameter']:
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
        # We cache the parameters because this method is called often,
        # and parameters are rarely added (and cannot be deleted)      
        return dict(super().descriptors, **self._instance_params)
    
    

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
    def __init__(mcs, name : str, bases : typing.Tuple, dict_ : dict) -> None:
        """
        Initialize the class object (not an instance of the class, but
        the class itself).
        """
        type.__init__(mcs, name, bases, dict_)
        mcs._create_param_container(dict_)
        mcs._update_docstring_signature(dict_.get('parameterized_docstring_signature', False))

    def _create_param_container(mcs, mcs_members : dict):
        mcs._param_container = ClassParameters(mcs, mcs_members) # value return when accessing cls/self.param
  
    @property
    def parameters(mcs) -> ClassParameters:
        return mcs._param_container

    def _update_docstring_signature(mcs, do : bool = True) -> None:
        """
        Autogenerate a keyword signature in the class docstring for
        all available parameters. This is particularly useful in the
        IPython Notebook as IPython will parse this signature to allow
        tab-completion of keywords.

        max_repr_len: Maximum length (in characters) of value reprs.
        """
        if do:
            processed_kws, keyword_groups = set(), []
            for cls in reversed(mcs.mro()):
                keyword_group = []
                for (k, v) in sorted(cls.__dict__.items()):
                    if isinstance(v, Parameter) and k not in processed_kws:
                        param_type = v.__class__.__name__
                        keyword_group.append("%s=%s" % (k, param_type))
                        processed_kws.add(k)
                keyword_groups.append(keyword_group)

            keywords = [el for grp in reversed(keyword_groups) for el in grp]
            class_docstr = "\n" + mcs.__doc__ if mcs.__doc__ else ''
            signature = "params(%s)" % (", ".join(keywords))
            description = param_pager(mcs) if param_pager else ''
            mcs.__doc__ = signature + class_docstr + '\n' + description # type: ignore
    
    def __setattr__(mcs, attribute_name : str, value : typing.Any) -> None:
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
        if attribute_name != '_param_container' and attribute_name != '__%s_params__' % mcs.__name__:
            parameter = mcs.parameters.descriptors.get(attribute_name, None)
            # checking isinstance(value, Parameter) will not work for ClassSelector 
            # and besides value is anyway validated. On the downside, this does not allow
            # altering of parameter instances if class already of the parameter with attribute_name
            if parameter: # and not isinstance(value, Parameter): 
                # if owning_class != mcs:
                #     parameter = copy.copy(parameter)
                #     parameter.owner = mcs
                #     type.__setattr__(mcs, attribute_name, parameter)
                mcs.__dict__[attribute_name].__set__(mcs, value)
                return
                # set with None should not supported as with mcs it supports 
                # class attributes which can be validated
        type.__setattr__(mcs, attribute_name, value)
            

   
class Parameterized(metaclass=ParameterizedMetaclass):
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
    def __init__(self, **params):
        self.create_param_containers(**params)
        
    def create_param_containers(self, **params):
        self._param_container = InstanceParameters(self.__class__, self)
        self._param_container._setup_parameters(**params)
    
    @property
    def parameters(self) -> InstanceParameters:
        return self._param_container
        
    # 'Special' methods
    def __getstate__(self):
        """
        Save the object's state: return a dictionary that is a shallow
        copy of the object's __dict__ and that also includes the
        object's __slots__ (if it has any).
        """
        state = self.__dict__.copy()
        for slot in get_occupied_slots(self):
            state[slot] = getattr(self, slot)
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




# As of Python 2.6+, a fn's **args no longer has to be a
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

    def __init__(self, overridden : Parameterized, dict_ : typing.Dict[str, typing.Any], 
                allow_extra_keywords : bool = False) -> None:
        """
        If allow_extra_keywords is False, then all keys in the
        supplied dict_ must match parameter names on the overridden
        object (otherwise a warning will be printed).

        If allow_extra_keywords is True, then any items in the
        supplied dict_ that are not also parameters of the overridden
        object will be available via the extra_keywords() method.
        """
        # This method should be fast because it's going to be
        # called a lot. This _might_ be faster (not tested):
        #  def __init__(self,overridden,**kw):
        #      ...
        #      dict.__init__(self,**kw)
        self._overridden = overridden
        dict.__init__(self, dict_)
        if allow_extra_keywords:
            self._extra_keywords = self._extract_extra_keywords(dict_)
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
        return getattr(self._overridden, name)

    def __repr__(self):
        # As dict.__repr__, but indicate the overridden object
        return dict.__repr__(self) + " overriding params from %s"%repr(self._overridden)

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
            self.__setitem__(name, val)
        else:
            dict.__setattr__(self, name, val)

    def get(self, key, default = None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self.__dict__ or key in self._overridden.parameters

    def _check_params(self,params):
        """
        Print a warning if params contains something that is not a
        Parameter of the overridden object.
        """
        overridden_object_params = list(self._overridden.parameters)
        for item in params:
            if item not in overridden_object_params:
                self.param.warning("'%s' will be ignored (not a Parameter).",item)

    def _extract_extra_keywords(self,params):
        """
        Return any items in params that are not also
        parameters of the overridden object.
        """
        extra_keywords = {}
        overridden_object_params = list(self._overridden.parameters)
        for name, val in params.items():
            if name not in overridden_object_params:
                extra_keywords[name]=val
                # Could remove name from params (i.e. del params[name])
                # so that it's only available via extra_keywords()
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
    def __str__(self):
        return self.__class__.__name__ + "()"

    def __call__(self, *args, **kw):
        raise NotImplementedError("Subclasses must implement __call__.")

    def __reduce__(self):
        # Control reconstruction (during unpickling and copying):
        # ensure that ParameterizedFunction.__new__ is skipped
        state = ParameterizedFunction.__getstate__(self)
        # Here it's necessary to use a function defined at the
        # module level rather than Parameterized.__new__ directly
        # because otherwise pickle will find .__new__'s module to be
        # __main__. Pretty obscure aspect of pickle.py...
        return (_new_parameterized, (self.__class__,), state)

    def __new__(cls, *args, **params):
        # Create and __call__() an instance of this class.
        inst = super().__new__(cls)
        return inst.__call__(*args, **params)



def descendents(class_ : type) -> typing.List[type]:
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


def param_union(*parameterizeds : Parameterized, warn_duplicate : bool = False):
    """
    Given a set of Parameterized objects, returns a dictionary
    with the union of all param name, value pairs across them.
    If warn is True (default), prints a warning if the same parameter has
    been given multiple values; otherwise uses the last value
    """
    d = dict()
    for o in parameterizeds:
        for k in o.parameters:
            if k != 'name':
                if k in d and warn_duplicate:
                    print(f"overwriting parameter {k}") 
                d[k] = getattr(o, k)
    return d


def parameterized_class(name, params, bases = Parameterized):
    """
    Dynamically create a parameterized class with the given name and the
    supplied parameters, inheriting from the specified base(s).
    """
    if not (isinstance(bases, list) or isinstance(bases, tuple)):
        bases=[bases]
    return type(name, tuple(bases), params)

