import param
import pytest

PARAMETERS = param.concrete_descendents(param.Parameter).values()


@pytest.mark.parametrize('ptype', PARAMETERS)
def test_warnings_positional_args(ptype):
    """
    Test the Parameters emit a warning if they're attempted to be instantiated
    with positional arguments. It does not matter whether the instantiation
    succeeds or not as the warning is emitted before any attribute validation.
    """
    with pytest.warns(param.parameterized.ParamDeprecationWarning):
        try:
            ptype(None)
        except:
            pass
