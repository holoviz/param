|BuildStatus|_

Param
=====

Param is a library providing Parameters: Python attributes extended to
have features such as type and range checking, dynamically generated
values, documentation strings, default values, etc., each of which is
inherited from parent classes if not specified in a subclass.

Please see `param's website <http://ioam.github.com/param/>`_ for
documentation and examples.
 

Installation
============

Param has no dependencies outside of Python's standard library.

Official releases of Param are available at
`PyPI <http://pypi.python.org/pypi/param>`_, and can be installed via ``pip
install --user param``, ``pip install param``, or ``easy_install param``.
Windows users can alternatively download and run an installer (exe).

More recent changes can be obtained by cloning the git repository.

Release Notes
=============

Notable additions, or changes that may require users to alter code,
are listed below.


1.2.0 (unreleased)
------------------

* Added support for Python 3 (thanks to Marco Elver).
* Dropped support for Python 2.5.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.1.0...v1.2.0>`_.


1.1.0 (2014/05)
---------------

* Switched to Python's own logging module.
* Improved support for time when using Dynamic parameters.
* Optional extension for IPython users.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.0.0...v1.1.0>`_.


1.0.0 (2012/07)
---------------

* First standalone release. Param was originally developed as part of
  `Topographica <http://ioam.github.io/topographica/>`_, and has been
  in heavy usage as part of that project since 2005.


.. |BuildStatus| image:: https://travis-ci.org/ioam/param.svg?branch=master
.. _BuildStatus: https://travis-ci.org/ioam/param
