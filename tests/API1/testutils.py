import datetime as dt

import param
import pytest

from param import guess_param_types

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None

now = dt.datetime.now()
today = dt.date.today()

guess_param_types_data = {
    'Parameter': (param.Parameter(), param.Parameter),
    'Date': (today, param.Date),
    'Datetime': (now, param.Date),
    'Boolean': (True, param.Boolean),
    'Integer': (1, param.Integer),
    'Number': (1.2, param.Number),
    'String': ('test', param.String),
    'Dict': (dict(a=1), param.Dict),
    'NumericTuple': ((1, 2), param.NumericTuple),
    'Tuple': (('a', 'b'), param.Tuple),
    'DateRange': ((dt.date(2000, 1, 1), dt.date(2001, 1, 1)), param.DateRange),
    'List': ([1, 2], param.List),
    'Unsupported_None': (None, param.Parameter),
}

if np:
    guess_param_types_data.update({
        'Array':(np.ndarray([1, 2]), param.Array),
    })
if pd:
    guess_param_types_data.update({
        'DataFrame': (pd.DataFrame(data=dict(a=[1])), param.DataFrame),
        'Series': (pd.Series([1, 2]), param.Series),
    })

@pytest.mark.parametrize('val,p', guess_param_types_data.values(), ids=guess_param_types_data.keys())
def test_guess_param_types(val, p):
    input = {'key': val}
    output = guess_param_types(**input)
    assert isinstance(output, dict)
    assert len(output) == 1
    assert 'key' in output
    out_param = output['key']
    assert isinstance(out_param, p)
    if not type(out_param) == param.Parameter:
        assert out_param.default is val
        assert out_param.constant
