import datetime
import decimal
import pathlib

import pytest

from param.parameterized import Comparator

try:
    import numpy as np
except ModuleNotFoundError:
    np = None
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

_now = datetime.datetime.now()
_today = datetime.date.today()

_supported = {
    'str': 'test',
    'float': 1.2,
    'int': 1,
    'decimal': decimal.Decimal(1) / decimal.Decimal(7),
    'bytes': (1024).to_bytes(2, byteorder='big'),
    'None': None,
    'list': [1, 2],
    'tuple': (1, 2),
    'set': {1, 2},
    'dict': {'a': 1, 'b': 2},
    'date': _today,
    'datetime': _now,
    'pathlib.Path': pathlib.Path('/tmp/test'),
    'pathlib.PurePosixPath': pathlib.PurePosixPath('/tmp/test'),
}

if np:
    _supported.update({
        'np.datetime64': np.datetime64(_now),
        'np.array_int': np.array([1, 2, 3]),
        'np.array_float': np.array([1.0, 2.0]),
        'np.array_2d': np.zeros((3, 4)),
    })
if pd:
    _supported.update({
        'pd.Timestamp': pd.Timestamp(_now),
        'pd.Series': pd.Series([1, 2, 3]),
        'pd.DataFrame': pd.DataFrame({'a': [1, 2], 'b': [3, 4]}),
    })

@pytest.mark.parametrize('obj', _supported.values(), ids=_supported.keys())
def test_comparator_equal(obj):
    assert Comparator.is_equal(obj, obj)


# ---- pathlib tests ----

def test_path_equal():
    assert Comparator.is_equal(pathlib.Path('/a/b'), pathlib.Path('/a/b'))

def test_path_not_equal():
    assert not Comparator.is_equal(pathlib.Path('/a/b'), pathlib.Path('/a/c'))

def test_purepath_equal():
    assert Comparator.is_equal(pathlib.PurePosixPath('/x'), pathlib.PurePosixPath('/x'))


# ---- numpy tests ----

@pytest.mark.skipif(np is None, reason='numpy not available')
class TestComparatorNumpy:

    def test_array_equal(self):
        a = np.array([1, 2, 3])
        b = np.array([1, 2, 3])
        assert Comparator.is_equal(a, b)

    def test_array_not_equal(self):
        a = np.array([1, 2, 3])
        b = np.array([1, 2, 4])
        assert not Comparator.is_equal(a, b)

    def test_array_different_shape(self):
        a = np.array([1, 2, 3])
        b = np.array([[1, 2, 3]])
        assert not Comparator.is_equal(a, b)

    def test_array_different_dtype(self):
        a = np.array([1, 2], dtype=np.int32)
        b = np.array([1, 2], dtype=np.float64)
        assert not Comparator.is_equal(a, b)

    def test_array_identity(self):
        a = np.array([1, 2, 3])
        assert Comparator.is_equal(a, a)

    def test_array_large_skips(self):
        """Arrays larger than array_max_size should return False."""
        old = Comparator.array_max_size
        try:
            Comparator.array_max_size = 5
            a = np.arange(10)
            b = np.arange(10)
            assert not Comparator.is_equal(a, b)
        finally:
            Comparator.array_max_size = old

    def test_array_with_nan(self):
        a = np.array([1.0, float('nan'), 3.0])
        b = np.array([1.0, float('nan'), 3.0])
        # np.array_equal treats NaN == NaN as False
        assert not Comparator.is_equal(a, b)


# ---- pandas tests ----

@pytest.mark.skipif(pd is None, reason='pandas not available')
class TestComparatorPandas:

    def test_series_equal(self):
        a = pd.Series([1, 2, 3])
        b = pd.Series([1, 2, 3])
        assert Comparator.is_equal(a, b)

    def test_series_not_equal(self):
        a = pd.Series([1, 2, 3])
        b = pd.Series([1, 2, 4])
        assert not Comparator.is_equal(a, b)

    def test_dataframe_equal(self):
        a = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})
        b = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})
        assert Comparator.is_equal(a, b)

    def test_dataframe_not_equal(self):
        a = pd.DataFrame({'x': [1, 2]})
        b = pd.DataFrame({'x': [1, 3]})
        assert not Comparator.is_equal(a, b)

    def test_dataframe_different_shape(self):
        a = pd.DataFrame({'x': [1, 2]})
        b = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})
        assert not Comparator.is_equal(a, b)

    def test_dataframe_with_nan(self):
        a = pd.DataFrame({'x': [1.0, float('nan')]})
        b = pd.DataFrame({'x': [1.0, float('nan')]})
        # pd.DataFrame.equals treats NaN as equal
        assert Comparator.is_equal(a, b)

    def test_series_large_skips(self):
        """Series larger than array_max_size should return False."""
        old = Comparator.array_max_size
        try:
            Comparator.array_max_size = 5
            a = pd.Series(range(10))
            b = pd.Series(range(10))
            assert not Comparator.is_equal(a, b)
        finally:
            Comparator.array_max_size = old
