"""
Unit test for Range parameters.
"""
import re
import unittest

import param
import pytest


class TestRangeParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
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
        msg = r"Attribute 'length' of Range parameter 'P.e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 2, 3)

    def test_raise_if_value_bad_length_constructor(self):
        msg = r"Attribute 'length' of Range parameter 'P.e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            self.P(e=(1, 1, 1))

    def test_raise_if_value_bad_length_setattr(self):
        p = self.P()
        msg = r"Attribute 'length' of Range parameter 'P.e' is not of the correct length \(3 instead of 2\)"
        with self.assertRaisesRegex(ValueError, msg):
            p.e = (1, 1, 1)

    def test_raise_if_default_is_None_and_no_length(self):
        msg = "Attribute 'length' of NumericTuple parameter 't' must be specified if no default is supplied"
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                t = param.NumericTuple(default=None)

    def test_bad_type(self):
        msg = r"Range parameter 'P.e' only takes a tuple value, not <(class|type) 'str'>."

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'

        msg = r"Range parameter 'e' only takes a tuple value, not <(class|type) 'str'>."
        with self.assertRaisesRegex(ValueError, msg):
            class P(param.Parameterized):
                e = param.Range(default='test')

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
        msg = "Range parameter 'P.g' only takes a tuple value, not <(class|type) 'NoneType'>."
        with self.assertRaisesRegex(ValueError, msg):
            p.g = None

        with self.assertRaisesRegex(ValueError, msg):
            self.P.g = None

    def test_initialization_out_of_bounds_lower(self):
        with pytest.raises(
            ValueError,
            match=re.escape("Range parameter 'q' lower bound must be in range [0, 1], not -1.")
        ):
            class Q(param.Parameterized):
                q = param.Range((-1, 1), bounds=(0, 1))

    def test_initialization_out_of_bounds_upper(self):
        with pytest.raises(
            ValueError,
            match=re.escape("Range parameter 'q' upper bound must be in range [0, 1], not 2.")
        ):
            class Q(param.Parameterized):
                q = param.Range((0, 2), bounds=(0, 1))

    def test_set_exclusive_out_of_bounds_upper(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10), inclusive_bounds=(True, False))
        with pytest.raises(
            ValueError,
            match=re.escape("Range parameter 'Q.q' upper bound must be in range [0, 10), not 10.")
        ):
            Q.q = (0, 10)

    def test_set_exclusive_out_of_bounds_lower(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10), inclusive_bounds=(False, True))
        with pytest.raises(
            ValueError,
            match=re.escape("Range parameter 'Q.q' lower bound must be in range (0, 10], not 0.")
        ):
            Q.q = (0, 10)

    def test_set_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10))
        with pytest.raises(
            ValueError,
            match=re.escape("Range parameter 'Q.q' upper bound must be in range [0, 10], not 11.")
        ):
            Q.q = (5, 11)

    def test_get_soft_bounds(self):
        q = param.Range((1,3), bounds=(0, 10), softbounds=(1, 9))
        self.assertEqual(q.get_soft_bounds(), (1, 9))

    def test_validate_step(self):
        msg = re.escape("Attribute 'step' of Range parameter can only be None or a numeric value, not <class 'str'>.")

        p = param.Range((1, 2), bounds=(0, 10), step=1)
        assert p.step == 1

        with self.assertRaisesRegex(ValueError, msg):
            param.Range((1, 2), bounds=(0, 10), step="1")

    def test_validate_order_on_val_with_positive_step(self):
        msg = re.escape("Range parameter 'Q.q' end 1 is less than its start 2 with positive step 1.")

        class Q(param.Parameterized):
            q = param.Range(bounds=(0, 10), step=1)

        with self.assertRaisesRegex(ValueError, msg):
            Q.q = (2, 1)

    def test_validate_order_on_val_with_negative_step(self):
        msg = re.escape("Range parameter 'Q.q' start -4 is less than its start -2 with negative step -1.")

        class Q(param.Parameterized):
            q = param.Range(bounds=(-5, -1), step=-1)

        with self.assertRaisesRegex(ValueError, msg):
            Q.q = (-4, -2)

    def test_validate_step_order_cannot_be_0(self):
        msg = re.escape("Attribute 'step' of Range parameter cannot be 0.")

        with self.assertRaisesRegex(ValueError, msg):
            param.Range(bounds=(0, 10), step=0)

    def test_validate_bounds_wrong_type_lower(self):
        msg = re.escape("Range parameter lower bound can only be None or a numerical value, not <class 'str'>.")
        with pytest.raises(ValueError, match=msg):
            param.Range(bounds=('a', 1))

    def test_validate_bounds_wrong_type_upper(self):
        msg = re.escape("Range parameter upper bound can only be None or a numerical value, not <class 'str'>.")
        with pytest.raises(ValueError, match=msg):
            param.Range(bounds=(0, 'b'))

    def test_validate_softbounds_wrong_type_lower(self):
        msg = re.escape("Range parameter lower softbound can only be None or a numerical value, not <class 'str'>.")
        with pytest.raises(ValueError, match=msg):
            param.Range(softbounds=('a', 1))

    def test_validate_softbounds_wrong_type_upper(self):
        msg = re.escape("Range parameter upper softbound can only be None or a numerical value, not <class 'str'>.")
        with pytest.raises(ValueError, match=msg):
            param.Range(softbounds=(0, 'b'))
