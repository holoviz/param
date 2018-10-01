"""
Test Parameters based on pandas
"""
import unittest
import os

import param
from . import API1TestCase

try:
    import pandas
except ImportError:
    if os.getenv('PARAM_TEST_PANDAS','0') == '1':
        raise ImportError("PARAM_TEST_PANDAS=1 but pandas not available.")
    else:
        raise unittest.SkipTest("pandas not available")


class TestPandas(API1TestCase):

    def test_simple_dataframe_param(self):
        class Z(param.Parameterized):
            z = param.DataFrame(default=pandas.DataFrame())

        z = Z()
        exception = "Parameter 'z' value must be an instance of DataFrame, not '3'"
        with self.assertRaisesRegexp(ValueError, exception):
            z.z = 3


if __name__ == "__main__":
    import nose
    nose.runmodule()
