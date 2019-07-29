"""
Unit tests for CalendarDateRange parameter.
"""

import unittest
import datetime as dt
import param


# Assuming tests of range parameter cover most of what's needed to
# test date range.

class TestDateTimeRange(unittest.TestCase):

    bad_range = (dt.date(2017,2,27),dt.date(2017,2,26))

    def test_wrong_type_default(self):
        try:
            class Q(param.Parameterized):
                a = param.CalendarDateRange(default=(1.0,2.0))
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date type was accepted.")

    def test_wrong_type_init(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        try:
            Q(a=self.bad_range)
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date type was accepted.")

    def test_wrong_type_set(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()
        q = Q()

        try:
            q.a = self.bad_range
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date type was accepted.")

    def test_start_before_end_default(self):
        try:
            class Q(param.Parameterized):
                a = param.CalendarDateRange(default=self.bad_range)
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date range was accepted.")

    def test_start_before_end_init(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        try:
            Q(a=self.bad_range)
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date range was accepted.")

    def test_start_before_end_set(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        q = Q()
        try:
            q.a = self.bad_range
        except ValueError:
            pass
        else:
            raise AssertionError("Bad date range was accepted.")
