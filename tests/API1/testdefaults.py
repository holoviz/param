"""
Do all subclasses of Parameter supply a valid default?
"""

from param.parameterized import add_metaclass
from param import concrete_descendents, Parameter

# import all parameter types
from param import * # noqa
from param import ClassSelector
from . import API1TestCase

positional_args = {
    ClassSelector: (object,)
}

skip = []

try:
    import numpy # noqa
except ImportError:
    skip.append('Array')
try:
    import pandas # noqa
except ImportError:
    skip.append('DataFrame')
    skip.append('Series')


class TestDefaultsMetaclass(type):
    def __new__(mcs, name, bases, dict_):

        def test_skip(*args,**kw):
            from nose.exc import SkipTest
            raise SkipTest

        def add_test(p):
            def test(self):
                # instantiate parameter with no default (but supply
                # any required args)
                p(*positional_args.get(p,tuple()))
            return test

        for p_name, p_type in concrete_descendents(Parameter).items():
            dict_["test_default_of_%s"%p_name] = add_test(p_type) if p_name not in skip else test_skip

        return type.__new__(mcs, name, bases, dict_)


@add_metaclass(TestDefaultsMetaclass)
class TestDefaults(API1TestCase):
    pass


if __name__ == "__main__":
    import nose
    nose.runmodule()
