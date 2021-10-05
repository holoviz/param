"""
Unit test for param.depends.
"""


import param
from . import API1TestCase



class TestParamDependsSubclassing(API1TestCase):

    def test_param_depends_override_depends_subset(self):

        class A(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a', 'b', watch=True)
            def test(self):
                pass

        a = A()

        assert len(a.param.params_depended_on('test')) == 2

        class B(A):

            @param.depends('b')
            def test(self):
                pass

        b = B()

        assert len(b.param.params_depended_on('test')) == 1
        assert len(B.param._depends['watch']) == 0

    def test_param_depends_override_depends_subset_watched(self):

        class A(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a', 'b', watch=True)
            def test(self):
                pass

        a = A()

        assert len(a.param.params_depended_on('test')) == 2

        class B(A):

            @param.depends('b', watch=True)
            def test(self):
                pass

        b = B()

        assert len(b.param.params_depended_on('test')) == 1
        assert len(B.param._depends['watch']) == 1
        m, _, deps, _ = B.param._depends['watch'][0]
        assert m == 'test'
        assert len(deps) == 1
        assert deps[0].name == 'b'

    def test_param_depends_override_all_depends(self):

        class A(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a', 'b', watch=True)
            def test(self):
                pass

        a = A()
        assert len(a.param.params_depended_on('test')) == 2

        class B(A):

            def test(self):
                pass

        b = B()
        assert len(b.param.params_depended_on('test')) == 3
        assert len(B.param._depends['watch']) == 0



class TestParamDepends(API1TestCase):

    def setUp(self):

        class P(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            single_count = param.Integer()
            attr_count = param.Integer()
            single_nested_count = param.Integer()
            nested_attr_count = param.Integer()
            nested_count = param.Integer()

            @param.depends('a', watch=True)
            def single_parameter(self):
                self.single_count += 1

            #@param.depends('a:constant', watch=True)
            def constant(self):
                self.attr_count += 1

            @param.depends('b.a', watch=True)
            def single_nested(self):
                self.single_nested_count += 1

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

    def test_param_depends(self):
        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter()

            test_count = param.Integer()

            @param.depends('a.c', 'a.d', watch=True)
            def test(self):
                self.test_count += 1

        b = B(a=A(c=1))
        b.a = A(c=1)
        assert b.test_count == 0

    def test_param_depends_class_default_dynamic(self):

        class A(param.Parameterized):
            c = param.Parameter()

        class B(param.Parameterized):
            a = param.Parameter(A())

            nested_count = param.Integer()

            @param.depends('a.c', watch=True)
            def nested(self):
                self.nested_count += 1

        b = B()

        b.a.c = 1
        assert b.nested_count == 1

        b.a = A()
        assert b.nested_count == 2

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
        init_b = self.P()
        inst = self.P(b=init_b)
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

        assert inst.single_nested_count == 0

        inst.b.a = 1
        assert inst.single_nested_count == 1

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
        assert inst.single_nested_count == 1

    def test_param_instance_depends_dynamic_nested_attribute(self):
        inst = self.P()
        pinfos = inst.param.params_depended_on('nested_attribute')
        self.assertEqual(len(pinfos), 0)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested_attribute')
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
        self.assertEqual(pinfo2.what, 'constant')

        assert inst.nested_attr_count == 1

        inst.b.param.a.constant = True
        assert inst.nested_attr_count == 2

    def test_param_instance_depends_dynamic_nested_attribute_initialized(self):
        inst = self.P(b=self.P())
        pinfos = inst.param.params_depended_on('nested_attribute')
        self.assertEqual(len(pinfos), 2)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested_attribute')
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
        self.assertEqual(pinfo2.what, 'constant')

        assert inst.nested_attr_count == 0

        inst.b.param.a.constant = True
        assert inst.nested_attr_count == 1

    def test_param_instance_depends_dynamic_nested(self):
        inst = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 0)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 9)
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
        init_b = self.P()
        inst = self.P(b=init_b)
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 9)

        inst.b = self.P()
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 9)
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

        assert inst.single_nested_count == 0

        inst.b.a = 1
        assert inst.single_nested_count == 1

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
        assert inst.single_nested_count == 1

    def test_param_instance_depends_dynamic_nested_changed_value(self):
        init_b = self.P(a=1)
        inst = self.P(b=init_b)
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 9)

        inst.b = self.P(a=2)
        pinfos = inst.param.params_depended_on('nested')
        self.assertEqual(len(pinfos), 9)
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

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
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
        self.assertEqual(len(pinfos), 9)
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
