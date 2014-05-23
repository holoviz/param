"""
Unit test for Parameterized.
"""

# CEBALERT: copy of Topographica's
# topo/tests/unit/testparameterizedobject.py.  Param is currently
# tested inside Topographica. This file is here as a placeholder to
# allow param's testing infrastructure to be set up.

import unittest

import param

# CEBALERT: not anything like a complete test of Parameterized!

import random

from nose.tools import istest, nottest

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

        # CB: couldn't figure out how to use assertRaises
        try:
            t = TestPO(ro=20)
        except TypeError:
            pass
        else:
            raise AssertionError("Read-only parameter was set!")

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

if __name__ == "__main__":
	import nose
	nose.runmodule()
