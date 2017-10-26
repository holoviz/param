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

Parameters make it simple to generate GUIs by separating your semantic
information (what is this parameter? what type can it have? does it
have bounds?) from anything to do with a particular GUI library.  To
use Parameters in a particular GUI toolkit, you just need to write a
simple set of interfaces that indicate how a given Parameter type
should be displayed, and what widgets to generate for it.  Currently,
interfaces are provided for use in Jupyter Notebooks (`ParamNB
<https://github.com/ioam/paramnb>`_) 
or in Tk (`ParamTk <http://ioam.github.com/paramtk/>`_), both of which
make it simple to provide a property sheet that automatically
generates a set of widgets for viewing and editing an object's
Parameters.


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
Parameterized programs can define a time function to maintain a
logical/simulated time, such as the state of a simulator, which
allows all Parameter values to be kept synchronized without
any special coordination code.


Installation
============

Param has no required dependencies outside of Python's standard
library.

Official releases of Param are available on
`Anaconda <https://anaconda.org/ioam/param>`_ and
`PyPI <http://pypi.python.org/pypi/param>`_, and can be installed via
``conda install -c ioam param``, ``pip install --user param``, or 
``pip install param``.

The very latest changes can be obtained via `conda install -c cball
param` or `pip install
https://github.com/ioam/param/archive/master.zip`.  Alternatively, the
`git repository <http://github.com/ioam/param>`_ can be cloned and
then 'develop installed' via `pip install -e .` or `python setup.py
develop`. To run the tests, you can install and run `tox`, or
otherwise install `nose` and run `nosetests`.


Comparison to other packages
============================

Param was first developed in 2003, in the context of the Topographica brain simulator project, and
was made into a separate package in 2012.  In the interim other parameter libraries were
developed, including `Traits <http://code.enthought.com/projects/traits>`_ and 
`Traitlets <https://github.com/ipython/traitlets/>`_.  These libraries have broadly similar goals,
but each differs in important ways:

**Dependencies**: 
  Traits is a much more heavyweight solution, requiring 
  installation of a large suite of tools, including C code, which makes it difficult to include in 
  separate projects.  In contrast, Param and Traitlets are both pure Python projects, with minimal dependencies.  

**GUI toolkits**: 
  Although any of the packages could in principle add support for any
  GUI toolkit, the toolkits actually provided differ: Traits (via the
  separate TraitsUI package) supports wxWidgets and QT, while Param
  supports Tkinter (via the separate ParamTk package) and
  browser-based IPython widgets (via the separate ParamNB package),
  while Traitlets only supports IPython widgets.

..   >>> from time import time
     >>> import traitlets as tr
     >>> class A(tr.HasTraits):
     ...     instantiation_time = tr.Float()
     ...     @tr.default('instantiation_time')
     ...     def _look_up_time(self):
     ...         return time()
     ... 
     >>> a=A()
     >>> a.instantiation_time
     1475587151.967874
     >>> a.instantiation_time
     1475587151.967874
     >>> b=A()
     >>> b.instantiation_time
     1475587164.750875

**Dynamic values**:
  Param, Traits, and Traitlets all allow any Python expression to be
  supplied for initializing parameters, allowing parameter default
  values to be computed at the time a module is first loaded.  Traits
  and Traitlets also allow a class author to add code for a given
  parameter to compute a default value on first access.  Param does
  not provide any special support for programmatic default values,
  instead allowing fully dynamic values for *any* numeric Parameter
  instance:

  >>> from time import time
  >>> import param
  >>> class A(param.Parameterized):
  ...     val=param.Number(0)
  ... 
  >>> a=A()
  >>> a.val
  0
  >>> a.val=lambda:time()
  >>> a.val
  1475587455.437027
  >>> a.val
  1475587456.501314

  Note that here it is the *user* of a Parameterized class, not the
  author of the class, that decides whether any particular value is
  dynamic, without writing any new methods or other code.  All the
  usual type checking, etc. is done on dynamic values when they are
  computed, and so the rest of the code does not need to know or care
  whether the user has set a particular parameter to a dynamic value.
  This approach provides an enormous amount of power to the user,
  without making the code more complex.

**On_change callbacks**
  Traitlets and Traits allow the author of a HasTraits-derived class
  to specify code to run when a specific parameter used in that class
  instance is modified.  Param supports similar capabilities, but not
  at the Parameterized class level, only at the Parameter class level
  or as part of ParamNB.  I.e., a class author needs to first write a
  new Parameter class, adding methods to implement checking on
  changes, and then add it to a Parameterized class, or else such
  functionality can be added as callbacks at the whole-object level,
  using ParamNB. Each approach has advantages and disadvantages, and
  per-parameter on_change callbacks could be added in the future if
  there are clear use cases.

All of these packages also overlap in functionality with Python
properties, which were added to the language after Traits and Param
were developed.  Like parameters and traits, properties act like
attributes with possible method-like actions, and so they can all be
used to provide the same user-visible functionality.  However,
implementing Param/Traits-like functionality using properties would
require vastly more code (multiple method definitions for *every*
parameter in a class), and so in practice Parameters and Traits are
much more practical for the use cases that they cover.
  

Release notes
=============

Recent release notes are available on `GitHub 
<https://github.com/ioam/param/releases>`_.

For older releases, see our `historical release notes
<historical_release_notes.html>`_.


Support
=======

Questions and comments are welcome at https://github.com/ioam/param/issues.

