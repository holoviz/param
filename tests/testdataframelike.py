"""Test the DataFrameLike Parameter (cross-backend via Narwhals)."""
import os
import unittest

import param
import pytest

from .utils import check_defaults

try:
    import narwhals  # noqa: F401
except ModuleNotFoundError:
    if os.getenv('PARAM_TEST_NARWHALS', '0') == '1':
        raise ImportError("PARAM_TEST_NARWHALS=1 but narwhals not available.")
    else:
        raise unittest.SkipTest("narwhals not available")

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

try:
    import polars as pl
except ModuleNotFoundError:
    pl = None

try:
    import pyarrow as pa
except ModuleNotFoundError:
    pa = None

try:
    import modin.pandas as mpd
except Exception:
    # modin import can fail for reasons beyond ModuleNotFoundError (missing
    # execution engine), so guard broadly and skip rather than error.
    mpd = None

skip_no_pandas = pytest.mark.skipif(pd is None, reason="pandas not available")
skip_no_polars = pytest.mark.skipif(pl is None, reason="polars not available")
skip_no_pyarrow = pytest.mark.skipif(pa is None, reason="pyarrow not available")
skip_no_modin = pytest.mark.skipif(mpd is None, reason="modin not available")


class TestDataFrameLikeDefaults(unittest.TestCase):

    def test_defaults_class(self):
        class P(param.Parameterized):
            df = param.DataFrameLike()

        check_defaults(P.param.df, label='Df', skip=['instantiate'])

    def test_defaults_inst(self):
        class P(param.Parameterized):
            df = param.DataFrameLike()

        check_defaults(P().param.df, label='Df', skip=['instantiate'])


@skip_no_pandas
class TestDataFrameLikeAccepts(unittest.TestCase):

    def test_pandas(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}))
        src = pd.DataFrame({'a': [3, 4]})
        p = P(df=src)
        # Value is passed through unchanged (no Narwhals wrapper).
        self.assertIs(p.df, src)

    @skip_no_polars
    def test_polars_eager(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
        src = pl.DataFrame({'a': [1, 2]})
        p = P(df=src)
        self.assertIs(p.df, src)
        self.assertIsInstance(p.df, pl.DataFrame)

    @skip_no_pyarrow
    def test_pyarrow(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
        src = pa.table({'a': [1, 2]})
        self.assertIs(P(df=src).df, src)

    @skip_no_modin
    def test_modin(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1]}), rows=2, columns={'a'})
        src = mpd.DataFrame({'a': [1, 2]})
        p = P(df=src)
        self.assertIs(p.df, src)
        self.assertIsInstance(p.df, mpd.DataFrame)
        with self.assertRaises(ValueError):
            P(df=mpd.DataFrame({'a': [1]}))  # rows=2 mismatch


@skip_no_pandas
class TestDataFrameLikeRejects(unittest.TestCase):

    def setUp(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
        self.P = P

    def test_list(self):
        with self.assertRaises(ValueError):
            self.P(df=[1, 2, 3])

    def test_dict(self):
        with self.assertRaises(ValueError):
            self.P(df={'a': [1]})

    def test_str(self):
        with self.assertRaises(ValueError):
            self.P(df='not a frame')

    def test_series(self):
        with self.assertRaises(ValueError):
            self.P(df=pd.Series([1, 2, 3]))

    def test_none_without_allow_none(self):
        with self.assertRaises(ValueError):
            self.P(df=None)

    def test_none_with_allow_none(self):
        class Q(param.Parameterized):
            df = param.DataFrameLike(default=None, allow_None=True)
        self.assertIsNone(Q(df=None).df)


@skip_no_pandas
class TestDataFrameLikeRows(unittest.TestCase):

    def test_rows_exact_ok(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2, 3]}), rows=3)
        P(df=pd.DataFrame({'a': [4, 5, 6]}))

    def test_rows_exact_mismatch(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2, 3]}), rows=3)
        with self.assertRaises(ValueError):
            P(df=pd.DataFrame({'a': [1, 2]}))

    def test_rows_bounds(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}), rows=(1, 4))
        P(df=pd.DataFrame({'a': [1, 2, 3, 4]}))
        with self.assertRaises(ValueError):
            P(df=pd.DataFrame({'a': list(range(5))}))

    @skip_no_polars
    def test_rows_polars(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}), rows=2)
        P(df=pl.DataFrame({'a': [9, 8]}))
        with self.assertRaises(ValueError):
            P(df=pl.DataFrame({'a': [1]}))


