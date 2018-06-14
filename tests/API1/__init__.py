import param
import unittest

class API1TestCase(unittest.TestCase):

    def setUp(self):
        param.parameterized.Parameters._disable_stubs = True

    def tearDown(self):
        param.parameterized.Parameters._disable_stubs = False
