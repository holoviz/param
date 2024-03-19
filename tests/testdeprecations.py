"""
Test deprecation warnings.
"""
import re
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
        with pytest.raises(param._utils.ParamDeprecationWarning):
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

    def test_deprecate_param_watchers(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.parameterized.Parameterized()._param_watchers

    def test_deprecate_param_watchers_setter(self):
        with pytest.raises(param._utils.ParamFutureWarning):
            param.parameterized.Parameterized()._param_watchers = {}

    def test_param_error_unsafe_ops_before_initialized(self):
        class P(param.Parameterized):

            x = param.Parameter()

            def __init__(self, **params):
                with pytest.raises(
                    param._utils.ParamFutureWarning,
                    match=re.escape(
                        'Looking up instance Parameter objects (`.param.objects()`) until '
                        'the Parameterized instance has been fully initialized is deprecated and will raise an error in a future version. '
                        'Ensure you have called `super().__init__(**params)` in your Parameterized '
                        'constructor before trying to access instance Parameter objects, or '
                        'looking up the class Parameter objects with `.param.objects(instance=False)` '
                        'may be enough for your use case.',
                    )
                ):
                    self.param.objects()

                with pytest.raises(
                    param._utils.ParamFutureWarning,
                    match=re.escape(
                        'Triggering watchers on a partially initialized Parameterized instance '
                        'is deprecated and will raise an error in a future version. '
                        'Ensure you have called super().__init__(**params) in '
                        'the Parameterized instance constructor before trying to set up a watcher.',
                    )
                ):
                    self.param.trigger('x')

                with pytest.raises(
                    param._utils.ParamFutureWarning,
                    match=re.escape(
                        '(Un)registering a watcher on a partially initialized Parameterized instance '
                        'is deprecated and will raise an error in a future version. Ensure '
                        'you have called super().__init__(**) in the Parameterized instance '
                        'constructor before trying to set up a watcher.',
                    )
                ):
                    self.param.watch(print, 'x')

                self.param.objects(instance=False)
                super().__init__(**params)

        P()

    # Inheritance tests to be move to testparameterizedobject.py when warnings will be turned into errors

    def test_inheritance_with_incompatible_defaults(self):
        class A(param.Parameterized):
            p = param.String()

        class B(A): pass

        with pytest.raises(
            param._utils.ParamFutureWarning,
            match=re.escape(
                "Number parameter 'C.p' failed to validate its "
                "default value on class creation, this is going to raise "
                "an error in the future. The Parameter type changed between class 'C' "
                "and one of its parent classes (B, A) which made it invalid. "
                "Please fix the Parameter type."
                "\nValidation failed with:\nNumber parameter 'C.p' only takes numeric values, not <class 'str'>."
            )
        ):
            class C(B):
                p = param.Number()

    def test_inheritance_default_validation_with_more_specific_type(self):
        class A(param.Parameterized):
            p = param.Tuple(default=('a', 'b'))

        class B(A): pass

        with pytest.raises(
            param._utils.ParamFutureWarning,
            match=re.escape(
                "NumericTuple parameter 'C.p' failed to validate its "
                "default value on class creation, this is going to raise "
                "an error in the future. The Parameter type changed between class 'C' "
                "and one of its parent classes (B, A) which made it invalid. "
                "Please fix the Parameter type."
                "\nValidation failed with:\nNumericTuple parameter 'C.p' only takes numeric values, not <class 'str'>."
            )
        ):
            class C(B):
                p = param.NumericTuple()

    def test_inheritance_with_changing_bounds(self):
        class A(param.Parameterized):
            p = param.Number(default=5)

        class B(A): pass

        with pytest.raises(
            param._utils.ParamFutureWarning,
            match=re.escape(
                "Number parameter 'C.p' failed to validate its "
                "default value on class creation, this is going to raise "
                "an error in the future. The Parameter is defined with attributes "
                "which when combined with attributes inherited from its parent "
                "classes (B, A) make it invalid. Please fix the Parameter attributes."
                "\nValidation failed with:\nNumber parameter 'C.p' must be at most 3, not 5."
            )
        ):
            class C(B):
                p = param.Number(bounds=(-1, 3))

    def test_inheritance_with_changing_default(self):
        class A(param.Parameterized):
            p = param.Number(default=5, bounds=(3, 10))

        class B(A): pass

        with pytest.raises(
            param._utils.ParamFutureWarning,
            match=re.escape(
                "Number parameter 'C.p' failed to validate its "
                "default value on class creation, this is going to raise "
                "an error in the future. The Parameter is defined with attributes "
                "which when combined with attributes inherited from its parent "
                "classes (B, A) make it invalid. Please fix the Parameter attributes."
                "\nValidation failed with:\nNumber parameter 'C.p' must be at least 3, not 1."
            )
        ):
            class C(B):
                p = param.Number(default=1)

    def test_inheritance_with_changing_class_(self):
        class A(param.Parameterized):
            p = param.ClassSelector(class_=int, default=5)

        class B(A): pass

        with pytest.raises(
            param._utils.ParamFutureWarning,
            match=re.escape(
                "ClassSelector parameter 'C.p' failed to validate its "
                "default value on class creation, this is going to raise "
                "an error in the future. The Parameter is defined with attributes "
                "which when combined with attributes inherited from its parent "
                "classes (B, A) make it invalid. Please fix the Parameter attributes."
                "\nValidation failed with:\nClassSelector parameter 'C.p' value must be an instance of str, not 5."
            )
        ):
            class C(B):
                p = param.ClassSelector(class_=str)

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