@skip_no_pandas
class TestDataFrameLikeColumns(unittest.TestCase):

    def test_set_subset_ok(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns={'a'})
        P(df=pd.DataFrame({'a': [1], 'b': [2], 'c': [3]}))

    def test_set_missing_column(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1]}), columns={'a'})
        with self.assertRaises(ValueError):
            P(df=pd.DataFrame({'x': [1]}))

    def test_list_exact_ordered(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns=['a', 'b'])
        P(df=pd.DataFrame({'a': [1], 'b': [2]}))
        with self.assertRaises(ValueError):
            P(df=pd.DataFrame({'b': [2], 'a': [1]}))

    def test_columns_numeric_bounds(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns=(1, 3))
        P(df=pd.DataFrame({'a': [1], 'b': [2], 'c': [3]}))
        with self.assertRaises(ValueError):
            P(df=pd.DataFrame({c: [1] for c in 'abcd'}))

    def test_set_with_ordered_raises(self):
        with self.assertRaises(ValueError):
            class P(param.Parameterized):
                df = param.DataFrameLike(
                    default=pd.DataFrame({'a': [1]}),
                    columns={'a'}, ordered=True)


@skip_no_pandas
@skip_no_polars
class TestDataFrameLikeAllowLazy(unittest.TestCase):

    def test_lazy_rejected_by_default(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
        with self.assertRaises(ValueError):
            P(df=pl.LazyFrame({'a': [1, 2]}))

    def test_lazy_accepted_when_allowed(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1]}), allow_lazy=True)
        src = pl.LazyFrame({'a': [1, 2]})
        self.assertIs(P(df=src).df, src)

    def test_lazy_columns_still_validated(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1]}),
                columns={'a'}, allow_lazy=True)
        P(df=pl.LazyFrame({'a': [1], 'b': [2]}))
        with self.assertRaises(ValueError):
            P(df=pl.LazyFrame({'x': [1]}))

    def test_lazy_rows_skipped_no_collect(self):
        # rows=2 would fail if collected (lazy frame has 3 rows); it must be
        # skipped for lazy frames so .collect() is never called implicitly.
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1, 2]}),
                rows=2, allow_lazy=True)
        lazy = pl.LazyFrame({'a': [1, 2, 3]})
        collected = {'called': False}
        orig_collect = pl.LazyFrame.collect

        def spy(self, *a, **k):
            collected['called'] = True
            return orig_collect(self, *a, **k)

        pl.LazyFrame.collect = spy
        try:
            P(df=lazy)
        finally:
            pl.LazyFrame.collect = orig_collect
        self.assertFalse(collected['called'], "lazy frame was implicitly collected")


@skip_no_pandas
class TestDataFrameLikeSerialize(unittest.TestCase):

    def test_serialize_none(self):
        self.assertIsNone(param.DataFrameLike.serialize(None))

    def test_serialize_records(self):
        recs = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']}))
        self.assertEqual(recs, [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}])

    @skip_no_polars
    def test_serialize_backend_neutral(self):
        recs_pd = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2]}))
        recs_pl = param.DataFrameLike.serialize(pl.DataFrame({'a': [1, 2]}))
        self.assertEqual(recs_pd, recs_pl)

    @skip_no_polars
    def test_serialize_lazy_collected(self):
        recs = param.DataFrameLike.serialize(pl.LazyFrame({'a': [1, 2]}))
        self.assertEqual(recs, [{'a': 1}, {'a': 2}])

    def test_deserialize_roundtrip(self):
        recs = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2]}))
        back = param.DataFrameLike.deserialize(recs)
        self.assertEqual(back.to_dict('records'), recs)
