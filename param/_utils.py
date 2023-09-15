import inspect
import functools
import re
import traceback
import warnings

from textwrap import dedent
from threading import get_ident
from collections import abc

DEFAULT_SIGNATURE = inspect.Signature([
    inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD),
    inspect.Parameter('params', inspect.Parameter.VAR_KEYWORD),
])

class ParamWarning(Warning):
    """Base Param Warning"""

class ParamPendingDeprecationWarning(ParamWarning, PendingDeprecationWarning):
    """Param PendingDeprecationWarning

    This warning type is useful when the warning is not meant to be displayed
    to REPL/notebooks users, as DeprecationWarning are displayed when triggered
    by code in __main__ (__name__ == '__main__' in a REPL).
    """


class ParamDeprecationWarning(ParamWarning, DeprecationWarning):
    """Param DeprecationWarning

    Ignored by default except when triggered by code in __main__
    """


class ParamFutureWarning(ParamWarning, FutureWarning):
    """Param FutureWarning

    Always displayed.
    """


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
    """Internal decorator for methods that issues warnings for positional arguments
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
                "has been deprecated since Param 2.0,0 and will raise an error in a future version, "
                "please pass them as keyword arguments.",
                ParamPendingDeprecationWarning,
                stacklevel=2,
            )

            zip_args = zip(kwonly_args[:n_extra_args], args[-n_extra_args:])
            kwargs.update({name: arg for name, arg in zip_args})

            return func(*args[:-n_extra_args], **kwargs)

        return func(*args, **kwargs)

    return inner


# Copy of Python 3.2 reprlib's recursive_repr but allowing extra arguments
def _recursive_repr(fillvalue='...'):
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
    return issubclass(type(value), (abc.MutableSequence, abc.MutableSet, abc.MutableMapping))


def _dict_update(dictionary, **kwargs):
    """
    Small utility to update a copy of a dict with the provided keyword args.
    """
    d = dictionary.copy()
    d.update(kwargs)
    return d
