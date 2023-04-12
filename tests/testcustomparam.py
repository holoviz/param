"""
Unit tests for checking the API defended to create custom Parameters.
"""

import param
import pytest

from .utils import check_defaults


@pytest.fixture
def custom_parameter():
    class CustomParameter(param.Parameter):
        def __init__(self, default='custom', **params):
            super().__init__(default=default, **params)

    return CustomParameter


@pytest.fixture
def custom_parameter_with_slot():
    class CustomParameter(param.Parameter):

        __slots__ = ['foo', 'bar']

        def __init__(self, default='custom', foo=True, bar=None, **params):
            super().__init__(default=default,  **params)
            self.foo = foo
            self.bar = bar

    return CustomParameter



def _check_simple_defaults(param):
    assert param.default == 'custom'
    assert param.allow_None is False


def _check_slot_defaults(param):
    assert param.default == 'custom'
    assert param.allow_None is False
    assert param.foo is True
    assert param.bar is None


def test_customparam_defaults_unbound(custom_parameter):
    c = custom_parameter()

    check_defaults(c, label=None)
    _check_simple_defaults(c)


def test_customparam_defaults_class(custom_parameter):
    class P(param.Parameterized):
        c = custom_parameter()

    check_defaults(P.param.c, label='C')
    _check_simple_defaults(P.param.c)


def test_customparam_defaults_inst(custom_parameter):
    class P(param.Parameterized):
        c = custom_parameter()

    p = P()

    check_defaults(p.param.c, label='C')
    _check_simple_defaults(p.param.c)


def test_customparam_slot_defaults_unbound(custom_parameter_with_slot):
    c = custom_parameter_with_slot()

    check_defaults(c, label=None)
    _check_slot_defaults(c)


def test_customparam_slot_defaults_class(custom_parameter_with_slot):
    class P(param.Parameterized):
        c = custom_parameter_with_slot()

    check_defaults(P.param.c, label='C')
    _check_slot_defaults(P.param.c)


def test_customparam_slot_defaults_inst(custom_parameter_with_slot):
    class P(param.Parameterized):
        c = custom_parameter_with_slot()

    p = P()

    check_defaults(p.param.c, label='C')
    _check_slot_defaults(p.param.c)


def test_customparam_inheritance(custom_parameter_with_slot):
    class A(param.Parameterized):
        c = param.Parameter(doc='foo')
    
    class B(A):
        c = custom_parameter_with_slot()
    
    assert B.param.c.doc == 'foo'
    assert B().param.c.doc == 'foo'


def test_customparam_inheritance_override(custom_parameter_with_slot):
    class A(param.Parameterized):
        c = param.Parameter(doc='foo')
    
    class B(A):
        c = custom_parameter_with_slot(doc='bar')
    
    assert B.param.c.doc == 'bar'
    assert B().param.c.doc == 'bar'

def test_inheritance_parameter_attribute_without_default():

    class CustomParameter(param.Parameter):

        __slots__ = ['foo']

        # foo has no default value defined in _slot_defaults

        def __init__(self, foo=param.Undefined, **params):
            super().__init__(**params)
            # To trigger Parameter.__getattribute__
            self.foo = foo
            if self.foo == 'bar':
                pass

    with pytest.raises(
        KeyError,
        match="Slot 'foo' on unbound parameter 'CustomParameter' has no default value defined in `_slot_defaults`"
    ):
        c = CustomParameter()

