"""Test the DataFrameLike Parameter (cross-backend via Narwhals)."""
import pytest

import param

from .utils import check_defaults

pytest.importorskip("narwhals")

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

skip_no_pandas = pytest.mark.skipif(pd is None, reason="pandas not available")
skip_no_polars = pytest.mark.skipif(pl is None, reason="polars not available")
skip_no_pyarrow = pytest.mark.skipif(pa is None, reason="pyarrow not available")


def test_defaults_class():
    class P(param.Parameterized):
        df = param.DataFrameLike()

    check_defaults(P.param.df, label='Df', skip=['instantiate'])


def test_defaults_inst():
    class P(param.Parameterized):
        df = param.DataFrameLike()

    check_defaults(P().param.df, label='Df', skip=['instantiate'])


@skip_no_pandas
def test_accepts_pandas():
    class P(param.Parameterized):
        df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}))
    src = pd.DataFrame({'a': [3, 4]})
    p = P(df=src)
    # Value is passed through unchanged (no Narwhals wrapper).
    assert p.df is src


@skip_no_pandas
@skip_no_polars
def test_accepts_polars_eager():
    class P(param.Parameterized):
        df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
    src = pl.DataFrame({'a': [1, 2]})
    p = P(df=src)
    assert p.df is src
    assert isinstance(p.df, pl.DataFrame)


@skip_no_pandas
@skip_no_pyarrow
def test_accepts_pyarrow():
    class P(param.Parameterized):
        df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))
    src = pa.table({'a': [1, 2]})
    assert P(df=src).df is src


@pytest.fixture
def P_pandas():
    pytest.importorskip("pandas")

    class P(param.Parameterized):
        df = param.DataFrameLike(default=pd.DataFrame({'a': [1]}))

    return P


@skip_no_pandas
class TestDataFrameLikeRejects:

    def test_list(self, P_pandas):
        with pytest.raises(ValueError):
            P_pandas(df=[1, 2, 3])

    def test_dict(self, P_pandas):
        with pytest.raises(ValueError):
            P_pandas(df={'a': [1]})

    def test_str(self, P_pandas):
        with pytest.raises(ValueError):
            P_pandas(df='not a frame')

    def test_series(self, P_pandas):
        with pytest.raises(ValueError):
            P_pandas(df=pd.Series([1, 2, 3]))

    def test_none_without_allow_none(self, P_pandas):
        with pytest.raises(ValueError):
            P_pandas(df=None)

    def test_none_with_allow_none(self):
        class Q(param.Parameterized):
            df = param.DataFrameLike(default=None, allow_None=True)
        assert Q(df=None).df is None


@skip_no_pandas
class TestDataFrameLikeRows:

    def test_rows_exact_ok(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2, 3]}), rows=3)
        P(df=pd.DataFrame({'a': [4, 5, 6]}))

    def test_rows_exact_mismatch(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2, 3]}), rows=3)
        with pytest.raises(ValueError):
            P(df=pd.DataFrame({'a': [1, 2]}))

    def test_rows_bounds(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}), rows=(1, 4))
        P(df=pd.DataFrame({'a': [1, 2, 3, 4]}))
        with pytest.raises(ValueError):
            P(df=pd.DataFrame({'a': list(range(5))}))

    @skip_no_polars
    def test_rows_polars(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pd.DataFrame({'a': [1, 2]}), rows=2)
        P(df=pl.DataFrame({'a': [9, 8]}))
        with pytest.raises(ValueError):
            P(df=pl.DataFrame({'a': [1]}))


@skip_no_pandas
class TestDataFrameLikeColumns:

    def test_set_subset_ok(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns={'a'})
        P(df=pd.DataFrame({'a': [1], 'b': [2], 'c': [3]}))

    def test_set_missing_column(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1]}), columns={'a'})
        with pytest.raises(ValueError):
            P(df=pd.DataFrame({'x': [1]}))

    def test_list_exact_ordered(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns=['a', 'b'])
        P(df=pd.DataFrame({'a': [1], 'b': [2]}))
        with pytest.raises(ValueError):
            P(df=pd.DataFrame({'b': [2], 'a': [1]}))

    def test_columns_numeric_bounds(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pd.DataFrame({'a': [1], 'b': [2]}), columns=(1, 3))
        P(df=pd.DataFrame({'a': [1], 'b': [2], 'c': [3]}))
        with pytest.raises(ValueError):
            P(df=pd.DataFrame({c: [1] for c in 'abcd'}))

    def test_set_with_ordered_raises(self):
        with pytest.raises(ValueError):
            class P(param.Parameterized):
                df = param.DataFrameLike(
                    default=pd.DataFrame({'a': [1]}),
                    columns={'a'}, ordered=True)


@skip_no_polars
class TestDataFrameLikeLazy:

    def test_lazy_rejected_by_default(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(default=pl.DataFrame({'a': [1]}))
        with pytest.raises(ValueError):
            P(df=pl.LazyFrame({'a': [1, 2]}))

    def test_lazy_accepted_when_allowed(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pl.DataFrame({'a': [1]}), eager_only=False)
        src = pl.LazyFrame({'a': [1, 2]})
        assert P(df=src).df is src

    def test_lazy_columns_still_validated(self):
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pl.DataFrame({'a': [1]}),
                columns={'a'}, eager_only=False)
        P(df=pl.LazyFrame({'a': [1], 'b': [2]}))
        with pytest.raises(ValueError):
            P(df=pl.LazyFrame({'x': [1]}))

    def test_lazy_rows_validated_via_count(self):
        # rows=2 must be validated against a LazyFrame without materialising
        # the whole frame; narwhals .count() is used to pull only a scalar.
        class P(param.Parameterized):
            df = param.DataFrameLike(
                default=pl.DataFrame({'a': [1, 2]}),
                rows=2, eager_only=False)
        # Matching row count passes.
        P(df=pl.LazyFrame({'a': [1, 2]}))
        # Non-matching row count fails (proves rows are actually checked).
        with pytest.raises(ValueError):
            P(df=pl.LazyFrame({'a': [1, 2, 3]}))


@skip_no_pandas
class TestDataFrameLikeSerialize:

    def test_serialize_none(self):
        assert param.DataFrameLike.serialize(None) is None

    def test_serialize_records(self):
        recs = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']}))
        assert recs == [{'a': 1, 'b': 'x'}, {'a': 2, 'b': 'y'}]

    @skip_no_polars
    def test_serialize_backend_neutral(self):
        recs_pd = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2]}))
        recs_pl = param.DataFrameLike.serialize(pl.DataFrame({'a': [1, 2]}))
        assert recs_pd == recs_pl

    @skip_no_polars
    def test_serialize_lazy_collected(self):
        recs = param.DataFrameLike.serialize(pl.LazyFrame({'a': [1, 2]}))
        assert recs == [{'a': 1}, {'a': 2}]

    def test_deserialize_roundtrip(self):
        recs = param.DataFrameLike.serialize(pd.DataFrame({'a': [1, 2]}))
        back = param.DataFrameLike.deserialize(recs)
        assert back.to_dict('records') == recs
