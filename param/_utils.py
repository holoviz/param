from __future__ import annotations

import asyncio
import collections
import contextvars
import datetime as dt
import functools
import inspect
import numbers
import os
import re
import sys
import traceback
import warnings
from collections import OrderedDict, abc, defaultdict
from contextlib import contextmanager
from numbers import Real
from textwrap import dedent
from threading import get_ident
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec

    P = ParamSpec("P")
    R = TypeVar("R")
    CallableT = TypeVar("CallableT", bound=Callable)

DEFAULT_SIGNATURE = inspect.Signature([
    inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    inspect.Parameter('params', inspect.Parameter.VAR_KEYWORD),
])

MUTABLE_TYPES = (abc.MutableSequence, abc.MutableSet, abc.MutableMapping)

class ParamWarning(Warning):
    """Base Param Warning"""

class ParamPendingDeprecationWarning(ParamWarning, PendingDeprecationWarning):
    """
    Param PendingDeprecationWarning

    This warning type is useful when the warning is not meant to be displayed
    to REPL/notebooks users, as DeprecationWarning are displayed when triggered
    by code in __main__ (__name__ == '__main__' in a REPL).
    """


class ParamDeprecationWarning(ParamWarning, DeprecationWarning):
    """
    Param DeprecationWarning

    Ignored by default except when triggered by code in __main__
    """


class ParamFutureWarning(ParamWarning, FutureWarning):
    """
    Param FutureWarning

    Always displayed.
    """

class Skip(Exception):
    """Exception that allows skipping an update when resolving a reference."""

def _deprecated(extra_msg="", warning_cat=ParamDeprecationWarning):
    def decorator(func):
        """Internal decorator used to mark functions/methods as deprecated."""
        @functools.wraps(func)
        def inner(*args, **kwargs):
            msg = f"{func.__name__!r} has been deprecated and will be removed in a future version."
            if extra_msg:
                em = dedent(extra_msg)
                em = em.strip().replace('\n', ' ')
                msg = msg + ' ' + em
            warnings.warn(msg, category=warning_cat, stacklevel=2)
            return func(*args, **kwargs)
        return inner
    return decorator


def _deprecate_positional_args(func):
    """
    Internal decorator for methods that issues warnings for positional arguments
    Using the keyword-only argument syntax in pep 3102, arguments after the
    ``*`` will issue a warning when passed as a positional argument.
    Adapted from scikit-learn
    """
    signature = inspect.signature(func)

    pos_or_kw_args = []
    kwonly_args = []
    for name, param in signature.parameters.items():
        if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY):
            pos_or_kw_args.append(name)
        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            kwonly_args.append(name)

    @functools.wraps(func)
    def inner(*args, **kwargs):
        name = func.__qualname__.split('.')[0]
        n_extra_args = len(args) - len(pos_or_kw_args)
        if n_extra_args > 0:
            extra_args = ", ".join(kwonly_args[:n_extra_args])

            warnings.warn(
                f"Passing '{extra_args}' as positional argument(s) to 'param.{name}' "
                "has been deprecated since Param 2.0.0 and will raise an error in a future version, "
                "please pass them as keyword arguments.",
                ParamFutureWarning,
                stacklevel=2,
            )

            zip_args = zip(kwonly_args[:n_extra_args], args[-n_extra_args:])
            kwargs.update({name: arg for name, arg in zip_args})

            return func(*args[:-n_extra_args], **kwargs)

        return func(*args, **kwargs)

    return inner


# Copy of Python 3.2 reprlib's recursive_repr but allowing extra arguments
def _recursive_repr(fillvalue='...'):
    """Decorator to make a repr function return fillvalue for a recursive call"""

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


def _is_auto_name(class_name, instance_name):
    return re.match('^'+class_name+'[0-9]{5}$', instance_name)


def _find_pname(pclass):
    """
    Go up the stack and attempt to find a Parameter declaration of the form
    `pname = param.Parameter(` or `pname = pm.Parameter(`.
    """
    stack = traceback.extract_stack()
    for frame in stack:
        match = re.match(r"^(\S+)\s*=\s*(param|pm)\." + pclass + r"\(", frame.line)
        if match:
            return match.group(1)


def _validate_error_prefix(parameter, attribute=None):
    """
    Generate an error prefix suitable for Parameters when they raise a validation
    error.

    - unbound and name can't be found: "Number parameter"
    - unbound and name can be found: "Number parameter 'x'"
    - bound parameter: "Number parameter 'P.x'"
    """
    from param.parameterized import ParameterizedMetaclass

    pclass = type(parameter).__name__
    if parameter.owner is not None:
        if type(parameter.owner) is ParameterizedMetaclass:
            powner = parameter.owner.__name__
        else:
            powner = type(parameter.owner).__name__
    else:
        powner = None
    pname = parameter.name
    out = []
    if attribute:
        out.append(f'Attribute {attribute!r} of')
    out.append(f'{pclass} parameter')
    if pname:
        if powner:
            desc = f'{powner}.{pname}'
        else:
            desc = pname
        out.append(f'{desc!r}')
    else:
        try:
            pname = _find_pname(pclass)
            if pname:
                out.append(f'{pname!r}')
        except Exception:
            pass
    return ' '.join(out)


