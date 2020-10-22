"""
Unit test for Parameterized.
"""

import unittest
import param
import numbergen

# CEBALERT: not anything like a complete test of Parameterized!


import random
from nose.tools import istest, nottest


from param.parameterized import ParamOverrides, shared_parameters

@nottest
class _SomeRandomNumbers(object):
    def __call__(self):
        return random.random()

@nottest
class TestPO(param.Parameterized):
    inst = param.Parameter(default=[1,2,3],instantiate=True)
    notinst = param.Parameter(default=[1,2,3],instantiate=False)
    const = param.Parameter(default=1,constant=True)
    ro = param.Parameter(default="Hello",readonly=True)
    ro2 = param.Parameter(default=object(),readonly=True,instantiate=True)

    dyn = param.Dynamic(default=1)

@nottest
class AnotherTestPO(param.Parameterized):
    instPO = param.Parameter(default=TestPO(),instantiate=True)
    notinstPO = param.Parameter(default=TestPO(),instantiate=False)

@nottest
class TestAbstractPO(param.Parameterized):
    __abstract = True

class _AnotherAbstractPO(param.Parameterized):
    __abstract = True


@nottest
class TestParamInstantiation(AnotherTestPO):
    instPO = param.Parameter(default=AnotherTestPO(),instantiate=False)

@istest
class TestParameterized(unittest.TestCase):

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

        self.assertEqual(testpo.params()['ro'].constant,True)

        # check that instantiate was ignored for readonly
        self.assertEqual(testpo.params()['ro2'].instantiate,False)



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
        assert t.params('instPO').instantiate is True
        assert isinstance(t.instPO,AnotherTestPO)


    def test_abstract_class(self):
        """Check that a class declared abstract actually shows up as abstract."""
        self.assertEqual(TestAbstractPO.abstract,True)
        self.assertEqual(_AnotherAbstractPO.abstract,True)
        self.assertEqual(TestPO.abstract,False)


    def test_params(self):
        """Basic tests of params() method."""


        # CB: test not so good because it requires changes if params
        # of PO are changed
        assert 'name' in param.Parameterized.params()
        assert len(param.Parameterized.params()) in [1,2]

        ## check for bug where subclass Parameters were not showing up
        ## if params() already called on a super class.
        assert 'inst' in TestPO.params()
        assert 'notinst' in TestPO.params()

        ## check caching
        assert param.Parameterized.params() is param.Parameterized().params(), "Results of params() should be cached." # just for performance reasons


    def test_state_saving(self):
        t = TestPO(dyn=_SomeRandomNumbers())
        g = t.get_value_generator('dyn')
        g._Dynamic_time_fn=None
        assert t.dyn!=t.dyn
        orig = t.dyn
        t.state_push()
        t.dyn
        assert t.inspect_value('dyn')!=orig
        t.state_pop()
        assert t.inspect_value('dyn')==orig



from param import parameterized

@nottest
class some_fn(param.ParameterizedFunction):
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

@istest
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


@nottest
class TestPO1(param.Parameterized):
    x = param.Number(default=numbergen.UniformRandom(lbound=-1,ubound=1,seed=1),bounds=(-1,1))
    y = param.Number(default=1,bounds=(-1,1))

@istest
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


@istest
class TestStringParameter(unittest.TestCase):

    def setUp(self):
        super(TestStringParameter, self).setUp()

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



@istest
class TestParamOverrides(unittest.TestCase):

    def setUp(self):
        super(TestParamOverrides, self).setUp()
        self.po = param.Parameterized(name='A',print_level=0)

    def test_init_name(self):
        self.assertEqual(self.po.name, 'A')

    def test_simple_override(self):
        overrides = ParamOverrides(self.po,{'name':'B'})
        self.assertEqual(overrides['name'], 'B')
        self.assertEqual(overrides['print_level'], 0)

    # CEBALERT: missing test for allow_extra_keywords (e.g. getting a
    # warning on attempting to override non-existent parameter when
    # allow_extra_keywords is False)

    def test_missing_key(self):
        overrides = ParamOverrides(self.po,{'name':'B'})
        with self.assertRaises(AttributeError):
            overrides['doesnotexist']


class TestSharedParameters(unittest.TestCase):

    def setUp(self):
        with shared_parameters():
            self.p1 = TestPO(name='A', print_level=0)
            self.p2 = TestPO(name='B', print_level=0)
            self.ap1 = AnotherTestPO(name='A', print_level=0)
            self.ap2 = AnotherTestPO(name='B', print_level=0)

    def test_shared_object(self):
        self.assertTrue(self.ap1.instPO is self.ap2.instPO)
        self.assertTrue(self.ap1.params('instPO').default is not self.ap2.instPO)

    def test_shared_list(self):
        self.assertTrue(self.p1.inst is self.p2.inst)
        self.assertTrue(self.p1.params('inst').default is not self.p2.inst)



if __name__ == "__main__":
    import nose
    nose.runmodule()
