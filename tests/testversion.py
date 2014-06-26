"""
Unit test for param.version.Version
"""
import unittest
from param.version import Version


class TestVersion(unittest.TestCase):

    def test_version_init_v1(self):
        Version(release=(1,0))

    def test_repr_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(repr(v1), 'Version((1, 0),None,None)')

    def test_repr_v101(self):
        v101 = Version(release=(1,0,1), commit='shortSHA')
        self.assertEqual(repr(v101), "Version((1, 0, 1),None,'shortSHA')")

    def test_version_init_v101(self):
        Version(release=(1,0,1))

    def test_version_release_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1.release, (1,0))

    def test_version_str_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(str(v1), '1.0')

    def test_version_v1_dirty(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1.dirty, False)

    def test_version_v1_commit_count(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1.commit_count, 0)

    def test_version_release_v101(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(v101.release, (1,0,1))

    def test_version_str_v101(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(str(v101), '1.0.1')

    def test_version_v101_dirty(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(v101.dirty, False)

    def test_version_v101_commit_count(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(v101.commit_count, 0)

    def test_version_commit(self):
        "No version control system assumed for tests"
        v1 = Version(release=(1,0), commit='shortSHA')
        self.assertEqual(v1.commit, 'shortSHA')

    #===========================#
    #  Comparisons and equality #
    #===========================#

    def test_version_less_than(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual((v1 < v101), True)

    def test_version_greater_than(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual((v1 > v101), False)

    def test_version_eq_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1==v1, True)

    def test_version_eq_v101(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(v101==v101, True)

    def test_version_neq(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual(v1 !=v101, True)


if __name__ == "__main__":
    import nose
    nose.runmodule()
