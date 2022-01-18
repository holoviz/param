"""
Test cases for the numbergen module.
"""
import numbergen
from . import API1TestCase

_seed = 0  # keep tests deterministic
_iterations = 1000


class TestUniformRandom(API1TestCase):
    def test_range(self):
        lbound = 2.0
        ubound = 5.0
        gen = numbergen.UniformRandom(
                seed=_seed,
                lbound=lbound,
                ubound=ubound)
        for _ in range(_iterations):
            value = gen()
            self.assertTrue(lbound <= value < ubound)

class TestUniformRandomOffset(API1TestCase):
    def test_range(self):
        lbound = 2.0
        ubound = 5.0
        gen = numbergen.UniformRandomOffset(
                seed=_seed,
                mean=(ubound + lbound) / 2,
                range=ubound - lbound)
        for _ in range(_iterations):
            value = gen()
            self.assertTrue(lbound <= value < ubound)
