import pickle

import cloudpickle
import param
import pytest


def eq(o1, o2):
    if not sorted(o1.param) == sorted(o2.param):
        return False

    for pname in o1.param:
        if getattr(o1, pname) != getattr(o2, pname):
            return False
    return True


class P1(param.Parameterized):
    x = param.Parameter()

@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_simple_class(pickler):
    s = pickler.dumps(P1)
    cls = pickler.loads(s)
    assert cls is P1


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_simple_instance(pickler):
    p = P1()
    s = pickler.dumps(p)
    inst = pickler.loads(s)
    assert eq(p, inst)


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_simple_instance_modif_after(pickler):
    p = P1()
    s = pickler.dumps(p)
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
    ac = param.Series()
    ad = param.Dict()
    ae = param.DataFrame()
    af = param.Array()


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_all_parameters_class(pickler):
    s = pickler.dumps(P2)
    cls = pickler.loads(s)
    assert cls is P2


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_all_parameters_instance(pickler):
    p = P2()
    s = pickler.dumps(p)
    inst = pickler.loads(s)
    assert eq(p, inst)


class P3(param.Parameterized):
    a = param.Integer(0)
    count = param.Integer(0)

    @param.depends("a", watch=True)
    def cb(self):
        self.count += 1


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_depends_watch_class(pickler):
    s = pickler.dumps(P3)
    cls = pickler.loads(s)
    assert cls is P3


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_depends_watch_instance(pickler):
    # https://github.com/holoviz/param/issues/757
    p = P3()
    s = pickler.dumps(p)
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


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_complex_depends_class(pickler):
    s = pickler.dumps(P4)
    cls = pickler.loads(s)
    assert cls is P4


@pytest.mark.parametrize('pickler', [cloudpickle, pickle])
def test_pickle_complex_depends_instance(pickler):
    p = P4()
    s = pickler.dumps(p)
    inst = pickler.loads(s)
    assert eq(p, inst)


def test_issue_757():
    # https://github.com/holoviz/param/issues/759
    class P(param.Parameterized):
        a = param.Parameter()

    p = P()
    s = cloudpickle.dumps(p)
    inst = cloudpickle.loads(s)
    assert eq(p, inst)
