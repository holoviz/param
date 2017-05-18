"""
Do all subclasses of Parameter supply a valid default?
"""

import unittest

from param.parameterized import add_metaclass
from param import concrete_descendents, Parameter

# import all parameter types
from param import *


positional_args = {
    ClassSelector: (object,)
}


class TestDefaultsMetaclass(type):
    def __new__(mcs, name, bases, dict_):

        def add_test(p):
            def test(self):
                # instantiate parameter with no default (but supply
                # any required args)
                p(*positional_args.get(p,tuple()))
            return test

        for p_name, p_type in concrete_descendents(Parameter).items():
            dict_["test_default_of_%s"%p_name] = add_test(p_type)

        return type.__new__(mcs, name, bases, dict_)


@add_metaclass(TestDefaultsMetaclass)
class TestDefaults(unittest.TestCase):
    pass


if __name__ == "__main__":
    import nose
    nose.runmodule()
