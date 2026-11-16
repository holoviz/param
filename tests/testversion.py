import pytest

from param.version import run_cmd

@pytest.mark.filterwarnings('ignore:param.version.run_cmd:FutureWarning')
def test_run_cmd():
    output = run_cmd(['echo', 'test'])
    assert output == 'test'
