"""
Unit test for param.depends.
"""

import asyncio

import param
import pytest

from param.parameterized import _parse_dependency_spec


def async_executor(func):
    # Using nest_asyncio to simplify the async_executor implementation
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(func())


@pytest.fixture
def use_async_executor():
    param.parameterized.async_executor = async_executor
    try:
        yield
    finally:
        param.parameterized.async_executor = None


@pytest.fixture
def class_name(request):
    if request.param.startswith('AP'):
        param.parameterized.async_executor = async_executor
    try:
        yield request.param
    finally:
        if request.param.startswith('AP'):
            param.parameterized.async_executor = None


class TestDependencyParser:

    def test_parameter_value(self):
        obj, attr, what = _parse_dependency_spec('parameter')
        assert obj is None
        assert attr == 'parameter'
        assert what == 'value'

    def test_parameter_attribute(self):
        obj, attr, what = _parse_dependency_spec('parameter:constant')
        assert obj is None
        assert attr == 'parameter'
        assert what == 'constant'

    def test_subobject_parameter(self):
        obj, attr, what = _parse_dependency_spec('subobject.parameter')
        assert obj == '.subobject'
        assert attr == 'parameter'
        assert what == 'value'

    def test_subobject_parameter_attribute(self):
        obj, attr, what = _parse_dependency_spec('subobject.parameter:constant')
        assert obj == '.subobject'
        assert attr == 'parameter'
        assert what == 'constant'

    def test_sub_subobject_parameter(self):
        obj, attr, what = _parse_dependency_spec('subobject.subsubobject.parameter')
        assert obj == '.subobject.subsubobject'
        assert attr == 'parameter'
        assert what == 'value'

    def test_sub_subobject_parameter_attribute(self):
        obj, attr, what = _parse_dependency_spec('subobject.subsubobject.parameter:constant')
        assert obj == '.subobject.subsubobject'
        assert attr == 'parameter'
        assert what == 'constant'