def _is_mutable_container(value):
    """True for mutable containers, which typically need special handling when being copied"""
    return isinstance(value, MUTABLE_TYPES)


def full_groupby(l, key=lambda x: x):
    """Groupby implementation which does not require a prior sort"""
    d = defaultdict(list)
    for item in l:
        d[key(item)].append(item)
    return d.items()


def iscoroutinefunction(function):
    """Whether the function is an asynchronous generator or a coroutine."""
    # Partial unwrapping not required starting from Python 3.11.0
    # See https://github.com/holoviz/param/pull/894#issuecomment-1867084447
    while isinstance(function, functools.partial):
        function = function.func
    return (
        inspect.isasyncgenfunction(function) or
        inspect.iscoroutinefunction(function)
    )

async def _to_thread(func, /, *args, **kwargs):
    """Polyfill for asyncio.to_thread in Python < 3.9"""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

async def _to_async_gen(sync_gen):
    done = object()

    def safe_next():
        # Converts StopIteration to a sentinel value to avoid:
        # TypeError: StopIteration interacts badly with generators and cannot be raised into a Future
        try:
            return next(sync_gen)
        except StopIteration:
            return done

    while True:
        if sys.version_info >= (3, 9):
            value = await asyncio.to_thread(safe_next)
        else:
            value = await _to_thread(safe_next)
        if value is done:
            break
        yield value

def flatten(line):
    """
    Flatten an arbitrarily nested sequence.

    Inspired by: pd.core.common.flatten

    Parameters
    ----------
    line : sequence
        The sequence to flatten

    Notes
    -----
    This only flattens list, tuple, and dict sequences.

    Returns
    -------
    flattened : generator

    """
    for element in line:
        if any(isinstance(element, tp) for tp in (list, tuple, dict)):
            yield from flatten(element)
        else:
            yield element


def accept_arguments(
    f: Callable[Concatenate[CallableT, P], R]
) -> Callable[P, Callable[[CallableT], R]]:
    """Decorator for decorators that accept arguments"""
    @functools.wraps(f)
    def _f(*args: P.args, **kwargs: P.kwargs) -> Callable[[CallableT], R]:
        return lambda actual_f: f(actual_f, *args, **kwargs)
    return _f


def _produce_value(value_obj):
    """
    A helper function that produces an actual parameter from a stored
    object: if the object is callable, call it, otherwise return the
    object.
    """
    if callable(value_obj):
        return value_obj()
    else:
        return value_obj


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def produce_value(value_obj):
    """
    A helper function that produces an actual parameter from a stored
    object: if the object is callable, call it, otherwise return the
    object.

    .. deprecated:: 2.0.0
    """
    return _produce_value(value_obj)


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def as_unicode(obj):
    """
    Safely casts any object to unicode including regular string
    (i.e. bytes) types in python 2.

    .. deprecated:: 2.0.0
    """
    return str(obj)


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def is_ordered_dict(d):
    """
    Predicate checking for ordered dictionaries. OrderedDict is always
    ordered, and vanilla Python dictionaries are ordered for Python 3.6+

    .. deprecated:: 2.0.0
    """
    py3_ordered_dicts = (sys.version_info.major == 3) and (sys.version_info.minor >= 6)
    vanilla_odicts = (sys.version_info.major > 3) or py3_ordered_dicts
    return isinstance(d, (OrderedDict)) or (vanilla_odicts and isinstance(d, dict))


def _hashable(x):
    """
    Return a hashable version of the given object x, with lists and
    dictionaries converted to tuples.  Allows mutable objects to be
    used as a lookup key in cases where the object has not actually
    been mutated. Lookup will fail (appropriately) in cases where some
    part of the object has changed.  Does not (currently) recursively
    replace mutable subobjects.
    """
    if isinstance(x, collections.abc.MutableSequence):
        return tuple(x)
    elif isinstance(x, collections.abc.MutableMapping):
        return tuple([(k,v) for k,v in x.items()])
    else:
        return x


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def hashable(x):
    """
    Return a hashable version of the given object x, with lists and
    dictionaries converted to tuples.  Allows mutable objects to be
    used as a lookup key in cases where the object has not actually
    been mutated. Lookup will fail (appropriately) in cases where some
    part of the object has changed.  Does not (currently) recursively
    replace mutable subobjects.

    .. deprecated:: 2.0.0
    """
    return _hashable(x)


def _named_objs(objlist, namesdict=None):
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
                objtoname[_hashable(v)] = k
            except TypeError:
                unhashables.append((k, v))

    for obj in objlist:
        if objtoname and _hashable(obj) in objtoname:
            k = objtoname[_hashable(obj)]
        elif any(obj is v for (_, v) in unhashables):
            k = [k for (k, v) in unhashables if v is obj][0]
        elif hasattr(obj, "name"):
            k = obj.name
        elif hasattr(obj, '__name__'):
            k = obj.__name__
        else:
            k = str(obj)
        objs[k] = obj
    return objs


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def named_objs(objlist, namesdict=None):
    """
    Given a list of objects, returns a dictionary mapping from
    string name for the object to the object itself. Accepts
    an optional name,obj dictionary, which will override any other
    name if that item is present in the dictionary.

    .. deprecated:: 2.0.0
    """
    return _named_objs(objlist, namesdict=namesdict)


