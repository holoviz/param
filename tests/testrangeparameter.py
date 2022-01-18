"""
Unit test for Range parameters.
"""
import unittest

import param


class TestRangeParameters(unittest.TestCase):

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

