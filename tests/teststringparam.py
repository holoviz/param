"""Unit test for String parameters"""
import unittest

import param

from .utils import check_defaults


ip_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

class TestStringParameters(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default == ''
        assert p.allow_None is False
        assert p.regex is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            s = param.String()

        check_defaults(A.param.s, label='S')
        self._check_defaults(A.param.s)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            s = param.String()

        a = A()

        check_defaults(a.param.s, label='S')
        self._check_defaults(a.param.s)

    def test_defaults_unbound(self):
        s = param.String()

        check_defaults(s, label=None)
        self._check_defaults(s)

    def test_regex_ok(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', regex=ip_regex)

        a = A()
        a.s = '123.123.0.1'

    def test_reject_none(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', regex=ip_regex)

        a = A()

        exception = "String parameter 'A.s' only takes a string value, not value of <class 'NoneType'>."
        with self.assertRaisesRegex(ValueError, exception):
            a.s = None  # because allow_None should be False

    def test_default_none(self):
        class A(param.Parameterized):
            s = param.String(None, regex=ip_regex)

        a = A()
        a.s = '123.123.0.1'
        a.s = None  # because allow_None should be True with default of None

    def test_regex_incorrect(self):
        class A(param.Parameterized):
            s = param.String('0.0.0.0', regex=ip_regex)

        a = A()

        exception = "String parameter 'A.s' value '123.123.0.256' does not match regex '%s'."  % ip_regex
        with self.assertRaises(ValueError) as e:
            a.s = '123.123.0.256'
        self.assertEqual(str(e.exception), exception.replace('\\', '\\\\'))

    def test_regex_incorrect_default(self):
        exception = "String parameter 's' value '' does not match regex '%s'." % ip_regex
        with self.assertRaises(ValueError) as e:
            class A(param.Parameterized):
                s = param.String(regex=ip_regex)  # default value '' does not match regular expression
        self.assertEqual(str(e.exception), exception.replace('\\', '\\\\'))
