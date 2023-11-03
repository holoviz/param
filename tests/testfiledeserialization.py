"""
Test deserialization routines that read from file
"""
import unittest
import param
import sys

from unittest import skipIf
from tempfile import mkdtemp
from shutil import rmtree

try:
    import numpy as np
    ndarray = np.array([[1,2,3],[4,5,6]])
except:
    np = ndarray = None

try:
    import pandas as pd
    pd_ver = pd.__version__.split('.')
    df = pd.DataFrame({'A':[1,2,3], 'B':[1.1,2.2,3.3]})
    modern_pd = pd if (int(pd_ver[0]) >= 1 and int(pd_ver[1]) >= 2) else None
except:
    pd = df1 = df2 = modern_pd = None

# The writer could be xlsxwriter, but the sufficient condition is the presence of
# openpyxl
try:
    import openpyxl as xlsxm
except:
    xlsxm = None

try:
    import odf as ods
except:
    ods = None

# prior to pandas version 1.2, xlrd was always the default excel reader (though it
# had to be be of a version before xlrd's 2.0).
xls = None
try:
    import xlrd as xls
    if int(xls.__version__.split('.')[0]) > 2:
        raise Exception()
except:
    if modern_pd is None:
        xlsxm = None

try:
    import pyarrow.feather as feather
except:
    feather = None

try:
    import fastparquet as parquet
except:
    parquet = None
try:
    import pyarrow as parquet
except:
    pass

try:
    import tables as hdf5
except:
    hdf5 = None

np_skip = skipIf(np is None, "NumPy is not available")
pd_skip = skipIf(pd is None, "pandas is not available")
modern_pd_skip = skipIf(modern_pd is None, "pandas is too old")
xlsxm_skip = skipIf(xlsxm is None, "openpyxl is not available")
ods_skip = skipIf(ods is None, "odfpy is not available")
xls_skip = skipIf(xls is None, "xlrd is not available")
feather_skip = skipIf(feather is None, "pyarrow.feather is not available")
parquet_skip = skipIf(parquet is None, "fastparquet and pyarrow are not available")
hdf5_skip = skipIf(hdf5 is None, "pytables is not available")


class P(param.Parameterized):
    array = None if np is None else param.Array(default=ndarray)
    data_frame = None if pd is None else param.DataFrame(default=df)


class TestFileDeserialization(unittest.TestCase):

    def run(self, result):
        self.temp_dir = mkdtemp().replace('\\', '/')
        try:
            return super(TestFileDeserialization, self).run(result=result)
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
    def test_fail_to_deserialize(self):
        path = '{}/val.foo'.format(self.temp_dir)
        with self.assertRaisesRegex(IOError, "does not exist or is not a file"):
            self._test_deserialize_array(P, path, 'array')
        with open(path, 'w'):
            pass
        with self.assertRaisesRegex(ValueError, "no deserialization method for files"):
            self._test_deserialize_array(P, path, 'array')
        path = '{}/val.npy'.format(self.temp_dir)
        with open(path, 'w'):
            pass
        with self.assertRaises(Exception):
            self._test_deserialize_array(P, path, 'array')

    @np_skip
    def test_array_npy(self):
        path = '{}/val.npy'.format(self.temp_dir)
        np.save(path, P.array)
        self._test_deserialize_array(P, path, 'array')

    @np_skip
    def test_array_txt(self):
        path = '{}/val.txt'.format(self.temp_dir)
        np.savetxt(path, P.array)
        self._test_deserialize_array(P, path, 'array')

    @np_skip
    def test_array_txt_gz(self):
        path = '{}/val.txt.gz'.format(self.temp_dir)
        np.savetxt(path, P.array)
        self._test_deserialize_array(P, path, 'array')

    @pd_skip
    def test_data_frame_pkl(self):
        path = '{}/val.pkl.zip'.format(self.temp_dir)
        P.data_frame.to_pickle(path)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    def test_data_frame_csv(self):
        path = '{}/val.csv.bz2'.format(self.temp_dir)
        P.data_frame.to_csv(path, index=False)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    def test_data_frame_tsv(self):
        path = '{}/val.tsv'.format(self.temp_dir)
        P.data_frame.to_csv(path, index=False, sep='\t')
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    def test_data_frame_json(self):
        path = '{}/val.json'.format(self.temp_dir)
        P.data_frame.to_json(path)
        self._test_deserialize_array(P, path, 'data_frame')

    # FIXME(sdrobert): xls are old-style excel files. There are two distinct engines for
    # reading and writing these, and the writer engine is deprecated by pandas. We could
    # store the serialized file as a byte array to future-proof somewhat, but that would
    # break if we ever decided to change the default data_frame value. Who cares.

    @pd_skip
    @xlsxm_skip
    def test_data_frame_xlsm(self):
        path = '{}/val.xlsm'.format(self.temp_dir)
        P.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    @xlsxm_skip
    def test_data_frame_xlsx(self):
        path = '{}/val.xlsx'.format(self.temp_dir)
        P.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    @ods_skip
    @skipIf(sys.version_info[0] < 3, "py2k pandas does not support 'ods'")
    def test_data_frame_ods(self):
        path = '{}/val.ods'.format(self.temp_dir)
        P.data_frame.to_excel(path, index=False)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    @feather_skip
    def test_data_frame_feather(self):
        path = '{}/val.feather'.format(self.temp_dir)
        P.data_frame.to_feather(path)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    @parquet_skip
    def test_data_frame_parquet(self):
        path = '{}/val.parquet'.format(self.temp_dir)
        P.data_frame.to_parquet(path)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    def test_data_frame_stata(self):
        path = '{}/val.dta'.format(self.temp_dir)
        P.data_frame.to_stata(path, write_index=False)
        self._test_deserialize_array(P, path, 'data_frame')

    @pd_skip
    @hdf5_skip
    def test_data_frame_hdf5(self):
        path = '{}/val.h5'.format(self.temp_dir)
        P.data_frame.to_hdf(path, 'df')
        self._test_deserialize_array(P, path, 'data_frame')
        path = '{}/val.hdf5'.format(self.temp_dir)
        P.data_frame.to_hdf(path, 'df')
        self._test_deserialize_array(P, path, 'data_frame')
