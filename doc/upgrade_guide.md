# Upgrade guide

Welcome to the Upgrade Guide for Param! When we make backward-incompatible changes, we will provide a detailed guide on how you can update your code to be compatible with the latest changes.

## Version 2.0

### Breaking changes

#### Parameter attributes inheritance

`Parameter`s have attributes like `default`, `doc`, `bounds`, etc. When redefining a `Parameter` in a subclass, the attributes are meant to be inherited; this is not a new feature, it's a core design of Param. You can see in the example below that the `doc` attribute of the `x` Parameter on the class `B` has been inherited from `A`:

```python
class A(param.Parameterized):

    x = param.Number(default=5, doc='The value of x')

class B(A):

    x = param.Number(default=10)

print(B().param['x'].doc)
# The value of x
```

However, this was broken in some subtle ways! It mostly resolved around `None` being used as the specific sentinel value for allowing inheritance. Let's have a look at two examples that have been fixed in Param 2.0.

In this first example we want to re-set the default value of `x` to `None` in a subclass. As you can see, this was discarded entirely in versions before Param 2.0, while the new version correctly assigns `None`.

```python
class A(param.Parameterized):

    x = param.Number(default=5.0)

class B(A):

    x = param.Number(default=None)

print(B().x)
# Param < 2: 5.0     :(
# Param 2.0: None    :)
```

In this second example we want to narrow the bounds `x` in the subclass `B`. While you would have expected the default value of `5.0` to be inherited from `A`, it turns out that it's not the case, it is instead the default value of the `Number` `Parameter` (`0.0`) that happens to be set on `B.x`.

```python
class A(param.Parameterized):

    x = param.Number(default=5.0, bounds=(-10, 10))

class B(A):

    x = param.Number(bounds=(0, 10))

print(B().x)
# Param < 2: 0.0    :(
# Param 2.0: 5.0    :)
```

These are just two of the most common cases that can affect your code, but there are more obviously. And as you can sense, these changes are subtle enough to have introduced changes in your code without you noticing, i.e. your `Parameter` attributes (like `default`, but other attributes are affected too) can now have different values in subclasses, without you getting any warning or your code raising any error. On its own this change was worth the major bump to Param 2.0!

Because we've worked a lot on making sure that Parameter attributes are properly inherited, we've realized that you can now more easily end up with a Parameter whose state, i.e. the combination of all of its attribute values, is invalid. Therefore, at the end of the class inheritance mechanism, we added a validation of the *default* value and decided for now to only emit a warning when it fails, not to break your code on imports! You should definitely take care of these warnings, they indicate a Parameter is in an invalid state:

```python
class A(param.Parameterized):
    x = param.Number(default=-1, bounds=(-5, 5))

class B(A):
    x = param.Number(bounds=(0, 5))

# Param < 2: No warning and B().x == 0.0
# Param 2.0: Warning and B().x == -1 / ParamFutureWarning: Number parameter 'B.x' failed to validate its default value on class creation, this is going to raise an error in the future. The Parameter is defined with attributes which when combined with attributes inherited from its parent classes (A) make it invalid. Please fix the Parameter attributes.
```

#### Defining custom `Parameter`s

To implement properly the `Parameter` attributes inheritance described in the section below we have had to make some changes to how `Parameter` classes are declared. While the custom `Parameter`s you previously wrote for Param before 2.0 should still work, they might suffer from the same attribute inheritance issues. We now recommend custom `Parameter`s to be written following the pattern we have adopted internally. In particular, we have:

- introduced the `param.parameterized.Undefined` sentinel object that is used as the default value of the `Parameter` parameters in its `__init__()` method
- introduced the `_slot_defaults` class attribute to declare the actual default values of the `Parameter` parameters, e.g. in the example below the default value of `some_attribute` is declared to be `10`
- leveraged `@typing.overload` to expose the real default values to static type checkers and IDEs like VSCode

All put together, this is now how `Parameter`s are structured internally and how we recommend writing custom `Parameter`s:

