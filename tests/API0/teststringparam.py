"""
Unit test for String parameters
"""

import unittest

import param


ip_regex = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

class TestStringParameters(unittest.TestCase):

    def test_regex_ok(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', ip_regex)

        a = A()
        a.s = '123.123.0.1'

    def test_reject_none(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', ip_regex)

        a = A()

        exception = "String 's' only takes a string value."
        with self.assertRaisesRegex(ValueError, exception):
            a.s = None  # because allow_None should be False

    def test_default_none(self):
        class A(param.Parameterized):
            s = param.String(None, ip_regex)

        a = A()
        a.s = '123.123.0.1'
        a.s = None  # because allow_None should be True with default of None

    def test_regex_incorrect(self):

        class A(param.Parameterized):
            s = param.String('0.0.0.0', regex=ip_regex)

        a = A()

        exception = "String 's': '123.123.0.256' does not match regex"
        with self.assertRaisesRegex(ValueError, exception):
            a.s = '123.123.0.256'

    def test_regex_incorrect_default(self):

        exception = "String 'None': '' does not match regex"
        with self.assertRaisesRegex(ValueError, exception):
            class A(param.Parameterized):
                s = param.String(regex=ip_regex)  # default value '' does not match regular expression


