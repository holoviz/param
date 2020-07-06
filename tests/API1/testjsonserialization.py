"""
Testing JSON serialization of parameters and the corresponding schemas.
"""

import json
import datetime
import param
from unittest import SkipTest
from . import API1TestCase

try:
    from jsonschema import validate, ValidationError
except ImportError:
    validate = None

try:
    import pandas as pd
except ImportError:
    pd = None


class TestSet(param.Parameterized):
    a = param.Integer(default=5, doc='Example doc', bounds=(2,30), inclusive_bounds=(True, False))
    b = param.Number(default=4.3, allow_None=True)
    c = param.String(default='foo')
    d = param.Boolean(default=False)
    e = param.List([1,2,3], class_=int)
    f = param.Date(default=datetime.datetime.now())
    g = param.Tuple(default=(1,2,3), length=3)
    h = param.NumericTuple(default=(1,2,3,4))
    i = param.XYCoordinates(default=(32.1, 51.5))
    j = param.Integer(default=1)
    k = param.Range(default=(1.1,2.3), bounds=(1,3))
    l = param.String(default='baz', allow_None=True)
    m = param.ObjectSelector(default=3, objects=[3,'foo'], allow_None=False)
    n = param.ListSelector(default=[1,4,5], objects=[1,2,3,4,5,6])
    o = param.DataFrame(default=pd.DataFrame({'A':[1.,2.,3.], 'B':[1.1,2.2,3.3]}), columns=2)
    p = param.DataFrame(default=pd.DataFrame({'A':[1.,2.,3.], 'B':[1.1,2.2,3.3]}), columns=(1,4), rows=(2,5))
    q = param.DataFrame(default=pd.DataFrame({'A':[1.1,2.2,3.3],
                                              'B':[1.1,2.2,3.3]}), columns=['A', 'B'])

test = TestSet(a=29)


class TestJSONSerialization(API1TestCase):

    def test_serialize_integer_class(self):
        serialization = TestSet.param.serialize_parameters(subset=['a'], mode='json')
        deserialized = json.loads(serialization)
        self.assertEqual(TestSet.a, 5)
        self.assertEqual(deserialized, {'a':TestSet.a})

    def test_serialize_integer_instance(self):
        serialization = test.param.serialize_parameters(subset=['a'], mode='json')
        deserialized = json.loads(serialization)
        self.assertEqual(test.a, 29)
        self.assertEqual(deserialized, {'a':test.a})

    def test_serialize_integer_schema_class(self):
        if validate is None:
            raise SkipTest('jsonschema needed for schema validation testing')
        param_schema = TestSet.param.schema(safe=True, subset=['a'], mode='json')
        schema = {"type" : "object", "properties" : param_schema}
        serialized = json.loads(TestSet.param.serialize_parameters(subset=['a']))
        self.assertEqual({'a':
                          {'type': 'integer', 'minimum': 2, 'exclusiveMaximum': 30,
                           'description': 'Example doc', 'title': 'A'}},
                         param_schema)
        validate(instance=serialized, schema=schema)

    def test_serialize_integer_schema_class_invalid(self):
        if validate is None:
            raise SkipTest('jsonschema needed for schema validation testing')
        param_schema = TestSet.param.schema(safe=True, subset=['a'], mode='json')
        schema = {"type" : "object", "properties" : param_schema}
        serialized = json.loads(TestSet.param.serialize_parameters(subset=['a']))
        self.assertEqual({'a':
                          {'type': 'integer', 'minimum': 2, 'exclusiveMaximum': 30,
                           'description': 'Example doc', 'title': 'A'}},
                         param_schema)

        exception = "1 is not of type 'object'"
        with self.assertRaisesRegexp(ValidationError, exception):
            validate(instance=1, schema=schema)


    def test_serialize_integer_schema_instance(self):
        if validate is None:
            raise SkipTest('jsonschema needed for schema validation testing')
        param_schema = test.param.schema(safe=True, subset=['a'], mode='json')
        schema = {"type" : "object", "properties" : param_schema}
        serialized = json.loads(test.param.serialize_parameters(subset=['a']))
        self.assertEqual({'a':
                          {'type': 'integer', 'minimum': 2, 'exclusiveMaximum': 30,
                           'description': 'Example doc', 'title': 'A'}},
                         param_schema)
        validate(instance=serialized, schema=schema)


    def test_instance_serialization(self):
        param_names = [el for el in test.param if el != 'name']
        for param_name in param_names:
            original_value = getattr(test, param_name)
            serialization = test.param.serialize_parameters(subset=[param_name], mode='json')
            json_loaded = json.loads(serialization)
            deserialized_values = test.param.deserialize_parameters(json_loaded)
            deserialized_value = deserialized_values[param_name]
            if isinstance(original_value, pd.DataFrame):
                self.assertEqual(original_value.equals(deserialized_value), True)
            else:
                self.assertEqual(original_value, deserialized_value)


    def test_class_instance_schemas_match_and_validate_unsafe(self):
        param_names = [el for el in test.param if el != 'name']
        for param_name in param_names:
            class_schema = TestSet.param.schema(safe=False, subset=[param_name], mode='json')
            instance_schema = test.param.schema(safe=False, subset=[param_name], mode='json')
            self.assertEqual(class_schema, instance_schema)

            instance_serialization_val = test.param.serialize_parameters(subset=[param_name])
            validate(instance=instance_serialization_val, schema=class_schema)

            class_serialization_val = TestSet.param.serialize_parameters(subset=[param_name])
            validate(instance=class_serialization_val, schema=class_schema)
