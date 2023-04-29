import datetime as dt
import os

import param
import pytest

from param import guess_param_types, resolve_path

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

@pytest.fixture
def reset_search_paths():
    # The default is [os.getcwd()] which doesn't play well with the testing
    # framework where every test creates a new temporary directory.
    # This fixture sets it temporarily to [].
    original = resolve_path.search_paths
    try:
        resolve_path.search_paths = []
        yield
    finally:
        resolve_path.search_paths = original


def test_resolve_path_file_default():
    assert resolve_path.path_to_file is True
    assert resolve_path.search_paths == [os.getcwd()]


def test_resolve_path_file_not_found():
    with pytest.raises(IOError, match='File surelyyoudontexist was not found in the following'):
        resolve_path('surelyyoudontexist')


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_file_not_found_other(tmpdir):
    cdir = os.getcwd()
    os.chdir(str(tmpdir))
    try:
        with pytest.raises(IOError, match='File notthere was not found in the following'):
            resolve_path('notthere')
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_folder_not_found(tmpdir):
    cdir = os.getcwd()
    os.chdir(str(tmpdir))
    try:
        with pytest.raises(IOError, match='Folder notthere was not found in the following'):
            resolve_path('notthere', path_to_file=False)
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_either_not_found(tmpdir):
    cdir = os.getcwd()
    os.chdir(str(tmpdir))
    try:
        with pytest.raises(IOError, match='Path notthere was not found in the following'):
            resolve_path('notthere', path_to_file=None)
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
@pytest.mark.parametrize('path_to_file', [True, False, None])
def test_resolve_path_abs_not_found(tmpdir, path_to_file):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    os.chdir(str(tmpdir))
    try:
        with pytest.raises(IOError, match='not found'):
            resolve_path(fp, path_to_file=path_to_file)
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_cwd_file(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    os.chdir(str(tmpdir))
    try:
        p = resolve_path('foo')
        assert os.path.isfile(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_cwd_folder(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    os.chdir(str(tmpdir))
    try:
        p = resolve_path('foo', path_to_file=False)
        assert os.path.isdir(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_cwd_either_file(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    os.chdir(str(tmpdir))
    try:
        p = resolve_path('foo', path_to_file=None)
        assert os.path.isfile(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_cwd_either_folder(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    os.chdir(str(tmpdir))
    try:
        p = resolve_path('foo', path_to_file=None)
        assert os.path.isdir(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_abs_file(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    os.chdir(str(tmpdir))
    try:
        p = resolve_path(fp)
        assert os.path.isfile(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_abs_folder(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    os.chdir(str(tmpdir))
    try:
        p = resolve_path(fp, path_to_file=False)
        assert os.path.isdir(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_abs_either_file(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    os.chdir(str(tmpdir))
    try:
        p = resolve_path(fp, path_to_file=None)
        assert os.path.isfile(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_abs_either_folder(tmpdir):
    cdir = os.getcwd()
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    os.chdir(str(tmpdir))
    try:
        p = resolve_path(fp, path_to_file=None)
        assert os.path.isdir(p)
        assert os.path.basename(p) == 'foo'
        assert os.path.isabs(p)
        assert p == fp
    finally:
        os.chdir(cdir)


def test_resolve_path_search_paths_file(tmpdir):
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    p = resolve_path('foo', search_paths=[str(tmpdir)])
    assert os.path.isfile(p)
    assert os.path.basename(p) == 'foo'
    assert os.path.isabs(p)
    assert p == fp


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_search_paths_folder(tmpdir):
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    p = resolve_path('foo', search_paths=[str(tmpdir)], path_to_file=False)
    assert os.path.isdir(p)
    assert os.path.basename(p) == 'foo'
    assert os.path.isabs(p)
    assert p == fp


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_search_paths_either_file(tmpdir):
    fp = os.path.join(str(tmpdir), 'foo')
    open(fp, 'w').close()
    p = resolve_path('foo', search_paths=[str(tmpdir)], path_to_file=None)
    assert os.path.isfile(p)
    assert os.path.basename(p) == 'foo'
    assert os.path.isabs(p)
    assert p == fp


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_search_paths_either_folder(tmpdir):
    fp = os.path.join(str(tmpdir), 'foo')
    os.mkdir(fp)
    p = resolve_path('foo', search_paths=[str(tmpdir)], path_to_file=None)
    assert os.path.isdir(p)
    assert os.path.basename(p) == 'foo'
    assert os.path.isabs(p)
    assert p == fp


@pytest.mark.usefixtures('reset_search_paths')
def test_resolve_path_search_paths_multiple_file(tmpdir):
    d1 = os.path.join(str(tmpdir), 'd1')
    d2 = os.path.join(str(tmpdir), 'd2')
    os.mkdir(d1)
    os.mkdir(d2)
    fp1 = os.path.join(d1, 'foo1')
    open(fp1, 'w').close()
    fp2 = os.path.join(d2, 'foo2')
    open(fp2, 'w').close()
    p = resolve_path('foo1', search_paths=[d1, d2])
    assert os.path.isfile(p)
    assert os.path.basename(p) == 'foo1'
    assert os.path.isabs(p)
    assert p == fp1

    p = resolve_path('foo2', search_paths=[d1, d2])
    assert os.path.isfile(p)
    assert os.path.basename(p) == 'foo2'
    assert os.path.isabs(p)
    assert p == fp2
