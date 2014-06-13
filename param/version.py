"""
A simple approach to automatically maintaining __version__ strings for
Python packages, as an alternative to larger, more complex solutions
like versioneer.py.

It is easy to forget to update __version__ strings when releasing a
project and it is important that the __version__ strings are useful
over the course of development, especially if releases are infrequent.

The Version class is designed to solve these problems, acting like a
simple version string for released versions while making additional
information accessible when working with version control during
development.  Currently the only version control system supported is
git, but others could be added easily. If version.py is in a package,
all you need to do to declare the version of the package is to add
two lines like this to the package's __init__.py file:

from .version import Version
__version__ = Version(release=(1,0), fpath=__file__)

The Version class assumes that you will tag the release in your
version control system with a string of the form v*.* before the
release is made, e.g. v1.0 or v2.6.3.  As a safety check, you can also
add a call to Version.verify() in your setup.py script, which will
remind you to create this tag if necessary, and will check that the
declared version in setup.py is consistent with the tag.

This file is in the public domain.  Anyone is free to copy, modify,
publish, use, compile, sell, or distribute it, for any purpose,
commercial or non-commercial, and by any means.  
The original file is maintained at:
https://github.com/ioam/param/blob/master/param/version.py
"""


__author__ = 'Jean-Luc Stevens'

import os, subprocess

def run_cmd(args, cwd=None):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=cwd)
    output, error = (str(s.decode()).strip() for s in proc.communicate())

    if proc.returncode != 0:
        raise Exception(proc.returncode, error)
    return output

class Version(object):
    """
    A simple approach to Python package versioning that supports PyPI
    releases and additional information when working with version
    control. When obtaining a package from PyPI, the version returned
    is a string-formatted rendering of the supplied release tuple.
    For instance, release (1,0) tagged as "v1.0" in the version
    control system will return "1.0" for str(__version__).  Any number
    of items can be supplied in the release tuple, with either two or
    three numeric versioning levels typical.

    During development, `git describe` will be used to compute the
    number of commits since the last version tag, the short commit
    hash, and whether the commit is dirty (has changes not yet
    committed). Version tags must start with a lowercase 'v' and have
    a period in them, e.g. v2.0, v0.9.8, v0.1a, or v0.2beta.  Note
    that any non-numeric portion of the version ("a", "beta", etc.)
    will currently be discarded for the purposes of numeric comparisons. 

    Also note that when version control information is used, the comparison
    operators take into account the number of commits since the last
    version tag. This approach is often useful in practice to decide
    which version is newer for a single developer, but will not
    necessarily be reliable when comparing against a different fork or
    branch in a distributed version control system.

    For git, if you want version control information available even in
    an exported archive (e.g. a .zip file from GitHub), you can set
    the following line in the .gitattributes file of your project:

    __init__.py export-subst
    """

    def __init__(self, release=None, fpath=None, commit=None, reponame=None):
        """
        release:  Release tuple (corresponding to the current git tag)
        fpath:    Set to __file__ to access version control information
        reponame: Used to verify VCS repository name.
        """
        self.fpath = fpath
        self._expected_commit = commit
        self.expected_release = release

        self._commit = None if commit in [None, "$Format:%h$"] else commit
        self._commit_count = 0
        self._release = None
        self._dirty = False
        self.reponame = reponame

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

         # Only git right now but easily extended to SVN, Mercurial, etc.
        for cmd in ['git', 'git.cmd', 'git.exe']:
            try:
                self.git_fetch(cmd)
                break
            except EnvironmentError:
                pass
        return self


    def git_fetch(self, cmd='git'):
        try:
            if self.reponame is not None:
                # Verify this is the correct repository
                output = run_cmd([cmd, 'remote', '-v'],
                                 cwd=os.path.dirname(self.fpath))
                if '/' + self.reponame + '.git' not in output:
                    return self

            output = run_cmd([cmd, 'describe', '--long', '--match', 'v*.*', '--dirty'],
                             cwd=os.path.dirname(self.fpath))
        except Exception as e:
            if e.args[1] == 'fatal: No names found, cannot describe anything.':
                raise Exception("Cannot find any git version tags of format v*.*")
            # If there is any other error, return (release value still useful)
            return self

        split = output[1:].split('-')
        self._release = tuple(int(el) for el in split[0].split('.'))
        self._commit_count = int(split[1])
        self._commit = str(split[2][1:]) # Strip out 'g' prefix ('g'=>'git')
        self._dirty = (split[-1]=='dirty')
        return self


    def __str__(self):
        """
        Version in x.y.z string format. Does not include the 'v'
        prefix of git version tags, for pip compatibility.

        If the commit count is non-zero or the repository is dirty, 
        the string representation is equivalent to the output of:

        `git describe --long --match v*.* --dirty` (with 'v' prefix removed)
        """
        if self.release is None: return 'None'
        release = '.'.join(str(el) for el in self.release)
        if self.commit_count == 0 and not self.dirty:
            return release

        dirty_status = '-dirty' if self.dirty else ''
        return '%s-%d-g%s%s' % (release, self.commit_count,
                                self.commit, dirty_status)

    def __repr__(self):
        return "Version(%r,%r,%r)" % (self.release,
                                      self.fpath if self.fpath else None,
                                      self.commit)

    def abbrev(self,dev_suffix=""):
        """
        Abbreviated string representation, optionally declaring whether it is 
        a development version.
        """
        return '.'.join(str(el) for el in self.release) + \
            (dev_suffix if self.commit_count > 0 or self.dirty else "")



    def __eq__(self, other):
        """
        Two versions are considered equivalent if and only if they are
        from the same release, with the same commit count, and are not
        dirty.  Any dirty version is considered different from any
        other version, since it could potentially have any arbitrary
        changes even for the same release and commit count.
        """
        if self.dirty or other.dirty: return False
        return (self.release, self.commit_count) == (other.release, other.commit_count)

    def __gt__(self, other):
        return (self.release, self.commit_count) > (other.release, other.commit_count)

    def __lt__(self, other):
        return (self.release, self.commit_count) < (other.release, other.commit_count)


    def verify(self):
        """
        Check that the version information is consistent with git before
        doing a release. Should be called from setup.py before releasing
        to PyPI.
        """
        if self.dirty:
            raise Exception("Current working directory is dirty.")

        if self.release != self.expected_release:
            raise Exception("Declared release does not match current release tag.")

        if self.commit_count !=0:
            raise Exception("Please update the git version tag before release.")

        if self._expected_commit not in [None, "$Format:%h$"]:
            raise Exception("Declared release does not match git version tag")
