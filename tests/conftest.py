import unittest

# Python 2 compatibility        
if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
    unittest.TestCase.assertRaisesRegex = API1TestCase.assertRaisesRegexp
if not hasattr(unittest.TestCase, 'assertEquals'):
    unittest.TestCase.assertEquals = API1TestCase.assertEqual
