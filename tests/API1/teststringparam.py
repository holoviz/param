"""
Unit test for String parameters
"""
from . import API1TestCase

import param


ip_regexp = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

class TestStringParameters(API1TestCase):

    def test_regexp_ok(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', ip_regexp)

        a = A()
        a.s = '123.123.0.1'

    def test_reject_none(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', ip_regexp)

        a = A()

        exception = "String 's' only takes a string value."
        with self.assertRaisesRegexp(ValueError, exception):
            a.s = None  # because allow_None should be False

    def test_default_none(self):
        class A(param.Parameterized):
            s = param.String(None, ip_regexp)

        a = A()
        a.s = '123.123.0.1'
        a.s = None  # because allow_None should be True with default of None

    def test_regexp_incorrect(self):

        class A(param.Parameterized):
            s = param.String('0.0.0.0', regexp=ip_regexp)

        a = A()

        exception = "String 's' does not match regular expression."
        with self.assertRaisesRegexp(ValueError, exception):
            a.s = '123.123.0.256'

    def test_regexp_incorrect_default(self):

        exception = "String 'None' does not match regular expression."
        with self.assertRaisesRegexp(ValueError, exception):
            class A(param.Parameterized):
                s = param.String(regexp=ip_regexp)  # default value '' does not match regular expression


