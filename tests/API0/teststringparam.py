"""
Unit test for String parameters
"""
import sys
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

        cls = 'class' if sys.version_info.major > 2 else 'type'
        exception = "String parameter 's' only takes a string value, not value of type <%s 'NoneType'>." % cls
        with self.assertRaisesRegexp(ValueError, exception):
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

        exception = "String parameter 's' value '123.123.0.256' does not match regex '%s'."  % ip_regex
        with self.assertRaises(ValueError) as e:
            a.s = '123.123.0.256'
        self.assertEqual(str(e.exception), exception.replace('\\', '\\\\'))

    def test_regex_incorrect_default(self):
        exception = "String parameter None value '' does not match regex '%s'." % ip_regex
        with self.assertRaises(ValueError) as e:
            class A(param.Parameterized):
                s = param.String(regex=ip_regex)  # default value '' does not match regular expression
        self.assertEqual(str(e.exception), exception.replace('\\', '\\\\'))
