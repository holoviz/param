import os
import shutil
import tempfile

import param

from . import API1TestCase


class TestFileSelectorParameters(API1TestCase):

    def setUp(self):
        super(TestFileSelectorParameters, self).setUp()

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
            a = param.FileSelector(path=glob1)
            b = param.FileSelector(default=fa, path=glob1)

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)
        shutil.rmtree(self.tmpdir2)

    def test_default_is_None(self):
        p = self.P()
        assert p.a is None

    def test_objects_auto_set(self):
        p = self.P()
        assert p.param.a.objects == [self.fa, self.fb]

    def test_default_None(self):
        class P(param.Parameterized):
            a = param.FileSelector(default=None)

    def test_default_not_in_glob(self):
        with self.assertRaises(ValueError):
            class P(param.Parameterized):
                a = param.FileSelector(default='not/in/glob', path=self.glob1)

    def test_set_object_constructor(self):
        p = self.P(a=self.fb)
        assert p.a == self.fb

    def test_set_object_outside_bounds(self):
        p = self.P()
        with self.assertRaises(ValueError):
            p.a = '/not/in/glob'

    def test_update_path(self):
        p = self.P()
        p.param.a.path = self.glob2
        assert p.param.a.objects == [self.fc, self.fd]

    def test_update_path_reset_default(self):
        p = self.P()
        assert p.b == self.fa
        assert p.param.b.default == self.fa
        p.param.b.path = self.glob2
        assert p.param.b.default is None
        # Default updated but not the value itself
        assert p.b == self.fa

    def test_get_range(self):
        p = self.P()
        r = p.param.a.get_range()
        assert r['a.txt'] == self.fa
        assert r['b.txt'] == self.fb
        p.param.a.path = self.glob2
        r = p.param.a.get_range()
        assert r['c.txt'] == self.fc
        assert r['d.txt'] == self.fd
