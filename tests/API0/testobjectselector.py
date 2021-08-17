"""
Unit test for object selector parameters.

Originally implemented as doctests in Topographica in the file
testEnumerationParameter.txt
"""

import unittest
import param


opts=dict(A=[1,2],B=[3,4],C=dict(a=1,b=2))


class TestObjectSelectorParameters(unittest.TestCase):

    def setUp(self):

        class P(param.Parameterized):
            e = param.ObjectSelector(default=5,objects=[5,6,7])
            f = param.ObjectSelector(default=10)
            h = param.ObjectSelector(default=None)
            g = param.ObjectSelector(default=None,objects=[7,8])
            i = param.ObjectSelector(default=7,objects=[9],check_on_set=False)
            d = param.ObjectSelector(default=opts['B'],objects=opts)
            
        self.P = P

    def test_set_object_constructor(self):
        p = self.P(e=6)
        self.assertEqual(p.e, 6)

    def test_get_range_mutable(self):
        r = self.P.param.params("d").get_range()
        self.assertEqual(r['A'],opts['A'])
        self.assertEqual(r['C'],opts['C'])
        self.d=opts['A']
        self.d=opts['C']
        self.d=opts['B']

    def test_set_object_outside_bounds(self):
        p = self.P(e=6)
        try:
            p.e = 9
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)


    def test_set_object_not_None(self):
        p = self.P(e=6)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr_post_error(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ObjectSelector created outside range.")


    def test_initialization_no_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ObjectSelector created without range.")
