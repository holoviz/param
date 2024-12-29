"""
Unit test for dynamic parameters.

Tests __get__, __set__ and that inspect_value() and
get_value_generator() work.

Originally implemented as doctests in Topographica in the file
testDynamicParameter.txt
"""
import copy
import unittest

import param
import numbergen


class TestDynamicParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        param.Dynamic.time_dependent = False

        class TestPO1(param.Parameterized):
            x = param.Dynamic(default=numbergen.UniformRandom(lbound=-1,ubound=1,seed=1),doc="nothing")
            y = param.Dynamic(default=1)

        class TestPO2(param.Parameterized):
            x = param.Dynamic(default=numbergen.UniformRandom(lbound=-1,ubound=1,seed=30))
            y = param.Dynamic(default=1.0)

        self.TestPO2 = TestPO2
        self.TestPO1 = TestPO1

        self.t1 = self.TestPO1()
        self.t2 = self.TestPO1(x=numbergen.UniformRandom(lbound=-1,ubound=1,seed=10))
        self.t3 = self.TestPO1(x=numbergen.UniformRandom(lbound=-1,ubound=1,seed=10))
        self.t2.param.set_dynamic_time_fn(None)
        self.t3.param.set_dynamic_time_fn(None)

        self.t6 = self.TestPO2()
        self.t7 = self.TestPO2()


class TestDynamicParameterBasics(TestDynamicParameters):

    def test_set_dynamic_time_fn_x(self):
        self.t1.param.set_dynamic_time_fn(None)
        self.assertEqual(
            self.t1.param['x']._value_is_dynamic(self.t1), True)

    def test_set_dynamic_time_fn_y(self):
        self.assertEqual(
            self.t1.param['y']._value_is_dynamic(self.t1), False)

    def test_inspect_x(self):
        """No value generated yet."""
        self.assertEqual(self.t1.param.inspect_value('x'), None)

    def test_inspect_y(self):
        self.assertEqual(self.t1.param.inspect_value('y'), 1)

    def test_inspect_y_set(self):
        self.t1.y = 2
        self.assertEqual(self.t1.param.inspect_value('y'), 2)

    def test_set_dynamic_numbergen(self):
        is_numbergen = isinstance(self.t2.param.get_value_generator('x'),
                                  numbergen.UniformRandom)
        self.assertEqual(is_numbergen, True)

    def test_matching_numbergen_streams(self):
        """Check that t2 and t3 have identical streams."""
        self.assertEqual(self.t2.x, self.t3.x)

    def test_numbergen_objects_distinct(self):
        """Check t2 and t3 do not share UniformRandom objects."""
        self.t2.x
        self.assertNotEqual(self.t2.param.inspect_value('x'),
                            self.t3.param.inspect_value('x'))

    def test_numbergen_inspect(self):
        """inspect_value() should return last generated value."""
        self.t2.x # Call 1
        self.t2.x # Call 2
        t2_last_value = self.t2.x  # advance t2 beyond t3

        self.assertEqual(self.t2.param.inspect_value('x'),
                         t2_last_value)
        # ensure last_value is not shared
        self.assertNotEqual(self.t3.param.inspect_value('x'), t2_last_value)

    def test_dynamic_value_instantiated(self):
        t6_first_value = self.t6.x
        self.assertNotEqual(self.t7.param.inspect_value('x'),
                            t6_first_value)

    def test_non_dynamic_value_not_instantiated(self):
        """non-dynamic value not instantiated."""
        self.TestPO2.y = 4
        self.assertEqual(self.t6.y, 4)
        self.assertEqual(self.t7.y, 4)

    def test_dynamic_value_setting(self):
        self.t6.y = numbergen.UniformRandom()
        t8 = self.TestPO2()
        self.TestPO2.y = 10
        # t6 got a dynamic value, but shouldn't have changed Parameter's instantiate
        self.assertEqual(t8.y, 10)

    def test_setting_y_param_numbergen(self):
        self.TestPO2.y=numbergen.UniformRandom()  # now the Parameter instantiate should be true
        t9 = self.TestPO2()
        self.assertEqual('y' in t9._param__private.values, True)

    def test_shared_numbergen(self):
        """
        Instances of TestPO2 that don't have their own value for the
        parameter share one UniformRandom object.
        """
        self.TestPO2.y=numbergen.UniformRandom()  # now the Parameter instantiate should be true
        self.assertEqual(self.t7.param.get_value_generator('y') is self.TestPO2().param['y'].default, True)
        self.assertEqual(self.TestPO2().param['y'].default.__class__.__name__, 'UniformRandom')

    def test_copy_match(self):
        """Check a copy is the same."""
        t9 = copy.deepcopy(self.t7)
        self.assertEqual(t9.param.get_value_generator('y') is self.TestPO2().param['y'].default, True)



