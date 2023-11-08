from param.version import run_cmd


def test_run_cmd():
    output = run_cmd(['echo', 'test'])
    assert output == 'test'
