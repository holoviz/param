"""
If numpy's present, is numpy stuff ok?
"""
import unittest
import os

import param
from . import API1TestCase
from .utils import check_defaults

try:
    import numpy
    import numpy.testing
except ImportError:
    if os.getenv('PARAM_TEST_NUMPY','0') == '1':
        raise ImportError("PARAM_TEST_NUMPY=1 but numpy not available.")
    else:
        raise unittest.SkipTest("numpy not available")


def _is_array_and_equal(test,ref):
    if not type(test) == numpy.ndarray:
        raise AssertionError
    numpy.testing.assert_array_equal(test,ref)

# TODO: incomplete
class TestNumpy(API1TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True
        assert p.class_ == numpy.ndarray

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.Array()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.Array()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.Array()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

    def test_array_param(self):
        class Z(param.Parameterized):
            z = param.Array(default=numpy.array([1]))

        _is_array_and_equal(Z.z,[1])

        z = Z(z=numpy.array([1,2]))
        _is_array_and_equal(z.z,[1,2])

    def test_array_param_positional(self):
        class Z(param.Parameterized):
            z = param.Array(numpy.array([1]))

        _is_array_and_equal(Z.z,[1])

        z = Z(z=numpy.array([1,2]))
        _is_array_and_equal(z.z,[1,2])
