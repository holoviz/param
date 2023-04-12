"""
Unit test for param.depends.
"""
import sys

import param
import pytest

from . import API1TestCase

try:
    import asyncio
except ImportError:
    asyncio = None


def async_executor(func):
    # Could be entirely replaced by asyncio.run(func()) in Python >=3.7
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(func())


class TestParamDepends(API1TestCase):

    def setUp(self):

        class P(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            single_count = param.Integer()
            attr_count = param.Integer()
            single_nested_count = param.Integer()
            double_nested_count = param.Integer()
            nested_attr_count = param.Integer()
            nested_count = param.Integer()

            @param.depends('a', watch=True)
            def single_parameter(self):
                self.single_count += 1

            @param.depends('a:constant', watch=True)
            def constant(self):
                self.attr_count += 1

            @param.depends('b.a', watch=True)
            def single_nested(self):
                self.single_nested_count += 1

            @param.depends('b.b.a', watch=True)
            def double_nested(self):
                self.double_nested_count += 1

            @param.depends('b.a:constant', watch=True)
            def nested_attribute(self):
                self.nested_attr_count += 1

            @param.depends('b.param', watch=True)
            def nested(self):
                self.nested_count += 1

        class P2(param.Parameterized):

            @param.depends(P.param.a)
            def external_param(self, a):
                pass

        self.P = P
        self.P2 = P2

    def test_async(self):
        try:
            param.parameterized.async_executor = async_executor
            class P(param.Parameterized):
                a = param.Parameter()
                single_count = param.Integer()

                @param.depends('a', watch=True)
                async def single_parameter(self):
                    self.single_count += 1

            inst = P()
            inst.a = 'test'
            assert inst.single_count == 1
        finally:
            param.parameterized.async_executor = None


class TestParamDependsFunction(API1TestCase):

    def setUp(self):
        class P(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()


        self.P = P

    @pytest.mark.skipif(sys.version_info.major == 2, reason='asyncio only on Python 3')
    def test_async(self):
        try:
            param.parameterized.async_executor = async_executor
            p = self.P(a=1)

            d = []

            @param.depends(p.param.a, watch=True)
            async def function(value):
                d.append(value)

            p.a = 2

            assert d == [2]
        finally:
            param.parameterized.async_executor = None
