"""
Unit tests for CalendarDateRange parameter.
"""

import datetime as dt
import param
from . import API1TestCase

# Assuming tests of range parameter cover most of what's needed to
# test date range.

class TestDateTimeRange(API1TestCase):

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
            r = param.CalendarDateRange()
        
        self._check_defaults(P.param.r)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            r = param.CalendarDateRange()

        p = P()

        self._check_defaults(p.param.r)

    def test_defaults_unbound(self):
        r = param.CalendarDateRange()

        self._check_defaults(r)

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
