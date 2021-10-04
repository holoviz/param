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

            single_count = param.Integer()
            attr_count = param.Integer()
            single_nested_count = param.Integer()
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

            @param.depends('b.param', watch=True)
            def nested(self):
                self.nested_count += 1

        class P2(param.Parameterized):

            @param.depends(P.param.a)
            def external_param(self, a):
                pass

        self.P = P
        self.P2 = P2

    def test_param_instance_depends_dynamic_single_nested(self):
        inst = self.P()
        pinfos = inst.param.params_depended_on('single_nested')
        self.assertEqual(len(pinfos), 0)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('single_nested')
        self.assertEqual(len(pinfos), 2)
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'b')
        self.assertEqual(pinfo.what, 'value')
        pinfo2 = pinfos[(inst.b, 'a')]
        self.assertIs(pinfo2.cls, self.P)
        self.assertIs(pinfo2.inst, inst.b)
        self.assertEqual(pinfo2.name, 'a')
        self.assertEqual(pinfo2.what, 'value')

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

    def test_param_instance_depends_dynamic_single_nested_initialized(self):
        inst = self.P(b=self.P())
        pinfos = inst.param.params_depended_on('single_nested')
        self.assertEqual(len(pinfos), 2)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('single_nested')
        self.assertEqual(len(pinfos), 2)
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'b')
        self.assertEqual(pinfo.what, 'value')
        pinfo2 = pinfos[(inst.b, 'a')]
        self.assertIs(pinfo2.cls, self.P)
        self.assertIs(pinfo2.inst, inst.b)
        self.assertEqual(pinfo2.name, 'a')
        self.assertEqual(pinfo2.what, 'value')

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

    def test_param_instance_depends_dynamic_nested(self):
        inst = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 0)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 8)
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'b')
        self.assertEqual(pinfo.what, 'value')
        for p in ['a', 'b', 'name', 'nested_count', 'single_count', 'attr_count']:
            pinfo2 = pinfos[(inst.b, p)]
            self.assertIs(pinfo2.cls, self.P)
            self.assertIs(pinfo2.inst, inst.b)
            self.assertEqual(pinfo2.name, p)
            self.assertEqual(pinfo2.what, 'value')

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

    def test_param_instance_depends_dynamic_nested_initialized(self):
        inst = self.P(b=self.P())
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 8)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 8)
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'b')
        self.assertEqual(pinfo.what, 'value')
        for p in ['a', 'b', 'name', 'nested_count', 'single_count', 'attr_count']:
            pinfo2 = pinfos[(inst.b, p)]
            self.assertIs(pinfo2.cls, self.P)
            self.assertIs(pinfo2.inst, inst.b)
            self.assertEqual(pinfo2.name, p)
            self.assertEqual(pinfo2.what, 'value')

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

    def test_param_instance_depends(self):
        p = self.P()
        pinfos = p.param.params_depended_on('single_parameter')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, p)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')

        p.a = 1
        assert p.single_count == 1

    def test_param_class_depends(self):
        pinfos = self.P.param.params_depended_on('single_parameter')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, None)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')

    def test_param_class_depends_constant(self):
        pinfos = self.P.param.params_depended_on('constant')
        self.assertEqual(len(pinfos), 1)
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, None)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'constant')

    def test_param_inst_depends_nested(self):
        inst = self.P(b=self.P())
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 8)
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, inst)
        self.assertEqual(pinfo.name, 'b')
        self.assertEqual(pinfo.what, 'value')
        for p in ['name', 'a', 'b']:
            info = pinfos[(inst.b, p)]
            self.assertEqual(info.name, p)
            self.assertIs(info.inst, inst.b)

    def test_param_external_param_instance(self):
        inst = self.P2()
        pinfos = inst.param.params_depended_on('external_param')
        pinfo = pinfos[0]
        self.assertIs(pinfo.cls, self.P)
        self.assertIs(pinfo.inst, None)
        self.assertEqual(pinfo.name, 'a')
        self.assertEqual(pinfo.what, 'value')



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
