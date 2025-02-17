"""Unit test for Parameterized."""
import inspect
import re
import unittest

import param
import numbergen

from .utils import MockLoggingHandler

# CEBALERT: not anything like a complete test of Parameterized!

import pytest

import random

from param import parameterized, Parameter
from param.parameterized import (
    ParamOverrides,
    Undefined,
    default_label_formatter,
    no_instance_params,
    shared_parameters,
)

class _SomeRandomNumbers:
    def __call__(self):
        return random.random()

class TestPO(param.Parameterized):
    __test__ = False

    inst = param.Parameter(default=[1,2,3],instantiate=True)
    notinst = param.Parameter(default=[1,2,3],instantiate=False, per_instance=False)
    const = param.Parameter(default=1,constant=True)
    ro = param.Parameter(default="Hello",readonly=True)
    ro2 = param.Parameter(default=object(),readonly=True,instantiate=True)
    ro_label = param.Parameter(default=object(), label='Ro Label')
    ro_format = param.Parameter(default=object())

    dyn = param.Dynamic(default=1)

class TestPOValidation(param.Parameterized):
    __test__ = False

    value = param.Number(default=2, bounds=(0, 4))

@no_instance_params
class TestPONoInstance(TestPO):
    __test__ = False
    pass

class AnotherTestPO(param.Parameterized):
    instPO = param.Parameter(default=TestPO(),instantiate=True)
    notinstPO = param.Parameter(default=TestPO(),instantiate=False)

class TestAbstractPO(param.Parameterized):
    __test__ = False

    __abstract = True

class _AnotherAbstractPO(param.Parameterized):
    __abstract = True

class TestParamInstantiation(AnotherTestPO):
    __test__ = False

    instPO = param.Parameter(default=AnotherTestPO(),instantiate=False)

