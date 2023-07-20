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


class TestDeprecateParameter:

    def test_deprecate_posargs_Parameter(self):
        with pytest.raises(param._utils.ParamPendingDeprecationWarning):
            param.Parameter(1, 'doc')

    def test_deprecate_List_class_(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.List(class_=int)

    def test_deprecate_Number_set_hook(self):
        class P(param.Parameterized):
            n = param.Number(set_hook=lambda obj, val: val)

        p = P()
        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.n = 1


class TestDeprecateInitModule:

    def test_deprecate_as_unicode(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.as_unicode(1)

    def test_deprecate_is_ordered_dict(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.is_ordered_dict(dict())

    def test_deprecate_produce_value(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.produce_value(1)

    def test_deprecate_hasbable(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.hashable('s')

    def test_deprecate_named_objs(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.named_objs(dict())

    def test_deprecate_normalize_path(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.normalize_path()

    def test_deprecate_abbreviate_path(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.abbreviate_paths()


class TestDeprecateParameterizedModule:

    def test_deprecate_overridable_property(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            class Foo:
                def _x(self): pass
                x = param.parameterized.overridable_property(_x)

    def test_deprecate_batch_watch(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            with param.parameterized.batch_watch(p):
                pass

    def test_deprecate_add_metaclass(self):
        class MC(type): pass

        with pytest.raises(param._utils.ParamDeprecationWarning):
            @param.parameterized.add_metaclass(MC)
            class Base: pass

    def test_deprecate_recursive_repr(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.parameterized.recursive_repr(lambda: '')

    def test_deprecate_all_equal(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.parameterized.all_equal(1, 1)

class TestDeprecateParameters:

    def test_deprecate_print_param_defaults(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.print_param_defaults()

    def test_deprecate_set_default(self):
        class P(param.Parameterized):
            x = param.Parameter()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            P.param.set_default('x', 1)

    def test_deprecate__add_parameter(self):
        class P(param.Parameterized):
            x = param.Parameter()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            P.param._add_parameter('y', param.Parameter())

    def test_deprecate_params(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.params()

    def test_deprecate_set_param(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.set_param('x', 1)

    def test_deprecate_get_param_values(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.get_param_values()

    def test_deprecate_params_depended_on(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.params_depended_on()

    def test_deprecate_defaults(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.defaults()

    def test_deprecate_print_param_values(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.print_param_values()

    def test_deprecate_message(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.message('test')

    def test_deprecate_verbose(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.verbose('test')

    def test_deprecate_debug(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamDeprecationWarning):
            p.param.debug('test')
