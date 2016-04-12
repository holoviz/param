*****
Param
*****

Param is a library providing Parameters: Python attributes extended to
have features such as type and range checking, dynamically generated
values, documentation strings, default values, etc., each of which is
inherited from parent classes if not specified in a subclass.  Param
lets you program declaratively in Python, by just stating facts about
each of your parameters, and then using them throughout your code.
With Parameters, error checking will be automatic, which eliminates
huge amounts of boilerplate code that would otherwise be required to
verify or test user-supplied values.

Param-based programs tend to contain much less code than other Python
programs, instead just having easily readable and maintainable
manifests of Parameters for each object or function.  This way your
remaining code can be much simpler and clearer, while users can also
easily see how to use it properly.

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

Param consists of two required BSD-licensed Python files, with no
dependencies outside of the standard library, and so it can easily be
included as part of larger projects without adding external dependencies.


Parameters make GUI programming simpler
_______________________________________

Parameters make it simple to generate GUIs. An interface for Tk already exists (`ParamTk <http://ioam.github.com/paramtk/>`_), providing a property sheet that can automatically generate a GUI window for viewing and editing an object's Parameters.


Optional dynamic parameter values using `numbergen`
_______________________________________

Providing random or other types of varying values for parameters can
be tricky, because unnamed ("lambda") functions as used above cannot
easily be pickled, causing problems for people who wish to store
Parameterized objects containing random state.  To avoid users having
to write a separate function for each random value, Param includes an
optional set of value-generating objects that are easily configured
and support pickling.  These objects are available if you import the
optional `numbergen` module.  If you wish to use numbergen, the above
example can be rewritten as:

>>> import param,numbergen
>>> class A(param.Parameterized):
...    a = param.Number(0.5,bounds=(0,1),doc="Probability that...")
...    b = param.Boolean(False,doc="Enable feature...")

>>> class B(A):
...    b = param.Boolean(True)

>>> x = B(a=numbergen.UniformRandom())
  
Numbergen objects support the usual arithmetic operations like +, -,
\*, /, //, %, \*\*, and abs(), and so they can be freely combined with
each other or with mathematical constants:

>>> y = B(a=2.0*numbergen.UniformRandom()/(numbergen.NormalRandom()+1.5))

Note that unlike the lambda-function approach, all varying numbergen
objects respect `param.Dynamic.time_fn`, e.g. to ensure that new
values will be generated only when Param's time has changed.


Installation
============

Param has no dependencies outside of Python's standard library.

Official releases of Param are available at
`PyPI <http://pypi.python.org/pypi/param>`_, and can be installed via ``pip
install --user param``, ``pip install param``, or ``easy_install param``.
Windows users can alternatively download and run an installer (exe).

More recent changes can be obtained by cloning the `git repository <http://github.com/ioam/param>`_.

Comparison to other packages
============================

Param was first developed in 2004, in the context of the Topographica brain simulator project, and
was made into a separate package until 2012.  During that time there were other parameter libraries
developed, including `Traits <http://code.enthought.com/projects/traits>`_ and 
`Traitlets <https://github.com/ipython/traitlets/>`_.  These libraries have broadly similar goals,
but each differs in important ways:

* **Dependencies**: Traits is a much more heavyweight solution, requiring 
installation of a large suite of tools, including C code, which makes it difficult to include in 
separate projects.  Param and Traitlets are both pure Python projects, with minimal dependencies.  

* **GUI toolkits**: The packages differ on which GUI toolkits are supported: Traits (via the 
separate TraitsUI package) supports wxWidgets and QT, while Param supports Tkinter (via the 
separate ParamTk package) and IPython widgets (via the separate ParamNB package), and Traitlets
supports IPython widgets.  

* **Dynamic support**: The packages differ in how they support "active" or "dynamic" values.  
Traits and Traitlets provide extensive mechanisms for defining custom callbacks and "onchange"
code associated with specific user-defined trait instances, which can be very valuable when it is
needed, but requires a significant amount of code to be written each time support for such 
dynamic execution is provided to users.  Param instead focuses on supporting dynamic parameter 
*values* for any parameter, not on implementing specific dynamic parameter *definitions*, 
allowing users to provide dynamic streams of values for any Parameter that has been defined.  
The `numbergen` package included with Param make it simple to define such streams (e.g. 
random values, values determined by a mathematical function, or values calculated using
arbitrary Python code). Users can then define a clock function for Param so that it is clear 
when the next dynamic value should be returned; each dynamic value is then a function of this
global clock value.  Param's approach is particularly well suited for use when there is a 
concept of time, whether simulated or real time, because it makes it simple to
coordinate many different dynamic parameter values without requiring any code to do the
coordination or handle generating the dynamic values themselves.

Release Notes
=============

Notable additions, or changes that may require users to alter code,
are listed below.

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

* First standalone release. Param was originally developed as part of
  `Topographica <http://ioam.github.io/topographica/>`_, and has been
  in heavy usage as part of that project since 2005.


Support
=======

Questions and comments are welcome at https://github.com/ioam/param/issues.

