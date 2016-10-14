#!/usr/bin/env python
import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    # check we can compile on this machine
    import cython; cython.inline("return 1;")
    
    from Cython.Build import cythonize
    ext_modules = cythonize("param/*.py", exclude=['param/ipython.py'])
except:
    ext_modules = []

setup_args = {}

setup_args.update(dict(
    name='param',
    version="1.4.2",
    description='Declarative Python programming using Parameters.',
    long_description=open('README.rst').read() if os.path.isfile('README.rst') else 'Consult README.rst',
    author= "IOAM",
    author_email= "developers@topographica.org",
    ext_modules=ext_modules,
    maintainer="IOAM",
    maintainer_email="developers@topographica.org",
    platforms=['Windows', 'Mac OS X', 'Linux'],
    license='BSD',
    url='http://ioam.github.com/param/',
    packages = ["param","numbergen"],
    provides = ["param","numbergen"],
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

    if ('upload' in sys.argv) or ('sdist' in sys.argv):
        import param, numbergen
        param.__version__.verify(setup_args['version'])
        numbergen.__version__.verify(setup_args['version'])

    setup(**setup_args)
