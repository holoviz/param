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

    def test_dataframe_positional_argument(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]},
                                    columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(valid_df)

    def test_dataframe_allow_none(self):
        class Test(param.Parameterized):
            df = param.DataFrame(default=None, rows=3)

        test = Test()
        self.assertIs(test.df, None)

    def test_dataframe_allow_none_constructor(self):
        class Test(param.Parameterized):
            df = param.DataFrame(allow_None=True, rows=3)

        test = Test(df=None)
        self.assertIs(test.df, None)

    def test_dataframe_allow_none_set_value(self):
        class Test(param.Parameterized):
            df = param.DataFrame(allow_None=True, rows=3)

        test = Test()
        test.df = None
        self.assertIs(test.df, None)

    def test_empty_dataframe_param_invalid_set(self):
        empty = pandas.DataFrame()
        class Test(param.Parameterized):
            df = param.DataFrame(default=empty)

        test = Test()
        exception = "DataFrame parameter 'df' value must be an instance of DataFrame, not 3."
        with self.assertRaisesRegex(ValueError, exception):
            test.df = 3

    def test_dataframe_unordered_column_set_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns={'a', 'b'})


    def test_dataframe_unordered_column_set_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'd':[4,5]}, columns=['b', 'a', 'd'])
        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns={'a', 'd'})


        test = Test()
        self.assertEqual(test.param.params('df').ordered, False)
        exception = r"Provided DataFrame columns \['b', 'a', 'c'\] does not contain required columns \['a', 'd'\]"
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df

    def test_dataframe_ordered_column_list_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            test = param.DataFrame(default=valid_df, columns=['b', 'a', 'c'])


    def test_dataframe_ordered_column_list_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'd':[4,5]}, columns=['b', 'a', 'd'])
        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['a', 'b', 'd'])

        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=['b', 'a', 'd'])

        test = Test()
        self.assertEqual(test.param.params('df').ordered, True)

        exception = r"Provided DataFrame columns \['a', 'b', 'd'\] must exactly match \['b', 'a', 'd'\]"
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df


    def test_dataframe_unordered_column_number_valid_df(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=3)

    def test_dataframe_unordered_column_number_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3]}, columns=['b', 'a'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=3)

        test = Test()
        self.assertEqual(test.param.params('df').ordered, None)

        exception = "Column length 2 does not match declared bounds of 3"
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df


    def test_dataframe_unordered_column_tuple_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=(None,3))

    def test_dataframe_unordered_column_tuple_invalid(self):

        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        exception = r"Columns length 3 does not match declared bounds of \(None, 2\)"
        with self.assertRaisesRegex(ValueError, exception):
            class Test(param.Parameterized):
                df = param.DataFrame(default=invalid_df, columns=(None,2))

    def test_dataframe_row_number_valid_df(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, rows=2)

    def test_dataframe_row_number_invalid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3]}, columns=['b', 'a'])
        invalid_df = pandas.DataFrame({'a':[1,2,4], 'b':[2,3,4]}, columns=['b', 'a'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, rows=2)

        test = Test()
        exception = "Row length 3 does not match declared bounds of 2"
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df

    def test_dataframe_unordered_row_tuple_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, rows=(None,3))

    def test_dataframe_unordered_row_tuple_invalid(self):

        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        exception = r"Row length 2 does not match declared bounds of \(5, 7\)"
        with self.assertRaisesRegex(ValueError, exception):
            class Test(param.Parameterized):
                df = param.DataFrame(default=invalid_df, rows=(5,7))


class TestSeries(API1TestCase):

    def test_series_positional_argument(self):
        valid_series = pandas.Series([1,2])
        class Test(param.Parameterized):
            series = param.Series(valid_series, rows=2)

    def test_series_row_number_valid(self):
        valid_series = pandas.Series([1,2])
        class Test(param.Parameterized):
            series = param.Series(default=valid_series, rows=2)

    def test_series_row_number_invalid(self):
        valid_series = pandas.Series([1,2])
        invalid_series = pandas.Series([1,2,3])
        class Test(param.Parameterized):
            series = param.Series(default=valid_series, rows=2)

        test = Test()
        exception = "Row length 3 does not match declared bounds of 2"
        with self.assertRaisesRegex(ValueError, exception):
            test.series = invalid_series

    def test_series_unordered_row_tuple_valid(self):
        valid_series = pandas.Series([1,2,3])
        class Test(param.Parameterized):
            series = param.Series(default=valid_series, rows=(None,3))

    def test_series_unordered_row_tuple_invalid(self):

        invalid_series = pandas.Series([1,2])

        exception = r"Row length 2 does not match declared bounds of \(5, 7\)"
        with self.assertRaisesRegex(ValueError, exception):
            class Test(param.Parameterized):
                series = param.Series(default=invalid_series, rows=(5,7))

    def test_series_allow_none(self):
        class Test(param.Parameterized):
            series = param.Series(default=None, rows=3)

        test = Test()
        self.assertIs(test.series, None)

    def test_series_allow_none_constructor(self):
        class Test(param.Parameterized):
            series = param.Series(allow_None=True, rows=3)

        test = Test(series=None)
        self.assertIs(test.series, None)

    def test_series_allow_none_set_value(self):
        class Test(param.Parameterized):
            series = param.Series(allow_None=True, rows=3)

        test = Test()
        test.series = None
        self.assertIs(test.series, None)
