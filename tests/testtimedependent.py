"""
Unit tests for the param.Time class, time dependent parameters and
time-dependent numbergenerators.
"""
import copy
import fractions
import unittest

import pytest

import param
import numbergen

try:
    import gmpy
except ImportError:
    import os
    if os.getenv('PARAM_TEST_GMPY','0') == '1':
        raise ImportError("PARAM_TEST_GMPY=1 but gmpy not available.")
    else:
        gmpy = None


class TestTimeClass(unittest.TestCase):

    def test_time_init(self):
        param.Time()

    def test_time_init_int(self):
        t = param.Time(time_type=int)
        self.assertEqual(t(), 0)

    def test_time_int_iter(self):
        t = param.Time(time_type=int)
        self.assertEqual(next(t), 0)
        self.assertEqual(next(t), 1)

    def test_time_init_timestep(self):
        t = param.Time(time_type=int, timestep=2)
        self.assertEqual(next(t), 0)
        self.assertEqual(next(t), 2)

    def test_time_int_until(self):
        t = param.Time(time_type=int, until=3)
        self.assertEqual(next(t), 0)
        self.assertEqual(next(t), 1)
        self.assertEqual(next(t), 2)
        self.assertEqual(next(t), 3)
        try:
            self.assertEqual(next(t), 4)
            raise AssertionError("StopIteration should have been raised")
        except StopIteration:
            pass

    def test_time_int_eq(self):
        t = param.Time(time_type=int)
        s = param.Time(time_type=int)
        t(3); s(3)
        self.assertEqual(t == s, True)

    def test_time_int_context(self):
        t = param.Time(time_type=int)
        t(3)
        with t:
            self.assertEqual(t(), 3)
            t(5)
            self.assertEqual(t(), 5)
        self.assertEqual(t(), 3)

    def test_time_int_context_iadd(self):

        with param.Time(time_type=int) as t:
            self.assertEqual(t(), 0)
            t += 5
            self.assertEqual(t(), 5)
        self.assertEqual(t(), 0)

    def test_time_int_change_type(self):
        t = param.Time(time_type=int)
        self.assertEqual(t(), 0)
        t(1, fractions.Fraction)
        self.assertEqual(t(), 1)
        self.assertEqual(t.time_type, fractions.Fraction)

    def test_time_integration(self):
        # This used to be a doctest of param.Time; moved
        # here not to have any doctest to run.
        time = param.Time(until=20, timestep=1)
        self.assertEqual(time(), 0)
        self.assertEqual(time(5), 5)
        time += 5
        self.assertEqual(time(), 10)
        with time as t:
            self.assertEqual(t(), 10)
            self.assertEqual(
                [val for val in t],
                [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
            )
            self.assertEqual(t(), 20)
            'Time after iteration: %s' % t()
            t += 2
            self.assertEqual(t(), 22)
        self.assertEqual(time(), 10)

    @pytest.mark.skipif(gmpy is None, reason="gmpy is not installed")
    def test_time_init_gmpy(self):
        t = param.Time(time_type=gmpy.mpq)
        self.assertEqual(t(), gmpy.mpq(0))
        t.advance(gmpy.mpq(0.25))
        self.assertEqual(t(), gmpy.mpq(1,4))

    @pytest.mark.skipif(gmpy is None, reason="gmpy is not installed")
    def test_time_init_gmpy_advanced(self):
        t = param.Time(time_type=gmpy.mpq,
                       timestep=gmpy.mpq(0.25),
                       until=1.5)
        self.assertEqual(t(), gmpy.mpq(0,1))
        t(0.5)
        self.assertEqual(t(), gmpy.mpq(1,2))
        with t:
            t.advance(0.25)
            self.assertEqual(t(), gmpy.mpq(3,4))
        self.assertEqual(t(), gmpy.mpq(1,2))
        tvals = [tval for tval in t]
        self.assertEqual(tvals, [gmpy.mpq(1,2),
                                 gmpy.mpq(3,4),
                                 gmpy.mpq(1,1),
                                 gmpy.mpq(5,4),
                                 gmpy.mpq(3,2)])


class TestTimeDependentDynamic(unittest.TestCase):

    def setUp(self):
        super().setUp()
        param.Dynamic.time_dependent=None
        self.time_fn= param.Time(time_type=int)

        class Incrementer:
            def __init__(self):
                self.i = -1
            def __call__(self):
                self.i+=1
                return self.i

        self.Incrementer = Incrementer

        class DynamicClass(param.Parameterized):
            a = param.Number(default = self.Incrementer())

        self.DynamicClass = DynamicClass
        self._start_state = copy.copy([param.Dynamic.time_dependent,
                                       numbergen.TimeAware.time_dependent,
                                       param.Dynamic.time_fn,
                                       numbergen.TimeAware.time_fn,
                                       param.random_seed])

    def tearDown(self):
        param.Dynamic.time_dependent = self._start_state[0]
        numbergen.TimeAware.time_dependent = self._start_state[1]
        param.Dynamic.time_fn = self._start_state[2]
        numbergen.TimeAware.time_fn = self._start_state[3]
        param.random_seed = self._start_state[4]

    def test_non_time_dependent(self):
        """
        With param.Dynamic.time_dependent=None every call should
        increment.
        """
        param.Dynamic.time_dependent=None
        param.Dynamic.time_fn = self.time_fn

        dynamic = self.DynamicClass()
        self.assertEqual(dynamic.a, 0)
        self.assertEqual(dynamic.a, 1)
        self.assertEqual(dynamic.a, 2)

    def test_time_fixed(self):
        """
        With param.Dynamic.time_dependent=True the value should only
        increment when the time value changes.
        """
        param.Dynamic.time_dependent=True
        param.Dynamic.time_fn = self.time_fn

        dynamic = self.DynamicClass()
        self.assertEqual(dynamic.a, 0)
        self.assertEqual(dynamic.a, 0)

        self.time_fn += 1
        self.assertEqual(dynamic.a, 1)
        self.assertEqual(dynamic.a, 1)
        param.Dynamic.time_fn -= 5
        self.assertEqual(dynamic.a, 2)
        self.assertEqual(dynamic.a, 2)


    def test_time_dependent(self):
        """
        With param.Dynamic.time_dependent=True and param.Dynamic and
        numbergen.TimeDependent sharing a common time_fn, the value
        should be a function of time.
        """
        param.Dynamic.time_dependent=True
        param.Dynamic.time_fn = self.time_fn
        numbergen.TimeDependent.time_fn = self.time_fn

        class DynamicClass(param.Parameterized):
            b = param.Number(default = numbergen.ScaledTime(factor=2))

        dynamic = DynamicClass()
        self.time_fn(0)
        self.assertEqual(dynamic.b, 0.0)
        self.time_fn += 5
        self.assertEqual(dynamic.b, 10.0)
        self.assertEqual(dynamic.b, 10.0)
        self.time_fn -= 2
        self.assertEqual(dynamic.b, 6.0)
        self.assertEqual(dynamic.b, 6.0)
        self.time_fn -= 3
        self.assertEqual(dynamic.b, 0.0)


    def test_time_dependent_random(self):
        """
        When set to time_dependent=True, random number generators
        should also be a function of time.
        """
        param.Dynamic.time_dependent=True
        numbergen.TimeAware.time_dependent=True
        param.Dynamic.time_fn = self.time_fn
        numbergen.TimeAware.time_fn = self.time_fn
        param.random_seed = 42

        class DynamicClass(param.Parameterized):
            c = param.Number(default = numbergen.UniformRandom(name = 'test1'))
            d = param.Number(default = numbergen.UniformRandom(name = 'test2'))
            e = param.Number(default = numbergen.UniformRandom(name = 'test1'))

        dynamic = DynamicClass()

        test1_t1 = 0.23589388250988552
        test2_t1 = 0.12576257837158122
        test1_t2 = 0.14117586161849593
        test2_t2 = 0.9134917395930359

        self.time_fn(0)
        self.assertEqual(dynamic.c,    test1_t1)
        self.assertEqual(dynamic.c,    dynamic.e)
        self.assertNotEqual(dynamic.c, dynamic.d)
        self.assertEqual(dynamic.d,    test2_t1)
        self.time_fn(1)
        self.assertEqual(dynamic.c, test1_t2)
        self.assertEqual(dynamic.c, test1_t2)
        self.assertEqual(dynamic.d, test2_t2)
        self.time_fn(0)
        self.assertEqual(dynamic.c, test1_t1)
        self.assertEqual(dynamic.d,  test2_t1)


    def test_time_hashing_integers(self):
        """
        Check that ints, fractions and strings hash to the same value
        for integer values.
        """
        hashfn = numbergen.Hash("test", input_count=1)
        hash_1 = hashfn(1)
        hash_42 = hashfn(42)
        hash_200001 = hashfn(200001)

        self.assertEqual(hash_1, hashfn(fractions.Fraction(1)))
        self.assertEqual(hash_1, hashfn("1"))

        self.assertEqual(hash_42, hashfn(fractions.Fraction(42)))
        self.assertEqual(hash_42, hashfn("42"))

        self.assertEqual(hash_200001, hashfn(fractions.Fraction(200001)))
        self.assertEqual(hash_200001, hashfn("200001"))


    def test_time_hashing_rationals(self):
        """
        Check that hashes fractions and strings match for some
        reasonable rational numbers.
        """
        hashfn = numbergen.Hash("test", input_count=1)
        pi = "3.141592"
        half = fractions.Fraction(0.5)
        self.assertEqual(hashfn(0.5), hashfn(half))
        self.assertEqual(hashfn(pi), hashfn(fractions.Fraction(pi)))


    @pytest.mark.skipif(gmpy is None, reason="gmpy is not installed")
    def test_time_hashing_integers_gmpy(self):
        """
        Check that hashes for gmpy values at the integers also matches
        those of ints, fractions and strings.
        """
        hashfn = numbergen.Hash("test", input_count=1)
        hash_1 = hashfn(1)
        hash_42 = hashfn(42)

        self.assertEqual(hash_1, hashfn(gmpy.mpq(1)))
        self.assertEqual(hash_1, hashfn(1))

        self.assertEqual(hash_42, hashfn(gmpy.mpq(42)))
        self.assertEqual(hash_42, hashfn(42))

    @pytest.mark.skipif(gmpy is None, reason="gmpy is not installed")
    def test_time_hashing_rationals_gmpy(self):
        """
        Check that hashes of fractions and gmpy mpqs match for some
        reasonable rational numbers.
        """
        pi = "3.141592"
        hashfn = numbergen.Hash("test", input_count=1)
        self.assertEqual(hashfn(0.5), hashfn(gmpy.mpq(0.5)))
        self.assertEqual(hashfn(pi), hashfn(gmpy.mpq(3.141592)))
