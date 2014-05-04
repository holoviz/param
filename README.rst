Param
=====

Param is a library providing Parameters: Python attributes extended to
have features such as type and range checking, dynamically generated
values, documentation strings, default values, etc., each of which is
inherited from parent classes if not specified in a subclass.

Please see `param's website <http://ioam.github.com/param/>`_ for documentation and
examples. Release instructions for developers may be 
`found on the wiki <https://github.com/ioam/param/wiki/Release-instructions>`_.

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


1.2.0
------

* Added support for Python 3 (thanks to Marco Elver).
* Dropped support for Python 2.5.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/1.1.0...1.2.0>`_.


1.1.0
------

* Switched to Python's own logging module.
* Improved support for time when using Dynamic parameters.
* Optional extension for IPython users.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/1.0.0...1.1.0>`_.


1.0.0
------

* Initial release.

