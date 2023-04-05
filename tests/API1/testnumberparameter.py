"""
Unit test for Number parameters and their subclasses.
"""
import param
from . import API1TestCase
from .utils import check_defaults


class TestNumberParameters(API1TestCase):

    def setUp(self):
        super(TestNumberParameters, self).setUp()
        class P(param.Parameterized):
            b = param.Number(allow_None=False)
            c = param.Number(default=1, allow_None=True)
            d = param.Number(default=None)
            e = param.Number(default=1)
            f = param.Number(default=1, step=0.5)
            g = param.Number(default=lambda: 1)
            h = param.Number(default=1, bounds=(0, 2))
            i = param.Number(bounds=(-1, 1))
            j = param.Number(bounds=(-1, 1), inclusive_bounds=(False, True))
            k = param.Number(bounds=(-1, 1), inclusive_bounds=(True, False))
            l = param.Number(bounds=(-1, 1), inclusive_bounds=(False, False))
            m = param.Number(bounds=(-1, None))
            n = param.Number(bounds=(None, 1))

        self.P = P

    def _check_defaults(self, p):
        assert p.default == 0.0
        assert p.allow_None is False
        assert p.bounds is None
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            n = param.Number()

        check_defaults(A.param.n, label='N')
        self._check_defaults(A.param.n)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            n = param.Number()

        a = A()

        check_defaults(a.param.n, label='N')
        self._check_defaults(a.param.n)

    def test_defaults_unbound(self):
        n = param.Number()

        check_defaults(n, label=None)
        self._check_defaults(n)

    def test_allow_None_class(self):
        self.P.c = None
        assert self.P.c is None
        self.P.d = None
        assert self.P.d is None

        exception = "Parameter 'b' only takes numeric values, not type <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.b = None

    def test_allow_None_inst(self):
        p = self.P()
        p.c = None
        assert p.c is None
        p.d = None
        assert p.d is None

        exception = "Parameter 'b' only takes numeric values, not type <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, exception):
            p.b = None

    def test_initialization_without_step_class(self):
        self.assertEqual(self.P.param['e'].step, None)

    def test_initialization_with_step_class(self):
        self.assertEqual(self.P.param['f'].step, 0.5)

    def test_initialization_without_step_instance(self):
        p = self.P()
        self.assertEqual(p.param['e'].step, None)

    def test_initialization_with_step_instance(self):
        p = self.P()
        self.assertEqual(p.param['f'].step, 0.5)

    def test_step_invalid_type_number_parameter(self):
        exception = "Step can only be None or a numeric value"
        with self.assertRaisesRegex(ValueError, exception):
            param.Number(step='invalid value')

    def test_outside_bounds(self):
        exception = "Parameter 'h' must be at most 2, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.h = 10

        p = self.P()

        with self.assertRaisesRegex(ValueError, exception):
            p.h = 10

    def test_unbounded_side_class(self):
        self.P.m = 10
        assert self.P.m == 10

        exception = "Parameter 'm' must be at least -1, not -10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.m = -10

        self.P.n = -10
        assert self.P.n == -10

        exception = "Parameter 'n' must be at most 1, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.n = 10

    def test_unbounded_side_inst(self):
        p = self.P()

        p.m = 10
        assert p.m == 10

        exception = "Parameter 'm' must be at least -1, not -10."
        with self.assertRaisesRegex(ValueError, exception):
            p.m = -10

        p.n = -10
        assert p.n == -10

        exception = "Parameter 'n' must be at most 1, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            p.n = 10

    def test_inclusive_bounds_no_error_class(self):
        self.P.i = -1
        assert self.P.i == -1
        self.P.i = 1
        assert self.P.i == 1

        self.P.j = 1
        assert self.P.j == 1

        self.P.k = -1
        assert self.P.k == -1

    def test_inclusive_bounds_no_error_inst(self):
        p = self.P()
        p.i = -1
        assert p.i == -1
        p.i = 1
        assert p.i == 1

        p.j = 1
        assert p.j == 1

        p.k = -1
        assert p.k == -1

    def test_inclusive_bounds_error_on_bounds(self):
        p = self.P()
        exception = "Parameter 'j' must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.j = -1
        with self.assertRaisesRegex(ValueError, exception):
            p.j = -1

        exception = "Parameter 'k' must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.k = 1
        with self.assertRaisesRegex(ValueError, exception):
            p.k = 1

        exception = "Parameter 'l' must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.l = -1
        with self.assertRaisesRegex(ValueError, exception):
            p.l = -1
        exception = "Parameter 'l' must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.l = 1
        with self.assertRaisesRegex(ValueError, exception):
            p.l = 1

    def test_inclusive_bounds_error_on_bounds_post(self):
        exception = "Parameter None must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Number(default=-1, bounds=(-1, 1), inclusive_bounds=(False, True))

        exception = "Parameter None must be less than 1, not 1"
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Number(default=1, bounds=(-1, 1), inclusive_bounds=(True, False))

        exception = "Parameter None must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Number(default=-1, bounds=(-1, 1), inclusive_bounds=(False, False))

        exception = "Parameter None must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Number(default=1, bounds=(-1, 1), inclusive_bounds=(False, False))

    def test_invalid_default_for_bounds(self):
        exception = "Parameter None must be at least 10, not 0.0."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                n = param.Number(bounds=(10, 20))

    def test_callable(self):
        assert self.P.g == 1
        p = self.P()
        assert p.g == 1

    def test_callable_wrong_type(self):
        class Q(param.Parameterized):
            q = param.Number(default=lambda: 'test')

        exception = "Parameter 'q' only takes numeric values, not type <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, exception):
            Q.q

        q = Q()

        with self.assertRaisesRegex(ValueError, exception):
            q.q

    def test_callable_outside_bounds(self):
        class Q(param.Parameterized):
            q = param.Number(default=lambda: 2, bounds=(0, 1))

        exception = "Parameter 'q' must be at most 1, not 2."
        with self.assertRaisesRegex(ValueError, exception):
            Q.q

        q = Q()

        with self.assertRaisesRegex(ValueError, exception):
            q.q

    def test_crop_to_bounds(self):
        p = self.P()

        # when allow_None is True
        assert p.param.d.crop_to_bounds(None) is None

        # no bounds
        assert p.param.e.crop_to_bounds(10000) == 10000

        # with concrete bounds
        assert p.param.h.crop_to_bounds(10) == 2
        assert p.param.h.crop_to_bounds(-10) == 0

        # return default if non numerical
        assert p.param.e.crop_to_bounds('test') == 1

        # Unbound
        assert p.param.m.crop_to_bounds(10) == 10
        assert p.param.n.crop_to_bounds(-10) == -10

    def test_inheritance_allow_None_behavior(self):
        class A(param.Parameterized):
            p = param.Number(allow_None=True)

        class B(A):
            p = param.Number()

        # A says None is not allowed, B disagrees.
        assert B.param.p.allow_None is False

        b = B()

        assert b.param.p.allow_None is False

    def test_inheritance_allow_None_behavior2(self):
        class A(param.Parameterized):
            p = param.Number(allow_None=False)
            
        class B(A):
            p = param.Number(default=None)


        # A says None is not allowed, B sets the default to None and recomputes
        # allow_None.
        assert B.param.p.allow_None is True

        b = B()

        assert b.param.p.allow_None is True

    def test_inheritance_callable_default_behavior(self):

        f = lambda: 2
        class A(param.Parameterized):
            p = param.Number(default=f)
            
        class B(A):
            p = param.Number()

        assert A.p == 2
        assert A.param.p.default == f
        assert A.param.p.instantiate is True

        # Default is not inherited but instantiate is still set to True
        assert B.p == 0.0
        assert B.param.p.default == 0.0
        assert B.param.p.instantiate is True

        b = B()

        assert b.p == 0.0
        assert b.param.p.default == 0.0
        assert b.param.p.instantiate is True


