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
        self.assertEqual(repr(v1), '1.0')

    def test_repr_v101(self):
        v101 = Version(release=(1,0,1), commit='fffffff')
        if not ((repr(v101) == '1.0.1-0-gfffffff') or (repr(v101), '1.0.1-x-gfffffff')):
            raise AssertionError('Unexpected version string returned')

    def test_repr_v101_10_commits(self):
        v101 = Version(release=(1,0,1), commit_count=10, commit='aaaaaaa')
        self.assertEqual(repr(v101), '1.0.1-10-gaaaaaaa')

    def test_repr_v101dev4_10_commits(self):
        v101 = Version(release=(1,0,1), commit_count=10, commit='aaaaaaa', dev=4)
        self.assertEqual(repr(v101), '1.0.1.dev4-10-gaaaaaaa')

    def test_version_init_v101(self):
        Version(release=(1,0,1))

    def test_version_release_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1.release, (1,0))

    def test_version_str_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(str(v1), '1.0')

    def test_version_str_v1dev3(self):
        v1 = Version(release=(1,0),dev=3)
        self.assertEqual(str(v1), '1.0.dev3')

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

    #===========================================#
    #  Update from VCS (currently git describe) #
    #===========================================#

    def test_version_simple_git_describe(self):
        v105 = Version(release=(1,0,5))
        v105._update_from_vcs('v1.0.5-42-gabcdefgh')
        self.assertEqual(v105.release, (1,0,5))
        self.assertEqual(v105.commit_count, 42)
        self.assertEqual(v105.dev, None)
        self.assertEqual(v105.commit, 'abcdefgh')

    def test_version_dev_pep440_git_describe(self):
        v105 = Version(release=(1,0,5), dev=4)
        v105._update_from_vcs('v1.0.6.dev4-42-gabcdefgh')
        self.assertEqual(v105.release, (1,0,6))
        self.assertEqual(v105.commit_count, 42)
        self.assertEqual(v105.dev, 4)
        self.assertEqual(v105.commit, 'abcdefgh')

    def test_version_dev_wo_pep440_git_describe(self):
        v105 = Version(release=(1,0,5), dev=4)
        v105._update_from_vcs('v1.0.6dev4-42-gabcdefgh')
        self.assertEqual(v105.release, (1,0,6))
        self.assertEqual(v105.commit_count, 42)
        self.assertEqual(v105.dev, 4)
        self.assertEqual(v105.commit, 'abcdefgh')

    #===========================#
    #  Comparisons and equality #
    #===========================#

    def test_version_less_than(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual((v1 < v101), True)

    def test_version_less_than_dev(self):
        v101 = Version(release=(1,0,1))
        v101dev2 = Version(release=(1,0,1), dev=2)
        self.assertEqual((v101dev2 < v101), True)

    def test_version_less_than_dev_number(self):
        v101dev1 = Version(release=(1,0,1), dev=1)
        v101dev2 = Version(release=(1,0,1), dev=2)
        self.assertEqual((v101dev1 < v101dev2), True)

    def test_version_greater_than(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual((v1 > v101), False)

    def test_version_greater_than_dev(self):
        v101 = Version(release=(1,0,1))
        v102dev3 = Version(release=(1,0,2), dev=3)
        self.assertEqual((v102dev3 > v101), True)

    def test_version_eq_v1(self):
        v1 = Version(release=(1,0))
        self.assertEqual(v1==v1, True)

    def test_version_eq_v101(self):
        v101 = Version(release=(1,0,1))
        self.assertEqual(v101==v101, True)

    def test_version_eq_v101_dev(self):
        v101dev3 = Version(release=(1,0,1), dev=3)
        self.assertEqual(v101dev3==v101dev3, True)

    def test_version_neq_v101_dev(self):
        v101dev2 = Version(release=(1,0,1), dev=2)
        v101dev3 = Version(release=(1,0,1), dev=3)
        self.assertEqual(v101dev2!=v101dev3, True)

    def test_version_neq(self):
        v1 = Version(release=(1,0))
        v101 = Version(release=(1,0,1))
        self.assertEqual(v1 !=v101, True)


if __name__ == "__main__":
    import nose
    nose.runmodule()
