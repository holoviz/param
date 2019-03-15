"""
Unit test for Number parameters and their subclasses.
"""
import param
from . import API1TestCase


class TestNumberParameters(API1TestCase):


    def test_initialization_without_step_class(self):
        class Q(param.Parameterized):
            q = param.Number(default=1)

        self.assertEqual(Q.param.params('q').step, None)

    def test_initialization_with_step_class(self):
        class Q(param.Parameterized):
            q = param.Number(default=1, step=0.5)

        self.assertEqual(Q.param.params('q').step, 0.5)

    def test_initialization_without_step_instance(self):
        class Q(param.Parameterized):
            q = param.Number(default=1)

        self.assertEqual(Q.param.params('q').step, None)

    def test_initialization_with_step_instance(self):
        class Q(param.Parameterized):
            q = param.Number(default=1, step=0.5)

        qobj = Q()
        self.assertEqual(qobj.param.params('q').step, 0.5)
