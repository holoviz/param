"""Testing JSON serialization of parameters and the corresponding schemas."""
import datetime
import json
import unittest

from unittest import SkipTest, skipIf

import param

try:
    from jsonschema import validate, ValidationError
except ModuleNotFoundError:
    import os
    if os.getenv('PARAM_TEST_JSONSCHEMA','0') == '1':
        raise ImportError("PARAM_TEST_JSONSCHEMA=1 but jsonschema not available.")
    validate = None

now = datetime.datetime.now()
after_now = now + datetime.timedelta(days=1)

try:
    import numpy as np
    ndarray = np.array([[1,2,3],[4,5,6]])
    npdt1 = np.datetime64(now)
    npdt2 = np.datetime64(after_now)
except ModuleNotFoundError:
    np, ndarray, npdt1, npdt2 = None, None, None, None

np_skip = skipIf(np is None, "NumPy is not available")

try:
    import pandas as pd
    df1 = pd.DataFrame({'A':[1,2,3], 'B':[1.1,2.2,3.3]})
    df2 = pd.DataFrame({'A':[1.1,2.2,3.3], 'B':[1.1,2.2,3.3]})
    pdts1 = pd.Timestamp(now)
    pdts2 = pd.Timestamp(after_now)
except ModuleNotFoundError:
    pd, df1, df2, pdts1, pdts2 = None, None, None, None, None

pd_skip = skipIf(pd is None, "pandas is not available")

simple_list = [1]

class TestSet(param.Parameterized):

    __test__ = False

    numpy_params = ['r','y']
    pandas_params = ['s','t','u','z']
    conditionally_unsafe = ['f', 'o']

    a = param.Integer(default=5, doc='Example doc', bounds=(2,30), inclusive_bounds=(True, False))
    b = param.Number(default=4.3, allow_None=True)
    c = param.String(default='foo')
    d = param.Boolean(default=False)
    e = param.List([1,2,3], item_type=int)
    f = param.List([1,2,3])
    g = param.Date(default=datetime.datetime.now())
    g2 = None if np is None else param.Date(default=npdt1)
    g3 = None if pd is None else param.Date(default=pdts1)
    h = param.Tuple(default=(1,2,3), length=3)
    i = param.NumericTuple(default=(1,2,3,4))
    j = param.XYCoordinates(default=(32.1, 51.5))
    k = param.Integer(default=1)
    l = param.Range(default=(1.1,2.3), bounds=(1,3))
    m = param.String(default='baz', allow_None=True)
    n = param.ObjectSelector(default=3, objects=[3,'foo'], allow_None=False)
    o = param.ObjectSelector(default=simple_list, objects=[simple_list], allow_None=False)
    p = param.ListSelector(default=[1,4,5], objects=[1,2,3,4,5,6])
    q = param.CalendarDate(default=datetime.date.today())
    r = None if np is None else param.Array(default=ndarray)
    s = None if pd is None else param.DataFrame(default=df1, columns=2)
    t = None if pd is None else param.DataFrame(default=pd.DataFrame(
        {'A':[1,2,3], 'B':[1.1,2.2,3.3]}), columns=(1,4), rows=(2,5))
    u = None if pd is None else param.DataFrame(default=df2, columns=['A', 'B'])
    v = param.Dict({'1':2})
    w = param.Date(default=None, allow_None=True)
    x = param.CalendarDate(default=None, allow_None=True)
    y = None if np is None else param.Array(default=None)
    z = None if pd is None else param.DataFrame(default=None, allow_None=True)
    aa = param.Tuple(default=None, allow_None=True, length=1)
    ab = param.CalendarDateRange(default=(
        datetime.date(2020, 1, 1),
        datetime.date(2021, 1, 1)
    ))
    ac = param.DateRange(default=(
        datetime.date(2020, 1, 1),
        datetime.date(2021, 1, 1)
    ))
    ad = param.DateRange(default=(
        datetime.datetime(2020, 1, 1, 1, 1, 1, 1),
        datetime.datetime(2021, 1, 1, 1, 1, 1, 1)
    ))
    ae = None if np is None else param.DateRange(default=(npdt1, npdt2))
    af = None if pd is None else param.DateRange(default=(pdts1, pdts2))


