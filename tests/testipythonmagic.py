"""Unit test for the IPython magic."""
import re
import sys
import unittest

import param
import pytest

try:
    import IPython # noqa
except ModuleNotFoundError:
    import os
    if os.getenv('PARAM_TEST_IPYTHON','0') == '1':
        raise ImportError("PARAM_TEST_IPYTHON=1 but ipython not available.")

from param.ipython import ParamPager

test1_repr = """\x1b[1;32mParameters of 'TestClass'\n=========================\n\x1b[0m\n\x1b[1;31mParameters changed from their default values are marked in red.\x1b[0m\n\x1b[1;36mSoft bound values are marked in cyan.\x1b[0m\nC/V= Constant/Variable, RO/RW = ReadOnly/ReadWrite, AN=Allow None\n\n\x1b[1;34mNameValue   Type     Bounds      Mode  \x1b[0m\n\nu    4    Number                V RW  \nw    4    Number                C RO  \nv    4    Number                C RW  \nx   None  String              V RW AN \ny    4    Number  (-1, None)    V RW  \nz    4    Number  (-1, 100)     V RW  \n\n\x1b[1;32mParameter docstrings:\n=====================\x1b[0m\n\n\x1b[1;34mu: < No docstring available >\x1b[0m\n\x1b[1;31mw: < No docstring available >\x1b[0m\n\x1b[1;34mv: < No docstring available >\x1b[0m\n\x1b[1;31mx: < No docstring available >\x1b[0m\n\x1b[1;34my: < No docstring available >\x1b[0m\n\x1b[1;31mz: < No docstring available >\x1b[0m"""


test2_repr = """\x1b[1;32mParameters of 'TestClass' instance\n==================================\n\x1b[0m\n\x1b[1;31mParameters changed from their default values are marked in red.\x1b[0m\n\x1b[1;36mSoft bound values are marked in cyan.\x1b[0m\nC/V= Constant/Variable, RO/RW = ReadOnly/ReadWrite, AN=Allow None\n\n\x1b[1;34mNameValue   Type     Bounds      Mode  \x1b[0m\n\nu    4    Number                V RW  \nw    4    Number                C RO  \nv    4    Number                C RW  \nx   None  String              V RW AN \ny    4    Number  (-1, None)    V RW  \nz    4    Number  (-1, 100)     V RW  \n\n\x1b[1;32mParameter docstrings:\n=====================\x1b[0m\n\n\x1b[1;34mu: < No docstring available >\x1b[0m\n\x1b[1;31mw: < No docstring available >\x1b[0m\n\x1b[1;34mv: < No docstring available >\x1b[0m\n\x1b[1;31mx: < No docstring available >\x1b[0m\n\x1b[1;34my: < No docstring available >\x1b[0m\n\x1b[1;31mz: < No docstring available >\x1b[0m"""

class TestParamPager(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.maxDiff = None

        class TestClass(param.Parameterized):
            u = param.Number(4, precedence=0)
            w = param.Number(4, readonly=True, precedence=1)
            v = param.Number(4, constant=True, precedence=2)
            x = param.String(None, allow_None=True, precedence=3)
            y = param.Number(4, bounds=(-1, None), precedence=4)
            z = param.Number(4, bounds=(-1, 100), softbounds=(-100, -200), precedence=5)

        self.TestClass = TestClass
        self.pager = ParamPager()

    def test_parameterized_class(self):
        page_string = self.pager(self.TestClass)
        # Remove params automatic numbered names
        page_string = re.sub(r'TestClass(\d+)', 'TestClass', page_string)
        ref_string = re.sub(r'TestClass(\d+)', 'TestClass', test1_repr)

        try:
            self.assertEqual(page_string, ref_string)
        except Exception as e:
            sys.stderr.write(page_string)  # Coloured output
            sys.stderr.write("\nRAW STRING:\n\n%r\n\n" % page_string)
            raise e

    def test_parameterized_instance(self):
        page_string = self.pager(self.TestClass())
        # Remove params automatic numbered names
        page_string = re.sub(r'TestClass(\d+)', 'TestClass', page_string)
        ref_string = re.sub(r'TestClass(\d+)', 'TestClass', test2_repr)

        try:
            self.assertEqual(page_string, ref_string)
        except Exception as e:
            sys.stderr.write(page_string)  # Coloured output
            sys.stderr.write("\nRAW STRING:\n\n%r\n\n" % page_string)
            raise e


# IPythonDisplay for `rx` objects

@pytest.fixture
def fake_ipython_display(monkeypatch):
    """
    Stand in for ``IPython.display.display``, recording every object it is
    asked to show and every subsequent update made through the handle it
    returns, without requiring a real IPython display backend.
    """
    pytest.importorskip("IPython")
    from IPython import display as ipydisplay

    updates = []

    class FakeHandle:
        def update(self, obj):
            updates.append(obj)

    def fake_display(obj, display_id=None):
        updates.append(obj)
        return FakeHandle()

    monkeypatch.setattr(ipydisplay, "display", fake_display)
    return updates


def test_ipython_display_sees_an_override(fake_ipython_display):
    from param.ipython import IPythonDisplay

    fx = param.rx(2)
    expr = param.rx(10).rx.pipe(lambda value, fx: value * fx, fx=fx)
    IPythonDisplay(expr)()

    assert fake_ipython_display == [20]

    expr.rx.overrides['fx'] = 1

    assert fake_ipython_display == [20, 10]


def test_ipython_display_skips_a_masked_ticks_repeat_value(fake_ipython_display):
    from param.ipython import IPythonDisplay

    fx = param.rx(2)
    expr = param.rx(10).rx.pipe(lambda value, fx: value * fx, fx=fx)
    IPythonDisplay(expr)()
    expr.rx.overrides['fx'] = 1

    fx.rx.value = 5
    fx.rx.value = 9

    assert fake_ipython_display == [20, 10]

    del expr.rx.overrides['fx']

    assert fake_ipython_display == [20, 10, 90]


def test_ipython_display_of_a_never_overridden_expression():
    pytest.importorskip("IPython")
    from param.ipython import IPythonDisplay

    n = param.rx(1) + 1
    # Must not raise merely from being displayed.
    IPythonDisplay(n)


def test_ipython_display_of_a_partially_bound_function_falls_back_to_repr(fake_ipython_display):
    """
    A callable that still needs a positional argument, such as a partial
    ``param.bind``, is not evaluable yet and therefore not displayable.
    ``IPythonDisplay`` must signal that to IPython by raising
    ``NotImplementedError`` (which tells the formatter to fall back to the
    plain repr) rather than letting the callable's own ``TypeError`` escape.
    """
    from param.ipython import IPythonDisplay

    def add(a, b):
        return a + b

    class P(param.Parameterized):
        a = param.Number(default=1)

    p = P()
    add_a = param.bind(add, p.param.a)

    with pytest.raises(NotImplementedError):
        IPythonDisplay(add_a)()
    assert fake_ipython_display == []
