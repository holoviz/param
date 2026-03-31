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

    def test_array_accepts_array_like_with_dunder_array(self):
        """Objects implementing __array__ should be accepted by param.Array."""
        class ArrayLike:
            """Minimal array-like with __array__ protocol."""
            def __init__(self, data):
                self._data = numpy.asarray(data)
            def __array__(self, dtype=None, copy=None):
                if dtype is not None:
                    return self._data.astype(dtype)
                return self._data

        class P(param.Parameterized):
            arr = param.Array()

        p = P()
        array_like = ArrayLike([1, 2, 3])
        p.arr = array_like  # Should not raise
        numpy.testing.assert_array_equal(numpy.asarray(p.arr), [1, 2, 3])
        # Verify serialize fallback (ArrayLike has no .tolist())
        self.assertEqual(param.Array.serialize(array_like), [1, 2, 3])

    def test_array_accepts_array_like_with_array_interface(self):
        """Objects with __array_interface__ should be accepted."""
        class ArrayInterface:
            """Minimal object with __array_interface__."""
            def __init__(self, data):
                self._arr = numpy.asarray(data)

            @property
            def __array_interface__(self):
                return self._arr.__array_interface__

        class P(param.Parameterized):
            arr = param.Array()

        p = P()
        obj = ArrayInterface([4, 5, 6])
        p.arr = obj  # Should not raise
        numpy.testing.assert_array_equal(numpy.asarray(p.arr), [4, 5, 6])

    def test_array_rejects_plain_list(self):
        """Plain lists should still be rejected (no __array__ attribute)."""
        class P(param.Parameterized):
            arr = param.Array()

        p = P()
        with self.assertRaises(ValueError):
            p.arr = [1, 2, 3]

    def test_array_rejects_string(self):
        """Strings should still be rejected."""
        class P(param.Parameterized):
            arr = param.Array()

        p = P()
        with self.assertRaises(ValueError):
            p.arr = "not an array"

    def test_array_accepts_pandas_extension_array(self):
        """pandas ExtensionArray subclasses should be accepted."""
        try:
            import pandas as pd
        except ImportError:
            self.skipTest("pandas not available")

        class P(param.Parameterized):
            arr = param.Array()

        p = P()
        # Categorical array implements __array__
        cat = pd.Categorical(["a", "b", "a"])
        p.arr = cat  # Should not raise
        # Verify serialization works on accepted array-like
        self.assertEqual(param.Array.serialize(cat), ["a", "b", "a"])

        # ArrowStringArray (pandas >= 1.2 with pyarrow) also implements __array__
        try:
            arrow_arr = pd.array(["x", "y", "z"], dtype="string[pyarrow]")
            p.arr = arrow_arr  # Should not raise
        except (ImportError, TypeError, ValueError):
            pass  # pyarrow not installed or dtype unavailable
