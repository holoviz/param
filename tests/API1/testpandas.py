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


class TestDataFrame(API1TestCase):

    def test_empty_dataframe_param_invalid_set(self):
        empty = pandas.DataFrame()
        class Test(param.Parameterized):
            df = param.DataFrame(default=empty)

        test = Test()
        exception = "Parameter 'df' value must be an instance of DataFrame, not '3'"
        with self.assertRaisesRegexp(ValueError, exception):
            test.df = 3

    def test_dataframe_unordered_column_set_valid(self):
        valid = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid, columns={'a', 'b'})


    def test_dataframe_unordered_column_set_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'd':[4,5]}, columns=['b', 'a', 'd'])
        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns={'a', 'd'})


        test = Test()
        self.assertEquals(test.param.params('df').ordered, False)
        exception = "Provided DataFrame columns \['b', 'a', 'c'\] does not contain required columns \['a', 'd'\]"
        with self.assertRaisesRegexp(Exception, exception):
            test.df = invalid_df

    def test_dataframe_ordered_column_list_valid(self):
        valid = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            test = param.DataFrame(default=valid, columns=['b', 'a', 'c'])


    def test_dataframe_ordered_column_list_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'd':[4,5]}, columns=['b', 'a', 'd'])
        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['a', 'b', 'd'])

        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=['b', 'a', 'd'])

        test = Test()
        self.assertEquals(test.param.params('df').ordered, True)

        exception = "Provided DataFrame columns \['a', 'b', 'd'\] must exactly match \['b', 'a', 'd'\]"
        with self.assertRaisesRegexp(Exception, exception):
            test.df = invalid_df


if __name__ == "__main__":
    import nose
    nose.runmodule()