class TestParameterized(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        log = param.parameterized.get_logger()
        cls.log_handler = MockLoggingHandler(level='DEBUG')
        log.addHandler(cls.log_handler)

    def test_name_default_to_class_name(self):
        assert TestPO.name == 'TestPO'

    def test_name_default_to_subclass_name(self):
        class Foo(TestPO):
            pass

        assert Foo.name == 'Foo'

    def test_name_as_argument(self):
        testpo = TestPO(name='custom')

        assert testpo.name == 'custom'

    def test_name_instance_generated(self):
        testpo = TestPO()

        match = re.fullmatch(r'TestPO\w{5}', testpo.name)
        assert match is not None

    def test_name_instance_generated_subclass(self):
        class Foo(TestPO):
            pass

        foo = Foo()

        match = re.fullmatch(r'Foo\w{5}', foo.name)
        assert match is not None

    def test_name_instance_generated_class_name_reset(self):
        class P(param.Parameterized):
            pass

        P.name = 'Other'

        assert P.name == 'Other'

        p = P()

        assert p.name == 'Other'

    def test_parameter_name_fixed(self):
        testpo = TestPO()

        with pytest.raises(AttributeError):
            testpo.param.const.name = 'notconst'

    def test_name_overriden(self):
        class P(param.Parameterized):
            name = param.String(default='other')

        assert P.name == 'other'

        p = P()

        assert p.name == 'other'

    def test_name_overriden_without_default(self):
        class A(param.Parameterized):
            pass
        class B(param.Parameterized):
            name = param.String(doc='some help')

        class C(B):
            pass

        assert B.name == 'B'
        assert B.param.name.doc == 'some help'
        assert C.name == 'C'
        assert C.param.name.doc == 'some help'

    def test_name_overriden_constructor(self):
        class P(param.Parameterized):
            name = param.String(default='other')

        p = P(name='another')

        assert p.name == 'another'

    def test_name_overriden_subclasses(self):
        class P(param.Parameterized):
            name = param.String(default='other')

        class Q(P):
            pass

        class R(Q):
            name = param.String(default='yetanother')

        assert Q.name == 'other'

        q1 = Q()

        assert q1.name == 'other'

        q2 = Q(name='another')

        assert q2.name == 'another'

        assert R.name == 'yetanother'

        r1 = R()

        assert r1.name == 'yetanother'

        r2 = R(name='last')

        assert r2.name == 'last'


    def test_name_overriden_subclasses_name_set(self):
        class P(param.Parameterized):
            name = param.String(default='other')

        class Q(P):
            pass

        P.name = 'another'

        assert Q.name == 'another'

        Q.name = 'yetanother'

        assert Q.name == 'yetanother'

        q = Q()

        assert q.name == 'yetanother'

    def test_name_overriden_error_not_String(self):

        msg = "Parameterized class 'P' cannot override the 'name' Parameter " \
              "with type <class 'str'>. Overriding 'name' is only allowed with " \
              "a 'String' Parameter."

        with pytest.raises(TypeError, match=msg):
            class P(param.Parameterized):
                name = 'other'

        msg = "Parameterized class 'P' cannot override the 'name' Parameter " \
              "with type <class 'param.parameterized.Parameter'>. Overriding 'name' " \
              "is only allowed with a 'String' Parameter."

        with pytest.raises(TypeError, match=msg):
            class P(param.Parameterized):  # noqa
                name = param.Parameter(default='other')

    def test_name_complex_hierarchy(self):
        class Mixin1: pass
        class Mixin2: pass
        class Mixin3(param.Parameterized): pass

        class A(param.Parameterized, Mixin1): pass
        class B(A): pass
        class C(B, Mixin2): pass
        class D(C, Mixin3): pass

        assert A.name == 'A'
        assert B.name == 'B'
        assert C.name == 'C'
        assert D.name == 'D'

    def test_name_overriden_complex_hierarchy(self):
        class Mixin1: pass
        class Mixin2: pass
        class Mixin3(param.Parameterized): pass

        class A(param.Parameterized, Mixin1): pass
        class B(A):
            name = param.String(default='other')

        class C(B, Mixin2):
            name = param.String(default='another')

        class D(C, Mixin3): pass

        assert A.name == 'A'
        assert B.name == 'other'
        assert C.name == 'another'
        assert D.name == 'another'

    def test_name_overriden_multiple(self):
        class A(param.Parameterized):
            name = param.String(default='AA')
        class B(param.Parameterized):
            name = param.String(default='BB')

        class C(A, B): pass

        assert C.name == 'AA'

    def test_constant_parameter_modify_class_before(self):
        """
        Test you can set on class and the new default is picked up
        by new instances.
        """
        TestPO.const=9
        testpo = TestPO()
        self.assertEqual(testpo.const,9)

    def test_constant_parameter_modify_class_after_init(self):
        """
        Test that setting the value on the class doesn't update the instance value
        even when the instance value hasn't yet been set.
        """
        oobj = []
        class P(param.Parameterized):
            x = param.Parameter(default=oobj, constant=True)

        p1 = P()

        P.x = nobj = [0]
        assert P.x is nobj
        assert p1.x == oobj
        assert p1.x is oobj

        p2 = P()
        assert p2.x == nobj
        assert p2.x is nobj

    def test_constant_parameter_after_init(self):
        """Test that you can't set a constant parameter after construction."""
        testpo = TestPO(const=17)
        self.assertEqual(testpo.const,17)
        self.assertRaises(TypeError,setattr,testpo,'const',10)

    def test_constant_parameter(self):
        """Test that you can't set a constant parameter after construction."""
        testpo = TestPO(const=17)
        self.assertEqual(testpo.const,17)
        self.assertRaises(TypeError,setattr,testpo,'const',10)

        # check you can set on class
        TestPO.const=9
        testpo = TestPO()
        self.assertEqual(testpo.const,9)

    def test_readonly_parameter(self):
        """Test that you can't set a read-only parameter on construction or as an attribute."""
        testpo = TestPO()
        self.assertEqual(testpo.ro,"Hello")

        with self.assertRaises(TypeError):
            t = TestPO(ro=20)

        t=TestPO()
        self.assertRaises(TypeError,setattr,t,'ro',10)

        # check you cannot set on class
        self.assertRaises(TypeError,setattr,TestPO,'ro',5)

        self.assertEqual(testpo.param['ro'].constant,True)

        # check that instantiate was ignored for readonly
        self.assertEqual(testpo.param['ro2'].instantiate,False)

    def test_basic_instantiation(self):
        """Check that instantiated parameters are copied into objects."""
        testpo = TestPO()

        self.assertEqual(testpo.inst,TestPO.inst)
        self.assertEqual(testpo.notinst,TestPO.notinst)

        TestPO.inst[1]=7
        TestPO.notinst[1]=7

        self.assertEqual(testpo.notinst,[1,7,3])
        self.assertEqual(testpo.inst,[1,2,3])

    def test_more_instantiation(self):
        """Show that objects in instantiated Parameters can still share data."""
        anothertestpo = AnotherTestPO()

        ### CB: AnotherTestPO.instPO is instantiated, but
        ### TestPO.notinst is not instantiated - so notinst is still
        ### shared, even by instantiated parameters of AnotherTestPO.
        ### Seems like this behavior of Parameterized could be
        ### confusing, so maybe mention it in documentation somewhere.
        TestPO.notinst[1]=7
        # (if you thought your instPO was completely an independent object, you
        # might be expecting [1,2,3] here)
        self.assertEqual(anothertestpo.instPO.notinst,[1,7,3])

    def test_instantiation_inheritance(self):
        """Check that instantiate=True is always inherited (SF.net #2483932)."""
        t = TestParamInstantiation()
        assert t.param['instPO'].instantiate is True
        assert isinstance(t.instPO,AnotherTestPO)

    def test_abstract_class(self):
        """Check that a class declared abstract actually shows up as abstract."""
        self.assertEqual(TestAbstractPO.abstract, True)
        self.assertEqual(_AnotherAbstractPO.abstract, True)
        self.assertEqual(TestPO.abstract, False)

    def test_override_class_param_validation(self):
        test = TestPOValidation()
        test.param.value.bounds = (0, 3)
        with self.assertRaises(ValueError):
            test.value = 4
        TestPOValidation.value = 4

    def test_remove_class_param_validation(self):
        test = TestPOValidation()
        test.param.value.bounds = None
        test.value = 20
        with self.assertRaises(ValueError):
            TestPOValidation.value = 10

    def test_instantiation_set_before_super(self):
        count = 0
        class P(param.Parameterized):

            x = param.Parameter(0)

            def __init__(self, x=1):
                self.x = x
                super().__init__()

            @param.depends('x', watch=True)
            def cb(self):
                nonlocal count
                count += 1

        p = P()

        assert p.x == 1
        assert count == 0

    def test_instantiation_set_before_super_contrived(self):
        # https://github.com/holoviz/param/pull/790#discussion_r1263483293
        class P(param.Parameterized):

            value = param.String(default="A")

            def __init__(self, depth=0):
                self.value = 'B'
                if depth < 2:
                    self.sub = P(depth+1)
                super().__init__()

        p = P()

        assert p.value == 'B'
        assert p.sub.value == 'B'

    def test_instantiation_set_before_super_subclass(self):
        # Inspired by a HoloViews use case (GenericElementPlot, GenericOverlayPlot)
        class A(param.Parameterized):

            def __init__(self, batched=False, **params):
                self.batched = batched
                super().__init__(**params)

        class B(A):

            batched = param.Boolean()

            def __init__(self, batched=True, **params):
                super().__init__(batched=batched, **params)

        a = A()
        assert a.batched is False

        # When b is instantiated the `batched` Parameter of B is set before
        # Parameterized.__init__ is called.
        b = B()
        assert b.batched is True

    def test_instantiation_param_objects_before_super_subclass(self):
        # Testing https://github.com/holoviz/param/pull/420


        class P(param.Parameterized):
            x = param.Parameter()

            def __init__(self):
                objs = self.param.objects(instance='existing')
                assert isinstance(objs, dict)
                super().__init__()

        P()

    @pytest.mark.xfail(
        raises=AttributeError,
        reason='Behavior not defined when setting a constant parameter before calling super()',
    )
    def test_instantiation_set_before_super_constant(self):
        count = 0
        class P(param.Parameterized):

            x = param.Parameter(0, constant=True)

            def __init__(self, x=1):
                self.x = x
                super().__init__()

            @param.depends('x', watch=True)
            def cb(self):
                nonlocal count
                count += 1

        p = P()

        assert p.x == 1
        assert count == 0

    def test_instantiation_set_before_super_readonly(self):
        class P(param.Parameterized):

            x = param.Parameter(0, readonly=True)

            def __init__(self, x=1):
                self.x = x
                super().__init__()

        with pytest.raises(TypeError, match="Read-only parameter 'x' cannot be modified"):
            P()

    def test_parameter_constant_iadd_allowed(self):
        # Testing https://github.com/holoviz/param/pull/400
        class P(param.Parameterized):

            list = param.List([], constant=True)

        p = P()
        p.list += [1, 2, 3]

        # Just to make sure that normal setting is still forbidden
        with pytest.raises(TypeError, match="Constant parameter 'list' cannot be modified"):
            p.list = [0]

    def test_parameter_constant_same_notallowed(self):
        L = [0, 1]
        class P(param.Parameterized):

            list = param.List(L, constant=True)

        p = P()

        # instantiate is set to true internally so a deepcopy is made of L,
        # it's no longer the same object
        with pytest.raises(TypeError, match="Constant parameter 'list' cannot be modified"):
            p.list = L

    def test_values(self):
        """Basic tests of params() method."""
        # CB: test not so good because it requires changes if params
        # of PO are changed
        assert 'name' in param.Parameterized.param.values()
        assert len(param.Parameterized.param.values()) in [1,2]

        ## check for bug where subclass Parameters were not showing up
        ## if values() already called on a super class.
        assert 'inst' in TestPO.param.values()
        assert 'notinst' in TestPO.param.values()

    def test_values_name_ignored_for_instances_and_onlychanged(self):
        default_inst = param.Parameterized()
        assert 'Parameterized' in default_inst.name
        # name ignored when automatically computed (behavior inherited from all_equal)
        assert 'name' not in default_inst.param.values(onlychanged=True)
        # name not ignored when set
        assert param.Parameterized(name='foo').param.values(onlychanged=True)['name'] == 'foo'

    def test_param_iterator(self):
        self.assertEqual(set(TestPO.param), {'name', 'inst', 'notinst', 'const', 'dyn',
                                             'ro', 'ro2', 'ro_label', 'ro_format'})

    def test_param_contains(self):
        for p in ['name', 'inst', 'notinst', 'const', 'dyn', 'ro', 'ro2']:
            self.assertIn(p, TestPO.param)

    def test_class_param_objects(self):
        objects = TestPO.param.objects()

        self.assertEqual(set(objects),
                         {'name', 'inst', 'notinst', 'const', 'dyn',
                          'ro', 'ro2', 'ro_label', 'ro_format'})

        # Check caching
        assert TestPO.param.objects() is objects

    def test_instance_param_objects(self):
        inst = TestPO()
        objects = inst.param.objects()

        for p, obj in objects.items():
            if p == 'notinst':
                assert obj is TestPO.param[p]
            else:
                assert obj is not TestPO.param[p]

    def test_instance_param_objects_set_to_false(self):
        inst = TestPO()
        objects = inst.param.objects(instance=False)

        for p, obj in objects.items():
            assert obj is TestPO.param[p]

    def test_instance_param_objects_set_to_current(self):
        inst = TestPO()
        inst_param = inst.param.inst
        objects = inst.param.objects(instance='existing')

        for p, obj in objects.items():
            if p == 'inst':
                assert obj is inst_param
            else:
                assert obj is TestPO.param[p]

    def test_param_error_unsafe_ops_before_initialized(self):
        class P(param.Parameterized):

            x = param.Parameter()

            def __init__(self, **params):
                with pytest.raises(
                    RuntimeError,
                    match=re.escape(
                        'Looking up instance Parameter objects (`.param.objects()`) until '
                        'the Parameterized instance has been fully initialized is not allowed. '
                        'Ensure you have called `super().__init__(**params)` in your Parameterized '
                        'constructor before trying to access instance Parameter objects, or '
                        'looking up the class Parameter objects with `.param.objects(instance=False)` '
                        'may be enough for your use case.',
                    )
                ):
                    self.param.objects()
        P()

    def test_instance_param_getitem(self):
        test = TestPO()
        assert test.param['inst'] is not TestPO.param['inst']

    def test_instance_param_getitem_not_per_instance(self):
        test = TestPO()
        assert test.param['notinst'] is TestPO.param['notinst']

    def test_instance_param_getitem_no_instance_params(self):
        test = TestPONoInstance()
        assert test.param['inst'] is TestPO.param['inst']

    def test_instance_param_getattr(self):
        test = TestPO()
        assert test.param.inst is not TestPO.param.inst

        # Assert no deep copy
        assert test.param.inst.default is TestPO.param.inst.default

    def test_pprint_instance_params(self):
        # Ensure .param.pprint does not make instance parameter copies
        test = TestPO()
        test.param.pprint()
        for p, obj in TestPO.param.objects('current').items():
            assert obj is TestPO.param[p]

    def test_update_instance_params(self):
        # Ensure update does not make instance parameter copies
        test = TestPO()
        test.param.update(inst=3)
        for p, obj in TestPO.param.objects('current').items():
            assert obj is TestPO.param[p]

    def test_values_instance_params(self):
        # Ensure values does not make instance parameter copies
        test = TestPO()
        test.param.values()
        for p, obj in TestPO.param.objects('current').items():
            assert obj is TestPO.param[p]

    def test_state_saving(self):
        t = TestPO(dyn=_SomeRandomNumbers())
        g = t.param.get_value_generator('dyn')
        g._Dynamic_time_fn=None
        assert t.dyn!=t.dyn
        orig = t.dyn
        t.param._state_push()
        t.dyn
        assert t.param.inspect_value('dyn')!=orig
        t.param._state_pop()
        assert t.param.inspect_value('dyn')==orig

    def test_label(self):
        t = TestPO()
        assert t.param['ro_label'].label == 'Ro Label'

    def test_label_set(self):
        t = TestPO()
        assert t.param['ro_label'].label == 'Ro Label'
        t.param['ro_label'].label = 'Ro relabeled'
        assert t.param['ro_label'].label == 'Ro relabeled'

    def test_label_default_format(self):
        t = TestPO()
        assert t.param['ro_format'].label == 'Ro format'

    def test_label_custom_format(self):
        param.parameterized.label_formatter = default_label_formatter.instance(capitalize=False)
        t = TestPO()
        assert t.param['ro_format'].label == 'ro format'
        param.parameterized.label_formatter = default_label_formatter

    def test_label_constant_format(self):
        param.parameterized.label_formatter = lambda x: 'Foo'
        t = TestPO()
        assert t.param['ro_format'].label == 'Foo'
        param.parameterized.label_formatter = default_label_formatter

    def test_error_if_non_param_in_constructor(self):
        msg = "TestPO.__init__() got an unexpected keyword argument 'not_a_param'"
        with pytest.raises(TypeError, match=re.escape(msg)):
            TestPO(not_a_param=2)

    def test_update_class(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        P.param.update(x=10)

        assert P.x == p.x == 10

    def test_update_context_class(self):
        class P(param.Parameterized):
            x = param.Parameter(10)

        p = P()

        with P.param.update(x=20):
            assert P.x == p.x == 20

        assert P.x == p.x == 10

    def test_update_class_watcher(self):
        class P(param.Parameterized):
            x = param.Parameter()

        events = []
        P.param.watch(events.append, 'x')

        P.param.update(x=10)

        assert len(events) == 1
        assert events[0].name == 'x' and events[0].new == 10

    def test_update_context_class_watcher(self):
        class P(param.Parameterized):
            x = param.Parameter(0)

        events = []
        P.param.watch(events.append, 'x')

        with P.param.update(x=20):
            pass

        assert len(events) == 2
        assert events[0].name == 'x' and events[0].new == 20
        assert events[1].name == 'x' and events[1].new == 0

    def test_update_instance_watcher(self):
        class P(param.Parameterized):
            x = param.Parameter()

        p = P()

        events = []
        p.param.watch(events.append, 'x')

        p.param.update(x=10)

        assert len(events) == 1
        assert events[0].name == 'x' and events[0].new == 10

    def test_update_context_instance_watcher(self):
        class P(param.Parameterized):
            x = param.Parameter(0)

        p = P()

        events = []
        p.param.watch(events.append, 'x')

        with p.param.update(x=20):
            pass

        assert len(events) == 2
        assert events[0].name == 'x' and events[0].new == 20
        assert events[1].name == 'x' and events[1].new == 0

    def test_update_error_not_param_class(self):
        with pytest.raises(ValueError, match="'not_a_param' is not a parameter of TestPO"):
            TestPO.param.update(not_a_param=1)

    def test_update_error_not_param_instance(self):
        t = TestPO(inst='foo')
        with pytest.raises(ValueError, match="'not_a_param' is not a parameter of TestPO"):
            t.param.update(not_a_param=1)

    def test_update_context_error_not_param_class(self):
        with pytest.raises(ValueError, match="'not_a_param' is not a parameter of TestPO"):
            with TestPO.param.update(not_a_param=1):
                pass

    def test_update_context_error_not_param_instance(self):
        t = TestPO(inst='foo')
        with pytest.raises(ValueError, match="'not_a_param' is not a parameter of TestPO"):
            with t.param.update(not_a_param=1):
                pass

    def test_update_error_while_updating(self):
        class P(param.Parameterized):
            x = param.Parameter(0, readonly=True)

        with pytest.raises(TypeError):
            P.param.update(x=1)

        assert P.x == 0

        with pytest.raises(TypeError):
            with P.param.update(x=1):
                pass

        assert P.x == 0

        p = P()

        with pytest.raises(TypeError):
            p.param.update(x=1)

        assert p.x == 0

        with pytest.raises(TypeError):
            with p.param.update(x=1):
                pass

        assert p.x == 0

    def test_update_dict_and_kwargs_instance(self):
        t = TestPO(inst='foo', notinst=0)
        t.param.update(dict(notinst=1, inst='bar'), notinst=2)
        assert t.notinst == 2
        assert t.inst == 'bar'

    def test_update_context_dict_and_kwargs_instance(self):
        t = TestPO(inst='foo', notinst=0)
        with t.param.update(dict(notinst=1, inst='bar'), notinst=2):
            assert t.notinst == 2
            assert t.inst == 'bar'
        assert t.notinst == 0
        assert t.inst == 'foo'

    def test_update_context_single_parameter(self):
        t = TestPO(inst='foo')
        with t.param.update(inst='bar'):
            assert t.inst == 'bar'
        assert t.inst == 'foo'

    def test_update_context_does_not_set_other_params(self):
        t = TestPO(inst='foo')
        events = []
        t.param.watch(events.append, list(t.param), onlychanged=False)
        with t.param.update(inst='bar'):
            pass
        assert len(events) == 2
        assert all(e.name == 'inst' for e in events)

    def test_update_context_multi_parameter(self):
        t = TestPO(inst='foo', notinst=1)
        with t.param.update(inst='bar', notinst=2):
            assert t.inst == 'bar'
            assert t.notinst == 2
        assert t.inst == 'foo'
        assert t.notinst == 1

    def test_constant_readonly_parameterized(self):
        class ParamClass(param.Parameterized):
            x = param.Number()

        pc1 = ParamClass(name="FOO1")
        pc2 = ParamClass(name="FOO2")

        class P(param.Parameterized):
            ro = param.Parameter(pc1, constant=True)
            const = param.Parameter(pc2, readonly=True)
            ro_i = param.Parameter(pc1, constant=True, instantiate=True)
            const_i = param.Parameter(pc2, readonly=True, instantiate=True)

        p = P()

        assert p.ro.name == 'FOO1'
        assert p.const.name == 'FOO2'
        assert p.ro_i.name.startswith('ParamClass0')
        assert p.const_i.name == 'FOO2'


class some_fn(param.ParameterizedFunction):
    __test__ = False

    num_phase = param.Number(18)
    frequencies = param.List([99])
    scale = param.Number(0.3)

    def __call__(self,**params_to_override):
        params = parameterized.ParamOverrides(self,params_to_override)
        num_phase = params['num_phase']
        frequencies = params['frequencies']
        scale = params['scale']
        return scale,num_phase,frequencies

instance = some_fn.instance()

class TestParameterizedFunction(unittest.TestCase):

    def _basic_tests(self,fn):
        self.assertEqual(fn(),(0.3,18,[99]))
        self.assertEqual(fn(frequencies=[1,2,3]),(0.3,18,[1,2,3]))
        self.assertEqual(fn(),(0.3,18,[99]))

        fn.frequencies=[10,20,30]
        self.assertEqual(fn(frequencies=[1,2,3]),(0.3,18,[1,2,3]))
        self.assertEqual(fn(),(0.3,18,[10,20,30]))

    def test_parameterized_function(self):
        self._basic_tests(some_fn)

    def test_parameterized_function_instance(self):
        self._basic_tests(instance)

    def test_pickle_instance(self):
        import pickle
        s = pickle.dumps(instance)
        instance.scale=0.8
        i = pickle.loads(s)
        self.assertEqual(i(),(0.3,18,[10,20,30]))


class TestPO1(param.Parameterized):
    __test__ = False

    x = param.Number(default=numbergen.UniformRandom(lbound=-1,ubound=1,seed=1),bounds=(-1,1))
    y = param.Number(default=1,bounds=(-1,1))

class TestNumberParameter(unittest.TestCase):

    def test_outside_bounds(self):
        t1 = TestPO1()
        # Test bounds (non-dynamic number)
        try:
            t1.y = 10
        except ValueError:
            pass
        else:
            assert False, "Should raise ValueError."

    def test_outside_bounds_numbergen(self):
        t1 = TestPO1()
        # Test bounds (dynamic number)
        t1.x = numbergen.UniformRandom(lbound=2,ubound=3)  # bounds not checked on set
        try:
            t1.x
        except ValueError:
            pass
        else:
            assert False, "Should raise ValueError."


class TestStringParameter(unittest.TestCase):

    def setUp(self):
        super().setUp()

        class TestString(param.Parameterized):
            a = param.String()
            b = param.String(default='',allow_None=True)
            c = param.String(default=None)

        self._TestString = TestString

    def test_handling_of_None(self):
        t = self._TestString()

        with self.assertRaises(ValueError):
            t.a = None

        t.b = None

        assert t.c is None


class TestParameterizedUtilities(unittest.TestCase):

    def setUp(self):
        super().setUp()


    def test_default_label_formatter(self):
        assert default_label_formatter('a_b_C') == 'A b C'


    def test_default_label_formatter_not_capitalized(self):
        assert default_label_formatter.instance(capitalize=False)('a_b_C') == 'a b C'


    def test_default_label_formatter_not_replace_underscores(self):
        assert default_label_formatter.instance(replace_underscores=False)('a_b_C') == 'A_b_C'
    def test_default_label_formatter_overrides(self):
        assert default_label_formatter.instance(overrides={'a': 'b'})('a') == 'b'

class TestParamOverrides(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.po = param.Parameterized(name='A')

    def test_init_name(self):
        self.assertEqual(self.po.name, 'A')

    def test_simple_override(self):
        overrides = ParamOverrides(self.po,{'name':'B'})
        self.assertEqual(overrides['name'], 'B')

    # CEBALERT: missing test for allow_extra_keywords (e.g. getting a
    # warning on attempting to override non-existent parameter when
    # allow_extra_keywords is False)

    def test_missing_key(self):
        overrides = ParamOverrides(self.po,{'name':'B'})
        with self.assertRaises(AttributeError):
            overrides['doesnotexist']


class TestSharedParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        with shared_parameters():
            self.p1 = TestPO(name='A')
            self.p2 = TestPO(name='B')
            self.ap1 = AnotherTestPO(name='A')
            self.ap2 = AnotherTestPO(name='B')

    def test_shared_object(self):
        self.assertTrue(self.ap1.instPO is self.ap2.instPO)
        self.assertTrue(self.ap1.param['instPO'].default is not self.ap2.instPO)

    def test_shared_list(self):
        self.assertTrue(self.p1.inst is self.p2.inst)
        self.assertTrue(self.p1.param['inst'].default is not self.p2.inst)


def test_inheritance_None_is_not_special_cased_default():

    class A(param.Parameterized):
        p = param.String(default='test')

    class B(A):
        p = param.String(default=None)

    b = B()

    assert b.p is None


@pytest.mark.parametrize('attribute', [
    'default',
    'doc',
    'precedence',
    'readonly',
    'pickle_default_value',
    'per_instance',
    # These 3 parameters of Parameter are handled dynamically, instantiating
    # Parameter with their value to None doesn't lead to the attribute value
    # on Parameter being None.
    # 'instantiate',
    # 'constant',
    # 'allow_None',
])
def test_inheritance_None_is_not_special_cased(attribute):
    """
    Somewhat strange test as it's setting attributes of Parameter to None
    while it's not necessarily an allowed value. It's to test that it's no
    longer considered as a sentinel allowing inheritance.
    """

    class A(param.Parameterized):
        p = param.Parameter(**{attribute: 'test'})

    class B(A):
        p = param.Parameter(**{attribute: None})

    b = B()

    assert getattr(b.param.p, attribute) is None


def test_inheritance_no_default_declared_in_subclass():
    default = 5.0
    class A(param.Parameterized):
        p = param.Number(default=default)

    class B(A):
        p = param.Number()

    b = B()
    assert b.p == 5.0


def test_inheritance_attribute_from_non_subclass_not_inherited():
    class A(param.Parameterized):
        p = param.String(doc='1')

    class B(A):
        p = param.Number(default=0.1)

    b = B()

    assert b.param.p.doc == '1'


def test_inheritance_sub_attribute_is_used():
    class A(param.Parameterized):
        p = param.String(doc='1')

    class B(A):
        p = param.String(doc='2')

    b = B()

    assert b.param.p.doc == '2'


def test_inheritance_default_is_not_None_in_sub():
    class A(param.Parameterized):
        p = param.String(default='1')

    class B(A):
        p = param.Number(default=0.1)

    b = B()

    assert b.p == 0.1


def test_inheritance_default_is_None_in_sub():
    class A(param.Parameterized):
        p = param.Tuple(default=(0, 1))

    class B(A):
        p = param.NumericTuple()

    b = B()

    assert b.p == (0, 1)


def test_inheritance_diamond_not_supported():
    """
    Test that Parameters don't respect diamond inheritance.

    In regular Python, the value of the class attribute p on D is resolved
    to 2:

        class A:
            p = 1

        class B(A):
            pass

        class C(A):
            p = 2

        class D(B, C):
            pass

        assert D.p == 2

    This is not supported by Param (https://github.com/holoviz/param/issues/715).
    """

    class A(param.Parameterized):
        p = param.Parameter(default=1, doc='11')

    class B(A):
        p = param.Parameter()

    class C(A):
        p = param.Parameter(default=2, doc='22')

    class D(B, C):
        p = param.Parameter()

    assert D.p != 2
    assert D.param.p.doc != '22'
    assert D.p == 1
    assert D.param.p.doc == '11'

    d = D()

    assert d.p != 2
    assert d.param.p.doc != '22'
    assert d.p == 1
    assert d.param.p.doc == '11'


def test_inheritance_from_multiple_params_class():
    class A(param.Parameterized):
        p = param.Parameter(doc='foo')

    class B(A):
        p = param.Parameter(default=2)

    class C(B):
        p = param.Parameter(instantiate=True)

    assert A.param.p.instantiate is False
    assert A.param.p.default is None
    assert A.param.p.doc == 'foo'

    assert B.param.p.instantiate is False
    assert B.param.p.default == 2
    assert B.param.p.doc == 'foo'

    assert C.param.p.instantiate is True
    assert C.param.p.default == 2
    assert C.param.p.doc == 'foo'


def test_inheritance_from_multiple_params_inst():
    # Picked Parameters whose default value is None
    class A(param.Parameterized):
        p = param.Parameter(doc='foo')

    class B(A):
        p = param.Dict(default={'foo': 'bar'})

    class C(B):
        p = param.ClassSelector(class_=object, allow_None=True)

    a = A()
    b = B()
    c = C()

    assert a.param.p.allow_None is True
    assert a.param.p.default is None
    assert a.param.p.doc == 'foo'

    assert b.param.p.allow_None is False
    assert b.param.p.default == {'foo': 'bar'}
    assert b.param.p.doc == 'foo'

    assert c.param.p.allow_None is True
    assert c.param.p.default == {'foo': 'bar'}
    assert c.param.p.doc == 'foo'


def test_inheritance_from_multiple_params_intermediate_setting():
    class A(param.Parameterized):
        p = param.Parameter(doc='foo')

    A.param.p.default = 1
    A.param.p.doc = 'bar'

    class B(A):
        p = param.Dict(default={'foo': 'bar'})

    assert A.param.p.default == 1
    assert A.param.p.doc == 'bar'

    assert B.param.p.default == {'foo': 'bar'}
    assert B.param.p.doc == 'bar'

    a = A()
    b = B()

    assert a.param.p.default == 1
    assert a.param.p.doc == 'bar'

    assert b.param.p.default == {'foo': 'bar'}
    assert b.param.p.doc == 'bar'


def test_inheritance_instantiate_behavior():
    class A(param.Parameterized):
        p = param.Parameter(instantiate=True)

    class B(A):
        p = param.Parameter(readonly=True)


    # Normally, param.Parameter(readonly=True, instantiate=True) ends up with
    # instantiate being False.
    assert B.param.p.instantiate is True

    b = B()

    assert b.param.p.instantiate is True


def test_inheritance_constant_behavior():
    class A(param.Parameterized):
        p = param.Parameter(readonly=True)

    class B(A):
        p = param.Parameter()


    # Normally, param.Parameter(readonly=True) ends up with constant being
    # True.
    assert B.param.p.constant is False

    b = B()

    assert b.param.p.constant is False


def test_inheritance_set_Parameter_instantiate_constant_before_instantation():
    # https://github.com/holoviz/param/issues/760
    class A(param.Parameterized):
        p0 = param.Parameter()
        p1 = param.Parameter(instantiate=True)
        p2 = param.Parameter(constant=True)

    class B(A):
        pass

    B.p0 = B.p1 = B.p2 = 2

    b = B()

    assert b.p0 == 2
    assert b.p1 == 2
    assert b.p2 == 2


def test_inheritance_allow_None_behavior():
    class A(param.Parameterized):
        p = param.Parameter(default=1)

    class B(A):
        p = param.Parameter()

    # A computes allow_None to False, B sets it to True.
    assert A.param.p.allow_None !=  B.param.p.allow_None
    assert B.param.p.allow_None is True

    a = A()
    b = B()

    assert a.param.p.allow_None !=  b.param.p.allow_None
    assert b.param.p.allow_None is True


def test_inheritance_allow_None_behavior2():
    class A(param.Parameterized):
        p = param.Parameter(allow_None=False)

    class B(A):
        p = param.Parameter(default=None)


    # A says None is not allowed, B sets the default to None and recomputes
    # allow_None.
    assert B.param.p.allow_None is True

    b = B()

    assert b.param.p.allow_None is True


def test_inheritance_class_attribute_behavior():
    class A(param.Parameterized):
        p = param.Parameter(1)

    class B(A):
        p = param.Parameter()

    assert B.p == 1

    A.p = 2

    # Should be 2?
    # https://github.com/holoviz/param/issues/718
    assert B.p == 1

class TestShallowCopyMutableAttributes:

    @pytest.fixture
    def foo(self):
        class Foo:
            def __init__(self, val):
                self.val = val

        return Foo

    @pytest.fixture
    def custom_param(self):
        class CustomParameter(Parameter):

            __slots__ = ['container']

            _slot_defaults = dict(Parameter._slot_defaults, container=None)

            def __init__(self, default=Undefined, *, container=Undefined, **kwargs):
                super().__init__(default=default, **kwargs)
                self.container = container

        return CustomParameter

    def test_shallow_copy_on_class_creation(self, custom_param, foo):
        clist = [foo(1), foo(2)]

        class P(param.Parameterized):
            cp = custom_param(container=clist)


        # the mutable container has been shallow-copied
        assert P.param.cp.container is not clist
        assert all(cval is val for cval, val in zip(P.param.cp.container, clist))

    def test_shallow_copy_inheritance_each_level(self, custom_param):

        clist = [1, 2]

        class A(param.Parameterized):
            p = custom_param(container=clist)

        class B(A):
            p = custom_param(default=1)

        clist.append(3)

        assert A.param.p.container == [1, 2]
        assert B.param.p.container == [1, 2]

        B.param.p.container.append(4)

        assert A.param.p.container == [1, 2]
        assert B.param.p.container == [1, 2, 4]

    def test_shallow_copy_on_instance_getitem(self, custom_param, foo):
        clist = [foo(1), foo(2)]

        class P(param.Parameterized):
            cp = custom_param(container=clist)

        p = P()

        assert 'cp' not in p._param__private.params

        p.param['cp']

        # the mutable container has been shallow-copied
        assert 'cp' in p._param__private.params
        assert P.param.cp.container == p._param__private.params['cp'].container
        assert P.param.cp.container is not p._param__private.params['cp'].container
        assert all(cval is val for cval, val in zip(p.param.cp.container, clist))

    def test_shallow_copy_on_instance_set(self, custom_param, foo):
        clist = [foo(1), foo(2)]

        class P(param.Parameterized):
            cp = custom_param(container=clist)

        p = P()

        assert 'cp' not in p._param__private.params

        p.cp = 'value'

        # the mutable container has been shallow-copied
        assert 'cp' in p._param__private.params
        assert P.param.cp.container == p._param__private.params['cp'].container
        assert P.param.cp.container is not p._param__private.params['cp'].container
        assert all(cval is val for cval, val in zip(p.param.cp.container, clist))

    def test_modify_class_container_before_shallow_copy(self, custom_param, foo):
        clist = [foo(1), foo(2)]
        clist2 = [foo(3), foo(4)]

        class P(param.Parameterized):
            cp = custom_param(container=clist)

        p1 = P()
        p2 = P()

        # Setting the class container will affect instances are the shallow copy
        # is lazy and has not yet been made.
        P.param.cp.container = clist2

        assert p1.param.cp.container == clist2
        assert p2.param.cp.container == clist2


@pytest.fixture
def custom_parameter1():
    class CustomParameter(param.Parameter):

        __slots__ = ['foo', 'bar']

        # foo has no default value defined in _slot_defaults

        def __init__(self, foo=param.Undefined, **params):
            super().__init__(**params)
            self.foo = foo

    return CustomParameter


def test_inheritance_parameter_attribute_without_default():

    class CustomParameter(param.Parameter):

        __slots__ = ['foo']

        # foo has no default value defined in _slot_defaults

        def __init__(self, foo=param.Undefined, **params):
            super().__init__(**params)
            self.foo = foo

    with pytest.raises(KeyError, match="Slot 'foo' of parameter 'c' has no default value defined in `_slot_defaults`"):
        class A(param.Parameterized):
            c = CustomParameter()


def _dir(obj):
    return [attr for attr in dir(obj) if not attr.startswith('__')]


def test_namespace_class():

    class P(param.Parameterized):
        x = param.Parameter()

        @param.depends('x', watch=True)
        def foo(self): pass

    P.x = 1
    P.param.x

    assert _dir(P) == [
        '_param__parameters',
        '_param__private',
        'foo',
        'name',
        'param',
        'x'
    ]


def test_namespace_inst():

    class P(param.Parameterized):
        x = param.Parameter()

        @param.depends('x', watch=True)
        def foo(self): pass

    p = P(x=2)
    p.param.x

    assert _dir(p) == [
        '_param__parameters',
        '_param__private',
        'foo',
        'name',
        'param',
        'x'
    ]


def test_parameterized_access_param_before_super():
    class P(param.Parameterized):
        x = param.Parameter(1)

        def __init__(self, **params):
            # Reaching out to a Parameter default before calling super
            assert self.x == 1
            super().__init__(**params)

    P()


def check_signature(parameterized_obj, parameters):
    assert parameterized_obj.__signature__ is not None
    sig = inspect.signature(parameterized_obj)
    assert len(parameters) == len(sig.parameters)
    for sparam, pname in zip(sig.parameters.values(), parameters):
        assert sparam.name == pname
        assert sparam.kind == inspect.Parameter.KEYWORD_ONLY


def test_parameterized_signature_base():
    check_signature(param.Parameterized, ['name'])


def test_parameterized_signature_simple():
    class P(param.Parameterized):
        x = param.Parameter()
    check_signature(P, ['x', 'name'])


def test_parameterized_signature_subclass_noparams():
    class A(param.Parameterized):
        x = param.Parameter()

    class B(A): pass

    check_signature(B, ['x', 'name'])


def test_parameterized_signature_subclass_with_params():
    class A(param.Parameterized):
        a1 = param.Parameter()
        a2 = param.Parameter()

    class B(A):
        b1 = param.Parameter()
        b2 = param.Parameter()

    class C(B):
        c1 = param.Parameter()
        c2 = param.Parameter()

    check_signature(A, ['a1', 'a2', 'name'])
    check_signature(B, ['b1', 'b2', 'a1', 'a2', 'name'])
    check_signature(C, ['c1', 'c2', 'b1', 'b2', 'a1', 'a2', 'name'])


def test_parameterized_signature_subclass_multiple_inheritance():
    class A(param.Parameterized):
        a1 = param.Parameter()
        a2 = param.Parameter()

    class B(param.Parameterized):
        b1 = param.Parameter()
        b2 = param.Parameter()

    class C(A, B):
        c1 = param.Parameter()
        c2 = param.Parameter()

    check_signature(C, ['c1', 'c2', 'a1', 'a2', 'b1', 'b2', 'name'])


def test_parameterized_signature_simple_init_same_as_parameterized():
    class P(param.Parameterized):
        x = param.Parameter()

        def __init__(self, **params):
            super().__init__(**params)

    check_signature(P, ['x', 'name'])


def test_parameterized_signature_simple_init_different():
    class P(param.Parameterized):
        x = param.Parameter()

        def __init__(self, x=1, **params):
            super().__init__(x=x, **params)

    assert P.__signature__ is None


def test_parameterized_signature_subclass_noparams_init_different():
    class A(param.Parameterized):
        x = param.Parameter()

    class B(A):
        def __init__(self, x=1, **params):
            super().__init__(x=x, **params)

    check_signature(A, ['x', 'name'])
    assert B.__signature__ is None


def test_parameterized_signature_subclass_with_params_init_different():
    class A(param.Parameterized):
        a1 = param.Parameter()
        a2 = param.Parameter()

    class B(A):
        b1 = param.Parameter()
        b2 = param.Parameter()

    class C(B):
        c1 = param.Parameter()
        c2 = param.Parameter()

        def __init__(self, c1=1, **params):
            super().__init__(c1=1, **params)

    check_signature(A, ['a1', 'a2', 'name'])
    check_signature(B, ['b1', 'b2', 'a1', 'a2', 'name'])
    assert C.__signature__ is None


def test_parameterized_signature_subclass_multiple_inheritance_init_different():
    class A(param.Parameterized):
        a1 = param.Parameter()
        a2 = param.Parameter()

    class B(param.Parameterized):
        b1 = param.Parameter()
        b2 = param.Parameter()

        def __init__(self, b1=1, **params):
            super().__init__(b1=1, **params)

    class C(A, B):
        c1 = param.Parameter()
        c2 = param.Parameter()

    check_signature(A, ['a1', 'a2', 'name'])
    assert B.__signature__ is None
    assert C.__signature__ is None


def test_inheritance_with_incompatible_defaults():
    class A(param.Parameterized):
        p = param.String()

    class B(A): pass

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Number parameter 'C.p' failed to validate its "
            "default value on class creation. "
            "The Parameter type changed between class 'C' "
            "and one of its parent classes (B, A) which made it invalid. "
            "Please fix the Parameter type."
            "\nValidation failed with:\nNumber parameter 'C.p' only takes numeric values, not <class 'str'>."
        )
    ):
        class C(B):
            p = param.Number()


def test_inheritance_default_validation_with_more_specific_type():
    class A(param.Parameterized):
        p = param.Tuple(default=('a', 'b'))

    class B(A): pass

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "NumericTuple parameter 'C.p' failed to validate its "
            "default value on class creation. "
            "The Parameter type changed between class 'C' "
            "and one of its parent classes (B, A) which made it invalid. "
            "Please fix the Parameter type."
            "\nValidation failed with:\nNumericTuple parameter 'C.p' only takes numeric values, not <class 'str'>."
        )
    ):
        class C(B):
            p = param.NumericTuple()


