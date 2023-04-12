"""
Unit test for ClassSelector parameters.
"""
import unittest

from numbers import Number

import param
from .utils import check_defaults


class TestClassSelectorParameters(unittest.TestCase):

    def setUp(self):
        super(TestClassSelectorParameters, self).setUp()
        class P(param.Parameterized):
            e = param.ClassSelector(default=1,class_=int)
            f = param.ClassSelector(default=int,class_=Number, is_instance=False)
            g = param.ClassSelector(default=1,class_=(int,str))
            h = param.ClassSelector(default=int,class_=(int,str), is_instance=False)

        self.P = P

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.ClassSelector(int)

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)
        assert P.param.s.class_ is int

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.ClassSelector(int)

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)
        assert p.param.s.class_ is int

    def test_defaults_unbound(self):
        s = param.ClassSelector(int)

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)
        assert s.class_ is int

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

    def test_class_selector_get_range(self):
        p = self.P()
        classes = p.param.g.get_range()
        self.assertIn('int', classes)
        self.assertIn('str', classes)

    def test_multiple_class_type_error(self):
        exception = r"ClassSelector parameter 'h' must be a subclass of \(int, str\), not 'float'."
        with self.assertRaisesRegex(ValueError, exception):
            self.P(h=float)


class TestDictParameters(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True
        assert p.class_ == dict

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.Dict()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.Dict()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.Dict()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

    def test_valid_dict_parameter(self):
        valid_dict = {1:2, 3:3}

        class Test(param.Parameterized):
            items = param.Dict(default=valid_dict)

    def test_valid_dict_parameter_positional(self):
        valid_dict = {1:2, 3:3}

        class Test(param.Parameterized):
            items = param.Dict(valid_dict)

    def test_dict_invalid_set(self):
        valid_dict = {1:2, 3:3}
        class Test(param.Parameterized):
            items = param.Dict(valid_dict)

        test = Test()
        exception = "Dict parameter 'items' value must be an instance of dict, not 3."
        with self.assertRaisesRegex(ValueError, exception):
            test.items = 3
