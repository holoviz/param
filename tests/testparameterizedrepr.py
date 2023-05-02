"""
Unit test for the repr and pprint of parameterized objects.
"""
import unittest

import param


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
