import inspect
import functools
import warnings

from threading import get_ident


class ParamDeprecationWarning(DeprecationWarning):
    """Param DeprecationWarning"""


class ParamFutureWarning(FutureWarning):
    """Param FutureWarning"""


def _deprecated(extra_msg="", warning_cat=ParamDeprecationWarning):
    def decorator(func):
        """Internal decorator used to mark functions/methods as deprecated."""
        @functools.wraps(func)
        def inner(*args, **kwargs):
            msg = f"{func.__name__!r} has been deprecated and will be removed in a future version."
            if extra_msg:
                msg = msg + ' ' + extra_msg
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
                PendingDeprecationWarning,
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
