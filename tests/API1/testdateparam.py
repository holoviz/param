"""
Unit test for Date parameters.
"""
import sys
import json
import datetime as dt
import param
from . import API1TestCase

class TestDateParameters(API1TestCase):

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

def test_date_serialization():
    class User(param.Parameterized):
        A = param.Date(default=None)

    # Validate round is possible
    User.param.deserialize_parameters(User.param.serialize_parameters())

    if sys.version_info.major == 2:
        return

    serialized_data = '{"name": "User", "A": null}'
    deserialized_data = {"name": "User", "A": None}

    assert serialized_data == json.dumps(deserialized_data)
    assert serialized_data == User.param.serialize_parameters()
    assert deserialized_data == User.param.deserialize_parameters(serialized_data)
