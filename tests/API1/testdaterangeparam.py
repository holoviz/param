"""
Unit tests for DateRange parameter.
"""

import datetime as dt

import param
import pytest

from . import API1TestCase

try:
    import numpy as np
except:
    np = None

# Assuming tests of range parameter cover most of what's needed to
# test date range.

class TestDateRange(API1TestCase):

    bad_range = (dt.datetime(2017,2,27),dt.datetime(2017,2,26))

    def test_wrong_type_default(self):
        with pytest.raises(
            ValueError,
            match="DateRange parameter None only takes a tuple value, not str."
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default='wrong')

    def test_wrong_inner_type_default(self):
        with pytest.raises(
            ValueError,
            match='DateRange parameter None only takes date/datetime values, not type float.'
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=(1.0,2.0))

    def test_wrong_inner_type_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a' only takes date/datetime values, not type float."
        ):
            Q(a=(1.0, 2.0))

    def test_wrong_inner_type_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a' only takes date/datetime values, not type float."
        ):
            q.a = (1.0, 2.0)

    def test_wrong_type_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a' only takes a tuple value, not str."
        ):
            Q(a='wrong')

    def test_wrong_type_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a' only takes a tuple value, not str."
        ):
            q.a = 'wrong'

    def test_start_before_end_default(self):
        with pytest.raises(
            ValueError,
            match="DateRange parameter None's end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00."
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=self.bad_range)

    def test_start_before_end_init(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a''s end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00."
        ):
            Q(a=self.bad_range)

    def test_start_before_end_set(self):
        class Q(param.Parameterized):
            a = param.DateRange()
        q = Q()
        with pytest.raises(
            ValueError,
            match="DateRange parameter 'a''s end datetime 2017-02-26 00:00:00 is before start datetime 2017-02-27 00:00:00."
        ):
            q.a = self.bad_range

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
            match="DateRange parameter None's end datetime 2022-01-01T00:00 is before start datetime 2022-10-01T00:00."
        ):
            class Q(param.Parameterized):
                a = param.DateRange(default=(np.datetime64('2022-10-01T00:00'), np.datetime64('2022-01-01T00:00')))
