"""
Test deserialization routines that read from file
"""

import logging
from unittest.case import skip
from param.parameterized import get_logger
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


# The writer could be xlsxwriter, but the sufficient condition is the presence of
# openpyxl
try:
    import openpyxl as xlsxm
except:
    xlsxm = None

xlsxm_skip = skipIf(xlsxm is None, "openpyxl is not available")


try:
    import odf as ods
except:
    ods = None

ods_skip = skipIf(ods is None, "odfpy is not available")


try:
    import feather
except:
    feather = None

feather_skip = skipIf(feather is None, "feather-format is not available")


try:
    import fastparquet as parquet
except:
    parquet = None

try:
    import pyarrow as parquet
except:
    pass

parquet_skip = skipIf(parquet is None, "fastparquet and pyarrow are not available")


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
    def _test_deserialize_array(self, obj, path, pname, check=True):
        # assumes the parameter has already been serialized to path!
        deserialized = obj.param.deserialize_value(
            pname, '"{}"'.format(path), mode='json')
        if check:
            self.assertTrue(np.array_equal(deserialized, getattr(obj, pname)))

    @np_skip
    def test_array_npy(self):
        path = '{}/val.npy'.format(self.temp_dir)
        np.save(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @np_skip
    def test_bad_deserialization_warns(self):
        path = '{}/val.npy'.format(self.temp_dir)
        with open(path, 'w'):
            pass
        with self.assertLogs(get_logger(), level=logging.WARN) as cm:
            # this parses successfully as a string array, but it's probably not what
            # the user wanted. Should warn
            self._test_deserialize_array(TestSet, path, 'array', False)
        self.assertRegex(cm.output[0], "Could not parse")

    @np_skip
    def test_array_txt(self):
        path = '{}/val.txt'.format(self.temp_dir)
        np.savetxt(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @np_skip
    def test_array_txt_gz(self):
        path = '{}/val.txt.gz'.format(self.temp_dir)
        np.savetxt(path, TestSet.array)
        self._test_deserialize_array(TestSet, path, 'array')

    @pd_skip
    def test_data_frame_pkl(self):
        path = '{}/val.pkl.zip'.format(self.temp_dir)
        TestSet.data_frame.to_pickle(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_data_frame_csv(self):
        path = '{}/val.csv.bz2'.format(self.temp_dir)
        TestSet.data_frame.to_csv(path, index=False)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_data_frame_tsv(self):
        path = '{}/val.tsv'.format(self.temp_dir)
        TestSet.data_frame.to_csv(path, index=False, sep='\t')
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    def test_data_frame_json(self):
        path = '{}/val.json'.format(self.temp_dir)
        TestSet.data_frame.to_json(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    # FIXME(sdrobert): xls are old-style excel files. There are two distinct engines for
    # reading and writing these, and the writer engine is deprecated by pandas. We could
    # store the serialized file as a byte array to future-proof somewhat, but that would
    # break if we ever decided to change the default data_frame value. Who cares.

    @pd_skip
    @xlsxm_skip
    def test_data_frame_xlsm(self):
        path = '{}/val.xlsm'.format(self.temp_dir)
        TestSet.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    @xlsxm_skip
    def test_data_frame_xlsx(self):
        path = '{}/val.xlsx'.format(self.temp_dir)
        TestSet.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @pd_skip
    @ods_skip
    def test_data_frame_ods(self):
        path = '{}/val.ods'.format(self.temp_dir)
        TestSet.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @feather_skip
    def test_data_frame_feather(self):
        path = '{}/val.feather'.format(self.temp_dir)
        TestSet.data_frame.to_feather(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')

    @parquet_skip
    def test_data_frame_parquet(self):
        path = '{}/val.parquet'.format(self.temp_dir)
        TestSet.data_frame.to_parquet(path)
        self._test_deserialize_array(TestSet, path, 'data_frame')
