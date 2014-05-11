"""
A simple approach to versioning that replaces the need to manually
maintain __version__ strings without requiring larger, less elegant
solutions (e.g. versioneer.py).

It is easy to forget to update __version__ strings when releasing a
project and it is important that the __version__ strings are useful
over the course of development, especially if releases are infrequent.

The Version class is designed to solve these problems, acting as a
simple version string for released versions while making additional
information accessible when working with version control during
development (currently only supports git). Here is a typical example
of how it is used:

__version__ = param.Version(release=(1,0), fpath=__file__)

The Version class assumes that you will tag the release in your
version control system with a string in the form v*.* before the
release is made. By calling the Version.verify method from setup.py,
you will be reminded to create this tag (is it has been forgotten) and
will check that all versioning information has been properly updated.
"""


__author__ = 'Jean-Luc Stevens'

import os, subprocess

class Version(object):
    """
    A simple, approach to versioning that supports PyPI releases and
    additional information when working with git version control. When
    obtaining from PyPI, the version is the supplied release tuple.

    During development `git describe` will be used to compute the
    number of commits since the last version tag, the short commit
    hash and determine if the commit is dirty. Version tags must start
    with a lowercase 'v' e.g. v1.0, v2.0, v0.9.8 etc.

    Note that when git is used, the comparison operators take into
    account the number of commits since the last version tag. This
    approach is often useful in practice but may fail when using
    distributed version control across forks and branches.

    To add git archive support in your project's '__init__.py' file
    you will need to set the following line in .gitattributes:

    __init__.py export-subst
    """

    def __init__(self, release=None, fpath=None, commit=None):
        """
        release:  Release tuple (corresponding to the current git tag)
        fpath:    Set to __file__ to access version control information
        describe: Set to "$Format:%h$" (double quotes) for git archive
        """
        self.fpath = fpath
        self._expected_commit = commit
        self.expected_release = release

        self._commit = None if commit in [None, "$Format:%h$"] else commit
        self._commit_count = 0
        self._release = None
        self._dirty = False

    @property
    def release(self):
        "Return the release tuple"
        return self.fetch()._release

    @property
    def commit(self):
        "The short git SHA"
        return self.fetch()._commit

    @property
    def commit_count(self):
        "Return the number of commits since the last release"
        return self.fetch()._commit_count

    @property
    def dirty(self):
        "True if there are uncommited changes, False otherwise"
        return self.fetch()._dirty

    def fetch(self):
        """
        Returns a tuple of the major version together with the
        appropriate SHA and dirty bit (for development version only).
        """
        if self._release is not None:
            return self

        self._release = self.expected_release
        if not self.fpath:
            self._commit = self._expected_commit
            return self

         # Only git right now but easily extended to SVN, Mercurial etc.
        for cmd in ['git', 'git.cmd', 'git.exe']:
            try:
                self.git_fetch(cmd)
                break
            except EnvironmentError:
                pass
        return self


    def git_fetch(self, cmd='git'):
        cmd = [cmd, 'describe', '--long', '--match', 'v*.*', '--dirty']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=os.path.dirname(self.fpath))
        output, error = (s.decode().strip() for s in proc.communicate())

        if error=='fatal: No names found, cannot describe anything.':
            raise Exception("Cannot find any git version tags of format v*.*")

        # If there is any other error, return (release value still useful)
        if proc.returncode != 0: return self

        split = output[1:].split('-')
        self._release = tuple(int(el) for el in split[0].split('.'))
        self._commit_count = int(split[1])
        self._commit = str(split[2][1:]) # Strip out 'g' prefix ('g'=>'git')
        self._dirty = (split[-1]=='dirty')
        return self

    def __str__(self):
        """
        Version in in x.y.z string format. Does not include the 'v'
        prefix of git version tags as format does not appear to be pip
        compatible.
        """
        return '.'.join(str(el) for el in self.release)

    def __repr__(self):
        return "Version(%r,%r,%r)" % (self.release,
                                      self.fpath if self.fpath else None,
                                      self.commit)

    def __eq__(self, other):
        if self.dirty or other.dirty: return False
        return (self.release, self.commit_count) == (other.release, other.commit_count)

    def __gt__(self, other):
        return (self.release, self.commit_count) > (other.release, other.commit_count)

    def __lt__(self, other):
        return (self.release, self.commit_count) < (other.release, other.commit_count)


    def verify(self):
        """
        Check the version information is consistent with git before
        doing a release. Should be called from setup.py when releasing
        to PyPI.
        """
        if self.release != self.expected_release:
            raise Exception("Declared release does not match current release tag.")

        if self.commit_count !=0:
            raise Exception("Please update the git version tag before release.")

        if self._expected_commit not in [None, "$Format:%h$"]:
            raise Exception("Declared release does not match git version tag")
