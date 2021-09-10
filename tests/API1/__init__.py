import param
import unittest

class API1TestCase(unittest.TestCase):

    def setUp(self):
        param.parameterized.Parameters._disable_stubs = True

    def tearDown(self):
        param.parameterized.Parameters._disable_stubs = False


# Python 2 compatibility        
if not hasattr(API1TestCase, 'assertRaisesRegex'):
    API1TestCase.assertRaisesRegex = API1TestCase.assertRaisesRegexp
if not hasattr(API1TestCase, 'assertEquals'):
    API1TestCase.assertEquals = API1TestCase.assertEqual
