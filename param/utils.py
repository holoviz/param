from collections import OrderedDict
import sys
import inspect
import typing
from functools import reduce, partial


def classlist(class_ : typing.Any) -> typing.Tuple[type]:
    """
    Return a list of the class hierarchy above (and including) the given class.

    Same as `inspect.getmro(class_)[::-1]`
    """
    return inspect.getmro(class_)[::-1]
    

def get_dot_resolved_attr(obj : typing.Any, attr : str, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return reduce(_getattr, [obj] + attr.split('.'))


def iscoroutinefunction(function : typing.Callable) -> bool:
    """
    Whether the function is an asynchronous coroutine function.
    """
    import asyncio
    try:
        return (
            inspect.isasyncgenfunction(function) or
            asyncio.iscoroutinefunction(function)
        )
    except AttributeError:
        return False
    

def get_method_owner(method : typing.Callable) -> typing.Any:
    """
    Gets the instance that owns the supplied method
    """
    if not inspect.ismethod(method):
        return None
    if isinstance(method, partial):
        method = method.func
    return method.__self__ if sys.version_info.major >= 3 else method.im_self


def is_ordered_dict(d):
    """
    Predicate checking for ordered dictionaries. OrderedDict is always
    ordered, and vanilla Python dictionaries are ordered for Python 3.6+
    """
    py3_ordered_dicts = (sys.version_info.major == 3) and (sys.version_info.minor >= 6)
    vanilla_odicts = (sys.version_info.major > 3) or py3_ordered_dicts
    return isinstance(d, OrderedDict)or (vanilla_odicts and isinstance(d, dict))


def get_all_slots(class_):
    """
    Return a list of slot names for slots defined in `class_` and its
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
            if hasattr(instance, slot)]




__all__ = ['classlist', 'get_dot_resolved_attr', 'iscoroutinefunction', 'get_method_owner', 'get_all_slots', 
        'get_occupied_slots']