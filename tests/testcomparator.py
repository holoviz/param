import datetime
import decimal
import sys

import pytest

from param.parameterized import Comparator

try:
    import numpy as np
except ImportError:
    np = None
try:
    import pandas as pd
except ImportError:
    pd = None

_now = datetime.datetime.now()
_today = datetime.date.today()

if sys.version_info[0] >= 3:
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
    }

    if np:
        _supported.update({
            'np.datetime64': np.datetime64(_now),
        })
    if pd:
        _supported.update({'pd.Timestamp': pd.Timestamp(_now)})
else:
    _supported = {}

@pytest.mark.skipif(sys.version_info[0] == 2, reason="requires python 3 or higher")
@pytest.mark.parametrize('obj', _supported.values(), ids=_supported.keys())
def test_comparator_equal(obj):
    assert Comparator.is_equal(obj, obj)

