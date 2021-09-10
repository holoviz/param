"""
Unit test for ClassSelector parameters.
"""

import unittest
from numbers import Number

import param

if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

class TestClassSelectorParameters(unittest.TestCase):

    def setUp(self):

        class P(param.Parameterized):
            e = param.ClassSelector(default=1,class_=int)
            f = param.ClassSelector(default=int,class_=Number, is_instance=False)
            g = param.ClassSelector(default=1,class_=(int,str))
            h = param.ClassSelector(default=int,class_=(int,str), is_instance=False)

        self.P = P

    def test_single_class_instance_constructor(self):
        p = self.P(e=6)
        self.assertEqual(p.e, 6)

    def test_single_class_instance_error(self):
        exception = "ClassSelector parameter 'e' value must be an instance of int, not 'a'."
        with self.assertRaisesRegex(ValueError, exception):
            self.P(e='a')

    def test_single_class_type_constructor(self):
        p = self.P(f=float)
        self.assertEqual(p.f, float)

    def test_single_class_type_error(self):
        exception = "ClassSelector parameter 'f' must be a subclass of Number, not 'str'."
        with self.assertRaisesRegex(ValueError, exception):
            self.P(f=str)

    def test_multiple_class_instance_constructor1(self):
        p = self.P(g=1)
        self.assertEqual(p.g, 1)

    def test_multiple_class_instance_constructor2(self):
        p = self.P(g='A')
        self.assertEqual(p.g, 'A')

    def test_multiple_class_instance_error(self):
        exception = r"ClassSelector parameter 'g' value must be an instance of \(int, str\), not 3.0."
        with self.assertRaisesRegex(ValueError, exception):
            self.P(g=3.0)

    def test_multiple_class_type_constructor1(self):
        p = self.P(h=int)
        self.assertEqual(p.h, int)

    def test_multiple_class_type_constructor2(self):
        p = self.P(h=str)
        self.assertEqual(p.h, str)

    def test_multiple_class_type_error(self):
        exception = r"ClassSelector parameter 'h' must be a subclass of \(int, str\), not 'float'."
        with self.assertRaisesRegex(ValueError, exception):
            self.P(h=float)