class TestDynamicTimeDependent(TestDynamicParameters):

    def setUp(self):
        super().setUp()
        param.Dynamic.time_dependent = True

        class TestPO3(param.Parameterized):
            x = param.Dynamic(default=numbergen.UniformRandom(name='xgen',
                                                              time_dependent=True))

        class TestPO4(self.TestPO1):
            """Nested parameterized objects."""

            z = param.Parameter(default=self.TestPO1())

        self.TestPO3 = TestPO3
        self.TestPO4 = TestPO4

        self.t10 = self.TestPO1()
        self.t11 = TestPO3()

    def test_dynamic_values_unchanged_dependent(self):
        param.Dynamic.time_dependent = True
        call_1 = self.t10.x
        call_2 = self.t10.x
        call_3 = self.t10.x
        self.assertEqual(call_1, call_2)
        self.assertEqual(call_2, call_3)

    def test_dynamic_values_changed_independent(self):
        param.Dynamic.time_dependent = False
        call_1 = self.t10.x
        call_2 = self.t10.x
        call_3 = self.t10.x
        self.assertNotEqual(call_1, call_2)
        self.assertNotEqual(call_2, call_3)

    def test_dynamic_values_change(self):
        param.Dynamic.time_dependent = True
        with param.Dynamic.time_fn as t:
            t(0)
            call_1 = self.t10.x
            t += 1
            call_2 = self.t10.x
            t(0)
            call_3 = self.t10.x
        self.assertNotEqual(call_1, call_2)
        self.assertNotEqual(call_1, call_3)

    def test_dynamic_values_time_dependent(self):
        param.Dynamic.time_dependent = True
        with param.Dynamic.time_fn as t:
            t(0)
            call_1 = self.t11.x
            t += 1
            call_2 = self.t11.x
            t(0)
            call_3 = self.t11.x
        self.assertNotEqual(call_1, call_2)
        self.assertEqual(call_1, call_3)

    def test_class_dynamic_values_change(self):
        call_1 = self.TestPO3.x
        call_2 = self.TestPO3.x
        self.assertEqual(call_1, call_2)
        with param.Dynamic.time_fn as t:
            t += 1
            call_3 = self.TestPO3.x
        self.assertNotEqual(call_2, call_3)

    def test_dynamic_value_change_independent(self):
        t12 = self.TestPO1()
        t12.param.set_dynamic_time_fn(None)
        self.assertNotEqual(t12.x, t12.x)
        self.assertEqual(t12.y, t12.y)

    def test_dynamic_value_change_disabled(self):
        """time_fn set on the UniformRandom() when t13.y was set."""
        t13 = self.TestPO1()
        t13.param.set_dynamic_time_fn(None)
        t13.y = numbergen.UniformRandom()
        self.assertNotEqual(t13.y, t13.y)

    def test_dynamic_value_change_enabled(self):
        """time_fn set on the UniformRandom() when t13.y was set."""
        t14 = self.TestPO1()
        t14.y = numbergen.UniformRandom()
        self.assertEqual(t14.y, t14.y)


    def test_dynamic_time_fn_not_inherited(self):
        """time_fn not inherited."""
        t15 = self.TestPO4()
        t15.param.set_dynamic_time_fn(None)
        with param.Dynamic.time_fn as t:
            call_1 = t15.z.x
            t += 1
            call_2 = t15.z.x
            self.assertNotEqual(call_1, call_2)



class TestDynamicSharedNumbergen(TestDynamicParameters):
    """Check shared generator."""

    def setUp(self):
        super().setUp()
        self.shared = numbergen.UniformRandom(lbound=-1,ubound=1,seed=20)

    def test_dynamic_shared_numbergen(self):
        param.Dynamic.time_dependent = True
        t11 = self.TestPO1(x=self.shared)
        t12 = self.TestPO1(x=self.shared)

        with param.Dynamic.time_fn as t:
            t += 1
            call_1 = t11.x
            self.assertEqual(call_1, t12.x)
            t += 1
            self.assertNotEqual(call_1, t12.x)


# Commented out block in the original doctest version.
# Maybe these are features originally planned but never implemented

# It is not yet possible to set time_fn for a Parameter instance
# >>> class TestPO5(param.Parameterized):
# ...    x = param.Dynamic(default=numbergen.UniformRandom(),dynamic_time_fn=None)

# We currently don't support iterators/generators in Dynamic unless
# they're wrapped.

# >>> i = iter([1,2,3])
# >>> t11.x = i

# >>> topo.sim.run(1)

# >>> t11.x
# 1

# >>> def gen():
# ...     yield 2
# ...     yield 4
# ...     yield 6

# >>> g = gen()

# >>> t11.x = g

# >>> t11.x
# 2

# >>> topo.sim.run(1)

# >>> t11.x
# 4
