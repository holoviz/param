# Comparison to other approaches

Param was first developed in 2003 for Python 2.1 as part of a long-running brain simulation [project](https://topographica.org), and was made into a separate package on [Github](https://github.com/holoviz/param/graphs/contributors) in 2012.  In the interim a variety of other libraries solving some of the same problems have been developed, including:

- [Traits](http://code.enthought.com/projects/traits)
- [Traitlets](https://github.com/ipython/traitlets)
- [attrs](https://github.com/python-attrs/attrs) (with optional [attrs-strict](https://github.com/bloomberg/attrs-strict))
- [Django models](https://docs.djangoproject.com/en/3.1/topics/db/models)
- [Pydantic](https://pydantic-docs.helpmanual.io)

Plus, Python itself has incorporated mechanisms addressing some of the same issues:

- [Python 3.6+ type annotations](https://www.python.org/dev/peps/pep-0526/)
- [Python 3.7+ data classes](https://docs.python.org/3/library/dataclasses.html)
- [Python 2.6+ namedtuples](https://docs.python.org/3/library/collections.html#namedtuple-factory-function-for-tuples-with-named-fields)
- [Python 2.2+ properties](https://docs.python.org/3/library/functions.html#property)

Each of these approaches overlaps with some but by no means all of the functionality provided by Param, as described below. Also see the comparisons provided with [attrs](https://www.attrs.org/en/stable/why.html) and by an [attr user](https://glyph.twistedmatrix.com/2016/08/attrs.html), which were written about `attrs` but also apply just as well to Param (with Param differing in also providing e.g. GUI support as listed below). [Other info](https://threeofwands.com/why-i-use-attrs-instead-of-pydantic/) comparing `attrs` to `pydantic` is also available.

Here we will use the word "parameter" as a generic term for a Python attribute, a Param Parameter, a Traitlets/HasTraits trait, or an attr `attr.ib`.


## Brevity of code

Python properties can be used to express nearly anything Param or Traitlets can do, but they require at least an order of magnitude more code to do it. You can think of Param and Traitlets as a pre-written implementation of a Python property that implements a configurable parameter. Avoiding having to write that code each time is a big win, because configurable parameters are all over any Python codebase, and Parameter/attr.ib/pydantic/Traits-based approaches lead to much simpler and more maintainable codebases.

Specifically, where Param or Traitlets can express an automatically validated type and bounds on an attribute in a simple and localized one-line declaration like `a = param.Integer(5, bounds=(1,10))`, implementing the same functionality using properties requires changes to the constructor plus separate explicit `get` and `set` methods, each with at least a half-dozen lines of validation code. Though this get/set/validate code may seem easy to write, it is difficult to read, difficult to maintain, and difficult to make comprehensive or exhaustive.
In practice, most programmers simply skip validation or implement it only partially, leaving their code behaving in undefined ways for unexpected inputs. With Param or Traitlets, you don't have to choose between short/readable/maintainable code and heavily validated code; you can have both for far less work!

`pydantic` and `attrs` provide many of these same benefits, though `attrs` type and bounds validation is treated as an extra step that is more general but also typically much more verbose. 

## Runtime checking

Python 3 type annotations allow users to specify types for attributes and function returns, but these types are not normally checked at runtime, and so they do not have the same role of validating user input or programmer error as the type declarations in Params, Traits, Traitlets, pydantic, and attr. They also are limited to the type, so they cannot enforce constraints on range ('state' must be in the list ['Alabama', 'Alaska',...]). Thus even if type hinting is used, programmers still need to write code to actually validate the inputs to functions and methods, which is the role of packages like Param and Traitlets. Note that Pydantic focuses on [generating valid outputs at runtime](https://github.com/samuelcolvin/pydantic/issues/578focused) rather than detecting invalid inputs, so it may or may not be suitable for the same types of applications as the other libraries discussed here.


## Generality and ease of integration with your project

The various Python features listed above are part of the standard library with the versions indicated above, and so do not add any dependencies at all to your build process, as long as you restrict yourself to the Python versions where that support was added.

Param, Traitlets, Pydantic, and attrs are all pure Python projects, with minimal dependencies, and so adding them to any project is generally straightforward. They also support a wide range of Python versions, making them usable in cases where the more recent Python-language features are not available.

Django models offer some of the same ways to declare parameters and generate web-based GUIs (below), but require the extensive Django web framework and normally rely on a database and web server, which in practice limit their usage to users building dedicated web sites, unlike the no-dependency Param and attrs libraries that can be added to Python projects of any type.

Traits is a very heavyweight solution, requiring installation and C compilation of a large suite of tools, which makes it difficult to include in separate projects.

## GUI toolkits

Several of these packages support automatically mapping parameters/traits/attributes into GUI widgets. Although any of them could in principle be supported for any GUI toolkit, only certain GUI interfaces are currently available:

- Panel: Jupyter and Bokeh-server support for Param, mapping Parameters to widgets and ParameterizedObjects to sets of widgets
- ParamTk: (unsupported) TKinter support for Param
- IPywidgets: Jupyter support for Traitlets, but without automatic mapping from trait to widget
- TraitsUI: wxWidgets and Qt support for Traits

## Dynamic values

Param, Traits, Traitlets, Pydantic, and attrs all allow any Python expression to be supplied for initializing parameters, allowing parameter default values to be computed at the time a module is first loaded. Pydantic, Traits, and Traitlets also allow a class author to add code for a given parameter to compute a default value on first access.

  ```python
  >>> from time import time, sleep
  >>> import traitlets as tr
  >>> class A(tr.HasTraits):
  ...        instantiation_time = tr.Float()
  ...        @tr.default('instantiation_time')
  ...        def _look_up_time(self):
  ...            return time()
  ...
  >>> a=A()
  >>> time()
  1634594159.2040331
  >>> sleep(1)
  >>> time()
  1634594165.3485172
  >>> a.instantiation_time
  1634594167.812151
  >>> a.instantiation_time
  1634594167.812151
  >>> sleep(1)
  >>> b=A()
  >>> b.instantiation_time
  1634594178.427819
  ```


Param's equivalent decorator `@param.depends(on_init=True)` will run a method when the Parameterized class is instantiated, not on first access.
On the other hand, Param does allow fully dynamic values for *any* access to a numeric Parameter instance, not just the original instantiation:

  ```python
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
  ```
