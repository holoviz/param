# Param - Static Typing - Problem

[HoloViz Param](https://param.holoviz.org/) is a powerful library for defining parameters on `param.Parameterized` classes:

```python
import param

class MyClass(param.Parameterized):
    my_parameter = param.String(default="some value", doc="A custom parameter")
```

## The Core Problem

**Param does not play well with Python's static typing ecosystem.**

Modern Python development expects type annotations to:
- Enable code completion and inline documentation in editors (like VS Code, PyCharm)
- Allow static analysis and error checking with tools like mypy and pylint
- Make code easier to understand, refactor, and maintain

But with Param, these benefits are lost:

- **No Automatic Type Inference:** When you declare a parameter (e.g. `my_parameter = param.String(...)`), neither the class nor its instances have a type annotation for `my_parameter`. Editors and type checkers cannot know its type.
- **Poor Editor Experience:** You don't get tab completion, hover help, or docstrings for parameter attributes on instances. For example, `instance.my_parameter` is invisible to your IDE.
- **False Type Checker Warnings:** Type checkers like mypy and pylint may complain about missing attributes or unknown types, even when the code is correct. For example, `instance.data.iloc` may trigger errors if `data` is a `param.DataFrame` parameter.
- **Unhelpful Constructor Signatures:** The `__init__` method of a `param.Parameterized` class does not show which parameters can be set, making it hard for users and tools to know what arguments are accepted.

### Why This Is a Big Deal

- **Static typing is now standard in Python.** Most modern libraries, editors, and teams expect it.
- **Without static typing, Param is harder to use, debug, and maintain.**
- **New users struggle to discover and use parameters.**
- **Advanced tooling (refactoring, auto-completion, documentation) is much less effective.**

## Example

```python
class Scatter2dWithSelectionComponent(param.Parameterized):
    data: pd.DataFrame = param.DataFrame(precedence=0.1)
```

Even with a type annotation, editors and type checkers do not recognize `data` as a `pd.DataFrame` on the instance. This leads to poor auto-completion and false warnings.

## What Is Needed

- **Automatic type annotations for parameters.** Parameter attributes should be typed so editors and type checkers know their types.
- **Constructor signatures that reflect available parameters.**
- **Better editor integration for auto-completion and documentation.**
- **No breaking changes unless absolutely necessary.**
- **Bonus:** If the solution speeds up Param or makes it compatible with dataclasses or Pydantic, that's a huge win.

See the full discussion and examples in [GitHub Issue #376](https://github.com/holoviz/param/issues/376).