class TestParamDependsSubclassing:

    def test_param_depends_override_depends_subset(self):

        class A(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a', 'b', watch=True)
            def test(self):
                pass

        a = A()

        assert len(a.param.method_dependencies('test')) == 2

        class B(A):

            @param.depends('b')
            def test(self):
                pass

        b = B()

        assert len(b.param.method_dependencies('test')) == 1
        assert len(B.param._depends['watch']) == 0

    def test_param_depends_override_depends_subset_watched(self):

        class A(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            @param.depends('a', 'b', watch=True)
            def test(self):
                pass

        a = A()

        assert len(a.param.method_dependencies('test')) == 2

        class B(A):

            @param.depends('b', watch=True)
            def test(self):
                pass

        b = B()

        assert len(b.param.method_dependencies('test')) == 1
        assert len(B.param._depends['watch']) == 1
        m, _, _, deps, _ = B.param._depends['watch'][0]
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
        assert len(a.param.method_dependencies('test')) == 2

        class B(A):

            def test(self):
                pass

        b = B()
        assert len(b.param.method_dependencies('test')) == 3
        assert len(B.param._depends['watch']) == 0

    def test_param_depends_subclass_ordering(self):

        values = []

        class A(param.Parameterized):
            a = param.String()

            @param.depends('a', watch=True)
            def test(self):
                values.append(self.a)

        class B(A):

            @param.depends('a', watch=True)
            def more_test(self):
                values.append(self.a.upper())

        b = B()

        b.a = 'a'

        assert values == ['a', 'A']



class TestParamDepends:

    def setup_method(self):

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

        class AP(param.Parameterized):
            a = param.Parameter()
            b = param.Parameter()

            single_count = param.Integer()
            attr_count = param.Integer()
            single_nested_count = param.Integer()
            double_nested_count = param.Integer()
            nested_attr_count = param.Integer()
            nested_count = param.Integer()

            @param.depends('a', watch=True)
            async def single_parameter(self):
                self.single_count += 1

            @param.depends('a:constant', watch=True)
            async def constant(self):
                self.attr_count += 1

            @param.depends('b.a', watch=True)
            async def single_nested(self):
                self.single_nested_count += 1

            @param.depends('b.b.a', watch=True)
            async def double_nested(self):
                self.double_nested_count += 1

            @param.depends('b.a:constant', watch=True)
            async def nested_attribute(self):
                self.nested_attr_count += 1

            @param.depends('b.param', watch=True)
            async def nested(self):
                self.nested_count += 1


        class P2(param.Parameterized):

            @param.depends(P.param.a)
            def external_param(self, a):
                pass

        class AP2(param.Parameterized):

            @param.depends(AP.param.a)
            async def external_param(self, a):
                pass


        self.P = P
        self.AP = AP
        self.P2 = P2
        self.AP2 = AP2

    def test_param_depends_on_init(self):
        class A(param.Parameterized):

            a = param.Parameter()

            value = param.Integer()

            @param.depends('a', watch=True, on_init=True)
            def callback(self):
                self.value += 1

        a = A()
        assert a.value == 1

        a.a = True
        assert a.value == 2

    def test_param_nested_depends_value_unchanged(self):
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

    @pytest.mark.usefixtures("use_async_executor")
    def test_param_nested_depends_value_unchanged_async(self):
        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter()

            test_count = param.Integer()

            @param.depends('a.c', 'a.d', watch=True)
            async def test(self):
                self.test_count += 1

        b = B(a=A(c=1))
        b.a = A(c=1)
        assert b.test_count == 0

    def test_param_nested_at_class_definition(self):

        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter(A())

            test_count = param.Integer()

            @param.depends('a.c', 'a.d', watch=True)
            def test(self):
                self.test_count += 1

        b = B()

        b.a.c = 1
        assert b.test_count == 1

        b.a.param.update(c=2, d=1)
        assert b.test_count == 2

        b.a = A()
        assert b.test_count == 3

        B.a.c = 5
        assert b.test_count == 3

    @pytest.mark.usefixtures("use_async_executor")
    def test_param_nested_at_class_definition_async(self):

        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter(A())

            test_count = param.Integer()

            @param.depends('a.c', 'a.d', watch=True)
            async def test(self):
                self.test_count += 1

        b = B()

        b.a.c = 1
        assert b.test_count == 1

        b.a.param.update(c=2, d=1)
        assert b.test_count == 2

        b.a = A()
        assert b.test_count == 3

        B.a.c = 5
        assert b.test_count == 3

    def test_param_nested_depends_expands(self):
        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter()

            test_count = param.Integer()

            @param.depends('a.param', watch=True)
            def test(self):
                self.test_count += 1

        b = B(a=A(c=1, name='A'))
        b.a = A(c=1, name='A')
        assert b.test_count == 0

    @pytest.mark.usefixtures("use_async_executor")
    def test_param_nested_depends_expands_async(self):
        class A(param.Parameterized):

            c = param.Parameter()

            d = param.Parameter()

        class B(param.Parameterized):

            a = param.Parameter()

            test_count = param.Integer()

            @param.depends('a.param', watch=True)
            async def test(self):
                self.test_count += 1

        b = B(a=A(c=1, name='A'))
        b.a = A(c=1, name='A')
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

    @pytest.mark.usefixtures("use_async_executor")
    def test_param_depends_class_default_dynamic_async(self):

        class A(param.Parameterized):
            c = param.Parameter()

        class B(param.Parameterized):
            a = param.Parameter(A())

            nested_count = param.Integer()

            @param.depends('a.c', watch=True)
            async def nested(self):
                self.nested_count += 1

        b = B()

        b.a.c = 1
        assert b.nested_count == 1

        b.a = A()
        assert b.nested_count == 2

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_single_nested(self, class_name):
        inst = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('single_nested', intermediate=True)
        assert len(pinfos) == 0

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('single_nested', intermediate=True)
        assert len(pinfos) == 2
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo2 = pinfos[(inst.b, 'a')]
        assert pinfo2.cls is getattr(self, class_name)
        assert pinfo2.inst is inst.b
        assert pinfo2.name == 'a'
        assert pinfo2.what == 'value'

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_single_nested_initialized_no_intermediates(self, class_name):
        init_b = getattr(self, class_name)()
        inst = getattr(self, class_name)(b=init_b)
        pinfos = inst.param.method_dependencies('single_nested', intermediate=False)
        assert len(pinfos) == 1

        assert pinfos[0].inst is init_b
        assert pinfos[0].name == 'a'

        new_b = getattr(self, class_name)()
        inst.b = new_b

        pinfos = inst.param.method_dependencies('single_nested', intermediate=False)
        assert len(pinfos) == 1
        assert pinfos[0].inst is new_b
        assert pinfos[0].name == 'a'

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_single_nested_initialized_only_intermediates(self, class_name):
        init_b = getattr(self, class_name)()
        inst = getattr(self, class_name)(b=init_b)
        pinfos = inst.param.method_dependencies('single_nested', intermediate='only')
        assert len(pinfos) == 1

        assert pinfos[0].inst is inst
        assert pinfos[0].name == 'b'

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_single_nested_initialized(self, class_name):
        init_b = getattr(self, class_name)()
        inst = getattr(self, class_name)(b=init_b)
        pinfos = inst.param.method_dependencies('single_nested', intermediate=True)
        assert len(pinfos) == 2

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('single_nested', intermediate=True)
        assert len(pinfos) == 2
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        pinfo.cls is getattr(self, class_name)
        pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo2 = pinfos[(inst.b, 'a')]
        pinfo2.cls is getattr(self, class_name)
        pinfo2.inst is inst.b
        assert pinfo2.name == 'a'
        assert pinfo2.what == 'value'

        assert inst.single_nested_count == 0

        inst.b.a = 1
        assert inst.single_nested_count == 1

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
        assert inst.single_nested_count == 1

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_double_nested(self, class_name):
        inst = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('double_nested', intermediate=True)
        assert len(pinfos) == 0

        inst.b = getattr(self, class_name)(b=getattr(self, class_name)())
        pinfos = inst.param.method_dependencies('double_nested', intermediate=True)
        assert len(pinfos) == 3
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo2 = pinfos[(inst.b, 'b')]
        assert pinfo2.cls is getattr(self, class_name)
        assert pinfo2.inst is inst.b
        assert pinfo2.name == 'b'
        assert pinfo2.what == 'value'
        pinfo3 = pinfos[(inst.b.b, 'a')]
        assert pinfo3.cls is getattr(self, class_name)
        assert pinfo3.inst is inst.b.b
        assert pinfo3.name == 'a'
        assert pinfo3.what == 'value'

        assert inst.double_nested_count == 1

        inst.b.b.a = 1
        assert inst.double_nested_count == 2

        old_subobj = inst.b.b
        inst.b.b = getattr(self, class_name)(a=3)
        assert inst.double_nested_count == 3

        old_subobj.a = 4
        assert inst.double_nested_count == 3

        inst.b.b = getattr(self, class_name)(a=3)
        assert inst.double_nested_count == 3

        inst.b.b.a = 4
        assert inst.double_nested_count == 4

        inst.b.b = getattr(self, class_name)(a=3)
        assert inst.double_nested_count == 5

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_double_nested_partially_initialized(self, class_name):
        inst = getattr(self, class_name)(b=getattr(self, class_name)())
        pinfos = inst.param.method_dependencies('double_nested', intermediate=True)
        assert len(pinfos) == 2

        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls == getattr(self, class_name)
        assert pinfo.inst == inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo = pinfos[(inst.b, 'b')]
        assert pinfo.cls == getattr(self, class_name)
        assert pinfo.inst == inst.b
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'

        inst.b.b = getattr(self, class_name)()
        assert inst.double_nested_count == 1

        inst.b.b.a = 1
        assert inst.double_nested_count == 2

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_nested_attribute(self, class_name):
        inst = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested_attribute', intermediate=True)
        assert len(pinfos) == 0

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested_attribute', intermediate=True)
        assert len(pinfos) == 2
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls == getattr(self, class_name)
        assert pinfo.inst == inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo2 = pinfos[(inst.b, 'a')]
        assert pinfo2.cls == getattr(self, class_name)
        assert pinfo2.inst == inst.b
        assert pinfo2.name == 'a'
        assert pinfo2.what == 'constant'

        assert inst.nested_attr_count == 1

        inst.b.param.a.constant = True
        assert inst.nested_attr_count == 2

        new_b = getattr(self, class_name)()
        new_b.param.a.constant = True
        inst.b = new_b
        assert inst.nested_attr_count == 2

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_nested_attribute_initialized(self, class_name):
        inst = getattr(self, class_name)(b=getattr(self, class_name)())
        pinfos = inst.param.method_dependencies('nested_attribute', intermediate=True)
        assert len(pinfos) == 2

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested_attribute', intermediate=True)
        assert len(pinfos) == 2
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls == getattr(self, class_name)
        assert pinfo.inst == inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        pinfo2 = pinfos[(inst.b, 'a')]
        assert pinfo2.cls == getattr(self, class_name)
        assert pinfo2.inst == inst.b
        assert pinfo2.name == 'a'
        assert pinfo2.what == 'constant'

        assert inst.nested_attr_count == 0

        inst.b.param.a.constant = True
        assert inst.nested_attr_count == 1

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_nested(self, class_name):
        inst = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 0

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        for p in ['a', 'b', 'name', 'nested_count', 'single_count', 'attr_count']:
            pinfo2 = pinfos[(inst.b, p)]
            assert pinfo2.cls is getattr(self, class_name)
            assert pinfo2.inst is inst.b
            assert pinfo2.name == p
            assert pinfo2.what == 'value'

        assert inst.nested_count == 1

        inst.b.a = 1
        assert inst.nested_count == 3

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_nested_initialized(self, class_name):
        init_b = getattr(self, class_name)()
        inst = getattr(self, class_name)(b=init_b)
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10

        inst.b = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        for p in ['a', 'b', 'name', 'nested_count', 'single_count', 'attr_count']:
            pinfo2 = pinfos[(inst.b, p)]
            assert pinfo2.cls is getattr(self, class_name)
            assert pinfo2.inst is inst.b
            assert pinfo2.name == p
            assert pinfo2.what == 'value'

        assert inst.single_nested_count == 0

        inst.b.a = 1
        assert inst.single_nested_count == 1

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
        assert inst.single_nested_count == 1

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends_dynamic_nested_changed_value(self, class_name):
        init_b = getattr(self, class_name)(a=1)
        inst = getattr(self, class_name)(b=init_b)
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10

        inst.b = getattr(self, class_name)(a=2)
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        for p in ['a', 'b', 'name', 'nested_count', 'single_count', 'attr_count']:
            pinfo2 = pinfos[(inst.b, p)]
            assert pinfo2.cls is getattr(self, class_name)
            assert pinfo2.inst is inst.b
            assert pinfo2.name == p
            assert pinfo2.what == 'value'

        assert inst.single_nested_count == 1

        inst.b.a = 1
        assert inst.single_nested_count == 2

        # Ensure watcher on initial value does not trigger event
        init_b.a = 2
        assert inst.single_nested_count == 2

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_instance_depends(self, class_name):
        p = getattr(self, class_name)()
        pinfos = p.param.method_dependencies('single_parameter')
        assert len(pinfos) == 1
        pinfo = pinfos[0]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is p
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

        p.a = 1
        assert p.single_count == 1

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_class_depends(self, class_name):
        pinfos = getattr(self, class_name).param.method_dependencies('single_parameter')
        assert len(pinfos) == 1
        pinfo = pinfos[0]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is None
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_class_depends_constant(self, class_name):
        pinfos = getattr(self, class_name).param.method_dependencies('constant')
        assert len(pinfos) == 1
        pinfo = pinfos[0]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is None
        assert pinfo.name == 'a'
        assert pinfo.what == 'constant'

    @pytest.mark.parametrize('class_name', ['P', 'AP'], indirect=True)
    def test_param_inst_depends_nested(self, class_name):
        inst = getattr(self, class_name)(b=getattr(self, class_name)())
        pinfos = inst.param.method_dependencies('nested')
        assert len(pinfos) == 10
        pinfos = {(pi.inst, pi.name): pi for pi in pinfos}
        pinfo = pinfos[(inst, 'b')]
        assert pinfo.cls is getattr(self, class_name)
        assert pinfo.inst is inst
        assert pinfo.name == 'b'
        assert pinfo.what == 'value'
        for p in ['name', 'a', 'b']:
            info = pinfos[(inst.b, p)]
            assert info.name == p
            assert info.inst is inst.b

    @pytest.mark.parametrize('class_name', ['P2', 'AP2'], indirect=True)
    def test_param_external_param_instance(self, class_name):
        inst = getattr(self, class_name)()
        pinfos = inst.param.method_dependencies('external_param')
        pinfo = pinfos[0]
        assert pinfo.cls is getattr(self, class_name[:-1])
        assert pinfo.inst is None
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

    @pytest.mark.usefixtures('use_async_executor')
    def test_async(self):
        class P(param.Parameterized):
            a = param.Parameter()
            single_count = param.Integer()

            @param.depends('a', watch=True)
            async def single_parameter(self):
                self.single_count += 1

        inst = P()
        inst.a = 'test'
        assert inst.single_count == 1

    def test_param_depends_on_parameterized_attribute(self):
        # Issue https://github.com/holoviz/param/issues/635

        called = []

        class Sub(param.Parameterized):
            s = param.String()

        class P(param.Parameterized):
            test_param = param.Parameter()

            def __init__(self, **params):
                self._sub = Sub()
                super().__init__(**params)

            @param.depends('_sub.s', watch=True)
            def cb(self):
                called.append(1)

        p = P()
        p.test_param = 'modified'

        assert not called

    @pytest.mark.usefixtures('use_async_executor')
    def test_param_depends_on_parameterized_attribute_async(self):
        # Issue https://github.com/holoviz/param/issues/635

        called = []

        class Sub(param.Parameterized):
            s = param.String()

        class P(param.Parameterized):
            test_param = param.Parameter()

            def __init__(self, **params):
                self._sub = Sub()
                super().__init__(**params)

            @param.depends('_sub.s', watch=True)
            async def cb(self):
                called.append(1)

        p = P()
        p.test_param = 'modified'

        assert not called

    def test_param_depends_on_method(self):

        method_count = 0

        class A(param.Parameterized):
            a = param.Integer()

            @param.depends('a', watch=True)
            def method1(self):
                pass

            @param.depends('method1', watch=True)
            def method2(self):
                nonlocal method_count
                method_count += 1

        inst = A()
        pinfos = inst.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is A
        assert pinfo.inst is inst
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

        inst.a = 2
        assert method_count == 1

    @pytest.mark.usefixtures('use_async_executor')
    def test_param_depends_on_method_async(self):

        method_count = 0

        class A(param.Parameterized):
            a = param.Integer()

            @param.depends('a', watch=True)
            async def method1(self):
                pass

            @param.depends('method1', watch=True)
            async def method2(self):
                nonlocal method_count
                method_count += 1

        inst = A()
        pinfos = inst.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is A
        assert pinfo.inst is inst
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

        inst.a = 2
        assert method_count == 1

    def test_param_depends_on_method_subparameter(self):

        method1_count = 0
        method2_count = 0

        class Sub(param.Parameterized):
            a = param.Integer()

            @param.depends('a')
            def method1(self):
                nonlocal method1_count
                method1_count += 1

        class Main(param.Parameterized):
            sub = param.Parameter()

            @param.depends('sub.method1', watch=True)
            def method2(self):
                nonlocal method2_count
                method2_count += 1

        sub = Sub()
        main = Main(sub=sub)
        pinfos = main.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is Sub
        assert pinfo.inst is sub
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

        sub.a = 2
        assert method1_count == 0
        assert method2_count == 1

    @pytest.mark.usefixtures('use_async_executor')
    def test_param_depends_on_method_subparameter_async(self):

        method1_count = 0
        method2_count = 0

        class Sub(param.Parameterized):
            a = param.Integer()

            @param.depends('a')
            async def method1(self):
                nonlocal method1_count
                method1_count += 1

        class Main(param.Parameterized):
            sub = param.Parameter()

            @param.depends('sub.method1', watch=True)
            async def method2(self):
                nonlocal method2_count
                method2_count += 1

        sub = Sub()
        main = Main(sub=sub)
        pinfos = main.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is Sub
        assert pinfo.inst is sub
        assert pinfo.name == 'a'
        assert pinfo.what == 'value'

        sub.a = 2
        assert method1_count == 0
        assert method2_count == 1

    def test_param_depends_on_method_subparameter_after_init(self):
        # Setup inspired from https://github.com/holoviz/param/issues/764

        method1_count = 0
        method2_count = 0

        class Controls(param.Parameterized):

            explorer = param.Parameter()

            @param.depends('explorer.method1', watch=True)
            def method2(self):
                nonlocal method2_count
                method2_count += 1


        class Explorer(param.Parameterized):

            controls = param.Parameter()

            x = param.Selector(objects=['a', 'b'])

            def __init__(self, **params):
                super().__init__(**params)
                self.controls = Controls(explorer=self)

            @param.depends('x')
            def method1(self):
                nonlocal method1_count
                method1_count += 1

        explorer = Explorer()

        pinfos = explorer.controls.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is Explorer
        assert pinfo.inst is explorer
        assert pinfo.name == 'x'
        assert pinfo.what == 'value'

        explorer.x = 'b'

        assert method1_count == 0
        assert method2_count == 1

    @pytest.mark.usefixtures('use_async_executor')
    def test_param_depends_on_method_subparameter_after_init_async(self):
        # Setup inspired from https://github.com/holoviz/param/issues/764

        method1_count = 0
        method2_count = 0

        class Controls(param.Parameterized):

            explorer = param.Parameter()

            @param.depends('explorer.method1', watch=True)
            async def method2(self):
                nonlocal method2_count
                method2_count += 1


        class Explorer(param.Parameterized):

            controls = param.Parameter()

            x = param.Selector(objects=['a', 'b'])

            def __init__(self, **params):
                super().__init__(**params)
                self.controls = Controls(explorer=self)

            @param.depends('x')
            async def method1(self):
                nonlocal method1_count
                method1_count += 1

        explorer = Explorer()

        pinfos = explorer.controls.param.method_dependencies('method2')
        assert len(pinfos) == 1

        pinfo = pinfos[0]
        assert pinfo.cls is Explorer
        assert pinfo.inst is explorer
        assert pinfo.name == 'x'
        assert pinfo.what == 'value'

        explorer.x = 'b'

        assert method1_count == 0
        assert method2_count == 1

    def test_param_depends_class_with_len(self):
        # https://github.com/holoviz/param/issues/747

        count = 0

        class P(param.Parameterized):
            x = param.Parameter()

            @param.depends('x', watch=True)
            def debug(self):
                nonlocal count
                count += 1

            # bool(P()) evaluates to False
            def __len__(self):
                return 0

        p = P()
        p.x = 1
        assert count == 1


class TestParamDependsFunction:

    def setup_method(self):
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
            'watch': False,
            'on_init': False
        }
        assert function._dinfo == dependencies

    def test_param_depends_function_class_params(self):
        p = self.P

        @param.depends(p.param.a, c=p.param.b)
        def function(value, c):
            pass

        dependencies = {
            'dependencies': (p.param.a,),
            'kw': {'c': p.param.b},
            'watch': False,
            'on_init': False
        }
        assert function._dinfo == dependencies

    def test_param_depends_function_instance_params_watch(self):
        p = self.P(a=1, b=2)

        d = []

        @param.depends(p.param.a, c=p.param.b, watch=True)
        def function(value, c):
            d.append(value+c)

        p.a = 2
        assert d == [4]
        p.b = 3
        assert d == [4, 5]

    def test_param_depends_function_class_params_watch(self):
        p = self.P
        p.a = 1
        p.b = 2

        d = []

        @param.depends(p.param.a, c=p.param.b, watch=True)
        def function(value, c):
            d.append(value+c)

        p.a = 2
        assert d == [4]
        p.b = 3
        assert d == [4, 5]

    @pytest.mark.usefixtures('use_async_executor')
    def test_async(self):
        p = self.P(a=1)

        d = []

        @param.depends(p.param.a, watch=True)
        async def function(value):
            d.append(value)

        p.a = 2

        assert d == [2]


def test_misspelled_parameter_in_depends():
    class Example(param.Parameterized):
        xlim = param.Range((0, 10), bounds=(0, 100))

        @param.depends("tlim")  # <- Misspelled xlim
        def test(self):
            return True

    example = Example()
    with pytest.raises(AttributeError, match="Attribute 'tlim' could not be resolved on"):
        # Simulating: pn.panel(example.test)
        example.param.method_dependencies(example.test.__name__)


def test_misspelled_parameter_in_depends_watch():
    with pytest.raises(AttributeError, match="Attribute 'tlim' could not be resolved on"):
        class Example(param.Parameterized):
            xlim = param.Range((0, 10), bounds=(0, 100))

            @param.depends("tlim", watch=True)  # <- Misspelled xlim
            def test(self):
                return True
