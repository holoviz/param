"""
Unit test for Range parameters.
"""
import unittest

import param


class TestRangeParameters(unittest.TestCase):

    def setUp(self):
        super(TestRangeParameters, self).setUp()
        class P(param.Parameterized):
            e = param.Range()
            f = param.Range(default=(0, 1), allow_None=True)
            g = param.Range(default=(0, 1))

        self.P = P

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.length == 2
        assert p.bounds is None
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class P(param.Parameterized):
            r = param.Range()
        
        self._check_defaults(P.param.r)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            r = param.Range()

        p = P()

        self._check_defaults(p.param.r)

    def test_defaults_unbound(self):
        r = param.Range()

        self._check_defaults(r)

    def test_set_object_constructor(self):
        p = self.P(e=(0, 20))
        assert p.e == (0, 20)

    def test_raise_not_2_tuple(self):
        p = self.P()
        msg = r"Tuple parameter 'e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 2, 3)

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

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Range((0, 2), bounds=(0, 1))
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_exclusive_out_of_bounds_upper(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10), inclusive_bounds=(True, False))
        try:
            Q.q = (0, 10)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_exclusive_out_of_bounds_lower(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10), inclusive_bounds=(False, True))
        try:
            Q.q = (0, 10)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10))
        try:
            Q.q = (5, 11)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_get_soft_bounds(self):
        q = param.Range((1,3), bounds=(0, 10), softbounds=(1, 9))
        self.assertEqual(q.get_soft_bounds(), (1, 9))