test = TestSet(a=29)


class TestSerialization(unittest.TestCase):
    """Base class for testing serialization of Parameter values."""

    mode = None

    __test__ = False

    def _test_serialize(self, obj, pname):
        serialized = obj.param.serialize_value(pname, mode=self.mode)
        deserialized = obj.param.deserialize_value(pname, serialized, mode=self.mode)
        self.assertEqual(deserialized, getattr(obj, pname))

    def test_serialize_integer_class(self):
        self._test_serialize(TestSet, 'a')

    def test_serialize_integer_instance(self):
        self._test_serialize(test, 'a')

    def test_serialize_number_class(self):
        self._test_serialize(TestSet, 'b')

    def test_serialize_number_instance(self):
        self._test_serialize(test, 'b')

    def test_serialize_string_class(self):
        self._test_serialize(TestSet, 'c')

    def test_serialize_string_instance(self):
        self._test_serialize(test, 'c')

    def test_serialize_boolean_class(self):
        self._test_serialize(TestSet, 'd')

    def test_serialize_boolean_instance(self):
        self._test_serialize(test, 'd')

    def test_serialize_list_class(self):
        self._test_serialize(TestSet, 'e')

    def test_serialize_list_instance(self):
        self._test_serialize(test, 'e')

    def test_serialize_date_class(self):
        self._test_serialize(TestSet, 'g')

    def test_serialize_date_instance(self):
        self._test_serialize(test, 'g')

    @np_skip
    def test_serialize_date_numpy_class(self):
        self._test_serialize(TestSet, 'g2')

    @np_skip
    def test_serialize_date_numpy_instance(self):
        self._test_serialize(test, 'g2')

    @pd_skip
    def test_serialize_date_pandas_class(self):
        self._test_serialize(TestSet, 'g3')

    @pd_skip
    def test_serialize_date_pandas_instance(self):
        self._test_serialize(test, 'g3')

    def test_serialize_tuple_class(self):
        self._test_serialize(TestSet, 'h')

    def test_serialize_tuple_instance(self):
        self._test_serialize(test, 'h')

    def test_serialize_calendar_date_class(self):
        self._test_serialize(TestSet, 'q')

    def test_serialize_calendar_date_instance(self):
        self._test_serialize(test, 'q')

    @np_skip
    def test_serialize_array_class(self):
        serialized = TestSet.param.serialize_value('r', mode=self.mode)
        deserialized = TestSet.param.deserialize_value('r', serialized, mode=self.mode)
        self.assertTrue(np.array_equal(deserialized, getattr(TestSet, 'r')))

    @np_skip
    def test_serialize_array_instance(self):
        serialized = test.param.serialize_value('r', mode=self.mode)
        deserialized = test.param.deserialize_value('r', serialized, mode=self.mode)
        self.assertTrue(np.array_equal(deserialized, getattr(test, 'r')))

    @pd_skip
    def test_serialize_dataframe_class(self):
        serialized = TestSet.param.serialize_value('s', mode=self.mode)
        deserialized = TestSet.param.deserialize_value('s', serialized, mode=self.mode)
        self.assertTrue(getattr(TestSet, 's').equals(deserialized))

    @pd_skip
    def test_serialize_dataframe_instance(self):
        serialized = test.param.serialize_value('s', mode=self.mode)
        deserialized = test.param.deserialize_value('s', serialized, mode=self.mode)
        self.assertTrue(getattr(test, 's').equals(deserialized))

    def test_serialize_dict_class(self):
        self._test_serialize(TestSet, 'v')

    def test_serialize_dict_instance(self):
        self._test_serialize(test, 'v')

    def test_instance_serialization(self):
        parameters = [p for p in test.param if p not in test.numpy_params + test.pandas_params]
        serialized = test.param.serialize_parameters(subset=parameters, mode=self.mode)
        deserialized = TestSet.param.deserialize_parameters(serialized, mode=self.mode)
        for pname in parameters:
            self.assertEqual(deserialized[pname], getattr(test, pname))

    @np_skip
    def test_numpy_instance_serialization(self):
        serialized = test.param.serialize_parameters(subset=test.numpy_params, mode=self.mode)
        deserialized = TestSet.param.deserialize_parameters(serialized, mode=self.mode)
        for pname in test.numpy_params:
            self.assertTrue(np.array_equal(deserialized[pname], getattr(test, pname)))

    @pd_skip
    def test_pandas_instance_serialization(self):
        serialized = test.param.serialize_parameters(subset=test.pandas_params, mode=self.mode)
        deserialized = TestSet.param.deserialize_parameters(serialized, mode=self.mode)
        for pname in test.pandas_params:
            if getattr(test, pname) is None:
                self.assertTrue(deserialized[pname] is None)
            else:
                self.assertTrue(getattr(test, pname).equals(deserialized[pname]))

    def test_serialize_calendar_date_range_class(self):
        self._test_serialize(TestSet, 'ab')

    def test_serialize_calendar_date_range_instance(self):
        self._test_serialize(test, 'ab')

    def test_serialize_date_range_class(self):
        self._test_serialize(TestSet, 'ac')

    def test_serialize_date_range_instance(self):
        self._test_serialize(test, 'ac')

    def test_serialize_datetime_range_class(self):
        self._test_serialize(TestSet, 'ad')

    def test_serialize_datetime_range_instance(self):
        self._test_serialize(test, 'ad')

    @np_skip
    def test_serialize_datetime_range_numpy_class(self):
        self._test_serialize(TestSet, 'ae')

    @np_skip
    def test_serialize_datetime_range_numpy_instance(self):
        self._test_serialize(test, 'ae')

    @pd_skip
    def test_serialize_datetime_range_pandas_class(self):
        self._test_serialize(TestSet, 'af')

    @pd_skip
    def test_serialize_datetime_range_pandas_instance(self):
        self._test_serialize(test, 'af')