def test_inheritance_with_changing_bounds():
    class A(param.Parameterized):
        p = param.Number(default=5)

    class B(A): pass

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Number parameter 'C.p' failed to validate its "
            "default value on class creation. "
            "The Parameter is defined with attributes "
            "which when combined with attributes inherited from its parent "
            "classes (B, A) make it invalid. Please fix the Parameter attributes."
            "\nValidation failed with:\nNumber parameter 'C.p' must be at most 3, not 5."
        )
    ):
        class C(B):
            p = param.Number(bounds=(-1, 3))


def test_inheritance_with_changing_default():
    class A(param.Parameterized):
        p = param.Number(default=5, bounds=(3, 10))

    class B(A): pass

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Number parameter 'C.p' failed to validate its "
            "default value on class creation. "
            "The Parameter is defined with attributes "
            "which when combined with attributes inherited from its parent "
            "classes (B, A) make it invalid. Please fix the Parameter attributes."
            "\nValidation failed with:\nNumber parameter 'C.p' must be at least 3, not 1."
        )
    ):
        class C(B):
            p = param.Number(default=1)


def test_inheritance_with_changing_class_():
    class A(param.Parameterized):
        p = param.ClassSelector(class_=int, default=5)

    class B(A): pass

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "ClassSelector parameter 'C.p' failed to validate its "
            "default value on class creation. "
            "The Parameter is defined with attributes "
            "which when combined with attributes inherited from its parent "
            "classes (B, A) make it invalid. Please fix the Parameter attributes."
            "\nValidation failed with:\nClassSelector parameter 'C.p' value must be an instance of str, not 5."
        )
    ):
        class C(B):
            p = param.ClassSelector(class_=str)
