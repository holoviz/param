"""
Unit test for the repr and script_repr of parameterized objects.
"""

import unittest
import param



class TestParameterizedRepr(unittest.TestCase):

    def setUp(self):
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
                super(A, self).__init__(a=a, b=b, c=c, **kwargs)

        self.A = A

        class B(param.Parameterized):  # Similar to A but no **kwargs
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)
            c = param.Number(4, precedence=0)
            d = param.Integer(-22, precedence=1)

            x = param.Number(1, precedence=2)
            def __init__(self, a, b, c=4, d=-22):
                super(B, self).__init__(a=a, b=b, c=c, name='ClassB')

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
                super(C, self).__init__(a=a, b=b, c=c, **kwargs)

        self.C = C


        class D(param.Parameterized):  # Similar to A but with missing parameters
            a = param.Number(4, precedence=-5)
            b = param.String('B', precedence=-4)

            def __init__(self, a, b, c=4, d=-22, **kwargs):
                super(D, self).__init__(a=a, b=b, **kwargs)

        self.D = D


    def testparameterizedrepr(self):
        obj = self.A(4,'B', name='test1')
        self.assertEqual(repr(obj),
                         "A(a=4, b='B', c=4, d=-22, name='test1', x=1, y=2, z=3)")

    def testparameterizedscriptrepr1(self):
        obj = self.A(4,'B', name='test')
        self.assertEqual(obj.script_repr(),
                         "A(4, 'B', name='test')")

    def testparameterizedscriptrepr2(self):
        obj = self.A(4,'B', c=5, name='test')
        self.assertEqual(obj.script_repr(),
                         "A(4, 'B', c=5, name='test')")

    def testparameterizedscriptrepr3(self):
        obj = self.A(4,'B', c=5,  x=True, name='test')
        self.assertEqual(obj.script_repr(),
                         "A(4, 'B', c=5, name='test')")

    def testparameterizedscriptrepr4(self):
        obj = self.A(4,'B', c=5,  x=10, name='test')
        self.assertEqual(obj.script_repr(),
                         "A(4, 'B', c=5, name='test', x=10)")


    def testparameterizedscriptrepr5(self):
        obj = self.A(4,'B', x=10, y=11, z=12, name='test')
        self.assertEqual(obj.script_repr(),
                         "A(4, 'B', name='test', z=12, y=11, x=10)")

    def testparameterizedscriptrepr_nokwargs(self):
        obj = self.B(4,'B', c=99)
        obj.x = 10 # Modified but not passable through constructor
        self.assertEqual(obj.script_repr(),
                         "B(4, 'B', c=99)")

    def testparameterizedscriptrepr_varags(self):
        obj = self.C(4,'C', c=99)
        self.assertEqual(obj.script_repr(),
                         "C(4, 'C', c=99, **varargs)")

    def testparameterizedscriptrepr_varags_kwargs(self):
        obj = self.C(4,'C', c=99, x=10, y=11, z=12)
        self.assertEqual(obj.script_repr(),
                         "C(4, 'C', c=99, z=12, y=11, x=10, **varargs)")

    def testparameterizedscriptrepr_missing_values(self):
        obj = self.D(4,'D', c=99)
        self.assertEqual(obj.script_repr(),
                         "D(4, 'D', c=<?>, d=<?>)")


if __name__ == "__main__":
    import nose
    nose.runmodule()
