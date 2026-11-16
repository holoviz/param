"""If numpy is present, test if numpy stuff is ok."""
import os
import unittest

import param

from .utils import check_defaults

try:
    import numpy
    import numpy.testing
except ModuleNotFoundError:
    if os.getenv('PARAM_TEST_NUMPY','0') == '1':
        raise ImportError("PARAM_TEST_NUMPY=1 but numpy not available.")
    else:
        raise unittest.SkipTest("numpy not available")


def _is_array_and_equal(test, ref):
    if type(test) is not numpy.ndarray:
        raise AssertionError
    numpy.testing.assert_array_equal(test,ref)


# TODO: incomplete
class TestNumpy(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True
        assert p.is_instance is True
        assert p.class_ == numpy.ndarray

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.Array()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.Array()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.Array()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

    def test_array_param(self):
        class Z(param.Parameterized):
            z = param.Array(default=numpy.array([1]))

        _is_array_and_equal(Z.z,[1])

        z = Z(z=numpy.array([1,2]))
        _is_array_and_equal(z.z,[1,2])

    def test_array_param_positional(self):
        class Z(param.Parameterized):
            z = param.Array(numpy.array([1]))

        _is_array_and_equal(Z.z,[1])

        z = Z(z=numpy.array([1,2]))
        _is_array_and_equal(z.z,[1,2])

    def test_array_pprint(self):
        class MatParam(param.Parameterized):
            mat = param.Array(numpy.zeros((2, 2)))

        mp = MatParam()
        mp.param.pprint()


class _DunderArray:
    def __init__(self, data):
        self._data = numpy.asarray(data)

    def __array__(self, dtype=None, copy=None):
        return self._data if dtype is None else self._data.astype(dtype)


class _ArrayInterface:
    def __init__(self, data):
        self._data = numpy.asarray(data)

    @property
    def __array_interface__(self):
        return self._data.__array_interface__


class _ArrayStruct:
    def __init__(self, data):
        self._data = numpy.asarray(data)

    @property
    def __array_struct__(self):
        return self._data.__array_struct__


class _RaisingGetattr:
    def __getattr__(self, name):
        raise RuntimeError(name)


class TestArrayLike(unittest.TestCase):

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.instantiate is True

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.ArrayLike()

        check_defaults(P.param.s, label='S', skip=['instantiate'])
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.ArrayLike()

        p = P()

        check_defaults(p.param.s, label='S', skip=['instantiate'])
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.ArrayLike()

        check_defaults(s, label=None, skip=['instantiate'])
        self._check_defaults(s)

    def test_arraylike_param(self):
        class Z(param.Parameterized):
            z = param.ArrayLike(default=numpy.array([1]))

        _is_array_and_equal(Z.z, [1])

        z = Z(z=numpy.array([1, 2]))
        _is_array_and_equal(z.z, [1, 2])

    def test_arraylike_param_positional(self):
        class Z(param.Parameterized):
            z = param.ArrayLike(numpy.array([1]))

        _is_array_and_equal(Z.z, [1])

    def test_arraylike_accepts_protocols(self):
        class Z(param.Parameterized):
            z = param.ArrayLike()

        z = Z()
        for cls in (_DunderArray, _ArrayInterface, _ArrayStruct):
            obj = cls([1, 2, 3])
            z.z = obj
            assert z.z is obj
            numpy.testing.assert_array_equal(numpy.asarray(z.z), [1, 2, 3])

    def test_arraylike_rejects_non_arrays(self):
        class Z(param.Parameterized):
            z = param.ArrayLike()

        z = Z()
        for value in ([1, 2, 3], (1, 2), 'abc', 1, {}, _RaisingGetattr()):
            with self.assertRaisesRegex(ValueError, "ArrayLike parameter 'Z.z' value must implement the array protocol"):
                z.z = value

    def test_arraylike_rejects_class(self):
        with self.assertRaises(ValueError):
            param.ArrayLike(default=numpy.ndarray)

    def test_arraylike_invalid_default(self):
        with self.assertRaises(ValueError):
            param.ArrayLike(default=[1, 2])

    def test_arraylike_allow_None_false(self):
        class Z(param.Parameterized):
            z = param.ArrayLike(default=numpy.array([1]), allow_None=False)

        with self.assertRaises(ValueError):
            Z(z=None)

    def test_arraylike_instantiate(self):
        arr = numpy.array([1, 2])

        class Z(param.Parameterized):
            z = param.ArrayLike(default=arr)

        z = Z()
        assert z.z is not arr
        _is_array_and_equal(z.z, [1, 2])

    def test_arraylike_serialize(self):
        assert param.ArrayLike.serialize(None) is None
        assert param.ArrayLike.serialize(_DunderArray([1, 2])) == [1, 2]
        assert param.ArrayLike.serialize(_ArrayInterface([[1], [2]])) == [[1], [2]]

    def test_arraylike_deserialize(self):
        assert param.ArrayLike.deserialize(None) is None
        assert param.ArrayLike.deserialize('null') is None
        _is_array_and_equal(param.ArrayLike.deserialize([1, 2]), [1, 2])

    def test_arraylike_json_roundtrip(self):
        class Z(param.Parameterized):
            z = param.ArrayLike(default=_DunderArray([1, 2, 3]))

        serialized = Z.param.serialize_value('z')
        _is_array_and_equal(Z.param.deserialize_value('z', serialized), [1, 2, 3])

    def test_arraylike_schema(self):
        class Z(param.Parameterized):
            z = param.ArrayLike(allow_None=False, default=numpy.array([1]))

        assert Z.param.schema()['z']['type'] == 'array'
        with self.assertRaises(param.serializer.UnsafeserializableException):
            Z.param.schema(safe=True)

    def test_arraylike_pandas_extension_arrays(self):
        try:
            import pandas as pd
        except ModuleNotFoundError:
            raise unittest.SkipTest("pandas not available")

        class Z(param.Parameterized):
            z = param.ArrayLike()
            a = param.Array()

        z = Z()
        cat = pd.Categorical(['a', 'b', 'a'])
        z.z = cat
        assert z.z is cat
        assert param.ArrayLike.serialize(cat) == ['a', 'b', 'a']
        with self.assertRaises(ValueError):
            z.a = cat

    def test_arraylike_pandas_arrow_string_array(self):
        try:
            import pandas as pd
            import pyarrow  # noqa: F401
        except ModuleNotFoundError:
            raise unittest.SkipTest("pandas or pyarrow not available")

        class Z(param.Parameterized):
            z = param.ArrayLike()

        arr = pd.array(['x', 'y'], dtype='string[pyarrow]')
        z = Z(z=arr)
        assert z.z is arr
        assert param.ArrayLike.serialize(arr) == ['x', 'y']
