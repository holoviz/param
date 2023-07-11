# Getting Started

## Installation

Param has no required dependencies outside of Python's standard library, and so it is very easy to install.

Official releases of Param are available from [conda](https://anaconda.org/ioam/param) and [PyPI](http://pypi.python.org/pypi/param), and can be installed via:

```
conda install -c pyviz param
```

or

```
pip install --user param
```

or

```
pip install param
```

## Using Param to get simple, robust code

The `param` library gives you Parameters, which are used in Parameterized classes.

A Parameter is a special type of Python class attribute extended to have various optional features such as type and range checking, dynamically generated values, documentation strings, default values, etc., each of which is inherited from parent classes if not specified in a subclass or instance:

```{code-block} python
import param

class A(param.Parameterized):
    title = param.String(default="sum", doc="Title for the result")

class B(A):
    a = param.Integer(2, bounds=(0,10), doc="First addend")
    b = param.Integer(3, bounds=(0,10), doc="Second addend")

    def __call__(self):
        return self.title + ": " + str(self.a + self.b)
```

```{code-block} python
>> o1 = B(b=4, title="Sum")
>> o1.a = 5
>> o1()
'Sum: 9'
```

```{code-block} python
>> o1.b
4
```

As you can see, the Parameters defined here work precisely like any other Python attributes in your code, so it's generally quite straightforward to migrate an existing class to use Param. Just inherit from `param.Parameterized`, then provide an optional `Parameter` declaration for each parameter the object accepts, including ranges and allowed values if appropriate. You only need to declare and document each parameter _once_, at the highest superclass where it applies, and its default value all the other metadata will be inherited by each subclass.

Once you've declared your parameters, a whole wealth of features and better behavior is now unlocked! For instance, what happens if a user tries to supply some inappropriate data? With Param, such errors will be caught immediately:

```{code-block} python
>>> B(a="four")
ValueError: Parameter 'a' must be an integer.

>>> o2 = B()
>>> o2.b = -5
ValueError: Parameter 'b' must be at least 0
```

Of course, you could always add more code to an ordinary Python class to check for errors like that, but as described in the [User Guide](user_guide/Simplifying_Codebases), that quickly gets unwieldy, with dozens of lines of exceptions, assertions, property definitions, and decorators that obscure what you actually wrote your code to do. Param lets you focus on the code you're writing, while letting your users know exactly what inputs they can supply.

The types in Param may remind you of the static types found in some languages, but here the validation is done at runtime and is checking not just types but also numeric ranges or for specific allowed values. Param thus helps you not just with programming correctness, as for static types, but also for validating user inputs. Validating user inputs is generally a large fraction of a program's code, because such inputs are a huge source of vulnerabilities and potential error conditions, and Param lets you avoid ever having to write nearly any of that code.

The [User Guide](user_guide/index) explains all the other Param features for simplifying your codebase, improving input validation, allowing flexible configuration, and supporting serialization.

## Using Param for configuration

Once you have declared your Parameters, they are now fully accessible from Python in a way that helps users of your code configure it and control it if they wish. Without any extra work by the author of the class, a user can use Python to reconfigure any of the defaults that will be used when they use these objects:

```{code-block} python
>>> A.title = "The sum is"
>>> B.a = 6

>>> o3 = B()
>>> o3()
'The sum is: 9'
```

Because this configuration is all declarative, the underlying values can come from a YAML file, a JSON blob, URL parameters, CLI arguments, or just about any source, letting you provide users full control over configuration with very little effort. Once you write a Parameterized class, it's up to a user to choose how they want to work with it; your job is done!

## Using Param to explore parameter spaces

Param is valuable for _any_ Python codebase, but it offers features that are particularly well suited for running models, simulations, machine learning pipelines, or other programs where the same code needs to be evaluated multiple times to see how it behaves with different parameter values. To facilitate such usage, numeric parameters in Param can be set to a callable value, which will be evaluated every time the parameter is accessed:

```{code-block} python
>>> import random
>>> o2 = B(a = lambda: random.randint(0,5))

>>> o2(), o2(), o2(), o2()
('The sum is: 6', 'The sum is: 7', 'The sum is: 3', 'The sum is: 3')
```

The code for `B` doesn't have to have any special knowledge or processing of dynamic values, because accessing `a` always simply returns an integer, not the callable function:

```{code-block} python
>>> o2.a
4
```

Thus the author of a Parameterized class does not have to take such dynamic values into account; their code simply works with whatever value is returned by the attribute lookup, whether it's dynamic or not. This approach makes Parameterized code immediately ready for exploration across parameter values, whether or not the code's author specifically provided for such usage.

Param includes a separate and optional module `numbergen` that makes it simple to generate streams of numeric values for use as Parameter values. `numbergen` objects are picklable (unlike a `lambda` as above) and can be combined into expressions to build up parameter sweeps or Monte Carlo simulations:

```{code-block} python
>>> import numbergen as ng

>>> o3 = B(a = ng.Choice(choices=[2,4,6]),
>>>       b = 1+2*ng.UniformRandomInt(ubound=3))

>>> o3(), o3(), o3(), o3()
('The sum is: 11', 'The sum is: 3', 'The sum is: 13', 'The sum is: 7')
```

Numbergen objects support the usual arithmetic operations like +, -, *, /, //, %, **, and `abs()`, and so they can be freely combined with each other or with mathematical constants. They also optionally respect a global "time" (e.g. a simulation time or a logical counter), which lets you synchronize changes to dynamic values without any special coordination code.

## Using Param to build GUIs

Param is useful for any sort of programming, but if you need a GUI with widgets, it turns out that the information captured by a Parameter is very often already what is needed to build such a GUI. For instance, we can use the separate [Panel](https://panel.holoviz.org) library to create widgets in a web browser and display the output from the above class automatically.

Panel and other GUI libraries can of course explicitly instantiate widgets, so why use Param in this way? Simply put, this approach lets you cleanly separate your domain-specific code, clearly declaring the parameters it requires and respects, from your GUI code. The GUI code controls GUI issues like layout and font size, but the fundamental declaration of what parameters are available is done at the level of the code that actually uses it (classes A and B in this case). With Param, you can _separately_ declare all your Parameters right where they are used, achieving robustness, type checking, and clear documentation, while avoiding having your GUI code be tightly bound up with your domain-specific details. This approach helps you build maintainable, general-purpose codebases that can easily be used with or without GUI interfaces, with unattended batch operation not needing any GUI support and GUIs not needing to be updated every time someone adds a new option or parameter to the underlying code.

## Learning more

The [User Guide](user_guide/index) goes through the major features of Param and how to use them. If you are interested in GUI programming, also see the [Param How-to guides](https://panel.holoviz.org/how_to/param/index.html) in Panel, and the rest of the [Panel](https://panel.holoviz.org) docs. Have fun making your life better with Param!
