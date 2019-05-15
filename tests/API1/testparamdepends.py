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
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'a')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')
        for p in ['name', 'a', 'b']:
            info = pinfos[(inst.a, p)]
            self.assertEqual(info.name, p)
            self.assertIs(info.inst, inst.a)



class TestParamDependsFunction(API1TestCase):

    def setUp(self):
        class P(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()


        self.P = P

    def test_param_depends_function_instance_params(self):
        p = self.P()

        @param.depends(p.param.a, c=p.param.b)
        def function(value, c):
            pass

        dependencies = {
            'dependencies': (p.param.a,),
            'kw': {'c': p.param.b},
            'watch': False
        }
        self.assertEqual(function._dinfo, dependencies)

    def test_param_depends_function_class_params(self):
        p = self.P

        @param.depends(p.param.a, c=p.param.b)
        def function(value, c):
            pass

        dependencies = {
            'dependencies': (p.param.a,),
            'kw': {'c': p.param.b},
            'watch': False
        }
        self.assertEqual(function._dinfo, dependencies)

    def test_param_depends_function_instance_params_watch(self):
        p = self.P(a=1, b=2)

        d = []

        @param.depends(p.param.a, c=p.param.b, watch=True)
        def function(value, c):
            d.append(value+c)

        p.a = 2
        self.assertEqual(d, [4])
        p.b = 3
        self.assertEqual(d, [4, 5])

    def test_param_depends_function_class_params_watch(self):
        p = self.P
        p.a = 1
        p.b = 2

        d = []

        @param.depends(p.param.a, c=p.param.b, watch=True)
        def function(value, c):
            d.append(value+c)

        p.a = 2
        self.assertEqual(d, [4])
        p.b = 3
        self.assertEqual(d, [4, 5])