class TestJSONSerialization(TestSerialization):

    mode = 'json'

    __test__ = True


class TestJSONSchema(unittest.TestCase):

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
        self.assertEqual({'a':
                          {'type': 'integer', 'minimum': 2, 'exclusiveMaximum': 30,
                           'description': 'Example doc', 'title': 'A'}},
                         param_schema)

        exception = "1 is not of type 'object'"
        with self.assertRaisesRegex(ValidationError, exception):
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

    @np_skip
    def test_numpy_schemas_always_unsafe(self):
        for param_name in test.numpy_params:
            with self.assertRaisesRegex(param.serializer.UnsafeserializableException,''):
                test.param.schema(safe=True, subset=[param_name], mode='json')

    @pd_skip
    def test_pandas_schemas_always_unsafe(self):
        for param_name in test.pandas_params:
            with self.assertRaisesRegex(param.serializer.UnsafeserializableException,''):
                test.param.schema(safe=True, subset=[param_name], mode='json')

    def test_class_instance_schemas_match_and_validate_unsafe(self):
        if validate is None:
            raise SkipTest('jsonschema needed for schema validation testing')

        for param_name in list(test.param):
            class_schema = TestSet.param.schema(safe=False, subset=[param_name], mode='json')
            instance_schema = test.param.schema(safe=False, subset=[param_name], mode='json')
            self.assertEqual(class_schema, instance_schema)

            instance_serialization_val = test.param.serialize_parameters(subset=[param_name])
            validate(instance=instance_serialization_val, schema=class_schema)

            class_serialization_val = TestSet.param.serialize_parameters(subset=[param_name])
            validate(instance=class_serialization_val, schema=class_schema)

    def test_conditionally_unsafe(self):
        for param_name in test.conditionally_unsafe:
            with self.assertRaisesRegex(param.serializer.UnsafeserializableException,''):
                test.param.schema(safe=True, subset=[param_name], mode='json')
