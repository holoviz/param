from . import version  # noqa: api import
from .depends import depends  # noqa: api import
from .parameterized import (  # noqa: api import
    Parameterized, Parameter, String, ParameterizedFunction, ParamOverrides,
    Undefined, get_logger
)
from .parameterized import (batch_watch, output, script_repr, # noqa: api import
                            discard_events, edit_constant)
from .parameterized import shared_parameters  # noqa: api import
from .parameterized import logging_level   # noqa: api import
from .parameterized import DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL  # noqa: api import
from .parameters import (  # noqa: api import
    guess_param_types,
    param_union,
    parameterized_class,
    guess_bounds,
    get_soft_bounds,
    resolve_path,
    normalize_path,
    Time,
    Infinity,
    Dynamic,
    Bytes,
    Number,
    Integer,
    Magnitude,
    Boolean,
    Tuple,
    NumericTuple,
    XYCoordinates,
    Callable,
    Action,
    Composite,
    SelectorBase,
    ListProxy,
    Selector,
    ObjectSelector,
    ClassSelector,
    List,
    HookList,
    Dict,
    Array,
    DataFrame,
    Series,
    Path,
    Filename,
    Foldername,
    FileSelector,
    ListSelector,
    MultiFileSelector,
    Date,
    CalendarDate,
    Color,
    Range,
    DateRange,
    CalendarDateRange,
    Event,
)
from .reactive import bind, rx # noqa: api import
from ._utils import (  # noqa: api import
    produce_value,
    as_unicode,
    is_ordered_dict,
    hashable,
    named_objs,
    descendents,
    concrete_descendents,
    abbreviate_paths,
    exceptions_summarized,
)


# Define '__version__'
try:
    # If setuptools_scm is installed (e.g. in a development environment with
    # an editable install), then use it to determine the version dynamically.
    from setuptools_scm import get_version

    # This will fail with LookupError if the package is not installed in
    # editable mode or if Git is not installed.
    __version__ = get_version(root="..", relative_to=__file__)
except (ImportError, LookupError):
    # As a fallback, use the version that is hard-coded in the file.
    try:
        from ._version import __version__
    except ModuleNotFoundError:
        # The user is probably trying to run this without having installed
        # the package.
        __version__ = "0.0.0+unknown"

#: Top-level object to allow messaging not tied to a particular
#: Parameterized object, as in 'param.main.warning("Invalid option")'.
main=Parameterized(name="main")


# A global random seed (integer or rational) available for controlling
# the behaviour of Parameterized objects with random state.
random_seed = 42
