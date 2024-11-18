"""
Unit test for Date parameters.
"""
import datetime as dt
import json
import re
import unittest

import param
import pytest

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from .utils import check_defaults


class TestDateParameters(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.bounds is None
        assert p.softbounds is None
        assert p.inclusive_bounds == (True, True)
        assert p.step is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            d = param.Date()

        check_defaults(A.param.d, label='D')
        self._check_defaults(A.param.d)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            d = param.Date()

        a = A()

        check_defaults(a.param.d, label='D')
        self._check_defaults(a.param.d)

    def test_defaults_unbound(self):
        d = param.Date()

        check_defaults(d, label=None)
        self._check_defaults(d)

    def test_initialization_out_of_bounds(self):
        with pytest.raises(
            ValueError,
            match=re.escape("Date parameter 'q' must be at most 2017-02-26 00:00:00, not 2017-02-27 00:00:00.")
        ):
            class Q(param.Parameterized):
                q = param.Date(dt.datetime(2017,2,27),
                               bounds=(dt.datetime(2017,2,1),
                                       dt.datetime(2017,2,26)))

    def test_set_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Date(bounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,26)))
        with pytest.raises(
            ValueError,
            match=re.escape("Date parameter 'Q.q' must be at most 2017-02-26 00:00:00, not 2017-02-27 00:00:00.")
        ):
            Q.q = dt.datetime(2017,2,27)

    def test_set_exclusive_out_of_bounds(self):
        class Q(param.Parameterized):
            q = param.Date(bounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,26)),
                           inclusive_bounds=(True, False))
        with pytest.raises(
            ValueError,
            match=re.escape("Date parameter 'Q.q' must be less than 2017-02-26 00:00:00, not 2017-02-26 00:00:00.")
        ):
            Q.q = dt.datetime(2017,2,26)

    def test_get_soft_bounds(self):
        q = param.Date(dt.datetime(2017,2,25),
                       bounds=(dt.datetime(2017,2,1),
                               dt.datetime(2017,2,26)),
                       softbounds=(dt.datetime(2017,2,1),
                                   dt.datetime(2017,2,25)))
        self.assertEqual(q.get_soft_bounds(), (dt.datetime(2017,2,1),
                                               dt.datetime(2017,2,25)))

    def test_wrong_type(self):
        with pytest.raises(
            ValueError,
            match=re.escape("Date parameter 'q' only takes datetime and date types, not <class 'str'>.")
        ):
            q = param.Date('wrong')  # noqa

    def test_step_invalid_type_datetime_parameter(self):
        exception = re.escape("Attribute 'step' of Date parameter can only be None, a datetime or date type, not <class 'float'>.")
        with pytest.raises(ValueError, match=exception):
            param.Date(dt.datetime(2017,2,27), step=3.2)

    @pytest.mark.skipif(np is None, reason='NumPy is not available')
    def test_support_mixed_date_datetime_bounds(self):
        # No error when comparing date and Python and Numpy datetimes

        date_bounds = (dt.date(2020, 1, 1), dt.date(2025, 1, 1))
        datetime_bounds = (dt.datetime(2020, 1, 1), dt.datetime(2025, 1, 1))
        numpy_bounds = (np.datetime64('2020-01-01T00:00'), np.datetime64('2025-01-01T00:00'))
        date_val = dt.date(2021, 1, 1)
        datetime_val = dt.datetime(2021, 1, 1)
        numpy_val = np.datetime64('2021-01-01T00:00')

        class A(param.Parameterized):
            s = param.Date(default=datetime_val, bounds=date_bounds)
            t = param.Date(default=numpy_val, bounds=date_bounds)
            u = param.Date(default=date_val, bounds=datetime_bounds)
            v = param.Date(default=numpy_val, bounds=datetime_bounds)
            w = param.Date(default=date_val, bounds=numpy_bounds)
            x = param.Date(default=datetime_val, bounds=numpy_bounds)

        a = A()

        a.s = date_val
        a.s = datetime_val


def test_date_serialization():
    class User(param.Parameterized):
        A = param.Date(default=None)

    # Validate round is possible
    User.param.deserialize_parameters(User.param.serialize_parameters())

    serialized_data = '{"name": "User", "A": null}'
    deserialized_data = {"name": "User", "A": None}

    assert serialized_data == json.dumps(deserialized_data)
    assert serialized_data == User.param.serialize_parameters()
    assert deserialized_data == User.param.deserialize_parameters(serialized_data)
