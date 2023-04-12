"""
Unit test for Boolean parameters.
"""
import unittest

import param

from .utils import check_defaults


class TestBooleanParameters(unittest.TestCase):

    def setUp(self):
        super(TestBooleanParameters, self).setUp()
        class P(param.Parameterized):
            e = param.Boolean()
            f = param.Boolean(default=None)

        self.P = P

    def _check_defaults(self, p):
        assert p.default is False
        assert p.allow_None is False
        assert p.bounds == (0, 1)

    def test_defaults_class(self):
        class A(param.Parameterized):
            b = param.Boolean()

        check_defaults(A.param.b, label='B')
        self._check_defaults(A.param.b)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            b = param.Boolean()

        a = A()

        check_defaults(a.param.b, label='B')
        self._check_defaults(a.param.b)

    def test_defaults_unbound(self):
        b = param.Boolean()

        check_defaults(b, label=None)
        self._check_defaults(b)

    def test_default_is_None(self):
        p = self.P()
        assert p.f is None
        assert p.param.f.allow_None is True

        p.f = True
        p.f = None
        assert p.f is None

    def test_raise_None_when_not_allowed(self):
        p = self.P()

        msg = r"Boolean parameter 'e' must be True or False, not None"
        with self.assertRaisesRegex(ValueError, msg):
                p.e = None

        with self.assertRaisesRegex(ValueError, msg):
                self.P.e = None

    def test_bad_type(self):
        msg = r"Boolean parameter 'e' must be True or False, not test"

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'

    def test_bad_default_type(self):
        msg = r"Boolean parameter must be True or False, not test."

        with self.assertRaisesRegex(ValueError, msg):
            class A(param.Parameterized):
                b = param.Boolean(default='test')


class TestEventParameters(unittest.TestCase):

    def setUp(self):
        super(TestEventParameters, self).setUp()
        class P(param.Parameterized):
            e = param.Event()
            f = param.Event(default=None)

        self.P = P

    def _check_defaults(self, p):
        assert p.default is False
        assert p.allow_None is False
        assert p.bounds == (0, 1)

    def test_defaults_class(self):
        class A(param.Parameterized):
            b = param.Event()

        check_defaults(A.param.b, label='B')
        self._check_defaults(A.param.b)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            b = param.Event()

        a = A()

        check_defaults(a.param.b, label='B')
        self._check_defaults(a.param.b)

    def test_defaults_unbound(self):
        b = param.Event()

        check_defaults(b, label=None)
        self._check_defaults(b)

    def test_resets_to_false(self):
        p = self.P()
        p.e = True
        assert p.e is False

    def test_default_is_None(self):
        p = self.P()
        assert p.f is None
        assert p.param.f.allow_None is True

        p.f = None
        assert p.f is False

    def test_raise_None_when_not_allowed(self):
        p = self.P()

        msg = r"Boolean parameter 'e' must be True or False, not None"
        with self.assertRaisesRegex(ValueError, msg):
                p.e = None

        with self.assertRaisesRegex(ValueError, msg):
                self.P.e = None

    def test_bad_type(self):
        msg = r"Boolean parameter 'e' must be True or False, not test"

        with self.assertRaisesRegex(ValueError, msg):
            self.P.e = 'test'

        with self.assertRaisesRegex(ValueError, msg):
            self.P(e='test')

        p = self.P()

        with self.assertRaisesRegex(ValueError, msg):
            p.e = 'test'
