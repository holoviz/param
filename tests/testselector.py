"""
Unit test for object selector parameters.

Originally implemented as doctests in Topographica in the file
testEnumerationParameter.txt
"""
import re
import unittest

from collections import OrderedDict

import param
import pytest

from .utils import check_defaults

opts=dict(A=[1,2],B=[3,4],C=dict(a=1,b=2))


class TestSelectorParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.Selector(objects=[5,6,7])
            f = param.Selector(default=10)
            h = param.Selector(default=None)
            g = param.Selector(objects=[7,8])
            i = param.Selector(default=7, objects=[9], check_on_set=False)
            s = param.Selector(default=3, objects=OrderedDict(one=1,two=2,three=3))
            p = param.Selector(default=3, objects=dict(one=1,two=2,three=3))
            d = param.Selector(default=opts['B'], objects=opts)

        self.P = P

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is None
        assert p.objects == []
        assert p.compute_default_fn is None
        assert p.check_on_set is False
        assert p.names == {}

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.Selector()

        check_defaults(P.param.s, label='S')
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.Selector()

        p = P()

        check_defaults(p.param.s, label='S')
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.Selector()

        check_defaults(s, label=None)
        self._check_defaults(s)

    def test_unbound_default_inferred(self):
        s = param.Selector(objects=[0, 1, 2])

        assert s.default == 0

    def test_unbound_default_explicit(self):
        s = param.Selector(default=1, objects=[0, 1, 2])

        assert s.default == 1

    def test_unbound_default_check_on_set_inferred(self):
        s1 = param.Selector(objects=[0, 1, 2])
        s2 = param.Selector(objects=[])
        s3 = param.Selector(objects={})
        s4 = param.Selector()

        assert s1.check_on_set is True
        assert s2.check_on_set is False
        assert s3.check_on_set is False
        assert s4.check_on_set is False

    def test_unbound_default_check_on_set_explicit(self):
        s1 = param.Selector(check_on_set=True)
        s2 = param.Selector(check_on_set=False)

        assert s1.check_on_set is True
        assert s2.check_on_set is False

    def test_set_object_constructor(self):
        p = self.P(e=6)
        self.assertEqual(p.e, 6)

    def test_allow_None_is_None(self):
        p = self.P()
        assert p.param.e.allow_None is None
        assert p.param.f.allow_None is None
        assert p.param.g.allow_None is None
        assert p.param.h.allow_None is None
        assert p.param.i.allow_None is None
        assert p.param.s.allow_None is None
        assert p.param.d.allow_None is None

    def test_allow_None_set_and_behavior_class(self):
        class P(param.Parameterized):
            a = param.Selector(objects=dict(a=1), allow_None=True)
            b = param.Selector(objects=dict(a=1), allow_None=False)
            c = param.Selector(default=1, objects=dict(a=1), allow_None=True)
            d = param.Selector(default=1, objects=dict(a=1), allow_None=False)

        assert P.param.a.allow_None is True
        assert P.param.b.allow_None is False
        assert P.param.c.allow_None is True
        assert P.param.d.allow_None is False

        P.a = None
        assert P.a is None
        with pytest.raises(
            ValueError,
            match=re.escape(r"Selector parameter 'P.b' does not accept None; valid options include: '[1]'")
        ):
            P.b = None
        P.c = None
        assert P.c is None
        with pytest.raises(ValueError):
            P.d = None

    def test_allow_None_set_and_behavior_instance(self):
        class P(param.Parameterized):
            a = param.Selector(objects=dict(a=1), allow_None=True)
            b = param.Selector(objects=dict(a=1), allow_None=False)
            c = param.Selector(default=1, objects=dict(a=1), allow_None=True)
            d = param.Selector(default=1, objects=dict(a=1), allow_None=False)

        p = P()

        assert p.param.a.allow_None is True
        assert p.param.b.allow_None is False
        assert p.param.c.allow_None is True
        assert p.param.d.allow_None is False

        p.a = None
        assert p.a is None
        with pytest.raises(ValueError):
            p.b = None
        p.c = None
        assert p.c is None
        with pytest.raises(ValueError):
            p.d = None

    def test_autodefault(self):
        class P(param.Parameterized):
            o1 = param.Selector(objects=[6, 7])
            o2 = param.Selector(objects={'a': 1, 'b': 2})

        assert P.o1 == 6
        assert P.o2 == 1

        p = P()

        assert p.o1 == 6
        assert p.o2 == 1

    def test_get_range_list(self):
        r = self.P.param['g'].get_range()
        self.assertEqual(r['7'],7)
        self.assertEqual(r['8'],8)

    def test_get_range_ordereddict(self):
        r = self.P.param['s'].get_range()
        self.assertEqual(r['one'],1)
        self.assertEqual(r['two'],2)

    def test_get_range_dict(self):
        r = self.P.param['p'].get_range()
        self.assertEqual(r['one'],1)
        self.assertEqual(r['two'],2)

    def test_get_range_mutable(self):
        r = self.P.param['d'].get_range()
        self.assertEqual(r['A'],opts['A'])
        self.assertEqual(r['C'],opts['C'])
        self.d=opts['A']
        self.d=opts['C']
        self.d=opts['B']

    def test_set_object_outside_bounds(self):
        p = self.P(e=6)
        try:
            p.e = 9
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)


    def test_set_object_not_None(self):
        p = self.P(e=6)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr_post_error(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Selector(default=5, objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("Selector created outside range.")


    def test_initialization_no_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Selector(default=5, objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("Selector created without range.")

    def test_check_on_set_on_init_unbound(self):

        i = param.Selector(default=7, objects=[9], check_on_set=False)
        h = param.Selector(default=None)

        assert i.objects == [9, 7]
        assert h.objects == []

    @pytest.mark.xfail(raises=AssertionError)
    def test_check_on_set_on_init_unbound_unsupported(self):
        # Tricky to update the objects to contain the default on an unbound
        # Selector as in that case the objects is always an empty list, that
        # is returned by the objects factory.

        f = param.Selector(default=10)

        assert f.objects == [10]

    def test_check_on_set_on_init_class(self):

        assert self.P.param.i.objects == [9, 7]
        assert self.P.param.f.objects == [10]
        assert self.P.param.h.objects == []

    def test_check_on_set_on_init_instance(self):

        p = self.P()

        assert p.param.i.objects == [9, 7]
        assert p.param.f.objects == [10]
        assert p.param.h.objects == []

    def test_check_on_set_defined(self):
        class P(param.Parameterized):
            o1 = param.Selector(check_on_set=True)
            o2 = param.Selector(check_on_set=False)

        assert P.param.o1.check_on_set is True
        assert P.param.o2.check_on_set is False

        p = P()

        assert p.param.o1.check_on_set is True
        assert p.param.o2.check_on_set is False

    def test_check_on_set_empty_objects(self):
        class P(param.Parameterized):
            o = param.Selector()

        assert P.param.o.check_on_set is False

        p = P()

        assert p.param.o.check_on_set is False

    def test_check_on_set_else(self):
        class P(param.Parameterized):
            o = param.Selector(objects=[0, 1])

        assert P.param.o.check_on_set is True

        p = P()

        assert p.param.o.check_on_set is True

    def test_inheritance_behavior1(self):
        class A(param.Parameterized):
            p = param.Selector()

        class B(A):
            p = param.Selector()

        assert B.param.p.default is None
        assert B.param.p.objects == []
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.default is None
        assert b.param.p.objects == []
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior2(self):
        class A(param.Parameterized):
            p = param.Selector(objects=[0, 1])

        class B(A):
            p = param.Selector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 0
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 0
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior3(self):
        class A(param.Parameterized):
            p = param.Selector(default=1, objects=[0, 1])

        class B(A):
            p = param.Selector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior4(self):
        class A(param.Parameterized):
            p = param.Selector(objects=[0, 1], check_on_set=False)

        class B(A):
            p = param.Selector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 0
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 0
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior5(self):
        class A(param.Parameterized):
            p = param.Selector(objects=[0, 1], check_on_set=True)

        class B(A):
            p = param.Selector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 0
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 0
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior6(self):
        class A(param.Parameterized):
            p = param.Selector(default=0, objects=[0, 1])

        class B(A):
            p = param.Selector(default=1)

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior7(self):
        class A(param.Parameterized):
            p = param.Selector(default=0)

        class B(A):
            p = param.Selector(default=1)

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is False


    def test_no_instantiate_when_constant(self):
        # https://github.com/holoviz/param/issues/287
        objs = [object(), object()]

        class A(param.Parameterized):
            p = param.Selector(default=objs[0], objects=objs, constant=True)

        a = A()
        assert a.p is objs[0]
