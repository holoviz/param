import functools
import warnings


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
