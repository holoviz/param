"""
Unit test for param.output.
"""
import sys

from unittest import SkipTest

import param

from . import API1TestCase


class TestParamDepends(API1TestCase):

    def test_simple_output(self):
        class P(param.Parameterized):

            @param.output()
            def single_output(self):
                return 1

        outputs = P.param.outputs()
        self.assertEqual(list(outputs), ['single_output'])

        otype, method, idx = outputs['single_output']
        self.assertIs(type(otype), param.Parameter)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'single_output': 1})

    def test_named_kwarg_output(self):
        class P(param.Parameterized):

            @param.output(value=param.Integer)
            def single_output(self):
                return 1

        outputs = P.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'value': 1})

    def test_named_and_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(('value', param.Integer))
            def single_output(self):
                return 1

        outputs = P.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True), {'value': 1})

    def test_named_arg_output(self):
        class P(param.Parameterized):

            @param.output('value')
            def single_output(self):
                return 1

        outputs = P.param.outputs()
        self.assertEqual(list(outputs), ['value'])

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Parameter)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True), {'value': 1})

    def test_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(int)
            def single_output(self):
                return 1
        
        outputs = P.param.outputs()
        self.assertEqual(list(outputs), ['single_output'])

        otype, method, idx = outputs['single_output']
        self.assertIs(type(otype), param.ClassSelector)
        self.assertIs(otype.class_, int)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True), {'single_output': 1})

    def test_multiple_named_kwarg_output(self):
        py_major = sys.version_info.major
        py_minor = sys.version_info.minor
        if (py_major < 3 or (py_major == 3 and py_minor < 6)):
            raise SkipTest('Multiple keyword output declarations only '
                           'supported in Python >= 3.6, skipping test.')

        class P(param.Parameterized):

            @param.output(value=param.Integer, value2=param.String)
            def multi_output(self):
                return (1, 'string')

        outputs = P.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.String)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 1)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'value': 1, 'value2': 'string'})

    def test_multi_named_and_typed_arg_output(self):
        class P(param.Parameterized):

            @param.output(('value', param.Integer), ('value2', param.String))
            def multi_output(self):
                return (1, 'string')

        outputs = P.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})
        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.String)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 1)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'value': 1, 'value2': 'string'})

    def test_multi_named_arg_output(self):
        class P(param.Parameterized):

            @param.output('value', 'value2')
            def multi_output(self):
                return (1, 2)

        outputs = P.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Parameter)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.Parameter)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 1)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'value': 1, 'value2': 2})

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

        outputs = P.param.outputs()
        self.assertEqual(set(outputs), {'value', 'value2', 'value3'})

        otype, method, idx = outputs['value']
        self.assertIs(type(otype), param.Integer)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 0)

        otype, method, idx = outputs['value2']
        self.assertIs(type(otype), param.ClassSelector)
        self.assertIs(otype.class_, str)
        self.assertIs(method, P.multi_output)
        self.assertEqual(idx, 1)

        otype, method, idx = outputs['value3']
        self.assertIs(type(otype), param.Number)
        self.assertIs(method, P.single_output)
        self.assertEqual(idx, None)

        self.assertEqual(P().param.outputs(evaluate=True),
                         {'value': 1, 'value2': 'string', 'value3': 3.0})
