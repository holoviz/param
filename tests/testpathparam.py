import os
import re
import shutil
import tempfile
import unittest

import param
import pytest

from .utils import check_defaults


class TestPathParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()

        tmpdir1 = tempfile.mkdtemp()

        self.curdir = os.getcwd()
        # Chanding the directory to tmpdir1 to test that Path resolves relative
        # paths to absolute paths automatically.
        os.chdir(tmpdir1)

        fa = os.path.join(tmpdir1, 'a.txt')
        fb = os.path.join(tmpdir1, 'b.txt')
        fc = 'c.txt'
        open(fa, 'w').close()
        open(fb, 'w').close()
        open(fc, 'w').close()

        self.tmpdir1 = tmpdir1
        self.fa = fa
        self.fb = fb
        self.fc = fc

        class P(param.Parameterized):
            a = param.Path()
            b = param.Path(self.fb)
            c = param.Path('a.txt', search_paths=[tmpdir1])
            d = param.Path(check_exists=False)
            e = param.Path(self.fc, check_exists=False)
            f = param.Path(self.fc)

        self.P = P

    def tearDown(self):
        os.chdir(self.curdir)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []
        assert p.check_exists is True

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

    def test_no_path_inst(self):
        p = self.P()
        assert p.a is None

    def test_unsupported_type(self):
        with pytest.raises(ValueError):
            param.Path(1)

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

        with pytest.raises(ValueError, match=re.escape(r"Path parameter 'P.b' does not accept None")):
            p.b = None

    def test_relative_cwd_class(self):
        assert os.path.isabs(self.P.f)

    def test_relative_cwd_class_set(self):
        self.P.a = self.fc
        assert os.path.isabs(self.P.a)

    def test_relative_cwd_inst(self):
        assert os.path.isabs(self.P().f)

    def test_relative_cwd_instantiation(self):
        p = self.P(a=self.fc)
        assert os.path.isabs(p.a)

    def test_relative_cwd_set(self):
        p = self.P()
        p.a = self.fc
        assert os.path.isabs(p.a)

    def test_search_paths(self):
        p = self.P()

        assert isinstance(p.c, str)
        assert os.path.isfile(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.fa

    def test_inheritance_behavior(self):

        # Inheritance isn't working great with search_paths and this test
        # isn't designed to be run from the tmpdir directory.
        startd = os.getcwd()
        try:
            os.chdir(self.curdir)
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
        finally:
            os.chdir(startd)

    def test_notfound_instantiation_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"Path file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            param.Path('non/existing/file')

    def test_set_notfound_raises_error(self):
        p = self.P()
        with pytest.raises(
            OSError,
            match=r"Path file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            p.a = 'non/existing/file'

    def test_set_notfound_class_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"Path file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            self.P.a = 'non/existing/file'

    def test_nonexisting_unbound_no_error(self):
        p = param.Path('non/existing/file', check_exists=False)
        assert p.default == 'non/existing/file'

    def test_nonexisting_class_no_error(self):
        self.P.d = 'non/existing/file'
        assert self.P.d == 'non/existing/file'

    def test_nonexisting_instantiation_no_error(self):
        p = self.P(d='non/existing/file')
        assert p.d == 'non/existing/file'

    def test_nonexisting_set_no_error(self):
        p = self.P()
        p.d = 'non/existing/file'
        assert p.d == 'non/existing/file'

    def test_optionalexistence_unbound_no_error(self):
        p = param.Path(self.fa, check_exists=False)
        assert os.path.isabs(p.default)

    def test_optionalexistence_class_no_error(self):
        assert os.path.isabs(self.P.e)
        self.P.d = self.fc
        assert os.path.isabs(self.P.d)

    def test_optionalexistence_instantiation_no_error(self):
        p = self.P(d=self.fc)
        assert os.path.isabs(p.d)

    def test_optionalexistence_set_no_error(self):
        p = self.P()
        p.d = self.fc
        assert os.path.isabs(p.d)

    def test_existence_bad_value(self):
        with pytest.raises(
            ValueError,
            match="'check_exists' attribute value must be a boolean"
        ):
            param.Path(check_exists='wrong_option')


class TestFilenameParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()

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
            d = param.Filename(check_exists=False)

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []
        assert p.check_exists is True

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

    def test_no_path_inst(self):
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
        with pytest.raises(ValueError, match=re.escape(r"Filename parameter 'P.b' does not accept None")):
            p.b = None

    def test_search_paths(self):
        p = self.P()

        assert isinstance(p.c, str)
        assert os.path.isfile(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.fa

    def test_notfound_instantiation_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"File file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            param.Filename('non/existing/file')

    def test_set_notfound_class_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"File file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            self.P.a = 'non/existing/file'

    def test_set_notfound_raises_error(self):
        p = self.P()
        with pytest.raises(
            OSError,
            match=r"File file was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)file'\]"
        ):
            p.a = 'non/existing/file'

    def test_nonexisting_unbound_no_error(self):
        p = param.Filename('non/existing/file', check_exists=False)
        assert p.default == 'non/existing/file'

    def test_nonexisting_class_no_error(self):
        self.P.d = 'non/existing/file'
        assert self.P.d == 'non/existing/file'

    def test_nonexisting_instantiation_no_error(self):
        p = self.P(d='non/existing/file')
        assert p.d == 'non/existing/file'

    def test_nonexisting_set_no_error(self):
        p = self.P()
        p.d = 'non/existing/file'
        assert p.d == 'non/existing/file'


class TestFoldernameParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()

        tmpdir1 = tempfile.mkdtemp()
        da = os.path.join(tmpdir1, 'da')
        os.mkdir(da)

        self.tmpdir1 = tmpdir1
        self.da = da

        class P(param.Parameterized):
            a = param.Foldername()
            b = param.Foldername(tmpdir1)
            c = param.Foldername('da', search_paths=[tmpdir1])
            d = param.Foldername(check_exists=False)

        self.P = P

    def tearDown(self):
        shutil.rmtree(self.tmpdir1)

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is True
        assert p.search_paths == []
        assert p.check_exists is True

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

    def test_no_path_inst(self):
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

        with pytest.raises(ValueError, match=re.escape(r"Foldername parameter 'P.b' does not accept None")):
            p.b = None

    def test_search_paths(self):
        p = self.P()

        assert isinstance(p.c, str)
        assert os.path.isdir(p.c)
        assert os.path.isabs(p.c)
        assert p.c == self.da

    def test_notfound_instantiation_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"Folder folder was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)folder'\]"
        ):
            param.Foldername('non/existing/folder')

    def test_set_notfound_raises_error(self):
        p = self.P()
        with pytest.raises(
            OSError,
            match=r"Folder folder was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)folder'\]"
        ):
            p.a = 'non/existing/folder'

    def test_set_notfound_class_raises_error(self):
        with pytest.raises(
            OSError,
            match=r"Folder folder was not found in the following place\(s\): \['\S+(\\\\|/)non(\\\\|/)existing(\\\\|/)folder'\]"
        ):
            self.P.a = 'non/existing/folder'

    def test_nonexisting_unbound_no_error(self):
        p = param.Foldername('non/existing/folder', check_exists=False)
        assert p.default == 'non/existing/folder'

    def test_nonexisting_class_no_error(self):
        self.P.d = 'non/existing/folder'
        assert self.P.d == 'non/existing/folder'

    def test_nonexisting_instantiation_no_error(self):
        p = self.P(d='non/existing/folder')
        assert p.d == 'non/existing/folder'

    def test_nonexisting_set_no_error(self):
        p = self.P()
        p.d = 'non/existing/folder'
        assert p.d == 'non/existing/folder'
