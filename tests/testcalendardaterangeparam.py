"""
Unit tests for CalendarDateRange parameter.
"""
import datetime as dt
import re
import unittest

import param
import pytest

# Assuming tests of range parameter cover most of what's needed to
# test date range.

class TestDateTimeRange(unittest.TestCase):

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
        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'a' only takes date types, not (1.0, 2.0).")
        ):
            class Q(param.Parameterized):
                a = param.CalendarDateRange(default=(1.0,2.0))

    def test_wrong_type_init(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'Q.a' end date 2017-02-26 is before start date 2017-02-27.")
        ):
            Q(a=self.bad_range)

    def test_wrong_type_set(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()
        q = Q()

        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'Q.a' end date 2017-02-26 is before start date 2017-02-27.")
        ):
            q.a = self.bad_range

    def test_start_before_end_default(self):
        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'a' end date 2017-02-26 is before start date 2017-02-27.")
        ):
            class Q(param.Parameterized):
                a = param.CalendarDateRange(default=self.bad_range)

    def test_start_before_end_init(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'Q.a' end date 2017-02-26 is before start date 2017-02-27.")
        ):
            Q(a=self.bad_range)

    def test_start_before_end_set(self):
        class Q(param.Parameterized):
            a = param.CalendarDateRange()

        q = Q()
        with pytest.raises(
            ValueError,
            match=re.escape("CalendarDateRange parameter 'Q.a' end date 2017-02-26 is before start date 2017-02-27.")
        ):
            q.a = self.bad_range
