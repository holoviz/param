"""Unit test for param.output."""
import unittest

import param


class TestParamDepends(unittest.TestCase):

    def test_simple_output(self):
        class P(param.Parameterized):

            @param.output()
            def single_output(self):
                return 1

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(list(outputs), ['single_output'])

        otype, method, idx = outputs['single_output']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

    def test_subclass_output(self):
        class A(param.Parameterized):

            @param.output()
            def single_output(self):
                return 1

        class B(param.Parameterized):

            @param.output()
            def another_output(self):
                return 2

        class C(A, B):
            pass

        p = C()
        outputs = p.param.outputs()
        self.assertEqual(sorted(outputs), ['another_output', 'single_output'])

        otype, method, idx = outputs['single_output']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

        otype, method, idx = outputs['another_output']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.another_output)
        self.assertEqual(idx, None)


    def test_named_kwarg_output(self):
        class P(param.Parameterized):

            @param.output(value=param.Integer)
            def single_output(self):
                return 1

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

    def test_named_and_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(('value', param.Integer))
            def single_output(self):
                return 1

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

    def test_named_arg_output(self):
        class P(param.Parameterized):

            @param.output('value')
            def single_output(self):
                return 1

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

    def test_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(int)
            def single_output(self):
                return 1

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(list(outputs), ['single_output'])

        otype, method, idx = outputs['single_output']
        self.assertIs(type(otype), param.ClassSelector)
        self.assertIs(otype.class_, int)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)

    def test_multiple_named_kwarg_output(self):
        class P(param.Parameterized):

            @param.output(value=param.Integer, value2=param.String)
            def multi_output(self):
                return (1, 'string')

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.String)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 1)

    def test_multi_named_and_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(('value', param.Integer), ('value2', param.String))
            def multi_output(self):
                return (1, 'string')

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})
        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.String)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 1)

    def test_multi_named_arg_output(self):
        class P(param.Parameterized):

            @param.output('value', 'value2')
            def multi_output(self):
                return (1, 2)

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.Parameter)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 1)

    def test_multi_typed_arg_output(self):
        with self.assertRaises(ValueError):
            class P(param.Parameterized):

                @param.output(int, str)
                def single_output(self):
                    return 1

    def test_multi_method_named_and_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(('value', param.Integer), ('value2', str))
            def multi_output(self):
                return (1, 'string')

            @param.output(('value3', param.Number))
            def single_output(self):
                return 3.0

        p = P()
        outputs = p.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2', 'value3'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.ClassSelector)
        self.assertIs(otype.class_, str)
        self.assertEqual(method, p.multi_output)
        self.assertEqual(idx, 1)

        otype, method, idx = outputs['value3']
        self.assertIs(type(otype), param.Number)
        self.assertEqual(method, p.single_output)
        self.assertEqual(idx, None)
