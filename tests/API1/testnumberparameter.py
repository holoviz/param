"""
Unit test for Number parameters and their subclasses.
"""
import param
import datetime as dt
from . import API1TestCase


class TestNumberParameters(API1TestCase):

    def test_initialization_without_step_class(self):
        class Q(param.Parameterized):
            q = param.Number(default=1)

        self.assertEqual(Q.param['q'].step, None)

    def test_initialization_with_step_class(self):
        class Q(param.Parameterized):
            q = param.Number(default=1, step=0.5)

        self.assertEqual(Q.param['q'].step, 0.5)

    def test_initialization_without_step_instance(self):
        class Q(param.Parameterized):
            q = param.Number(default=1)

        qobj = Q()
        self.assertEqual(qobj.param['q'].step, None)

    def test_initialization_with_step_instance(self):
        class Q(param.Parameterized):
            q = param.Number(default=1, step=0.5)

        qobj = Q()
        self.assertEqual(qobj.param['q'].step, 0.5)

    def test_step_invalid_type_number_parameter(self):
        exception = "Step parameter can only be None or a numeric value"
        with self.assertRaisesRegex(ValueError, exception):
            param.Number(step='invalid value')

    def test_step_invalid_type_integer_parameter(self):
        exception = "Step parameter can only be None or an integer value"
        with self.assertRaisesRegex(ValueError, exception):
            param.Integer(step=3.4)

    def test_step_invalid_type_datetime_parameter(self):
        exception = "Step parameter can only be None, a datetime or datetime type"
        with self.assertRaisesRegex(ValueError, exception):
            param.Date(dt.datetime(2017,2,27), step=3.2)

    def test_step_invalid_type_date_parameter(self):
        exception = "Step parameter can only be None or a date type"
        with self.assertRaisesRegex(ValueError, exception):
            param.CalendarDate(dt.date(2017,2,27), step=3.2)
