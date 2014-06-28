"""
Unit test for the IPython magic
"""

import re
import sys
import unittest
import param


# SkipTest will be raised if IPython unavailable
from param.ipython import ParamPager

test1_repr = """\x1b[1;32mParameters of 'TestClass'\n=========================\n\x1b[0m\n\x1b[1;31mParameters changed from their default values are marked in red.\x1b[0m\n\x1b[1;36mSoft bound values are marked in cyan.\x1b[0m\nC/V= Constant/Variable, RO/RW = ReadOnly/ReadWrite, AN=Allow None\n\n\x1b[1;34mNameValue   Type     Bounds      Mode  \x1b[0m\n\nu    4    Number                V RW  \nv    4    Number                C RW  \nw    4    Number                C RO  \nx   None  String              V RW AN \ny    4    Number  (-1, None)    V RW  \nz    4    Number  (-1, 100)     V RW  \n\n\x1b[1;32mParameter docstrings:\n=====================\x1b[0m\n\n\x1b[1;34mu: < No docstring available >\x1b[0m\n\x1b[1;31mv: < No docstring available >\x1b[0m\n\x1b[1;34mw: < No docstring available >\x1b[0m\n\x1b[1;31mx: < No docstring available >\x1b[0m\n\x1b[1;34my: < No docstring available >\x1b[0m\n\x1b[1;31mz: < No docstring available >\x1b[0m"""


test2_repr = """\x1b[1;32mParameters of 'TestClass01034'\n==============================\n\x1b[0m\n\x1b[1;31mParameters changed from their default values are marked in red.\x1b[0m\n\x1b[1;36mSoft bound values are marked in cyan.\x1b[0m\nC/V= Constant/Variable, RO/RW = ReadOnly/ReadWrite, AN=Allow None\n\n\x1b[1;34mNameValue   Type     Bounds      Mode  \x1b[0m\n\nu    4    Number                V RW  \nv    4    Number                C RW  \nw    4    Number                C RO  \nx   None  String              V RW AN \ny    4    Number  (-1, None)    V RW  \nz    4    Number  (-1, 100)     V RW  \n\n\x1b[1;32mParameter docstrings:\n=====================\x1b[0m\n\n\x1b[1;34mu: < No docstring available >\x1b[0m\n\x1b[1;31mv: < No docstring available >\x1b[0m\n\x1b[1;34mw: < No docstring available >\x1b[0m\n\x1b[1;31mx: < No docstring available >\x1b[0m\n\x1b[1;34my: < No docstring available >\x1b[0m\n\x1b[1;31mz: < No docstring available >\x1b[0m"""

class TestParamPager(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        class TestClass(param.Parameterized):
            u = param.Number(4)
            v = param.Number(4, constant=True)
            w = param.Number(4, readonly=True)
            x = param.String(None, allow_None=True)
            y = param.Number(4, bounds=(-1, None))
            z = param.Number(4, bounds=(-1, 100), softbounds=(-100, -200))

        self.TestClass = TestClass
        self.pager = ParamPager()

    def test_parameterized_class(self):
        page_string = self.pager(self.TestClass)
        # Remove params automatic numbered names
        page_string = re.sub('TestClass(\d+)', 'TestClass', page_string)
        ref_string = re.sub('TestClass(\d+)', 'TestClass', test1_repr)

        try:
            self.assertEqual(page_string, ref_string)
        except Exception as e:
            sys.stderr.write(page_string)  # Coloured output
            sys.stderr.write("\nRAW STRING:\n\n%r\n\n" % page_string)
            raise e

    def test_parameterized_instance(self):
        page_string = self.pager(self.TestClass())
        # Remove params automatic numbered names
        page_string = re.sub('TestClass(\d+)', 'TestClass', page_string)
        ref_string = re.sub('TestClass(\d+)', 'TestClass', test2_repr)

        try:
            self.assertEqual(page_string, ref_string)
        except Exception as e:
            sys.stderr.write(page_string)  # Coloured output
            sys.stderr.write("\nRAW STRING:\n\n%r\n\n" % page_string)
            raise e

