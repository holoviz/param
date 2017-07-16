"""
Unit test for String parameters
"""

import unittest

import param

# TODO: very incomplete!

class TestStringParameters(unittest.TestCase):

    def test_default_none(self):
        class A(param.Parameterized):
            s = param.String(None)

        a = A()
        a.s = "hello"
        a.s = None # because allow_None should be True with default of None
            
