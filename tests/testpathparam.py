import os
import shutil
import tempfile
import unittest

import param
import pytest

from .utils import check_defaults


class TestPathParameters(unittest.TestCase):

    def setUp(self):
        super(TestPathParameters, self).setUp()

        tmpdir1 = tempfile.mkdtemp()
        fa = os.path.join(tmpdir1, 'a.txt')
        fb = os.path.join(tmpdir1, 'b.txt')
        open(fa, 'w').close()
        open(fb, 'w').close()

        self.tmpdir1 = tmpdir1
        self.fa = fa
        self.fb = fb

        class P(param.Parameterized):
            a = param.Path()
            b = param.Path(self.fb)
            c = param.Path('a.txt', search_paths=[tmpdir1])

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []

    def test_defaults_class(self):
        class P(param.Parameterized):
            p = param.Path()

        check_defaults(P.param.p, label='P')
        self._check_defaults(P.param.p)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            p = param.Path()

        p = P()

        check_defaults(p.param.p, label='P')
        self._check_defaults(p.param.p)

    def test_defaults_unbound(self):
        p = param.Path()

        check_defaults(p, label=None)
        self._check_defaults(p)

    def test_no_path_class(self):
        assert self.P.a is None

    def test_no_path_class(self):
        p = self.P()
        assert p.a is None

    def test_inst_with_path(self):
        p = self.P(a=self.fa)
        assert isinstance(p.a, str)
        assert os.path.isfile(p.a)
        assert os.path.isabs(p.a)
        assert p.a == self.fa

    def test_set_to_None_allowed(self):
        p = self.P()

        assert p.param.b.allow_None is False
        # This should probably raise an error (#708)
        p.b = None

    def test_search_paths(self):
        p = self.P()
        
        assert isinstance(p.c, str)
        assert os.path.isfile(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.fa

    def test_inheritance_behavior(self):

            # a = param.Path()
            # b = param.Path(self.fb)
            # c = param.Path('a.txt', search_paths=[tmpdir1])

        class B(self.P):
            a = param.Path()
            b = param.Path()
            c = param.Path()

        assert B.a is None
        assert B.b == self.fb
        # search_paths is empty instead of [tmpdir1] and getting c raises an error
        assert B.param.c.search_paths == []
        with pytest.raises(OSError, match='Path a.txt was not found'):
            assert B.c is None

        b = B()

        assert b.a is None
        assert b.b == self.fb

        assert b.param.c.search_paths == []
        with pytest.raises(OSError, match='Path a.txt was not found'):
            assert b.c is None


class TestFilenameParameters(unittest.TestCase):

    def setUp(self):
        super(TestFilenameParameters, self).setUp()

        tmpdir1 = tempfile.mkdtemp()
        fa = os.path.join(tmpdir1, 'a.txt')
        fb = os.path.join(tmpdir1, 'b.txt')
        open(fa, 'w').close()
        open(fb, 'w').close()

        self.tmpdir1 = tmpdir1
        self.fa = fa
        self.fb = fb

        class P(param.Parameterized):
            a = param.Filename()
            b = param.Filename(self.fb)
            c = param.Filename('a.txt', search_paths=[tmpdir1])

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []

    def test_defaults_class(self):
        class P(param.Parameterized):
            p = param.Filename()

        check_defaults(P.param.p, label='P')
        self._check_defaults(P.param.p)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            p = param.Filename()

        p = P()

        check_defaults(p.param.p, label='P')
        self._check_defaults(p.param.p)

    def test_defaults_unbound(self):
        p = param.Filename()

        check_defaults(p, label=None)
        self._check_defaults(p)

    def test_no_path_class(self):
        assert self.P.a is None

    def test_no_path_class(self):
        p = self.P()
        assert p.a is None

    def test_inst_with_path(self):
        p = self.P(a=self.fa)
        assert isinstance(p.a, str)
        assert os.path.isfile(p.a)
        assert os.path.isabs(p.a)
        assert p.a == self.fa

    def test_set_to_None_allowed(self):
        p = self.P()

        assert p.param.b.allow_None is False
        # This should probably raise an error (#708)
        p.b = None

    def test_search_paths(self):
        p = self.P()
        
        assert isinstance(p.c, str)
        assert os.path.isfile(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.fa


class TestFoldernameParameters(unittest.TestCase):

    def setUp(self):
        super(TestFoldernameParameters, self).setUp()

        tmpdir1 = tempfile.mkdtemp()
        da = os.path.join(tmpdir1, 'da')
        os.mkdir(da)

        self.tmpdir1 = tmpdir1
        self.da = da

        class P(param.Parameterized):
            a = param.Foldername()
            b = param.Foldername(tmpdir1)
            c = param.Path('da', search_paths=[tmpdir1])

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []

    def test_defaults_class(self):
        class P(param.Parameterized):
            p = param.Foldername()

        check_defaults(P.param.p, label='P')
        self._check_defaults(P.param.p)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            p = param.Foldername()

        p = P()

        check_defaults(p.param.p, label='P')
        self._check_defaults(p.param.p)

    def test_defaults_unbound(self):
        p = param.Foldername()

        check_defaults(p, label=None)
        self._check_defaults(p)

    def test_no_path_class(self):
        assert self.P.a is None

    def test_no_path_class(self):
        p = self.P()
        assert p.a is None

    def test_inst_with_path(self):
        p = self.P(a=self.da)
        assert isinstance(p.a, str)
        assert os.path.isdir(p.a)
        assert os.path.isabs(p.a)
        assert p.a == self.da

    def test_set_to_None_allowed(self):
        p = self.P()

        assert p.param.b.allow_None is False
        # This should probably raise an error (#708)
        p.b = None

    def test_search_paths(self):
        p = self.P()
        
        assert isinstance(p.c, str)
        assert os.path.isdir(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.da
