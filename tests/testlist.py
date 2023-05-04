import unittest

import param

from .utils import check_defaults
# TODO: I copied the tests from testobjectselector, although I
# struggled to understand some of them. Both files should be reviewed
# and cleaned up together.

# TODO: tests copied from testobjectselector could use assertRaises
# context manager (and could be updated in testobjectselector too).

class TestListParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.List([5,6,7], item_type=int)
            l = param.List(["red","green","blue"], item_type=str, bounds=(0,10))

        self.P = P

    def _check_defaults(self, p):
        assert p.default == []
        assert p.allow_None is False
        assert p.class_ is None
        assert p.item_type is None
        assert p.bounds == (0, None)
        assert p.instantiate is True

    def test_defaults_class(self):
        class P(param.Parameterized):
            l = param.List()

        check_defaults(P.param.l, label='L', skip=['instantiate'])
        self._check_defaults(P.param.l)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            l = param.List()

        p = P()

        check_defaults(p.param.l, label='L', skip=['instantiate'])
        self._check_defaults(p.param.l)

    def test_defaults_unbound(self):
        l = param.List()

        check_defaults(l, label=None, skip=['instantiate'])
        self._check_defaults(l)

    def test_default_None(self):
        class Q(param.Parameterized):
            r = param.List(default=[])  #  Also check None)

    def test_set_object_constructor(self):
        p = self.P(e=[6])
        self.assertEqual(p.e, [6])

    def test_set_object_outside_bounds(self):
        p = self.P()
        try:
            p.l=[6]*11
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_wrong_type(self):
        p = self.P()
        try:
            p.e=['s']
        except TypeError:
            pass
        else:
            raise AssertionError("Object allowed of wrong type.")

    def test_set_object_not_None(self):
        p = self.P(e=[6])
        try:
            p.e = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_inheritance_behavior1(self):
        class A(param.Parameterized):
            p = param.List()

        class B(A):
            p = param.List()

        assert B.param.p.default == []
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (0, None)

        b = B()

        assert b.param.p.default == []
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (0, None)

    def test_inheritance_behavior2(self):
        class A(param.Parameterized):
            p = param.List(default=[0, 1])

        class B(A):
            p = param.List()

        # B inherits default from A
        assert B.param.p.default == [0 ,1]
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (0, None)

        b = B()

        assert b.param.p.default == [0, 1]
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (0, None)

    def test_inheritance_behavior3(self):
        class A(param.Parameterized):
            p = param.List(default=[0, 1], bounds=(1, 10))

        class B(A):
            p = param.List()

        # B inherits default and bounds from A
        assert B.param.p.default == [0, 1]
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (1, 10)

        b = B()

        assert b.param.p.default == [0, 1]
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (1, 10)

    def test_inheritance_behavior4(self):
        class A(param.Parameterized):
            p = param.List(default=[0], item_type=int)

        class B(A):
            p = param.List()

        # B inherit item_type
        assert B.param.p.default == [0]
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (0, None)
        assert B.param.p.item_type == int

        b = B()

        assert b.param.p.default == [0]
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (0, None)
        assert b.param.p.item_type == int

    def test_inheritance_behavior5(self):
        class A(param.Parameterized):
            p = param.List(default=[0, 1], allow_None=True)

        class B(A):
            p = param.List()

        # B does not inherit allow_None
        assert B.param.p.default == [0, 1]
        assert B.param.p.allow_None is False
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (0, None)

        b = B()

        assert b.param.p.default == [0, 1]
        assert b.param.p.allow_None is False
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (0, None)

    def test_inheritance_behavior6(self):
        class A(param.Parameterized):
            p = param.List(default=[0, 1], bounds=(1, 10))

        class B(A):
            p = param.List(default=[0, 1, 2, 3])

        assert B.param.p.default == [0, 1, 2, 3]
        assert B.param.p.instantiate is True
        assert B.param.p.bounds == (1, 10)

        b = B()

        assert b.param.p.default == [0, 1, 2, 3]
        assert b.param.p.instantiate is True
        assert b.param.p.bounds == (1, 10)


class TestHookListParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.HookList([abs])
            l = param.HookList(bounds=(0,10))

        self.P = P

    def _check_defaults(self, p):
        assert p.default == []
        assert p.allow_None is False
        assert p.class_ is None
        assert p.item_type is None
        assert p.bounds == (0, None)
        assert p.instantiate is True

    def test_defaults_class(self):
        class P(param.Parameterized):
            l = param.HookList()

        check_defaults(P.param.l, label='L', skip=['instantiate'])
        self._check_defaults(P.param.l)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            l = param.HookList()

        p = P()

        check_defaults(p.param.l, label='L', skip=['instantiate'])
        self._check_defaults(p.param.l)

    def test_defaults_unbound(self):
        l = param.HookList()

        check_defaults(l, label=None, skip=['instantiate'])
        self._check_defaults(l)

    def test_default_None(self):
        class Q(param.Parameterized):
            r = param.HookList(default=[])  #  Also check None)

    def test_set_object_constructor(self):
        p = self.P(e=[abs])
        self.assertEqual(p.e, [abs])

    def test_set_object_outside_bounds(self):
        p = self.P()
        try:
            p.l = [abs]*11
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_wrong_type_foo(self):
        p = self.P()
        try:
            p.e = ['s']
        except ValueError:
            pass
        else:
            raise AssertionError("Object allowed of wrong type.")

    def test_set_object_not_None(self):
        p = self.P()
        try:
            p.e = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")
