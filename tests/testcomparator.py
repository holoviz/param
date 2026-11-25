import datetime
import decimal
import operator
import pathlib
import uuid

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
    'timedelta': datetime.timedelta(hours=1),
    'Path': pathlib.Path('a', 'b'),
    'PurePosixPath': pathlib.PurePosixPath('a/b'),
    'UUID': uuid.UUID(int=1),
}

if np:
    _supported.update({
        'np.datetime64': np.datetime64(_now),
    })
if pd:
    _supported.update({'pd.Timestamp': pd.Timestamp(_now), 'pd.Timedelta': pd.Timedelta(1, 'h')})

@pytest.mark.parametrize('obj', _supported.values(), ids=_supported.keys())
def test_comparator_equal(obj):
    assert Comparator.is_equal(obj, obj)


@pytest.mark.parametrize('obj', _supported.values(), ids=_supported.keys())
def test_comparator_equal_to_equal_copy(obj):
    assert Comparator.is_equal(obj, type(obj)(obj) if isinstance(obj, (list, tuple, set, dict)) else obj)


def test_comparator_equal_values_of_value_types():
    assert Comparator.is_equal(datetime.timedelta(hours=1), datetime.timedelta(minutes=60))
    assert Comparator.is_equal(pathlib.Path('a', 'b'), pathlib.Path('a/b'))
    assert Comparator.is_equal(uuid.UUID(int=1), uuid.UUID(int=1))
    assert not Comparator.is_equal(datetime.timedelta(hours=1), datetime.timedelta(hours=2))
    assert not Comparator.is_equal(pathlib.Path('a'), pathlib.Path('b'))
    assert not Comparator.is_equal(uuid.UUID(int=1), uuid.UUID(int=2))


_missing = {'nan': float('nan'), 'decimal NaN': decimal.Decimal('NaN')}
if np:
    _missing.update({'np.nan': np.float64('nan'), 'np.datetime64 NaT': np.datetime64('NaT', 'ns')})
if pd:
    _missing.update({'pd.NaT': pd.NaT})


@pytest.mark.parametrize('obj', _missing.values(), ids=_missing.keys())
def test_comparator_missing_values_equal_each_other(obj):
    assert Comparator.is_equal(obj, obj)
    assert not Comparator.is_equal(obj, _supported['float'] if isinstance(obj, (float, decimal.Decimal)) else _now)


def test_comparator_nan_in_container():
    assert Comparator.is_equal([1, float('nan')], [1, float('nan')])
    assert Comparator.is_equal({'a': float('nan')}, {'a': float('nan')})


class _Point:
    def __init__(self, x):
        self.x = x


@pytest.fixture
def restore_equalities():
    equalities = Comparator.equalities
    yield
    Comparator.equalities = equalities


def test_comparator_register_type(restore_equalities):
    assert not Comparator.is_equal(_Point(1), _Point(1))
    eq = Comparator.register(_Point, lambda a, b: a.x == b.x)
    assert callable(eq)
    assert Comparator.is_equal(_Point(1), _Point(1))
    assert not Comparator.is_equal(_Point(1), _Point(2))


def test_comparator_register_predicate(restore_equalities):
    Comparator.register(lambda o: hasattr(o, 'x'), lambda a, b: a.x == b.x)
    assert Comparator.is_equal(_Point(1), _Point(1))


def test_comparator_register_takes_precedence_over_defaults(restore_equalities):
    Comparator.register(str, lambda a, b: a.lower() == b.lower())
    assert Comparator.is_equal('A', 'a')


def test_comparator_register_replaces_earlier_registration(restore_equalities):
    Comparator.register(_Point, lambda a, b: True)
    Comparator.register(_Point, operator.is_)
    point = _Point(1)
    assert Comparator.is_equal(point, point)
    assert not Comparator.is_equal(point, _Point(1))
    assert list(Comparator.equalities).count(_Point) == 1


@pytest.mark.skipif(np is None, reason='numpy is not installed')
def test_comparator_register_overrides_generated_default(restore_equalities):
    Comparator.register(np.datetime64, lambda a, b: True)
    assert Comparator.is_equal(np.datetime64('2020-01-01'), np.datetime64('2021-01-01'))


def test_setting_nan_again_does_not_notify_onlychanged_watchers():
    import param

    class P(param.Parameterized):
        x = param.Number(float('nan'))

    p, events = P(), []
    p.param.watch(events.append, 'x')
    p.x = float('nan')
    assert events == []
    p.x = 1.0
    assert len(events) == 1
