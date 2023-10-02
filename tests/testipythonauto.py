import importlib
from unittest.mock import patch

import param
from param.display import _display_accessors

def test_ipython_autoloaded():
    with patch('param._utils._in_ipython') as mock_in_python:
        mock_in_python.return_value = True
        importlib.reload(param.parameterized)
        assert param.parameterized.param_pager is not None
        assert '_ipython_display_' in _display_accessors
