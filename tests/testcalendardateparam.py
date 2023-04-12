"""
Unit test for CalendarDate parameters.
"""
import datetime as dt
import unittest

import pytest

import param
from .utils import check_defaults


class TestDateTimeParameters(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.bounds is None
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            d = param.CalendarDate()

        check_defaults(A.param.d, label='D')
        self._check_defaults(A.param.d)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            d = param.CalendarDate()

        a = A()

        check_defaults(a.param.d, label='D')
        self._check_defaults(a.param.d)

    def test_defaults_unbound(self):
        d = param.CalendarDate()

        check_defaults(d, label=None)
        self._check_defaults(d)

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

    def test_step_invalid_type_parameter(self):
        exception = "Step can only be None or a date type"
        with self.assertRaisesRegex(ValueError, exception):
            param.CalendarDate(dt.date(2017,2,27), step=3.2)
