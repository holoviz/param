"""
Unit test for Date parameters.
"""

import unittest
import datetime as dt
import param


class TestDateParameters(unittest.TestCase):

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Date(dt.datetime(2017,2,27),
                               bounds=(dt.datetime(2017,2,1),
                                       dt.datetime(2017,2,26)))
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Date(bounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,26)))
        try:
            Q.q = dt.datetime(2017,2,27)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_exclusive_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Date(bounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,26)),
                           inclusive_bounds=(True, False))
        try:
            Q.q = dt.datetime(2017,2,26)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_get_soft_bounds(self):
        q = param.Date(dt.datetime(2017,2,25),
                       bounds=(dt.datetime(2017,2,1),
                               dt.datetime(2017,2,26)),
                       softbounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,25)))
        self.assertEqual(q.get_soft_bounds(), (dt.datetime(2017,2,1),
                                               dt.datetime(2017,2,25)))

