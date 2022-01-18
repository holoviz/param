"""
If numpy's present, is numpy stuff ok?
"""
import unittest
import os

import param
from . import API1TestCase

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
