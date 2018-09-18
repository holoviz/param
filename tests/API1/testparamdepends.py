"""
Unit test for param.depends.
"""


import param
from . import API1TestCase


class TestParamDepends(API1TestCase):

    def setUp(self):
        class P(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a')
            def single_parameter(self):
                pass

            @param.depends('a:constant')
            def constant(self):
                pass

            @param.depends('a.param')
            def nested(self):
                pass

        self.P = P

    def test_param_depends_instance(self):
        p = self.P()
        pinfos = p.param.params_depended_on('single_parameter')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, p)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')

    def test_param_depends_class(self):
        pinfos = self.P.param.params_depended_on('single_parameter')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, None)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')

    def test_param_depends_constant(self):
        pinfos = self.P.param.params_depended_on('constant')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, None)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'constant')

    def test_param_depends_nested(self):
        inst = self.P(a=self.P())
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 4)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')
        for info, p in zip(pinfos[1:], ['name', 'a', 'b']):
            self.assertEqual(info.name, p)
            self.assertIs(info.inst, inst.a)
