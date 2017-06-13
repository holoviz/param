************************
Historical release notes
************************

Note: current release notes are on `GitHub 
<https://github.com/ioam/param/releases>`_.

Notable additions, or changes that may require users to alter code,
are listed below.


1.4.1 (2016/07)
_______________

* Selector parameters now respect order of options supplied
* Allowed softbounds to be accessed like an attribute

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.4.0...v1.4.1>`_.


1.4.0 (2016/07)
_______________

* Added support for new `ParamNB <https://github.com/ioam/paramnb>`_ project
* Added new parameter types Action, FileSelector, and ListSelector

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.3.2...v1.4.0>`_.


1.3.2 (2015/04)
_______________

* Added Unicode support for param.String.
* Minor bugfixes.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.3.1...v1.3.2>`_.


1.3.1 (2015/03)
_______________

* Minor bugfix release to restore pre-1.3.0 script_repr behavior
  (accidentally changed in 1.3.0) and to fix issues with logging.
* Param's logging interface now matches that of Python's logging
  module, making it simpler to use logging (see Python's logging
  module for details). Note therefore that Param's logging methods (a)
  no longer call functions that are passed as arguments (instead,
  Python's logging module does lazy string merges), and (b) no longer
  automatically combine strings passed as arguments (instead, Python's
  logging module supports string formatting).
* Improved set_param() method, now allowing multiple parameters to be
  set easily via keyword arguments (as on initialization).

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.3.0...v1.3.1>`_.


1.3.0 (2015/03)
_______________

* Added 'allow_None' support to all Parameters. Any subclass of
  Parameter that checks types and/or values should be modified to add
  appropriate handling of allow_None.
* Improved pretty printing (script_repr) of Parameterized instances,
  and made available via the pprint method. The script_repr name will
  be removed in a future release.
* Added (reproducible) time-dependent random streams
  (numbergen.TimeAwareRandomState).
* Added label and unit parameters to param.Time class.
* Improved optional IPython extension.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.2.1...v1.3.0>`_.


1.2.1 (2014/06)
_______________

* Minor bugfix release to fix issues with version when param is
  installed in a foreign git repository
* Made version module optional
* Improved ClassSelector and ParamOverrides

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.2.0...v1.2.1>`_.


1.2.0 (2014/06)
_______________

* Added support for Python 3 (thanks to Marco Elver).
* Dropped support for Python 2.5.
* Added version module.
* Added optional numbergen package.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.1.0...v1.2.0>`_.


1.1.0 (2014/05)
_______________

* Switched to Python's own logging module.
* Improved support for time when using Dynamic parameters.
* Optional extension for IPython users.

A full list of changes since the previous release is available 
`on GitHub <https://github.com/ioam/param/compare/v1.0.0...v1.1.0>`_.


1.0.0 (2012/07)
_______________

* First standalone release.


Pre-1.0 (2003)
______________

* Param was originally developed as part of `Topographica
  <http://ioam.github.io/topographica/>`_, and has been in heavy
  usage as part of that project since 2003.
