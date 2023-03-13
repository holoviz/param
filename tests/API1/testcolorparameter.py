"""
Unit test for Color parameters.
"""
import param
from . import API1TestCase
from .utils import check_defaults

class TestColorParameters(API1TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.allow_named is True

    def test_defaults_class(self):
        class A(param.Parameterized):
            c = param.Color()

        check_defaults(A.param.c, label='C')
        self._check_defaults(A.param.c)

    def test_defaults_inst(self):
        class A(param.Parameterized):
            c = param.Color()

        a = A()

        check_defaults(a.param.c, label='C')
        self._check_defaults(a.param.c)

    def test_defaults_unbound(self):
        c = param.Color()

        check_defaults(c, label=None)
        self._check_defaults(c)

    def test_initialization_invalid_string(self):
        try:
            class Q(param.Parameterized):
                q = param.Color('red', allow_named=False)
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on invalid color")

    def test_set_invalid_string(self):
        class Q(param.Parameterized):
            q = param.Color(allow_named=False)
        try:
            Q.q = 'red'
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on invalid color")

    def test_set_invalid_named_color(self):
        class Q(param.Parameterized):
            q = param.Color(allow_named=True)
        try:
            Q.q = 'razzmatazz'
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on invalid color")

    def test_invalid_long_hex(self):
        class Q(param.Parameterized):
            q = param.Color()
        try:
            Q.q = '#gfffff'
        except ValueError:
            pass
        else:
            raise AssertionError("No exception raised on invalid color")

    def test_valid_long_hex(self):
        class Q(param.Parameterized):
            q = param.Color()
        Q.q = '#ffffff'
        self.assertEqual(Q.q, '#ffffff')

    def test_valid_short_hex(self):
        class Q(param.Parameterized):
            q = param.Color()
        Q.q = '#fff'
        self.assertEqual(Q.q, '#fff')

    def test_valid_named_color(self):
        class Q(param.Parameterized):
            q = param.Color(allow_named=True)
        Q.q = 'indianred'
        self.assertEqual(Q.q, 'indianred')

    def test_valid_named_color_mixed_case(self):
        class Q(param.Parameterized):
            q = param.Color(allow_named=True)
        Q.q = 'WhiteSmoke'
        self.assertEqual(Q.q, 'WhiteSmoke')
