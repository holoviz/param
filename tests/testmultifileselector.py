import os
import shutil
import tempfile
import unittest

import param

from .utils import check_defaults


class TestMultiFileSelectorParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()

        tmpdir1 = tempfile.mkdtemp()
        fa = os.path.join(tmpdir1, 'a.txt')
        fb = os.path.join(tmpdir1, 'b.txt')
        glob1 = os.path.join(tmpdir1, '*')
        open(fa, 'w').close()
        open(fb, 'w').close()
        tmpdir2 = tempfile.mkdtemp()
        fc = os.path.join(tmpdir2, 'c.txt')
        fd = os.path.join(tmpdir2, 'd.txt')
        glob2 = os.path.join(tmpdir2, '*')
        open(fc, 'w').close()
        open(fd, 'w').close()

        self.tmpdir1 = tmpdir1
        self.tmpdir2 = tmpdir2
        self.fa = fa
        self.fb = fb
        self.fc = fc
        self.fd = fd
        self.glob1 = glob1
        self.glob2 = glob2

        class P(param.Parameterized):
            a = param.MultiFileSelector(path=glob1)
            b = param.MultiFileSelector(default=[fa], path=glob1)

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)
        shutil.rmtree(self.tmpdir2)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is None
        assert p.objects == []
        assert p.compute_default_fn is None
        assert p.check_on_set is False
        assert p.names == {}
        assert p.path == ''

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.MultiFileSelector()

        check_defaults(P.param.s, label='S')
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.MultiFileSelector()

        p = P()

        check_defaults(p.param.s, label='S')
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.MultiFileSelector()

        check_defaults(s, label=None)
        self._check_defaults(s)

    def test_default_is_None(self):
        p = self.P()
        assert p.a is None
        assert p.param.a.default is None

    def test_default_is_honored(self):
        p = self.P()
        assert p.b == [self.fa]
        assert p.param.b.default ==[self.fa]

    def test_allow_default_None(self):
        class P(param.Parameterized):
            a = param.MultiFileSelector(default=None)

    def test_objects_auto_set(self):
        p = self.P()
        assert p.param.a.objects == [self.fa, self.fb]

    def test_default_not_in_glob(self):
        with self.assertRaises(ValueError):
            class P(param.Parameterized):
                a = param.MultiFileSelector(default=['not/in/glob'], path=self.glob1)

    def test_objects_auto_set_sorted(self):
        p = self.P()
        assert sorted(p.param.a.objects) == sorted([self.fa, self.fb])

    def test_set_object_constructor(self):
        p = self.P(a=[self.fb])
        assert p.a == [self.fb]

    def test_set_object_outside_bounds(self):
        p = self.P()
        with self.assertRaises(ValueError):
            p.a = ['/not/in/glob']

    def test_set_path_and_update(self):
        p = self.P()
        p.param.b.path = self.glob2
        p.param.b.update()
        assert sorted(p.param.b.objects) == sorted([self.fc, self.fd])
        assert sorted(p.param.b.default) == sorted([self.fc, self.fd])
        # Default updated but not the value itself
        assert p.b == [self.fa]

    def test_get_range(self):
        p = self.P()
        r = p.param.a.get_range()
        assert r['a.txt'] == self.fa
        assert r['b.txt'] == self.fb
        p.param.a.path = self.glob2
        p.param.a.update()
        r = p.param.a.get_range()
        assert r['c.txt'] == self.fc
        assert r['d.txt'] == self.fd

    def test_update_file_removed(self):
        p = self.P()
        assert p.param.b.objects == [self.fa, self.fb]
        assert p.param.b.default == [self.fa]
        os.remove(self.fa)
        p.param.b.update()
        assert p.param.b.objects == [self.fb]
        assert p.param.b.default == [self.fb]
