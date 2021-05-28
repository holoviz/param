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


try:
    import pandas as pd
    df = pd.DataFrame({'A':[1,2,3], 'B':[1.1,2.2,3.3]})
except:
    pd, df1, df2 = None, None, None

pd_skip = skipIf(pd is None, "pandas is not available")


class TestSet(param.Parameterized):
    array = None if np is None else param.Array(default=ndarray)
    data_frame = None if pd is None else param.DataFrame(default=df)


class TestFileDeserialization(API1TestCase):

    def run(self, result):
        self.temp_dir = mkdtemp().replace('\\', '/')
        try:
            return super().run(result=result)
        finally:
            rmtree(self.temp_dir, ignore_errors=True)

    @np_skip
    def _test_deserialize_array(self, obj, path, pname):
        # assumes the parameter has already been serialized to path!
        deserialized = obj.param.deserialize_value(
            pname, '"{}"'.format(path), mode='json')
        self.assertTrue(np.array_equal(deserialized, getattr(obj, pname)))

    @np_skip
    def test_numpy_npy(self):
        path = '{}/val.npy'.format(self.temp_dir)
        np.save(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @np_skip
    def test_numpy_txt(self):
        path = '{}/val.txt'.format(self.temp_dir)
        np.savetxt(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @np_skip
    def test_numpy_txt_gz(self):
        path = '{}/val.txt.gz'.format(self.temp_dir)
        np.savetxt(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @pd_skip
    def test_pandas_pkl(self):
        path = '{}/val.pkl.zip'.format(self.temp_dir)
        TestSet.data_frame.to_pickle(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_pandas_csv(self):
        path = '{}/val.csv.bz2'.format(self.temp_dir)
        TestSet.data_frame.to_csv(path, index=False)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_pandas_tsv(self):
        path = '{}/val.tsv'.format(self.temp_dir)
        TestSet.data_frame.to_csv(path, index=False, sep='\t')
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_pandas_json(self):
        path = '{}/val.json'.format(self.temp_dir)
        TestSet.data_frame.to_json(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')
