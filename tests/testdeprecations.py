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

    def test_deprecate_Parameter_pickle_default_value(self):
        with pytest.raises(param._utils.ParamDeprecationWarning):
            param.Parameter(pickle_default_value=False)


class TestDeprecateParameterizedModule:

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
