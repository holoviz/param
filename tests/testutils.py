import datetime as dt
import os

from collections.abc import Iterable
from functools import partial

import param
import pytest

from param import guess_param_types, resolve_path
from param.parameterized import bothmethod, Parameterized, ParameterizedABC
from param._utils import (
    ParamWarning,
    _is_abstract,
    _is_mutable_container,
    concrete_descendents,
    descendents,
    iscoroutinefunction,
    gen_types,
)


try:
    import numpy as np
except ModuleNotFoundError:
    np = None

try:
    import pandas as pd
except ModuleNotFoundError:
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

class CustomMetaclass(param.parameterized.ParameterizedMetaclass): pass


@pytest.mark.parametrize('val,p', guess_param_types_data.values(), ids=guess_param_types_data.keys())
def test_guess_param_types(val, p):
    input = {'key': val}
    output = guess_param_types(**input)
    assert isinstance(output, dict)
    assert len(output) == 1
    assert 'key' in output
    out_param = output['key']
    assert isinstance(out_param, p)
    if type(out_param) is not param.Parameter:
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


def test_both_method():

    class A:

        @bothmethod
        def method(self_or_cls):
            return self_or_cls

    assert A.method() is A

    a = A()

    assert a.method() is a


def test_error_prefix_unbound_defined():
    with pytest.raises(ValueError, match="Number parameter 'x' only"):
        x = param.Number('wrong')  # noqa


def test_error_prefix_unbound_unexpected_pattern():
    from param import Number
    with pytest.raises(ValueError, match="Number parameter only"):
        Number('wrong')


def test_error_prefix_before_class_creation():
    with pytest.raises(ValueError, match="Number parameter 'x' only"):
        class P(param.Parameterized):
            x = param.Number('wrong')


def test_error_prefix_set_class():
    class P(param.Parameterized):
        x = param.Number()
    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        P.x = 'wrong'


def test_error_prefix_instantiate():
    class P(param.Parameterized):
        x = param.Number()
    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        P(x='wrong')


def test_error_prefix_set_instance():
    class P(param.Parameterized):
        x = param.Number()

    p = P()

    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        p.x = 'wrong'


def test_error_prefix_custom_metaclass_before_class_creation():
    with pytest.raises(ValueError, match="Number parameter 'x' only"):
        class P(param.Parameterized, metaclass=CustomMetaclass):
            x = param.Number('wrong')


def test_error_prefix_custom_metaclass_set_class():
    class P(param.Parameterized, metaclass=CustomMetaclass):
        x = param.Number()
    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        P.x = 'wrong'


def test_error_prefix_custom_metaclass_instantiate():
    class P(param.Parameterized, metaclass=CustomMetaclass):
        x = param.Number()

    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        P(x='wrong')


def test_error_prefix_custom_metaclass_set_instance():
    class P(param.Parameterized, metaclass=CustomMetaclass):
        x = param.Number()

    p = P()

    with pytest.raises(ValueError, match="Number parameter 'P.x' only"):
        p.x = 'wrong'


@pytest.mark.parametrize(
        ('obj,ismutable'),
        [
            ([1, 2], True),
            ({1, 2}, True),
            ({'a': 1, 'b': 2}, True),
            ((1, 2), False),
            ('string', False),
            (frozenset([1, 2]), False)
        ]
)
def test__is_mutable_container(obj, ismutable):
    assert _is_mutable_container(obj) is ismutable


async def coro():
    return


def test_iscoroutinefunction_coroutine():
    assert iscoroutinefunction(coro)


def test_iscoroutinefunction_partial_coroutine():
    pcoro = partial(partial(coro))
    assert iscoroutinefunction(pcoro)


async def agen():
    yield


def test_iscoroutinefunction_asyncgen():
    assert iscoroutinefunction(agen)


def test_iscoroutinefunction_partial_asyncgen():
    pagen = partial(partial(agen))
    assert iscoroutinefunction(pagen)

def test_gen_types():
    @gen_types
    def _int_types():
        yield int

    assert isinstance(1, (str, _int_types))
    assert isinstance(5, _int_types)
    assert isinstance(5.0, _int_types) is False

    assert issubclass(int, (str, _int_types))
    assert issubclass(int, _int_types)
    assert issubclass(float, _int_types) is False

    assert next(iter(_int_types())) is int
    assert next(iter(_int_types)) is int
    assert isinstance(_int_types, Iterable)


@pytest.mark.filterwarnings("ignore:'_UnionGenericAlias' is deprecated and slated for removal in Python 3.17")
def test_descendents_object():
    # Used to raise an unhandled error, see https://github.com/holoviz/param/issues/1013.
    assert descendents(object)


@pytest.mark.filterwarnings("ignore:'_UnionGenericAlias' is deprecated and slated for removal in Python 3.17")
def test_descendents_bad_type():
    with pytest.raises(
        TypeError,
        match="descendents expected a class object, not int"
    ):
        descendents(1)


class A(Parameterized):
    __abstract = True
class B(A): pass
class C(A): pass
class X(B): pass
class Y(B): pass


def test_descendents():
    assert descendents(A) == [A, B, C, X, Y]


def test_descendents_concrete():
    assert descendents(A, concrete=True) == [B, C, X, Y]


def test_is_abstract_false():
    class A: pass
    class B(Parameterized): pass
    assert not _is_abstract(A)
    assert not _is_abstract(B)


def test_is_abstract_attribute():
    class A(Parameterized):
        __abstract = True
    class B(A): pass

    assert _is_abstract(A)
    assert not _is_abstract(B)


def test_is_abstract_abc():
    class A(ParameterizedABC): pass
    class B(A): pass

    assert _is_abstract(A)
    assert not _is_abstract(B)


def test_concrete_descendents():
    assert concrete_descendents(A) == {
        'B': B,
        'C': C,
        'X': X,
        'Y': Y,
    }


def test_concrete_descendents_same_name_warns():
    class X: pass
    class Y(X): pass
    y = Y  # noqa
    class Y(X): pass
    with pytest.warns(
        ParamWarning,
        match=r".*\['Y'\]"
    ):
        cd = concrete_descendents(X)
    # y not returned
    assert cd == {'X': X, 'Y': Y}
