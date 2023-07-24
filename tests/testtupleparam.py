import unittest


import param
import pytest

from .utils import check_defaults

try:
    import numpy as np
except:
    np = None


class TestTupleParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.Tuple(default=(1, 1))
            f = param.Tuple(default=(0, 0, 0))
            g = param.Tuple(default=None, length=3)
            h = param.Tuple(length=2, allow_None=True)

        self.P = P

    def _check_defaults(self, p):
        assert p.default == (0, 0)
        assert p.length == 2
        assert p.allow_None is False

    def test_defaults_class(self):
        class P(param.Parameterized):
            t = param.Tuple()

        check_defaults(P.param.t, label='T')
        self._check_defaults(P.param.t)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            t = param.Tuple()

        p = P()

        check_defaults(p.param.t, label='T')
        self._check_defaults(p.param.t)

    def test_defaults_unbound(self):
        t = param.Tuple()

        check_defaults(t, label=None)
        self._check_defaults(t)

    def test_unbound_length_inferred(self):
        t = param.Tuple((0, 1, 2))

        assert t.length == 3

    def test_unbound_length_set(self):
        t = param.Tuple(default=None, length=3)

        assert t.length == 3

    def test_set_object_constructor(self):
        p = self.P(e=(2, 2))
        self.assertEqual(p.e, (2, 2))

    def test_length_inferred_from_default(self):
        p = self.P()
        assert p.param.f.length == 3

    def test_raise_if_value_bad_length_constructor(self):
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=(1, 1, 'extra'))

    def test_raise_if_value_bad_length_setattr(self):
        p = self.P()
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 1, 'extra')

    def test_raise_if_default_is_None_and_no_length(self):
        msg = "length must be specified if no default is supplied"
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                t = param.Tuple(default=None)

    def test_None_default(self):
        p = self.P()
        assert p.g is None
        assert p.param.g.length == 3
        assert p.param.g.allow_None

    def test_raise_if_default_is_None_and_bad_length(self):
        msg = r"Tuple parameter 'g' is not of the correct length \(2 instead of 3\)."
        with self.assertRaisesRegex(ValueError, msg):
            p = self.P(g=(0, 0))

        p = self.P()
        with self.assertRaisesRegex(ValueError, msg):
            p.g = (0, 0)

    def test_bad_type(self):
        msg = r"Tuple parameter 'e' only takes a tuple value, not <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'

        msg = r"Tuple parameter None only takes a tuple value, not <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.Tuple(default='test')

    def test_support_allow_None(self):
        p = self.P()
        assert p.h == (0, 0)
        p.h = None
        p.h = (1, 1)
        assert p.h == (1, 1)

        class P(param.Parameterized):
            h = param.Tuple(length=2, allow_None=True)

        P.h = None
        P.h = (1, 1)
        assert P.h == (1, 1)

    def test_inheritance_length_behavior1(self):
        class A(param.Parameterized):
            p = param.Tuple(default=(0, 1, 2))

        class B(A):
            p = param.Tuple()

        assert B.p == (0, 1, 2)
        assert B.param.p.length == 3

        b = B()

        assert b.p == (0, 1, 2)
        assert b.param.p.default == (0, 1, 2)
        assert b.param.p.length == 3

    def test_inheritance_length_behavior2(self):
        class A(param.Parameterized):
            p = param.Tuple(default=(0, 1, 2), length=3)

        class B(A):
            p = param.Tuple()

        assert B.p == (0, 1, 2)
        assert B.param.p.length == 3

        b = B()

        assert b.p == (0, 1, 2)
        assert b.param.p.default == (0, 1, 2)
        assert b.param.p.length == 3

    def test_inheritance_length_behavior3(self):
        class A(param.Parameterized):
            p = param.Tuple()

        class B(A):
            p = param.Tuple(default=(0, 1, 2, 3))

        assert B.p == (0, 1, 2, 3)
        assert B.param.p.length == 4

        b = B()

        assert b.p == (0, 1, 2, 3)
        assert b.param.p.default == (0, 1, 2, 3)
        assert b.param.p.length == 4

    def test_inheritance_length_behavior4(self):
        class A(param.Parameterized):
            p = param.Tuple(default=(0, 1, 2))

        class B(A):
            p = param.Tuple(default=(0, 1, 2, 3))

        assert B.p == (0, 1, 2, 3)
        assert B.param.p.length == 4

        b = B()

        assert b.p == (0, 1, 2, 3)
        assert b.param.p.default == (0, 1, 2, 3)
        assert b.param.p.length == 4

    def test_inheritance_length_behavior5(self):
        class A(param.Parameterized):
            p = param.Tuple(default=(0, 1, 2, 3))

        class B(A):
            p = param.Tuple(default=(0, 1, 2))

        assert B.p == (0, 1, 2)
        assert B.param.p.length == 3

        b = B()

        assert b.p == (0, 1, 2)
        assert b.param.p.default == (0, 1, 2)
        assert b.param.p.length == 3

class TestNumericTupleParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.NumericTuple(default=(1, 1))
            f = param.NumericTuple(default=(0, 0, 0))
            g = param.NumericTuple(default=None, length=3)
            h = param.NumericTuple(length=2, allow_None=True)

        self.P = P

    def _check_defaults(self, p):
        assert p.default == (0, 0)
        assert p.length == 2
        assert p.allow_None is False

    def test_defaults_class(self):
        class P(param.Parameterized):
            t = param.NumericTuple()

        check_defaults(P.param.t, label='T')
        self._check_defaults(P.param.t)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            t = param.NumericTuple()

        p = P()

        check_defaults(p.param.t, label='T')
        self._check_defaults(p.param.t)

    def test_defaults_unbound(self):
        t = param.NumericTuple()

        check_defaults(t, label=None)
        self._check_defaults(t)

    def test_set_object_constructor(self):
        p = self.P(e=(2, 2))
        self.assertEqual(p.e, (2, 2))

    def test_length_inferred_from_default(self):
        p = self.P()
        assert p.param.f.length == 3

    def test_raise_if_value_bad_length_constructor(self):
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=(1, 1, 1))

    def test_raise_if_value_bad_length_setattr(self):
        p = self.P()
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 1, 1)

    def test_raise_if_default_is_None_and_no_length(self):
        msg = "length must be specified if no default is supplied"
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                t = param.NumericTuple(default=None)

    def test_None_default(self):
        p = self.P()
        assert p.g is None
        assert p.param.g.length == 3
        assert p.param.g.allow_None

    def test_raise_if_default_is_None_and_bad_length(self):
        msg = r"Tuple parameter 'g' is not of the correct length \(2 instead of 3\)."
        with self.assertRaisesRegex(ValueError, msg):
            p = self.P(g=(0, 0))

        p = self.P()
        with self.assertRaisesRegex(ValueError, msg):
            p.g = (0, 0)

    def test_bad_type(self):
        msg = r"Tuple parameter 'e' only takes a tuple value, not <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'

        msg = r"Tuple parameter None only takes a tuple value, not <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.NumericTuple(default='test')

    def test_support_allow_None(self):
        p = self.P()
        assert p.h == (0, 0)
        p.h = None
        p.h = (1, 1)
        assert p.h == (1, 1)

        class P(param.Parameterized):
            h = param.NumericTuple(length=2, allow_None=True)

        P.h = None
        P.h = (1, 1)
        assert P.h == (1, 1)

    def test_raise_on_non_numeric_values(self):
        msg = r"NumericTuple parameter 'e' only takes numeric values, not type <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = ('bad', 1)

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=('bad', 1))

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = ('bad', 1)

        msg = r"NumericTuple parameter None only takes numeric values, not type <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.NumericTuple(default=('bad', 1))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_support_numpy_values(self):
        self.P(e=(np.int64(1), np.float32(2)))


class TestXYCoordinatesParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.XYCoordinates(default=(1, 1))
            f = param.XYCoordinates(default=(0, 1), allow_None=True)
            g = param.XYCoordinates(default=(1, 2))

        self.P = P

    def _check_defaults(self, p):
        assert p.default == (0.0, 0.0)
        assert p.length == 2
        assert p.allow_None is False

    def test_defaults_class(self):
        class P(param.Parameterized):
            t = param.XYCoordinates()

        self._check_defaults(P.param.t)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            t = param.XYCoordinates()

        p = P()

        self._check_defaults(p.param.t)

    def test_defaults_unbound(self):
        t = param.XYCoordinates()

        self._check_defaults(t)

    def test_set_object_constructor(self):
        p = self.P(e=(2, 2))
        self.assertEqual(p.e, (2, 2))

    def test_raise_if_value_bad_length_constructor(self):
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=(1, 1, 1))

    def test_raise_if_value_bad_length_setattr(self):
        p = self.P()
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 1, 1)

    def test_bad_type(self):
        msg = r"Tuple parameter 'e' only takes a tuple value, not <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'

        msg = r"Tuple parameter None only takes a tuple value, not <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.NumericTuple(default='test')

    def test_support_allow_None_True(self):
        p = self.P()
        assert p.f == (0, 1)
        p.f = None
        assert p.f is None

        class P(param.Parameterized):
            f = param.Range(default=(0, 1), allow_None=True)

        P.f = None
        assert P.f is None

    def test_support_allow_None_False(self):
        p = self.P()
        msg = "Tuple parameter 'g' only takes a tuple value, not <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, msg):
            p.g = None

        msg = "Tuple parameter 'g' only takes a tuple value, not <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, msg):
            self.P.g = None

    def test_raise_on_non_numeric_values(self):
        msg = r"NumericTuple parameter 'e' only takes numeric values, not type <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = ('bad', 1)

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=('bad', 1))

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = ('bad', 1)

        msg = r"NumericTuple parameter None only takes numeric values, not type <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.NumericTuple(default=('bad', 1))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_support_numpy_values(self):
        self.P(e=(np.int64(1), np.float32(2)))