def _get_min_max_value(min, max, value=None, step=None):
    """Return min, max, value given input values with possible None."""
    # Either min and max need to be given, or value needs to be given
    if value is None:
        if min is None or max is None:
            raise ValueError(
                f'unable to infer range, value from: ({min}, {max}, {value})'
            )
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
        raise ValueError(f'value must be between min and max (min={min}, value={value}, max={max})')
    return min, max, value


def _deserialize_from_path(ext_to_routine, path, type_name):
    """
    Call deserialization routine with path according to extension.
    ext_to_routine should be a dictionary mapping each supported
    file extension to a corresponding loading function.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "Could not parse file '{}' as {}: does not exist or is not a file"
            "".format(path, type_name))
    root, ext = os.path.splitext(path)
    if ext in {'.gz', '.bz2', '.xz', '.zip'}:
        # A compressed type. We'll assume the routines can handle such extensions
        # transparently (if not, we'll fail later)
        ext = os.path.splitext(root)[1]
    # FIXME(sdrobert): try...except block below with "raise from" might be a good idea
    # once py2.7 support is removed. Provides error + fact that failure occurred in
    # deserialization
    if ext in ext_to_routine:
        return ext_to_routine[ext](path)
    raise ValueError(
        "Could not parse file '{}' as {}: no deserialization method for files with "
        "'{}' extension. Supported extensions: {}"
        "".format(path, type_name, ext, ', '.join(sorted(ext_to_routine))))


def _is_number(obj):
    if isinstance(obj, numbers.Number): return True
    # The extra check is for classes that behave like numbers, such as those
    # found in numpy, gmpy, etc.
    elif (hasattr(obj, '__int__') and hasattr(obj, '__add__')): return True
    # This is for older versions of gmpy
    elif hasattr(obj, 'qdiv'): return True
    else: return False


def _is_abstract(class_):
    try:
        return class_.abstract
    except AttributeError:
        return False


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
    return {c.__name__:c for c in descendents(parentclass)
            if not _is_abstract(c)}

def _abbreviate_paths(pathspec,named_paths):
    """
    Given a dict of (pathname,path) pairs, removes any prefix shared by all pathnames.
    Helps keep menu items short yet unambiguous.
    """
    from os.path import commonprefix, dirname, sep

    prefix = commonprefix([dirname(name)+sep for name in named_paths.keys()]+[pathspec])
    return OrderedDict([(name[len(prefix):],path) for name,path in named_paths.items()])


# PARAM3_DEPRECATION
@_deprecated(warning_cat=ParamFutureWarning)
def abbreviate_paths(pathspec,named_paths):
    """
    Given a dict of (pathname,path) pairs, removes any prefix shared by all pathnames.
    Helps keep menu items short yet unambiguous.

    .. deprecated:: 2.0.0
    """
    return _abbreviate_paths(pathspec, named_paths)


def _to_datetime(x):
    """
    Internal function that will convert date objs to datetime objs, used
    for comparing date and datetime objects without error.
    """
    if isinstance(x, dt.date) and not isinstance(x, dt.datetime):
        return dt.datetime(*x.timetuple()[:6])
    return x


@contextmanager
def exceptions_summarized():
    """
    Useful utility for writing docs that need to show expected errors.
    Shows exception only, concisely, without a traceback.
    """
    try:
        yield
    except Exception:
        import sys
        etype, value, tb = sys.exc_info()
        print(f"{etype.__name__}: {value}", file=sys.stderr)


def _in_ipython():
    try:
        get_ipython()
        return True
    except NameError:
        return False

_running_tasks = set()

def async_executor(func):
    try:
        event_loop = asyncio.get_running_loop()
    except RuntimeError:
        event_loop = asyncio.new_event_loop()
    if event_loop.is_running():
        task = asyncio.ensure_future(func())
        _running_tasks.add(task)
        task.add_done_callback(_running_tasks.discard)
    else:
        event_loop.run_until_complete(func())

class _GeneratorIsMeta(type):
    def __instancecheck__(cls, inst):
        return isinstance(inst, tuple(cls.types()))

    def __subclasscheck__(cls, sub):
        return issubclass(sub, tuple(cls.types()))

    def __iter__(cls):
        yield from cls.types()

class _GeneratorIs(metaclass=_GeneratorIsMeta):
    @classmethod
    def __iter__(cls):
        yield from cls.types()

def gen_types(gen_func):
    """
    Decorator which takes a generator function which yields difference types
    make it so it can be called with isinstance and issubclass.
    """
    if not inspect.isgeneratorfunction(gen_func):
        msg = "gen_types decorator can only be applied to generator"
        raise TypeError(msg)
    return type(gen_func.__name__, (_GeneratorIs,), {"types": staticmethod(gen_func)})
