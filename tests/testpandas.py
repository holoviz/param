"""Test Parameters based on pandas."""
import os
import re
import unittest

import param
import pytest

from .utils import check_defaults

try:
    import pandas
except ModuleNotFoundError:
    if os.getenv('PARAM_TEST_PANDAS','0') == '1':
        raise ImportError("PARAM_TEST_PANDAS=1 but pandas not available.")
    else:
        raise unittest.SkipTest("pandas not available")


class TestDataFrame(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True
        assert p.rows is None
        assert p.columns is None
        assert p.ordered is None
        assert p.class_ == pandas.DataFrame

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.DataFrame()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.DataFrame()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.DataFrame()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

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
        exception = "DataFrame parameter 'Test.df' value must be an instance of DataFrame, not 3."
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
        self.assertEqual(test.param['df'].ordered, False)
        exception = re.escape("DataFrame parameter 'Test.df': provided columns ['b', 'a', 'c'] does not contain required columns ['a', 'd']")
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
        self.assertEqual(test.param['df'].ordered, True)

        exception = re.escape("DataFrame parameter 'Test.df': provided columns ['a', 'b', 'd'] must exactly match ['b', 'a', 'd']")
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
        self.assertEqual(test.param['df'].ordered, None)

        exception = "column length 2 does not match declared bounds of 3"
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df

    def test_dataframe_unordered_column_tuple_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, columns=(None,3))

    def test_dataframe_unordered_column_tuple_invalid(self):

        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        exception = re.escape("DataFrame parameter 'df': columns length 3 does not match declared bounds of (None, 2)")
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
        exception = re.escape("DataFrame parameter 'Test.df': row length 3 does not match declared bounds of 2")
        with self.assertRaisesRegex(ValueError, exception):
            test.df = invalid_df

    def test_dataframe_unordered_row_tuple_valid(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        class Test(param.Parameterized):
            df = param.DataFrame(default=valid_df, rows=(None,3))

    def test_dataframe_unordered_row_tuple_invalid(self):

        invalid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])

        exception = r"row length 2 does not match declared bounds of \(5, 7\)"
        with self.assertRaisesRegex(ValueError, exception):
            class Test(param.Parameterized):
                df = param.DataFrame(default=invalid_df, rows=(5,7))

    def test_dataframe_unordered_columns_as_set_error(self):
        valid_df = pandas.DataFrame({'a':[1,2], 'b':[2,3], 'c':[4,5]}, columns=['b', 'a', 'c'])
        with pytest.raises(
            ValueError,
            match=re.escape("DataFrame parameter 'df': columns cannot be ordered when specified as a set"),
        ):
            df = param.DataFrame(default=valid_df, columns=set(['a', 'b']), ordered=True)  # noqa

class TestSeries(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True
        assert p.rows is None
        assert p.class_ == pandas.Series

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.Series()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.Series()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.Series()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

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
        exception = re.escape("Series parameter 'Test.series': row length 3 does not match declared bounds of 2")
        with self.assertRaisesRegex(ValueError, exception):
            test.series = invalid_series

    def test_series_unordered_row_tuple_valid(self):
        valid_series = pandas.Series([1,2,3])
        class Test(param.Parameterized):
            series = param.Series(default=valid_series, rows=(None,3))

    def test_series_unordered_row_tuple_invalid(self):

        invalid_series = pandas.Series([1,2])

        exception = re.escape("Series parameter 'series': row length 2 does not match declared bounds of (5, 7)")
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
