import pickle

import param
import pytest

try:
    import cloudpickle
except ImportError:
    cloudpickle = None
try:
    import numpy as np
except:
    np = None
try:
    import pandas as pd
except:
    pd = None


def eq(o1, o2):
    if not sorted(o1.param) == sorted(o2.param):
        return False

    for pname in o1.param:
        if getattr(o1, pname) != getattr(o2, pname):
            return False
    return True


@pytest.fixture
def pickler(request):
    if request.param is None:
        pytest.skip('cloudpickle not available')
    return request.param


class P1(param.Parameterized):
    x = param.Parameter()

@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_simple_class(pickler, protocol):
    s = pickler.dumps(P1, protocol=protocol)
    cls = pickler.loads(s)
    assert cls is P1


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_simple_instance(pickler, protocol):
    p = P1()
    s = pickler.dumps(p, protocol=protocol)
    inst = pickler.loads(s)
    assert eq(p, inst)


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_simple_instance_modif_after(pickler, protocol):
    p = P1()
    s = pickler.dumps(p, protocol=protocol)
    p.x = 'modified'
    inst = pickler.loads(s)
    assert not eq(p, inst)
    assert inst.x is None


class P2(param.Parameterized):
    a = param.Parameter()
    b = param.String()
    c = param.Dynamic()
    d = param.Number()
    e = param.Integer()
    f = param.Action()
    g = param.Event()
    h = param.Callable()
    i = param.Tuple()
    k = param.NumericTuple()
    l = param.Range()
    m = param.XYCoordinates()
    n = param.CalendarDateRange()
    o = param.DateRange()
    p = param.List()
    q = param.HookList()
    r = param.Path()
    s = param.Filename()
    t = param.Foldername()
    u = param.Date()
    v = param.CalendarDate()
    w = param.Selector()
    x = param.ObjectSelector()
    y = param.FileSelector()
    z = param.ListSelector()
    aa = param.MultiFileSelector()
    ab = param.ClassSelector(class_=type(None))
    ac = None if pd is None else param.Series()
    ad = param.Dict()
    ae = None if pd is None else param.DataFrame()
    af = None if np is None else param.Array()


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_all_parameters_class(pickler, protocol):
    s = pickler.dumps(P2, protocol=protocol)
    cls = pickler.loads(s)
    assert cls is P2


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_all_parameters_instance(pickler, protocol):
    p = P2()
    s = pickler.dumps(p, protocol=protocol)
    inst = pickler.loads(s)
    assert eq(p, inst)


class P3(param.Parameterized):
    a = param.Integer(0)
    count = param.Integer(0)

    @param.depends("a", watch=True)
    def cb(self):
        self.count += 1


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_depends_watch_class(pickler, protocol):
    s = pickler.dumps(P3, protocol=protocol)
    cls = pickler.loads(s)
    assert cls is P3


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_depends_watch_instance(pickler, protocol):
    # https://github.com/holoviz/param/issues/757
    p = P3()
    s = pickler.dumps(p, protocol=protocol)
    inst = pickler.loads(s)
    assert eq(p, inst)

    inst.a += 1
    assert inst.count == 1


class P4(param.Parameterized):
    a = param.Parameter()
    b = param.Parameter()

    single_count = param.Integer()
    attr_count = param.Integer()
    single_nested_count = param.Integer()
    double_nested_count = param.Integer()
    nested_attr_count = param.Integer()
    nested_count = param.Integer()

    @param.depends('a', watch=True)
    def single_parameter(self):
        self.single_count += 1

    @param.depends('a:constant', watch=True)
    def constant(self):
        self.attr_count += 1

    @param.depends('b.a', watch=True)
    def single_nested(self):
        self.single_nested_count += 1

    @param.depends('b.b.a', watch=True)
    def double_nested(self):
        self.double_nested_count += 1

    @param.depends('b.a:constant', watch=True)
    def nested_attribute(self):
        self.nested_attr_count += 1

    @param.depends('b.param', watch=True)
    def nested(self):
        self.nested_count += 1


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_complex_depends_class(pickler, protocol):
    s = pickler.dumps(P4, protocol=protocol)
    cls = pickler.loads(s)
    assert cls is P4


@pytest.mark.parametrize('pickler', [cloudpickle, pickle], indirect=True)
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_pickle_complex_depends_instance(pickler, protocol):
    p = P4()
    s = pickler.dumps(p, protocol=protocol)
    inst = pickler.loads(s)
    assert eq(p, inst)


@pytest.mark.skipif(cloudpickle is None, reason='cloudpickle not available')
@pytest.mark.parametrize('protocol', [0, pickle.DEFAULT_PROTOCOL, pickle.HIGHEST_PROTOCOL])
def test_issue_757(protocol):
    # https://github.com/holoviz/param/issues/759
    class P(param.Parameterized):
        a = param.Parameter()

    p = P()
    s = cloudpickle.dumps(p, protocol=protocol)
    inst = cloudpickle.loads(s)
    assert eq(p, inst)