class TestIntegerParameters(API1TestCase):

    def setUp(self):
        super(TestIntegerParameters, self).setUp()
        class P(param.Parameterized):
            b = param.Integer(allow_None=False)
            c = param.Integer(default=1, allow_None=True)
            d = param.Integer(default=None)
            e = param.Integer(default=1)
            f = param.Integer(default=1, step=1)
            g = param.Integer(default=lambda: 1)
            h = param.Integer(default=1, bounds=(0, 2))
            i = param.Integer(bounds=(-1, 1))
            j = param.Integer(bounds=(-1, 1), inclusive_bounds=(False, True))
            k = param.Integer(bounds=(-1, 1), inclusive_bounds=(True, False))
            l = param.Integer(bounds=(-1, 1), inclusive_bounds=(False, False))
            m = param.Integer(bounds=(-1, None))
            n = param.Integer(bounds=(None, 1))

        self.P = P

    def _check_defaults(self, p):
        assert isinstance(p.default, int)
        assert p.default == 0
        assert p.allow_None is False
        assert p.bounds is None
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            n = param.Integer()

        check_defaults(A.param.n, label='N')
        self._check_defaults(A.param.n)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            n = param.Integer()

        a = A()

        check_defaults(a.param.n, label='N')
        self._check_defaults(a.param.n)

    def test_defaults_unbound(self):
        n = param.Integer()

        check_defaults(n, label=None)
        self._check_defaults(n)

    def test_allow_None_class(self):
        self.P.c = None
        assert self.P.c is None
        self.P.d = None
        assert self.P.d is None

        exception = "Integer parameter 'b' must be an integer, not type <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.b = None

    def test_allow_None_inst(self):
        p = self.P()
        p.c = None
        assert p.c is None
        p.d = None
        assert p.d is None

        exception = "Integer parameter 'b' must be an integer, not type <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, exception):
            p.b = None

    def test_initialization_without_step_class(self):
        class Q(param.Parameterized):
            q = param.Integer(default=1)

        self.assertEqual(Q.param['q'].step, None)


    def test_initialization_without_step_class(self):
        self.assertEqual(self.P.param['e'].step, None)

    def test_initialization_with_step_class(self):
        self.assertEqual(self.P.param['f'].step, 1)

    def test_initialization_without_step_instance(self):
        p = self.P()
        self.assertEqual(p.param['e'].step, None)

    def test_initialization_with_step_instance(self):
        p = self.P()
        self.assertEqual(p.param['f'].step, 1)

    def test_step_invalid_type_number_parameter(self):
        exception = "Step can only be None or an integer value"
        with self.assertRaisesRegex(ValueError, exception):
            param.Integer(step='invalid value')

    def test_step_invalid_type_integer_parameter(self):
        exception = "Step can only be None or an integer value"
        with self.assertRaisesRegex(ValueError, exception):
            param.Integer(step=3.4)

    def test_outside_bounds(self):
        exception = "Parameter 'h' must be at most 2, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.h = 10

        p = self.P()

        with self.assertRaisesRegex(ValueError, exception):
            p.h = 10

    def test_unbounded_side_class(self):
        self.P.m = 10
        assert self.P.m == 10

        exception = "Parameter 'm' must be at least -1, not -10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.m = -10

        self.P.n = -10
        assert self.P.n == -10

        exception = "Parameter 'n' must be at most 1, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.n = 10

    def test_unbounded_side_inst(self):
        p = self.P()

        p.m = 10
        assert p.m == 10

        exception = "Parameter 'm' must be at least -1, not -10."
        with self.assertRaisesRegex(ValueError, exception):
            p.m = -10

        p.n = -10
        assert p.n == -10

        exception = "Parameter 'n' must be at most 1, not 10."
        with self.assertRaisesRegex(ValueError, exception):
            p.n = 10

    def test_inclusive_bounds_no_error_class(self):
        self.P.i = -1
        assert self.P.i == -1
        self.P.i = 1
        assert self.P.i == 1

        self.P.j = 1
        assert self.P.j == 1

        self.P.k = -1
        assert self.P.k == -1

    def test_inclusive_bounds_no_error_inst(self):
        p = self.P()
        p.i = -1
        assert p.i == -1
        p.i = 1
        assert p.i == 1

        p.j = 1
        assert p.j == 1

        p.k = -1
        assert p.k == -1

    def test_inclusive_bounds_error_on_bounds(self):
        p = self.P()
        exception = "Parameter 'j' must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.j = -1
        with self.assertRaisesRegex(ValueError, exception):
            p.j = -1

        exception = "Parameter 'k' must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.k = 1
        with self.assertRaisesRegex(ValueError, exception):
            p.k = 1

        exception = "Parameter 'l' must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.l = -1
        with self.assertRaisesRegex(ValueError, exception):
            p.l = -1
        exception = "Parameter 'l' must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            self.P.l = 1
        with self.assertRaisesRegex(ValueError, exception):
            p.l = 1

    def test_inclusive_bounds_error_on_bounds_post(self):
        exception = "Parameter None must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Integer(default=-1, bounds=(-1, 1), inclusive_bounds=(False, True))

        exception = "Parameter None must be less than 1, not 1"
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Integer(default=1, bounds=(-1, 1), inclusive_bounds=(True, False))

        exception = "Parameter None must be greater than -1, not -1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Integer(default=-1, bounds=(-1, 1), inclusive_bounds=(False, False))

        exception = "Parameter None must be less than 1, not 1."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                j = param.Integer(default=1, bounds=(-1, 1), inclusive_bounds=(False, False))

    def test_invalid_default_for_bounds(self):
        exception = "Parameter None must be at least 10, not 0."
        with self.assertRaisesRegex(ValueError, exception):
            class P(param.Parameterized):
                n = param.Integer(bounds=(10, 20))

    def test_callable(self):
        assert self.P.g == 1
        p = self.P()
        assert p.g == 1

    def test_callable_wrong_type(self):
        class Q(param.Parameterized):
            q = param.Integer(default=lambda: 'test')

        exception = "Integer parameter 'q' must be an integer, not type <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, exception):
            Q.q

        q = Q()

        with self.assertRaisesRegex(ValueError, exception):
            q.q

    def test_callable_outside_bounds(self):
        class Q(param.Parameterized):
            q = param.Integer(default=lambda: 2, bounds=(0, 1))

        exception = "Parameter 'q' must be at most 1, not 2."
        with self.assertRaisesRegex(ValueError, exception):
            Q.q

        q = Q()

        with self.assertRaisesRegex(ValueError, exception):
            q.q

    def test_crop_to_bounds(self):
        p = self.P()

        # when allow_None is True
        assert p.param.d.crop_to_bounds(None) is None

        # no bounds
        assert p.param.e.crop_to_bounds(10000) == 10000

        # with concrete bounds
        assert p.param.h.crop_to_bounds(10) == 2
        assert p.param.h.crop_to_bounds(-10) == 0

        # return default if non numerical
        assert p.param.e.crop_to_bounds('test') == 1

        # Unbound
        assert p.param.m.crop_to_bounds(10) == 10
        assert p.param.n.crop_to_bounds(-10) == -10


class TestMagnitudeParameters(API1TestCase):

    def _check_defaults(self, p):
        assert p.default == 1.0
        assert p.allow_None is False
        assert p.bounds == (0.0, 1.0)
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            n = param.Magnitude()

        check_defaults(A.param.n, label='N')
        self._check_defaults(A.param.n)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            n = param.Magnitude()

        a = A()

        check_defaults(a.param.n, label='N')
        self._check_defaults(a.param.n)

    def test_defaults_unbound(self):
        n = param.Magnitude()

        check_defaults(n, label=None)
        self._check_defaults(n)
