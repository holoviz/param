"""
Test deprecation warnings.
"""

import warnings

import param
import pytest


@pytest.fixture(autouse=True)
def specific_filter():
    """
    Used to make sure warnings are set up with the right stacklevel.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        warnings.filterwarnings('error', module=__name__)
        yield


def test_deprecate_posargs_Parameter():
    with pytest.raises(param._utils.ParamPendingDeprecationWarning):
        param.Parameter(1, 'doc')


def test_deprecate_List_class_():
    with pytest.raises(param._utils.ParamDeprecationWarning):
        param.List(class_=int)


def test_deprecate_as_unicode():
    with pytest.raises(param._utils.ParamDeprecationWarning):
        param.as_unicode(1)


def test_deprecate_is_ordered_dict():
    with pytest.raises(param._utils.ParamDeprecationWarning):
        param.is_ordered_dict(dict())


def test_deprecate_Number_set_hook():
    class P(param.Parameterized):
        n = param.Number(set_hook=lambda obj, val: val)

    p = P()
    with pytest.raises(param._utils.ParamDeprecationWarning):
        p.n = 1


def test_deprecate_overridable_property():
    with pytest.raises(param._utils.ParamDeprecationWarning):
        class A:
            def __init__(self):
                self._x = 1
            def _get_x(self):
                return self._x
            x = param.parameterized.overridable_property(_get_x)
