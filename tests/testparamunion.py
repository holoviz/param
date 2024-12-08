"""UnitTest for param_union helper"""
import logging
import unittest

import param


class MyHandler(logging.StreamHandler):

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class TestParamUnion(unittest.TestCase):

    def setUp(self):
        self.logger = param.get_logger()
        self.handler = MyHandler()
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_param_union_values(self):
        class A(param.Parameterized):
            a = param.Number(1)
        class B(param.Parameterized):
            b = param.Number(2)
        class C(A, B):
            pass
        a = A()
        a.a = 10
        b = B()
        b.b = 5
        c_1 = C(**param.param_union(a))
        self.assertTrue(c_1.a == 10 and c_1.b == 2)
        c_2 = C(**param.param_union(b))
        self.assertTrue(c_2.a == 1 and c_2.b == 5)
        c_3 = C(**param.param_union(a, b))
        self.assertTrue(c_3.a == 10 and c_3.b == 5)
        c_4 = C(**param.param_union())
        self.assertTrue(c_4.a == 1 and c_4.b == 2)

    def test_param_union_warnings(self):
        class A(param.Parameterized):
            a = param.Number(1)
        a = A()
        A(**param.param_union(a))
        self.assertFalse(self.handler.records)
        A(**param.param_union())
        self.assertFalse(self.handler.records)
        A(**param.param_union(a, a))
        self.assertTrue(self.handler.records)
        self.handler.records.pop()
        A(**param.param_union(a, a, warn=False))
        self.assertFalse(self.handler.records)

    def test_param_union_raises_on_unexpected_kwarg(self):
        with self.assertRaises(TypeError):
            param.param_union(dumbdumbface=True)
