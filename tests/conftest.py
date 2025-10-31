import os

os.environ["PARAM_PARAMETER_SIGNATURE"] = "1"  # To force signature in _ParameterBase.__init_subclass__

import param
import pytest

param.parameterized.warnings_as_exceptions = True

@pytest.fixture
def dataframe():
    pd = pytest.importorskip("pandas")
    return pd.DataFrame({
        'int': [1, 2, 3],
        'float': [3.14, 6.28, 9.42],
        'str': ['A', 'B', 'C']
    }, index=[1, 2, 3], columns=['int', 'float', 'str'])
