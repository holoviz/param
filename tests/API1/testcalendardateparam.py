"""
Unit test for CalendarDate parameters.
"""


import datetime as dt
import pytest
import param
from . import API1TestCase


class TestDateTimeParameters(API1TestCase):

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.CalendarDate(dt.date(2017,2,27),
                                       bounds=(dt.date(2017,2,1),
                                               dt.date(2017,2,26)))
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.CalendarDate(bounds=(dt.date(2017,2,1),
                                           dt.date(2017,2,26)))
        try:
            Q.q = dt.date(2017,2,27)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_set_exclusive_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.CalendarDate(bounds=(dt.date(2017,2,1),
                                           dt.date(2017,2,26)),
                                   inclusive_bounds=(True, False))
        try:
            Q.q = dt.date(2017,2,26)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on out-of-bounds date")

    def test_get_soft_bounds(self):
        q = param.CalendarDate(dt.date(2017,2,25),
                               bounds=(dt.date(2017,2,1),
                                       dt.date(2017,2,26)),
                               softbounds=(dt.date(2017,2,1),
                                           dt.date(2017,2,25)))
        self.assertEqual(q.get_soft_bounds(), (dt.date(2017,2,1),
                                               dt.date(2017,2,25)))

    def test_datetime_not_accepted(self):
        with pytest.raises(ValueError):
            param.CalendarDate(dt.datetime(2021, 8, 16, 10))
