"""
Unit test for Bytes parameters
"""
import unittest
import sys

import pytest

from .utils import check_defaults

import param


ip_regex = br'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

class TestBytesParameters(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default == b''
        assert p.allow_None is False
        assert p.regex is None

    def test_defaults_class(self):
        class A(param.Parameterized):
            b = param.Bytes()

        check_defaults(A.param.b, label='B')
        self._check_defaults(A.param.b)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            b = param.Bytes()

        a = A()

        check_defaults(a.param.b, label='B')
        self._check_defaults(a.param.b)

    def test_defaults_unbound(self):
        b = param.Bytes()

        check_defaults(b, label=None)
        self._check_defaults(b)

    def test_bytes_default_type(self):
        if sys.version_info.major < 3:
            pytest.skip()

        with pytest.raises(ValueError):
            class A(param.Parameterized):
                s = param.Bytes('abc')

    def test_bytes_value_type(self):
        if sys.version_info.major < 3:
            pytest.skip()

        class A(param.Parameterized):
            s = param.Bytes()

        with pytest.raises(ValueError):
            A(s='abc')
        
            
    def test_regex_ok(self):
        class A(param.Parameterized):
            s = param.Bytes(b'0.0.0.0', ip_regex)

        a = A()
        a.s = b'123.123.0.1'

    def test_reject_none(self):
        class A(param.Parameterized):
            s = param.Bytes(b'0.0.0.0', ip_regex)

        a = A()

        cls = 'class' if sys.version_info.major > 2 else 'type'
        exception = "Bytes parameter 's' only takes a byte string value, not value of type <%s 'NoneType'>." % cls
        with self.assertRaisesRegex(ValueError, exception):
            a.s = None  # because allow_None should be False

    def test_default_none(self):
        class A(param.Parameterized):
            s = param.Bytes(None, ip_regex)

        a = A()
        a.s = b'123.123.0.1'
        a.s = None  # because allow_None should be True with default of None

    def test_regex_incorrect(self):
        class A(param.Parameterized):
            s = param.Bytes(b'0.0.0.0', regex=ip_regex)

        a = A()

        b = 'b' if sys.version_info.major > 2 else ''
        exception = "Bytes parameter 's' value %s'123.123.0.256' does not match regex %r."  % (b, ip_regex)
        with self.assertRaises(ValueError) as e:
            a.s = b'123.123.0.256'
        self.assertEqual(str(e.exception), exception)

    def test_regex_incorrect_default(self):
        b = 'b' if sys.version_info.major > 2 else ''
        exception = "Bytes parameter None value %s'' does not match regex %r." % (b, ip_regex)
        with self.assertRaises(ValueError) as e:
            class A(param.Parameterized):
                s = param.Bytes(regex=ip_regex)  # default value '' does not match regular expression
        self.assertEqual(str(e.exception), exception)
