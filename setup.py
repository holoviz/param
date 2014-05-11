#!/usr/bin/env python
import sys
from distutils.core import setup
import param

setup_args = {}

setup_args.update(dict(
    name='param',
    version=str(param.__version__),
    description='Declarative Python programming using Parameters.',
    long_description=open('README.rst').read(),
    author= "IOAM",
    author_email= "developers@topographica.org",
    maintainer= "IOAM",
    maintainer_email= "developers@topographica.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://ioam.github.com/param/',
    packages = ["param"],
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries"]
))



if __name__=="__main__":

    if 'bdist_wininst' in sys.argv or 'upload' in sys.argv:
        param.__version__.verify()

    setup(**setup_args)
