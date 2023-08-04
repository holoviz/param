"""
Unit tests for DateRange parameter.
"""
import datetime as dt
import re
import unittest

import param
import pytest

from .utils import check_defaults

try:
    import numpy as np
except:
    np = None

# Assuming tests of range parameter cover most of what's needed to
# test date range.

class TestDateRange(unittest.TestCase):

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
            r = param.DateRange()

        check_defaults(P.param.r, label='R')
        self._check_defaults(P.param.r)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            r = param.DateRange()

        p = P()

        check_defaults(p.param.r, label='R')
        self._check_defaults(p.param.r)

    def test_defaults_unbound(self):
        r = param.DateRange()

        check_defaults(r, label=None)
        self._check_defaults(r)

    bad_range = (dt.datetime(2017,2,27),dt.datetime(2017,2,26))

    def test_wrong_type_default(self):
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'a' only takes a tuple value, not <class 'str'>.")
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default='wrong')

    def test_wrong_inner_type_default(self):
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'a' only takes date/datetime values, not <class 'float'>.")
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=(1.0,2.0))

    def test_wrong_inner_type_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' only takes date/datetime values, not <class 'float'>.")
        ):
            Q(a=(1.0, 2.0))

    def test_wrong_inner_type_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' only takes date/datetime values, not <class 'float'>.")
        ):
            q.a = (1.0, 2.0)

    def test_wrong_type_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' only takes a tuple value, not <class 'str'>.")
        ):
            Q(a='wrong')

    def test_wrong_type_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' only takes a tuple value, not <class 'str'>.")
        ):
            q.a = 'wrong'

    def test_start_before_end_default(self):
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'a' end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00.")
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=self.bad_range)

    def test_start_before_end_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00.")
        ):
            Q(a=self.bad_range)

    def test_start_before_end_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'Q.a' end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00.")
        ):
            q.a = self.bad_range

    def test_change_value_type(self):
        class DateSlider(param.Parameterized):
            date = param.DateRange(
                default=(dt.date(2021, 1, 1), dt.date(2024, 1, 1)),
                bounds=(dt.date(2020, 1, 1), dt.date(2025, 1, 1)),
            )

        ds = DateSlider()

        # Change the value from date to datetime without erroring
        ds.date = (dt.datetime(2022, 1, 1), dt.datetime(2023, 1, 1))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_support_mixed_date_datetime_bounds(self):
        # No error when comparing date and Python and Numpy datetimes

        date_bounds = (dt.date(2020, 1, 1), dt.date(2025, 1, 1))
        datetime_bounds = (dt.datetime(2020, 1, 1), dt.datetime(2025, 1, 1))
        numpy_bounds = (np.datetime64('2020-01-01T00:00'), np.datetime64('2025-01-01T00:00'))
        date_val = (dt.date(2021, 1, 1), dt.date(2024, 1, 1))
        datetime_val = (dt.datetime(2021, 1, 1), dt.datetime(2024, 1, 1))
        numpy_val = (np.datetime64('2021-01-01T00:00'), np.datetime64('2024-01-01T00:00'))

        class A(param.Parameterized):
            s = param.DateRange(default=datetime_val, bounds=date_bounds)
            t = param.DateRange(default=numpy_val, bounds=date_bounds)
            u = param.DateRange(default=date_val, bounds=datetime_bounds)
            v = param.DateRange(default=numpy_val, bounds=datetime_bounds)
            w = param.DateRange(default=date_val, bounds=numpy_bounds)
            x = param.DateRange(default=datetime_val, bounds=numpy_bounds)

        a = A()

        a.s = date_val
        a.s = datetime_val

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_numpy_default(self):
        class Q(param.Parameterized):
            a = param.DateRange(default=(np.datetime64('2022-01-01T00:00'), np.datetime64('2022-10-01T00:00')))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_numpy_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        q.a = (np.datetime64('2022-01-01T00:00'), np.datetime64('2022-10-01T00:00'))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_numpy_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        Q(a=(np.datetime64('2022-01-01T00:00'), np.datetime64('2022-10-01T00:00')))

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_numpy_start_before_end_default(self):
        with pytest.raises(
            ValueError,
            match=re.escape("DateRange parameter 'a' end datetime 2022-01-01T00:00 is before start datetime 2022-10-01T00:00.")
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=(np.datetime64('2022-10-01T00:00'), np.datetime64('2022-01-01T00:00')))
