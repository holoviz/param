"""
Test deserialization routines that read from file
"""

import param

from . import API1TestCase
from unittest import skipIf
from tempfile import mkdtemp
from shutil import rmtree

try:
    import numpy as np
    ndarray = np.array([[1,2,3],[4,5,6]])
except:
    np, ndarray = None, None

np_skip = skipIf(np is None, "NumPy is not available")


class TestSet(param.Parameterized):
    array = None if np is None else param.Array(default=ndarray)

class TestFileDeserialization(API1TestCase):

    def run(self, result):
        self.temp_dir = mkdtemp().replace('\\', '/')
        try:
            return super().run(result=result)
        finally:
            rmtree(self.temp_dir, ignore_errors=True)

    def _test_deserialize(self, obj, path, pname, check=True):
        # assumes the parameter has already been serialized to path!
        deserialized = obj.param.deserialize_value(
            pname, '"{}"'.format(path), mode='json')
        if check:
            self.assertEqual(deserialized, getattr(obj, pname))
        return deserialized

    @np_skip
    def test_numpy_npy(self):
        path = '{}/val.npy'.format(self.temp_dir)
        np.save(path, TestSet.array)
        deserialized = self._test_deserialize(TestSet, path, 'array', False)
        self.assertTrue(np.array_equal(deserialized, getattr(TestSet, 'array')))
