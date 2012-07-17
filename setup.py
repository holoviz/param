#!/usr/bin/env python

import sys
from distutils.core import setup


setup_args = {}

setup_args.update(dict(
    name='param',
    version='0.01',
    description='Declarative Python programming using Parameters.',

    long_description="""
`Param`_ is a library providing Parameters, a special type of Python
attribute extended to have features such as type and range checking,
dynamically generated values, documentation strings, default values,
etc., each of which is inherited from parent classes if not specified
in a subclass.

Please see http://ioam.github.com/param/ for more information.

Installation
============

Param has no dependencies outside the standard library, and can be
installed via ``easy_install param`` or ``pip install
param``. Alternatively, you can download and unpack the archive below,
and then install with a command like ``python setup.py install``
(e.g. ``sudo python setup.py install`` for a site-wide installation,
or ``python setup.py install --user`` to install into ``~/.local``).

.. _Param:
   http://ioam.github.com/param/
""",

    author= "IOAM",
    author_email= "developers@topographica.org",
    maintainer= "IOAM",
    maintainer_email= "developers@topographica.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://ioam.github.com/topographica.org/',
    packages = ["param"],
    classifiers = [
        "License :: OSI Approved :: BSD License",
# (until packaging tested)
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries"]
))


if __name__=="__main__":
    setup(**setup_args)
