*****
Param
*****

Param is a library providing Parameters: Python attributes extended to
have features such as type and range checking, dynamically generated
values, documentation strings, default values, etc., each of which is
inherited from parent classes if not specified in a subclass.


What is a Parameter?
====================
A Parameter is a special type of Python attribute extended to have features such as type and range checking, dynamically generated values, documentation strings, default values, etc., each of which is inherited from parent classes if not specified in a subclass.


>>> import param,random
>>> class A(param.Parameterized):
...    a = param.Number(0.5,bounds=(0,1),doc="Probability that...")
...    b = param.Boolean(False,doc="Enable feature...")

>>> class B(A):
...    b = param.Boolean(True)

>>> x = B(a=lambda: random.uniform(0,1))

>>> x.a
0.37053399325641945

>>> x.a
0.64907392300071842


Parameters provide optional range and type checking
___________________________________________________


>>> x.a=5
[...]
ValueError: Parameter 'a' must be at most 1

>>> x.a="0.5"
[...]
ValueError: Parameter 'a' only takes numeric values

Parameters have docstrings
__________________________


>>> help(x)
[...]
class B(A)
[...]
   Data descriptors defined here:
   b
       Enable feature...
[...]
   Data descriptors inherited from A:
   a
       Probability that...

Param is lightweight
____________________

Param consists of two BSD-licensed Python files, with no dependencies outside of the standard library.


Parameters make GUI programming simpler
_______________________________________

Parameters make it simple to generate GUIs. An interface for Tk already exists (`ParamTk <http://ioam.github.com/paramtk/>`_), providing a property sheet that can automatically generate a GUI window for viewing and editing an object's Parameters.


Installation
============

Official releases of Param are available at `PyPI <http://pypi.python.org/pypi/param>`_, and can be installed via `pip install param` or `easy_install param` (or via `python setup.py install` of the source).

More recent changes can be obtained by cloning the `git repository <http://github.com/ioam/param>`_.

|BuildStatus|_

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


Support
=======

Questions and comments are welcome at https://github.com/ioam/param/issues.


.. |BuildStatus| image:: https://travis-ci.org/ioam/param.svg?branch=master
.. _BuildStatus: https://travis-ci.org/ioam/param
