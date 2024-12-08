"""Unit test for the repr and pprint of parameterized objects, and for pprint/script_repr."""
import inspect
import unittest

import param
import pytest


class TestParameterizedRepr(unittest.TestCase):

    def setUp(self):
        super().setUp()
        # initialize a parameterized class
        class A(param.Parameterized):
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)
            c = param.Number(4, precedence=0)
            d = param.Integer(-22, precedence=1)

            x = param.Number(1, precedence=2)
            y = param.Number(2, precedence=-1)
            z = param.Number(3, precedence=-2)
            def __init__(self, a, b, c=4, d=-22, **kwargs):
                super().__init__(a=a, b=b, c=c, **kwargs)

        self.A = A

        class B(param.Parameterized):  # Similar to A but no **kwargs
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)
            c = param.Number(4, precedence=0)
            d = param.Integer(-22, precedence=1)

            x = param.Number(1, precedence=2)
            def __init__(self, a, b, c=4, d=-22):
                super().__init__(a=a, b=b, c=c, name='ClassB')

        self.B = B

        class C(param.Parameterized):  # Similar to A but with *varargs
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)
            c = param.Number(4, precedence=0)
            d = param.Integer(-22, precedence=1)

            x = param.Number(1, precedence=2)
            y = param.Number(2, precedence=-1)
            z = param.Number(3, precedence=-2)

            def __init__(self, a, b, c=4, d=-22, *varargs, **kwargs):
                super().__init__(a=a, b=b, c=c, **kwargs)

        self.C = C


        class D(param.Parameterized):  # Similar to A but with missing parameters
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)

            def __init__(self, a, b, c=4, d=-22, **kwargs):
                super().__init__(a=a, b=b, **kwargs)

        self.D = D


        # More realistically, positional args are not params
        class E(param.Parameterized):
            a = param.Number(4, precedence=-5)

            def __init__(self, p, q=4, **params): # (plus non-param kw too)
                super().__init__(**params)

        self.E = E


    def testparameterizedrepr(self):
        obj = self.A(4,'B', name='test1')
        self.assertEqual(repr(obj),
                         "A(a=4, b='B', c=4, d=-22, name='test1', x=1, y=2, z=3)")

    def testparameterizedscriptrepr1(self):
        obj = self.A(4,'B', name='test')
        self.assertEqual(obj.param.pprint(),
                         "A(4, 'B', name='test')")

    def testparameterizedscriptrepr2(self):
        obj = self.A(4,'B', c=5, name='test')
        self.assertEqual(obj.param.pprint(),
                         "A(4, 'B', c=5, name='test')")

    def testparameterizedscriptrepr3(self):
        obj = self.A(4,'B', c=5,  x=True, name='test')
        self.assertEqual(obj.param.pprint(),
                         "A(4, 'B', c=5, name='test')")

    def testparameterizedscriptrepr4(self):
        obj = self.A(4,'B', c=5,  x=10, name='test')
        self.assertEqual(obj.param.pprint(),
                         "A(4, 'B', c=5, name='test', x=10)")


    def testparameterizedscriptrepr5(self):
        obj = self.A(4,'B', x=10, y=11, z=12, name='test')
        self.assertEqual(obj.param.pprint(),
                         "A(4, 'B', name='test', z=12, y=11, x=10)")

    def testparameterizedscriptrepr_nokwargs(self):
        obj = self.B(4,'B', c=99)
        obj.x = 10 # Modified but not passable through constructor
        self.assertEqual(obj.param.pprint(),
                         "B(4, 'B', c=99)")

    def testparameterizedscriptrepr_varags(self):
        obj = self.C(4,'C', c=99)
        self.assertEqual(obj.param.pprint(),
                         "C(4, 'C', c=99, **varargs)")

    def testparameterizedscriptrepr_varags_kwargs(self):
        obj = self.C(4,'C', c=99, x=10, y=11, z=12)
        self.assertEqual(obj.param.pprint(),
                         "C(4, 'C', c=99, z=12, y=11, x=10, **varargs)")

    def testparameterizedscriptrepr_missing_values(self):
        obj = self.D(4,'D', c=99)
        self.assertEqual(obj.param.pprint(),
                         "D(4, 'D', c=<?>, d=<?>)")

    def testparameterizedscriptrepr_nonparams(self):
        obj = self.E(10,q='hi', a=99)
        self.assertEqual(obj.param.pprint(),
                         "E(<?>, q=<?>, a=99)")

    def testparameterizedscriptrepr_recursive(self):
        class Q(param.Parameterized):
            a = param.Number(default=39, bounds=(0,50), doc='Number a')
            b = param.String(default="str", doc='A string')

        class P(Q):
            c = param.ClassSelector(default=Q(), class_=Q, doc='An instance of Q')
            e = param.ClassSelector(default=param.Parameterized(), class_=param.Parameterized, doc='A Parameterized instance')
            f = param.Range(default=(0,1), doc='A range')

        p = P(f=(2,3), name="demo")
        p.c = P(c=p)

        assert p.param.pprint() == "P(c=P(c=...,     e=Parameterized()), e=Parameterized(), f=(2,3), name='demo')"


    def test_exceptions(self):
        obj = self.E(10,q='hi',a=99)
        try:
            obj.param.pprint(unknown_value=False)
        except Exception:
            pass
        else:
            raise AssertionError

    def test_suppression(self):
        obj = self.E(10,q='hi',a=99)
        self.assertEqual(obj.param.pprint(unknown_value=None),
                         "E(a=99)")

    def test_imports_deduplication(self):
        obj = self.E(10,q='hi', a=99)
        imports = ['import me','import me']
        obj.param.pprint(imports=imports)
        self.assertEqual(imports.count('import me'),1)

    def test_qualify(self):
        obj = self.E(10,q='hi', a=99)

        r = "E(<?>, q=<?>, a=99)"
        self.assertEqual(obj.param.pprint(qualify=False),
                         r)

        self.assertEqual(obj.param.pprint(qualify=True),
                         "tests.testparameterizedrepr."+r)


