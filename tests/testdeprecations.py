"""Test deprecation warnings."""
import warnings

import param
import pytest


@pytest.fixture(autouse=True)
def specific_filter():
    """Make sure warnings are set up with the right stacklevel."""
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        warnings.filterwarnings('error', module=__name__)
        yield


class TestDeprecateParameter:

    def test_deprecate_posargs_Parameter(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.Parameter(1, 'doc')

    def test_deprecate_List_class_(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.List(class_=int)

    def test_deprecate_Number_set_hook(self):
        class P(param.Parameterized):
            n = param.Number(set_hook=lambda obj, val: val)

        p = P()
        with pytest.raises(param._utils.ParamFutureWarning):
            p.n = 1

    def test_deprecate_Parameter_pickle_default_value(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.Parameter(pickle_default_value=False)



class TestDeprecateInitModule:

    def test_deprecate_as_unicode(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.as_unicode(1)

    def test_deprecate_is_ordered_dict(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.is_ordered_dict(dict())

    def test_deprecate_produce_value(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.produce_value(1)

    def test_deprecate_hasbable(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.hashable('s')

    def test_deprecate_named_objs(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.named_objs(dict())

    def test_deprecate_normalize_path(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.normalize_path()

    def test_deprecate_abbreviate_path(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.abbreviate_paths()


class TestDeprecateParameterizedModule:

    def test_deprecate_overridable_property(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            class Foo:
                def _x(self): pass
                x = param.parameterized.overridable_property(_x)

    def test_deprecate_batch_watch(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            with param.parameterized.batch_watch(p):
                pass

    def test_deprecate_add_metaclass(self):
        class MC(type): pass

        with pytest.raises(param._utils.ParamFutureWarning):
            @param.parameterized.add_metaclass(MC)
            class Base: pass

    def test_deprecate_recursive_repr(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.parameterized.recursive_repr(lambda: '')

    def test_deprecate_all_equal(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.parameterized.all_equal(1, 1)

    def test_deprecate_setting_parameter_before_init(self):
        class P(param.Parameterized):
            x = param.Parameter()

            def __init__(self, **params):
                self.x = 10
                super().__init__(**params)
        with pytest.raises(param._utils.ParamPendingDeprecationWarning):
            P()

    def test_deprecate_watch_values_keyword_what(self):
        class P(param.Parameterized):
            x = param.Parameter()

            def __init__(self, **params):
                super().__init__(**params)
                self.param.watch_values(lambda _: None, ['x'], 'doc')

        with pytest.raises(param._utils.ParamFutureWarning):
            P()


class TestDeprecateParameters:

    def test_deprecate_print_param_defaults(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.print_param_defaults()

    def test_deprecate_set_default(self):
        class P(param.Parameterized):
            x = param.Parameter()

        with pytest.raises(param._utils.ParamFutureWarning):
            P.param.set_default('x', 1)

    def test_deprecate__add_parameter(self):
        class P(param.Parameterized):
            x = param.Parameter()

        with pytest.raises(param._utils.ParamFutureWarning):
            P.param._add_parameter('y', param.Parameter())

    def test_deprecate_params(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.params()

    def test_deprecate_set_param(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.set_param('x', 1)

    def test_deprecate_get_param_values(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.get_param_values()

    def test_deprecate_params_depended_on(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.params_depended_on()

    def test_deprecate_defaults(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.defaults()

    def test_deprecate_print_param_values(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.print_param_values()

    def test_deprecate_message(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.message('test')

    def test_deprecate_verbose(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.verbose('test')

    def test_deprecate_debug(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        with pytest.raises(param._utils.ParamFutureWarning):
            p.param.debug('test')


class TestDeprecateVersion:
    def test_deprecate_Version(self):
        with pytest.raises(FutureWarning):
            param.version.Version()

    def test_deprecate_OldDeprecatedVersion(self):
        with pytest.raises(FutureWarning):
            param.version.OldDeprecatedVersion()

    def test_deprecate_run_cmd(self):
        with pytest.raises(FutureWarning):
            param.version.run_cmd(['echo', 'test'])

    def test_deprecate_get_setup_version(self):
        with pytest.raises(FutureWarning):
            param.version.get_setup_version('dummy', 'dummy')

    def test_deprecate_get_setupcfg_version(self):
        with pytest.raises(FutureWarning):
            param.version.get_setupcfg_version()