```python
class CustomParameter(Parameter):

    __slots__ = ['some_attribute']

    _slot_defaults = _dict_update(Parameter._slot_defaults,
        default=None, some_attribute=10
    )

    @typing.overload
    def __init__(
        self,
        default=None, *, some_attribute=10,
        doc=None, label=None, precedence=None, instantiate=False, constant=False,
        readonly=False, pickle_default_value=True, allow_None=False, per_instance=True,
        allow_refs=False, nested_refs=False
    ):
        ...

    def __init__(self, default=Undefined, *, some_attribute=Undefined, **params):
        super().__init__(default=default, **params)
        self.some_attribute = some_attribute

    ...

```

To make this work as expected, we have overriden `Parameter.__getattribute__` to detect whether the attribute value as been set to something that is not `Undefined`, and if not fall back to returning the default value declared in `_slot_defaults`:

```python
print(CustomParameter(some_attribute=0).some_attribute)
# 0

print(CustomParameter().some_attribute)  # Fallback case
# 10
```

#### Default value of `name` accounted for

Every `Parameterized` class is equipped with a `name` `Parameter`. At the class level its value is the class name, this is equivalent to `<class>.__name__`, and at the instance level its value is automatically generated, unless you set it in the constructor:

```python
class A(param.Parameterized):
    x = param.Number()

print(A.name)
# A
print(A().name)
# A00002
print(A(name='some name').name)
# some name
```

However, sometimes you want to set the default value of `name`, as in the following example. Before Param 2.0, the default value was discarded at both the class and instance levels, this is now fixed:

```python
class Person(param.Parameterized):
    name = param.String(default='Eva')

print(Person.name)
# Param < 2: Person         :(
# Param 2.0: Eva            :)

print(Person().name)
# Param < 2: Person0000     :(
# Param 2.0: Eva            :)
```

#### Setting a non-Parameter attribute via the constructor

Before Param 2.0 you could set an instance attribute that was not a `Parameter` via the constructor. This behavior was prone to let typos slip through your code, setting the wrong instance attribute (with a warning though). Starting from Param 2.0 this now raises a `TypeError`, similarly to when you call a Python callable with a wrong parameter name:

```python
class A(param.Parameterized):
    number = param.Number()

A(numbre=10)  # oops typo!
# Param < 2: WARNING:param.A00002: Setting non-parameter attribute numbre=10 using a mechanism intended only for parameters
# Param 2.0: TypeError: A.__init__() got an unexpected keyword argument 'numbre'
```

#### `instance.param.watchers` value changed

`instance.param.watchers` no longer returns the transient watchers state, that isn't very useful, but instead returns what you would expect, i.e. a dictionary of the watchers set up on this instance, which you could previously get from the now deprecated `instance._param_watchers`:

```python
class A(param.Parameterized):
    x = param.Number()

    @param.depends('x', watch=True)
    def cb(self):
        pass

print(A().param.watchers)
# Param < 2: []
# Param 2.0: {'x': {'value': [Watcher(...)]}}
```

#### Clean-up of the `Parameterized` namespace

The methods listed below were removed from the `Parameterized` namespace (i.e. members that are available to classes that inherit from `param.Parameterized`). Most of the time, a replacement method is available from the `.param` namespace:

- `_add_parameter`: use instead `param.add_parameter`
- `params`: use instead `.param.values()` or `.param['param']`
- `set_default`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
- `print_param_defaults`: `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
- `set_param`: use instead `.param.update`
- `set_dynamic_time_fn`: use instead `.param.set_dynamic_time_fn`
- `get_param_values`: use instead `.param.values().items()` (or `.param.values()` for the common case of `dict(....param.get_param_values())`)
- `force_new_dynamic_value`: use instead `.param.force_new_dynamic_value`
- `get_value_generator`: use instead `.param.get_value_generator`
- `inspect_value`: use instead `.param.inspect_value`
- `_set_name`: no replacement
- `__db_print`: no replacement
- `warning`: use instead `.param.warning`
- `message`: use instead `.param.log(param.MESSAGE, ...)`
- `verbose`: use instead `.param.log(param.VERBOSE, ...)`
- `debug`: use instead `.param.log(param.DEBUG, ...)`
- `print_param_values`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
- `defaults`: use instead `{k:v.default for k,v in p.param.objects().items()}`
- `pprint` and `_pprint`: use instead `.param.pprint`
- `script_repr`: use instead `param.parameterized.script_repr`
- `state_pop`: moved to `.param._state_pop`, it might be removed in a future version, let us know if you need it!
- `state_push`: moved to `.param._state_push`, it might be removed in a future version, let us know if you need it!

#### `Parameter` clean-up

- Removed unused `bounds` slot from `Boolean` and `Event`
- Removed private Parameter `_internal_name` slot

#### Additional removals

- Removed `Time.next` method that was only needed for Python 2

### Deprecations

Param 2.0 was supposed to clean up even more Param's API, except that we noticed that deprecating API in the release notes of previous versions was not enough to warn Param's users (including ourselves!), so we decided to postpone removing some APIs and this time properly warn Param's users. We've also spent a lot of time looking at the code base while working on this major release and noticed more clean up that could be made in the future. Therefore and perhaps somewhat unconventionnally we have released Param 2.0 with quite a large number of deprecation warnings. Make sure you're adapting your code as soon as you can whenever you notice one of the newly emitted warnings. You will find below the complete list of deprecation warnings added in Param 2.0.

- Parameter signature:
  - Instantiating most parameters with positional arguments beyond `default` is deprecated:
    - `String('prefix-test', '^prefix')`: deprecated!
    - `String('prefix-test', regex='^prefix')`: OK
    - `String(default='prefix-test', regex='^prefix')`: OK
  - For `Selector` parameters that accept `objects` as first positional argument, and `ClassSelector` parameters that accept `class_` as first positional argument, passing any argument by position is deprecated:
    - `Selector([1, 2])`: deprecated!
    - `Selector(objects=[1, 2])`: OK
    - `ClassSelector((str, int))`: deprecated!
    - `ClassSelector(class_=(str, int))`: OK
    - It's possible that in the future the signature of these two parameters will be aligned with the other parameters to accept `default` as first and only positional argument, but for now please use an explicit keyword so that your code will be compatible with all versions.
- Parameter slots:
  - `List._class`: use instead `item_type`.
  - `Number.set_hook`: no replacement
- `param.__init__` module:
  - `param.produce_value`: no replacement
  - `param.as_unicode`: no replacement
  - `param.is_ordered_dict`: no replacement
  - `param.is_ordered_dict`: no replacement
  - `param.hashable`: no replacement
  - `param.named_objs`: no replacement
  - `param.normalize_path`: no replacement
  - `param.abbreviate_paths`: no replacement
- `param.parameterized` module:
  - `param.parameterized.all_equal`: no replacement
  - `param.parameterized.add_metaclass`: no replacement
  - `param.parameterized.batch_watch`: use instead `batch_call_watchers`
  - `param.parameterized.recursive_repr`: no replacement
  - `param.parameterized.overridable_property`: no replacement
- Parameterized `.param` namespace; many of these methods have been deprecated since version 1.12.0, however, this was just announced in the release notes and we realised many users missed them, sometimes even us included! They now all emit deprecation warnings when executed and are clearly marked as deprecated in the API reference:
  - `.param.set_default`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
  - `.param._add_parameter`: use instead `.param.add_parameter`
  - `.param.params`: use instead `.param.values()` or `.param['param']`
  - `.param.set_param`: use instead `.param.update`
  - `.param.get_param_values`: use instead `.param.values().items()` (or `.param.values()` for the common case of `dict(....param.get_param_values())`)
  - `.param.params_depended_on`: use instead `.param.method_dependencies`
  - `.param.defaults`: use instead `{k:v.default for k,v in p.param.objects().items()}`
  - `.param.print_param_defaults`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
  - `.param.print_param_values`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")`
  - `.param.message`: use instead `.param.log(param.MESSAGE, ...)`
  - `.param.verbose`: use instead `.param.log(param.VERBOSE, ...)`
  - `.param.debug`: use instead `.param.log(param.DEBUG, ...)`
- Running unsafe operations **during Parameterized instance initialization**, instead run these operations after having called `super().__init__(**params)`:
  - `instance.param.objects(instance=True)`
  - `instance.param.trigger("<param_name>")`
  - `instance.param.watch(callback, "<param_name>")`
- Parameterized namespace:
  - `instance._param_watchers` (getter and setter): use instead the property `inst.param.watchers`