@pytest.fixture
def P():
    class P(param.Parameterized):
        x = param.Parameter()
        y = param.Parameter()

        def __init__(self, x, **params):
            params['x'] = x
            super().__init__(**params)

    return P

def test_pprint_type(P):
    assert param.parameterized.pprint(P) == f'{__name__}.P'


def test_pprint_parameterized_instance(P):
    p = P(1, y=2)
    assert param.parameterized.pprint(p) == 'P(1,\n        y=2)'


def test_pprint_parameterized_other():
    assert param.parameterized.pprint('2') == repr('2')


def test_script_repr_type(P):
    assert param.script_repr(P) == f'import {__name__}\n\n{__name__}.P'


def test_script_repr_parameterized_instance(P):
    p = P(1, y=2)
    sr = param.script_repr(p)
    assert f'import {__name__.split(".")[0]}' in sr
    assert f'import {__name__}' in sr
    assert f'{__name__}.P(1,\n\n        y=2)' in sr


def test_script_repr_parameterized_other():
    assert param.script_repr('2') == "\n\n'2'"


def test_pprint_signature_overriden():
    # https://github.com/holoviz/param/issues/785

    class P(param.Parameterized):
        def __init__(self, **params): pass

    class T(P): pass

    t = T()

    # This is actually setting the signature of P.__init__
    # as T doesn't define __init__

    # bad
    T.__init__.__signature__ = inspect.Signature(
        [
            inspect.Parameter('test', inspect.Parameter.KEYWORD_ONLY),
        ]
    )

    with pytest.raises(KeyError, match=r"'T\.__init__\.__signature__' must contain 'self' as its first Parameter"):
        t.param.pprint()

    # good
    T.__init__.__signature__ = inspect.Signature(
        [
            inspect.Parameter('self', inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter('test', inspect.Parameter.KEYWORD_ONLY),
        ]
    )

    assert t.param.pprint() == 'T()'
