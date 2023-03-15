"""
Unit test for object selector parameters.

Originally implemented as doctests in Topographica in the file
testEnumerationParameter.txt
"""

import param
from . import API1TestCase
from .utils import check_defaults
from collections import OrderedDict


opts=dict(A=[1,2],B=[3,4],C=dict(a=1,b=2))


class TestObjectSelectorParameters(API1TestCase):

    def setUp(self):
        super(TestObjectSelectorParameters, self).setUp()
        class P(param.Parameterized):
            e = param.ObjectSelector(default=5,objects=[5,6,7])
            f = param.ObjectSelector(default=10)
            h = param.ObjectSelector(default=None)
            g = param.ObjectSelector(default=None,objects=[7,8])
            i = param.ObjectSelector(default=7,objects=[9],check_on_set=False)
            s = param.ObjectSelector(default=3,objects=OrderedDict(one=1,two=2,three=3))
            d = param.ObjectSelector(default=opts['B'],objects=opts)

        self.P = P

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is None
        assert p.objects == []
        assert p.compute_default_fn is None
        assert p.check_on_set is False
        assert p.names is None

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.ObjectSelector()

        check_defaults(P.param.s, label='S')
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.ObjectSelector()

        p = P()

        check_defaults(p.param.s, label='S')
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.ObjectSelector()

        check_defaults(s, label=None)
        self._check_defaults(s)

    def test_unbound_default_inferred(self):
        s = param.ObjectSelector(objects=[0, 1, 2])

        assert s.default is None

    def test_unbound_default_explicit(self):
        s = param.ObjectSelector(default=1, objects=[0, 1, 2])

        assert s.default == 1

    def test_unbound_default_check_on_set_inferred(self):
        s1 = param.ObjectSelector(objects=[0, 1, 2])
        s2 = param.ObjectSelector(objects=[])
        s3 = param.ObjectSelector(objects={})
        s4 = param.ObjectSelector()

        assert s1.check_on_set is True
        assert s2.check_on_set is False
        assert s3.check_on_set is False
        assert s4.check_on_set is False

    def test_unbound_default_check_on_set_explicit(self):
        s1 = param.ObjectSelector(check_on_set=True)
        s2 = param.ObjectSelector(check_on_set=False)

        assert s1.check_on_set is True
        assert s2.check_on_set is False

    def test_unbound_allow_None_not_dynamic(self):
        s = param.ObjectSelector(objects=[0, 1, 2])

        assert s.allow_None is None

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

    def test_get_range_list(self):
        r = self.P.param.params("g").get_range()
        self.assertEqual(r['7'],7)
        self.assertEqual(r['8'],8)

    def test_get_range_dict(self):
        r = self.P.param.params("s").get_range()
        self.assertEqual(r['one'],1)
        self.assertEqual(r['two'],2)

    def test_get_range_mutable(self):
        r = self.P.param.params("d").get_range()
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
                q = param.Selector(default=5,objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ObjectSelector created outside range.")


    def test_initialization_no_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Selector(default=5,objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ObjectSelector created without range.")


    def test_initialization_out_of_bounds_objsel(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ObjectSelector created outside range.")


    def test_initialization_no_bounds_objsel(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ObjectSelector created without range.")

    def test_compute_default_fn_in_objects(self):
        class P(param.Parameterized):
            o = param.ObjectSelector(objects=[0, 1], compute_default_fn=lambda: 1)

        assert P.param.o.default is None

        P.param.o.compute_default()

        assert P.param.o.default == 1

        p = P()

        assert p.o == 1


    def test_compute_default_fn_not_in_objects(self):
        class P(param.Parameterized):
            o = param.ObjectSelector(objects=[0, 1], compute_default_fn=lambda: 2)

        assert P.param.o.default is None

        P.param.o.compute_default()

        assert P.param.o.default == 2

        p = P()

        assert p.o == 2

    def test_inheritance_behavior1(self):
        class A(param.Parameterized):
            p = param.ObjectSelector()

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.default is None
        assert B.param.p.objects == []
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.default is None
        assert b.param.p.objects == []
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior2(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1])

        class B(A):
            p = param.ObjectSelector()

        # B does not inherit objects from A
        assert B.param.p.objects == []
        assert B.param.p.default is None
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == []
        assert b.param.p.default is None
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior3(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(default=1, objects=[0, 1])

        class B(A):
            p = param.ObjectSelector()

        # B does not inherit objects from A but the default gets anyway set to 1
        # and check_on_set is False
        assert B.param.p.objects == []
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == []
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior4(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1], check_on_set=False)

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == []
        assert B.param.p.default is None
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == []
        assert b.param.p.default is None
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior5(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1], check_on_set=True)

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == []
        assert B.param.p.default is None
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == []
        assert b.param.p.default is None
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior6(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(default=0, objects=[0, 1])

        class B(A):
            p = param.ObjectSelector(default=1)

        assert B.param.p.objects == []
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == []
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is False
