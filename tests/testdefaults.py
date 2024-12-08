"""Do all subclasses of Parameter supply a valid default?"""
import unittest

import pytest

import param

from param import concrete_descendents, Parameter

# import all parameter types
from param import * # noqa
from param import ClassSelector

from .utils import check_defaults

kw_args = {
    ClassSelector: dict(class_=object),
}

skip = []

try:
    import numpy # noqa
except ModuleNotFoundError:
    skip.append('Array')
try:
    import pandas # noqa
except ModuleNotFoundError:
    skip.append('DataFrame')
    skip.append('Series')


class DefaultsMetaclassTest(type):
    def __new__(mcs, name, bases, dict_):

        def test_skip(*args,**kw):
            pytest.skip()

        def add_test_unbound(parameter):
            def test(self):
                # instantiate parameter with no default (but supply
                # any required args)
                p = parameter(**kw_args.get(parameter, {}))

                for slot in param.parameterized.get_all_slots(parameter):
                    # Handled in a special way, skip it
                    if parameter == param.Composite and slot == 'objtype':
                        continue
                    assert getattr(p, slot) is not param.Undefined

            return test

        def add_test_class(parameter):
            def test(self):
                # instantiate parameter with no default (but supply
                # any required args)
                class P(param.Parameterized):
                    p = parameter(**kw_args.get(parameter, {}))

                for slot in param.parameterized.get_all_slots(parameter):
                    # Handled in a special way, skip it
                    if type(parameter) is param.Composite and slot == 'objtype':
                        continue
                    assert getattr(P.param.p, slot) is not param.Undefined
                    # Handled in a special way, skip it
                    if parameter == param.Composite:
                        continue
                    assert P.p == P.param.p.default

            return test

        def add_test_inst(parameter):
            def test(self):
                # instantiate parameter with no default (but supply
                # any required args)
                class P(param.Parameterized):
                    p = parameter(**kw_args.get(parameter, {}))

                inst = P()

                for slot in param.parameterized.get_all_slots(parameter):
                    # Handled in a special way, skip it
                    if type(parameter) is param.Composite and slot == 'objtype':
                        continue
                    assert getattr(inst.param.p, slot) is not param.Undefined
                    # Handled in a special way, skip it
                    if parameter == param.Composite:
                        continue
                    assert inst.p == inst.param.p.default

            return test

        for p_name, p_type in concrete_descendents(Parameter).items():
            dict_["test_default_of_unbound_%s"%p_name] = add_test_unbound(p_type) if p_name not in skip else test_skip
            dict_["test_default_of_class_%s"%p_name] = add_test_class(p_type) if p_name not in skip else test_skip
            dict_["test_default_of_inst_%s"%p_name] = add_test_inst(p_type) if p_name not in skip else test_skip

        return type.__new__(mcs, name, bases, dict_)


class TestDefaults(unittest.TestCase, metaclass=DefaultsMetaclassTest):
    pass


def test_defaults_parameter_inst():
    class A(param.Parameterized):
        s = param.Parameter()

    a = A()

    check_defaults(a.param.s, label='S')
    assert a.param.s.default is None
    assert a.param.s.allow_None is True

def test_defaults_parameter_class():
    class A(param.Parameterized):
        s = param.Parameter()

    check_defaults(A.param.s, label='S')
    assert A.param.s.default is None
    assert A.param.s.allow_None is True

def test_defaults_parameter_unbound():
    s = param.Parameter()

    check_defaults(s, label=None)
    assert s.default is None
    assert s.allow_None is True

def test_defaults_parameter_inst_allow_None():
    class A(param.Parameterized):
        s1 = param.Parameter(default='not None')
        s2 = param.Parameter(default='not None', allow_None=False)
        s3 = param.Parameter(default='not None', allow_None=True)
        s4 = param.Parameter(default=None)
        s5 = param.Parameter(default=None, allow_None=False)
        s6 = param.Parameter(default=None, allow_None=True)

    a = A()

    assert a.param.s1.allow_None is False
    assert a.param.s2.allow_None is False
    assert a.param.s3.allow_None is True
    assert a.param.s4.allow_None is True
    assert a.param.s5.allow_None is True
    assert a.param.s6.allow_None is True


def test_defaults_parameter_class_allow_None():
    class A(param.Parameterized):
        s1 = param.Parameter(default='not None')
        s2 = param.Parameter(default='not None', allow_None=False)
        s3 = param.Parameter(default='not None', allow_None=True)
        s4 = param.Parameter(default=None)
        s5 = param.Parameter(default=None, allow_None=False)
        s6 = param.Parameter(default=None, allow_None=True)

    assert A.param.s1.allow_None is False
    assert A.param.s2.allow_None is False
    assert A.param.s3.allow_None is True
    assert A.param.s4.allow_None is True
    assert A.param.s5.allow_None is True
    assert A.param.s6.allow_None is True


def test_defaults_parameter_unbound_allow_None():
    s1 = param.Parameter(default='not None')
    s2 = param.Parameter(default='not None', allow_None=False)
    s3 = param.Parameter(default='not None', allow_None=True)
    s4 = param.Parameter(default=None)
    s5 = param.Parameter(default=None, allow_None=False)
    s6 = param.Parameter(default=None, allow_None=True)

    assert s1.allow_None is False
    assert s2.allow_None is False
    assert s3.allow_None is True
    assert s4.allow_None is True
    assert s5.allow_None is True
    assert s6.allow_None is True
