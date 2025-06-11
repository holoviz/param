# Releases

## Version 2.2.1

Date: 2025-06-11

This patch release contains a bug fix for nested references. Thanks to @philippjfr for their contribution.

Bug Fixes:

- Do not remove nested_refs when updating another ref ([#1061](https://github.com/holoviz/param/pull/1061))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.2.0...v2.2.1)

## Version 2.2.0

Date: 2024-12-16

This minor release brings a few enhancements and bugfixes. Importantly, it includes some breaking changes, removing deprecated APIs or raising errors during unsafe operations which would previously only emit warnings. Many thanks to @gandhis1 and @JRRudy1 for their first contributions, and to @hoxbro, @maximlt,and @MarcSkovMadsen for their continued maintenance and development efforts.

Enhancements:

- Annotate `depends` and `accept_arguments` decorators ([#962](https://github.com/holoviz/param/pull/962))
- Stop directly importing numpy and add `gen_types` decorator ([#966](https://github.com/holoviz/param/pull/966))

Bug Fixes:

- Added missing `super().__init_subclass__` call in `_ParameterBase.__init_subclass__` ([#969](https://github.com/holoviz/param/pull/969))
- Remove `_dict_update` ([#980](https://github.com/holoviz/param/pull/980))

Documentation:

- Improve some docstrings and set up `ruff` to validate them ([#977](https://github.com/holoviz/param/pull/977), [#982](https://github.com/holoviz/param/pull/982), and [#983](https://github.com/holoviz/param/pull/983))

Breaking changes / Deprecations:

- Remove `_param_watchers`, raise `RuntimeError` on unsafe ops during init, and failed validation of a parameter default after inheritance ([#973](https://github.com/holoviz/param/pull/973))
- Promote many deprecation warnings to future warnings ([#974](https://github.com/holoviz/param/pull/974))

Compatibility:

- Test Python 3.13 ([#971](https://github.com/holoviz/param/pull/971))
- Drop Python 3.8 support ([#986](https://github.com/holoviz/param/pull/986))

Infrastructure / Tests:

- Replace `hatch` with `pixi` ([#971](https://github.com/holoviz/param/pull/971))
- Fix reactive tests failing intermittently on Windows ([#971](https://github.com/holoviz/param/pull/971), [#967](https://github.com/holoviz/param/pull/967))
- Change linting to `ruff` ([#978](https://github.com/holoviz/param/pull/978))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.1.1...v2.2.0)

## Version 2.1.1

Date: 2024-06-25

This minor release contains bug fixes for reactive expressions and a few minor documentation improvements. Thanks to @jrycw for their first contribution! And to @ahuang11, @maximlt, and @philippjfr for their continued maintenance and development efforts.

Bug fixes:

- Ensure `rx._callback` resolves accessors ([#949](https://github.com/holoviz/param/pull/949))
- Ensure refs can be updated by watcher of the same parameter ([#929](https://github.com/holoviz/param/pull/929))
- Recursively resolve references on args and kwargs passed to a reactive operation ([#944](https://github.com/holoviz/param/pull/944))
- Only override the name of a Parameterized instance on Parameter instantiation when `instantiate=True` ([#938](https://github.com/holoviz/param/pull/938))

Documentation:

- Various minor documentation improvements ([#933](https://github.com/holoviz/param/pull/933), [#935](https://github.com/holoviz/param/pull/935), [#941](https://github.com/holoviz/param/pull/941), [#947](https://github.com/holoviz/param/pull/947))

Maintenance:

- Fix `test_reactive_logic_unary_ops` on Python 3.12 ([#946](https://github.com/holoviz/param/pull/946))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.1.0...v2.1.1)

## Version 2.1.0

Date: 2024-03-22

This minor release focuses on improving reactive expressions and support for asynchronous (and synchronous) generators. Many thanks to @maximlt, @Hoxbro and @philippjfr for their continued maintenance and development efforts.

Enhancements:

- Improvements for synchronous and asychronous generators ([#908](https://github.com/holoviz/param/pull/908))
- Additions to the .rx namespace including `and_`, `bool`, `map`, `not_`, `or_` and `updating` ([#906](https://github.com/holoviz/param/pull/906))
- Add support for adding asynchronous watcher to `rx` ([#917](https://github.com/holoviz/param/pull/917))
- Make it possible to resolve reactive expressions recursively with `.rx.resolve` ([#918](https://github.com/holoviz/param/pull/918))
- Add support for async and generator functions in `.rx.pipe` ([#924](https://github.com/holoviz/param/pull/924))

Bug fixes:

- Ensure that `.param.update` context manager restore refs ([#915](https://github.com/holoviz/param/pull/915))
- Avoid overeager root invalidation on `rx` leading to unnecessary evaluation ([#919](https://github.com/holoviz/param/pull/919))

Deprecations:

- Passing positional arguments to `Parameter` now raises a `ParamDeprecationWarning` ([#921](https://github.com/holoviz/param/pull/921))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.0.2...v2.1.0)

## Version 2.0.2

Date: 2024-01-17

This patch release fixes a few bugs and introduces a performance enhancement. Many thanks to @alfredocarella for their first contribution, and to the maintainers @maximlt and @philippjfr for contributing to this release.

Optimization:

- Minor optimizations in hot codepaths accessing class parameters ([#893](https://github.com/holoviz/param/pull/893))

Bug fixes:

- Unpack partial callables in `iscoroutinefunction` ([#894](https://github.com/holoviz/param/pull/894))
- Fix building Param with `setuptools-scm<7` ([#903](https://github.com/holoviz/param/pull/903))

Documentation:
- Replace *Google Analytics* with *GoatCounter* ([#895](https://github.com/holoviz/param/pull/895))
- Fix a typo in `Outputs.ipynb` ([#892](https://github.com/holoviz/param/pull/892))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.0.1...v2.0.2)

## Version 2.0.1

Date: 2023-11-08

This minor release fixes a number of bugs, including a regression introduced by the replacement of the build backend (`setuptools` for `hatchling`) which led to the `doc` folder being wrongly packaged. Many thanks to @SultanOrazbayev for their first contribution, to @musicinmybrain for spotting the regression and submitting fixes, and to the maintainers @Hoxbro, @jbednar and @maximlt for contributing to this release.

Bug fixes:

- Do not install `doc` folder in *site-packages* ([#878](https://github.com/holoviz/param/pull/878))
- Drop the `feather-format` test dependency ([#879](https://github.com/holoviz/param/pull/879))
- Add `tables` to the `tests-deser` extra ([#880](https://github.com/holoviz/param/pull/880))
- Fix `_state_push` and `_state_pop` ([#884](https://github.com/holoviz/param/pull/884))
- `version.py`: new process should not create a window on Windows ([#882](https://github.com/holoviz/param/pull/882), [#886](https://github.com/holoviz/param/pull/886))
- Don't import `setuptools_scm` if the `.git` folder doesn't exist ([#885](https://github.com/holoviz/param/pull/885))

Documentation:

- Add migration guide to Param 2.0 ([#883](https://github.com/holoviz/param/pull/883))
- Update Parameter API reference ([#881](https://github.com/holoviz/param/pull/881))

[*Full Changelog*](https://github.com/holoviz/param/compare/v2.0.0...v2.0.1)

## Version 2.0.0

Date: 2023-10-24

20 years after its creation, Param has reached version 2.0! Can you guess when Param 3.0 will be released?

Param 2.0 is a major new release available for Python 3.8 and above, significantly streamlining, simplifying, and improving the Param API. Many long-supported but also long-obsolete functions, methods, and usages will now warn loudly so that you can make sure your code is only using the fully supported and safe current approaches. Because upgrading to Param 2 is likely to reveal compatibility issues with older codebases, new releases in the 1.x series are expected to continue for some time, focused on compatibility with the ecosystem rather than adding new features. Thus you can keep using Param 1.x with your older code, but Param 2 is the future!

We would like to thank @minimav for their first contribution, and @droumis, @Hoxbro, @jbednar, @maximlt, @philippjfr and @sdrobert for their contributions. We would also like to thank @ceball, who made the first plans for Param 2.0 quite a few years ago, and we are glad to be delivering on them at last!

### Major enhancements and features

- Parameter slot values are now all inherited correctly across a hierarchy of Parameterized classes, making their behavior much clearer and more consistent. Let's say we have class `B` being a subclass of `A`, itself being a subclass of `param.Parameterized`. If `A` defines `x = Number(1, bounds=(0, 10))` and `B` defines `x = Number(2)`, `B.param['x'].bounds` is now going to be inherited from `A` and equal to `(0, 10)` as you would expect. Parameterized classes have always supported inheritance, but the previous mechanism was based on using `None` to indicate which values should be inherited, which was highly problematic because `None` was also a valid value for many slots. All Parameter slot signatures now default to the new `Undefined` sentinel, finally allowing `None` to be inherited where appropriate. ([#605](https://github.com/holoviz/param/pull/605), [#771](https://github.com/holoviz/param/pull/771), [#791](https://github.com/holoviz/param/pull/791), [#874](https://github.com/holoviz/param/pull/874))
- The `objects` slot of a Selector was previously highly confusing, because it accepted either a dictionary or a list for initialization but then was accessible only as a list, making it difficult to watch or update the objects. There is now a `ListProxy` wrapper around `Selector.objects` (with forward and backward compatibility) to easily update `objects` and watch `objects` updates ([#598](https://github.com/holoviz/param/pull/598), [#825](https://github.com/holoviz/param/pull/825))
- Parameterized classes and instances now have a rich HTML representation that is displayed automatically in a Jupyter/IPython notebook. For a class or instance `p`, just return `p.param` in a notebook cell to see a table of all the Parameters of the class/instance, their state, type, and range, plus the docstring on hover. It is likely we will improve the content and design of this repr based on feedback, so please let us know what you think! ([#425](https://github.com/holoviz/param/pull/425), [#781](https://github.com/holoviz/param/pull/781), [#821](https://github.com/holoviz/param/pull/821), [#831](https://github.com/holoviz/param/pull/831))
- Parameters have all gained the `allow_refs` and `nested_refs` attributes, bringing an exceptionally useful feature that was available in Panel since version 1.2 to Param. Declaring a Parameter with `allow_refs=True` (`False` by default) allows setting this Parameter value with a *reference* to automatically mirror the value of the reference. Supported references include class/instance Parameter objects, functions/methods decorated with `param.depends`, reactive functions and expressions, asynchronous generators and custom objects transformed into a valid reference with a hook registered with `param.parameterized.register_reference_transform`. `nested_refs` indicate whether references should be resolved even when they are nested inside a container ([#843](https://github.com/holoviz/param/pull/843), [#845](https://github.com/holoviz/param/pull/845), [#849](https://github.com/holoviz/param/pull/849), [#865](https://github.com/holoviz/param/pull/865), [#862](https://github.com/holoviz/param/pull/862), [#876](https://github.com/holoviz/param/pull/876))
- Experimental new `rx` reactive expressions: Param is widely used for building web apps in the HoloViz ecosystem, where packages have added various mechanisms for dynamic updates (e.g. `pn.bind` and `pn.depends` in Panel, and `.interactive` in hvPlot). These mechanisms were already built on Param and can be used far more widely than just in those packages, so that functionality has now been generalized, streamlined, and moved into Param. Nearly any Python expression can now be made reactive with `param.rx()`, at which point it will collect and be able to replay any operations (e.g. method calls) performed on them. This reactive programming approach lets you take just about any existing Python workflow and replace attributes with widgets or other reactive values, creating an app with fine-grained user control without having to design callbacks, event handlers, or any other complex logic! `rx` support is still experimental while we get feedback about the API, packaging, and documentation, but it's fully ready to try out and give us suggestions!
([#460](https://github.com/holoviz/param/pull/460), [#842](https://github.com/holoviz/param/pull/842), [#841](https://github.com/holoviz/param/pull/841), [#844](https://github.com/holoviz/param/pull/844), [#846](https://github.com/holoviz/param/pull/846), [#847](https://github.com/holoviz/param/pull/847), [#850](https://github.com/holoviz/param/pull/850), [#851](https://github.com/holoviz/param/pull/851), [#856](https://github.com/holoviz/param/pull/856), [#860](https://github.com/holoviz/param/pull/860), [#854](https://github.com/holoviz/param/pull/854), [#859](https://github.com/holoviz/param/pull/859), [#858](https://github.com/holoviz/param/pull/858), [#873](https://github.com/holoviz/param/pull/873))


### Enhancements

- Parameter slot values that are set to mutable containers (e.g. `Selector(objects=a_list)`) will now be shallow-copied on instantiation, so that the container is no longer confusingly shared between the class and its subclasses and instances ([#826](https://github.com/holoviz/param/pull/826))
- To further clean up the Parameterized namespace (first started in version 1.7.0), the remaining private attributes haven been collected under two private namespaces `_param__private` and `_param__parameters` ([#766](https://github.com/holoviz/param/pull/766), [#790](https://github.com/holoviz/param/pull/790))
- You can now use `.param.update` as a context manager for applying temporary updates ([#779](https://github.com/holoviz/param/pull/779))
- The `name` Parameter has always had special behavior dating to its use in labeling objects in a GUI context, but this behavior is now able to be overriden at the class and instance level ([#740](https://github.com/holoviz/param/pull/740))
- Improved Parameter signatures for static and dynamic code analysis ([#742](https://github.com/holoviz/param/pull/742))
- Removed inferred Parameterized docstring signature and add basic `__signature__` support ([#802](https://github.com/holoviz/param/pull/802))
- For speed, only generate the Parameter docstring in an IPython context ([#774](https://github.com/holoviz/param/pull/774))
- Improve Parameter validation error messages ([#808](https://github.com/holoviz/param/pull/808))
- Support for deserialization of file types into `Array` and `DataFrame` ([#482](https://github.com/holoviz/param/pull/482))
- `Integer` now accepts `numpy.integer` values ([#735](https://github.com/holoviz/param/pull/735))
- `Range` now does stricter validation of the slot values ([#725](https://github.com/holoviz/param/pull/725), [#824](https://github.com/holoviz/param/pull/824))
- `Path` now has `check_exists` attribute, leading it to raise an error if `path` is not found on parameter instantiation ([#800](https://github.com/holoviz/param/pull/800))
- Add top-level `__all__` and move Parameter classes to `parameters.py` ([#853](https://github.com/holoviz/param/pull/853))

### Bug fixes

- Allow type change for `DateRange` and `Date` ([#733](https://github.com/holoviz/param/pull/733))
- Ensure class watchers are not inherited by instance parameter ([#833](https://github.com/holoviz/param/pull/833))
- Fix multi-level indirection in Parameters access ([#840](https://github.com/holoviz/param/pull/840))
- Ensure non-function types are not resolved as empty function declarations ([#753](https://github.com/holoviz/param/pull/753))
- Fix watchers support when the Parameterized instance is falsy ([#769](https://github.com/holoviz/param/pull/769))
- Fix depending on the method of a sub-parameter object ([#765](https://github.com/holoviz/param/pull/765))
- Raise an error on bad non-watched references ([#777](https://github.com/holoviz/param/pull/777))
- Ensure that the root dependency can be resolved, and error otherwise ([#813](https://github.com/holoviz/param/pull/813))
- Fix basic pickling ([#783](https://github.com/holoviz/param/pull/783), [#792](https://github.com/holoviz/param/pull/792))
- Validate that `self` is present in the `__init__` signature of a Parameterized class ([#786](https://github.com/holoviz/param/pull/786))
- No longer force `instantiate` to True when `constant` is True ([#776](https://github.com/holoviz/param/pull/776))
- Instantiate default Parameter values based on all the Parameters available ([#798](https://github.com/holoviz/param/pull/798))
- `Array`: fix `param.pprint` ([#795](https://github.com/holoviz/param/pull/795))
- `Array`: don't hard-code `allow_None` to `True` ([#726](https://github.com/holoviz/param/pull/726))
- `Boolean`: validate the default type ([#722](https://github.com/holoviz/param/pull/722))
- `FileSelector`: made more consistent with `Selector` by defaulting to the first globbed path ([#801](https://github.com/holoviz/param/pull/801))
- `FileSelector`: ensure path separators are consistent on Windows ([#805](https://github.com/holoviz/param/pull/805))
- `Path`: raise a `ValueError` if set to `None` while not allowed ([#799](https://github.com/holoviz/param/pull/799))
- `Selector`: populate `objects` when `check_on_set` is False and `default` is not in `objects` ([#794](https://github.com/holoviz/param/pull/794), [#817](https://github.com/holoviz/param/pull/817))
- `File/MultiFileSelector`: updating `path` updates `objects` ([#814](https://github.com/holoviz/param/pull/814))

### Documentation

- Build the site with `sphinx` directly and refactor the API reference ([#810](https://github.com/holoviz/param/pull/810))
- Update to the latest version of `pydata-sphinx-theme` ([#752](https://github.com/holoviz/param/pull/752))
- Update to Google Analytics 4 ([#758](https://github.com/holoviz/param/pull/758))
- Fix minor errors in the Getting Started ([#787](https://github.com/holoviz/param/pull/787))
- Add OpenCollective sponsor link on the repository page ([#811](https://github.com/holoviz/param/pull/811))

### Infrastructure

- Increase the test suite coverage ([#716](https://github.com/holoviz/param/pull/716), [#717](https://github.com/holoviz/param/pull/717), [#719](https://github.com/holoviz/param/pull/719), [#720](https://github.com/holoviz/param/pull/720), [#739](https://github.com/holoviz/param/pull/739), [#775](https://github.com/holoviz/param/pull/775), [#778](https://github.com/holoviz/param/pull/778))
- Turn warnings into exceptions in the test suite ([#738](https://github.com/holoviz/param/pull/738))
- Add notebook smoke tests ([#750](https://github.com/holoviz/param/pull/750))
- Upgrades to leverage `hatch`, `pyproject.toml` and `pre-commit` ([#749](https://github.com/holoviz/param/pull/749), [#772](https://github.com/holoviz/param/pull/772))
- Add basic benchmark suite using `asv` ([#788](https://github.com/holoviz/param/pull/788))
- Reduce the number of tested Python versions ([#732](https://github.com/holoviz/param/pull/732))
- Run the tests with Python 3.12 ([#863](https://github.com/holoviz/param/pull/863))

### Compatibility

- Drop support for Python 2.7, 3.6, and 3.7 and upgrade the code base accordingly ([#741](https://github.com/holoviz/param/pull/741), [#784](https://github.com/holoviz/param/pull/784))

### Breaking changes

- While it's a major improvement to the definition of Parameters, properly inheriting Parameter slots can result in some Parameter slot values being different in Param 2, because Param 1 was sometimes silently not inheriting slot values.
- User-defined `Parameter` classes should be updated to use `Undefined` as the formal default for any new slots, with the actual default defined on the new `_slot_defaults` dictionary. Otherwise, any new slot will fail to support inheritance, even if it was set to `None`, which would previously support inheritance.
- `Parameterized` methods that were deprecated since Param 1.7.0 have finally been removed. These are now mostly available on the `.param` namespace ([#592](https://github.com/holoviz/param/pull/592))
- No longer supports setting non-Parameter class attributes during initialization, and no longer warns when setting non-Parameter class attributes directly ([#729](https://github.com/holoviz/param/pull/729))
- `instance.param.watchers` no longer returns the transient dict of watchers but instead returns the instance watchers, as the now deprecated `instance._param_watchers` ([#797](https://github.com/holoviz/param/pull/797))
- Removed deprecated `Parameterized.pprint`, `Parameterized._pprint`, `Parameterized.script_repr`, `ParameterizedFunction.script_repr` ([#767](https://github.com/holoviz/param/pull/767))
- Removed `Time.next` method needed only for Python 2, and moved `Parameterized.state_pop` and `Parameterized.state_push` to the `.param` namespace ([#767](https://github.com/holoviz/param/pull/767))
- Some removals were considered harmless and thus implemented immediately without a deprecation period:
  - Removed unused `bounds` slot from `Boolean` and `Event` ([#744](https://github.com/holoviz/param/pull/744), [#755](https://github.com/holoviz/param/pull/755))
  - Removed private Parameter `_internal_name` slot ([#796](https://github.com/holoviz/param/pull/796))

### Deprecations

This section lists functionality that is expected to be removed sometime in the next couple of 2.x releases, so if you use Param 2, please take care of these warnings as soon as you encounter them, and certainly before you upgrade to the next release!

Param 2.0 adds a validation step of the *default* value of a Parameter after the inheritance mechanism has completed if its type has changed (e.g. `x` in class `A` is a `Number` and in class `B(A)` is an `Integer`) or one of its slot values has changed ([#812](https://github.com/holoviz/param/pull/812), [#820](https://github.com/holoviz/param/pull/820), [#857](https://github.com/holoviz/param/pull/857)). We have decided to only emit a warning when this validation fails to make your life easier when upgrading your code from Param 1 to 2, as the validation is performed on class creation which means that any validation error breaks importing your code. You should definitely take care of these warnings, they indicate a Parameter is in an invalid state!

We continue to clean up Param's API ([#734](https://github.com/holoviz/param/pull/734), [#751](https://github.com/holoviz/param/pull/751), [#768](https://github.com/holoviz/param/pull/768), [#797](https://github.com/holoviz/param/pull/797), [#834](https://github.com/holoviz/param/pull/834), [#838](https://github.com/holoviz/param/pull/838)) but have decided to do it in a gentle way, emitting deprecation warnings for a period of time before proceeding with removals. You will find below the complete list of deprecation warnings added in Param 2.0.

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

[*Full Changelog*](https://github.com/holoviz/param/compare/v1.13.0...v2.0.0)

## Version 1.13.0

Date: 2023-03-14

The `1.13.0` is the last release of Param before the 2.0 release. However, Param 1.13 is meant to receive long-term support; security patches and fixes to critical bugs are planned to be backported to the 1.13.x series.

This release includes a new `Bytes` *Parameter* and a few important bug fixes. This release is also marked by the adoption of a formal project governance, ensuring Param's future as a healthy open-source project. Many thanks to @ovidner and @droumis for their first contributions! And to @maximlt, @Hoxbro, @jlstevens, @philippjfr and @jbednar for their continuing support to fixing and improving Param.

Bug fixes:

* Fix copying when having watchers on e.g. bounds on inherited Parameter types ([#675](https://github.com/holoviz/param/pull/675))
* Allow JSON serialization to work with `json.dumps` ([#655](https://github.com/holoviz/param/pull/655))
* `ListSelector` restricted to `list` type objects ([#531](https://github.com/holoviz/param/pull/531))
* Fix `depends` async wrapper ([#684](https://github.com/holoviz/param/pull/684))
* Allow named colors to be any case ([#711](https://github.com/holoviz/param/pull/711))

New features:

* Add Bytes parameter ([#542](https://github.com/holoviz/param/pull/542))

Documentation:

* Fix param module link ([#682](https://github.com/holoviz/param/pull/682))

Project governance:

* Create initial project governance docs ([#674](https://github.com/holoviz/param/pull/674))

Maintenance:

* Rename `master` branch to `main` ([#672](https://github.com/holoviz/param/pull/672))
* Add more tests ([#710](https://github.com/holoviz/param/pull/710))
* Various CI related fixes ([#680](https://github.com/holoviz/param/pull/680), [#683](https://github.com/holoviz/param/pull/683) and [#709](https://github.com/holoviz/param/pull/709))

## Version 1.12.3

Date: 2022-12-06

The `1.12.3` release adds support for Python 3.11. Many thanks to @musicinmybrain (first contribution!) and @maximlt for contributing to this release.

Enhancements:

* Preserve existing Random seed behavior in Python 3.11 ([#638](https://github.com/holoviz/param/pull/638))
* Add support for Python 3.11 ([#658](https://github.com/holoviz/param/pull/658))

## Version 1.12.2

Date: 2022-06-14

The `1.12.2` release fixes a number of bugs and adds support again for Python 2.7, which was unfortunately no longer supported in the last release. Note however that Param 2.0 will still drop support of Python 2.7 as already announced. Many thanks to @Hoxbro and the maintainers @jbednar, @jlstevens, @maximlt and @philippjfr for contributing to this release.

Bug fixes:

* Match against complete spec name when determining dynamic watchers ([#615](https://github.com/holoviz/param/pull/615))
* Ensure async functionality does not cause python2 syntax errors ([#624](https://github.com/holoviz/param/pull/624))
* Allow (de)serializing `CalendarRange` and `DateRange` `Parameters` ([#625](https://github.com/holoviz/param/pull/625))
* Improve `DateRange` validation ([#627](https://github.com/holoviz/param/pull/627))
* Fix regression in `@param.depends` execution ordering ([#628](https://github.com/holoviz/param/pull/628))
* Ensure `named_objs` does not fail on unhashable objects ([#632](https://github.com/holoviz/param/pull/632))
* Support comparing date-like objects ([#629](https://github.com/holoviz/param/pull/629))
* Fixed `BinaryPower` example in the docs to use the correct name `EvenInteger`([#634](https://github.com/holoviz/param/pull/634))

## Version 1.12.1

The 1.12.1 release fixes a number of bugs related to async callback handling when using `param.depends` and `.param.watch` and a number of documentation and error messages. Many thanks to @HoxBro and the maintainers @jbednar, @jlstevens, @maximlt and @philippjfr for contributing to this release.

Error handling and documentation:

- Fixed description of shared_parameters ([#568](https://github.com/holoviz/param/pull/568))
- Improve the error messages of Date and DateRange ([#579](https://github.com/holoviz/param/pull/579))
- Clarified step error messages and other docs and links ([#604](https://github.com/holoviz/param/pull/604))

Bug fixes:

- Make iscoroutinefunction more robust ([#572](https://github.com/holoviz/param/pull/572))
- Fix for handling misspelled parameter ([#575](https://github.com/holoviz/param/pull/575))
- Handle None serialization for Date, CalendarDate, Tuple, Array, and DataFrame ([#582](https://github.com/holoviz/param/pull/582))
- Support async coroutines in param.depends ([#591](https://github.com/holoviz/param/pull/591))
- Handle async functions in depends with watch=True ([#611](https://github.com/holoviz/param/pull/611))
- Avoid equality check on Watcher ([#612](https://github.com/holoviz/param/pull/612))

Documentation:

- Fix binder ([#564](https://github.com/holoviz/param/pull/564))
- Fixed description of shared_parameters ([#568](https://github.com/holoviz/param/pull/568))

## Version 1.12.0

Version 1.12.0 introduces a complete user manual and website (for the first time since 2003!) along with extensive API improvements gearing up for the 2.0 release (which will be Python3 only).

The pre-2.0 API is still being preserved and no new warnings are added in this release, so the older API can continue to be used with this release, but the next 1.x release is expected to enable warnings for deprecated API. If you have older code using the deprecated Param features below, please update your API calls as described below to be compatible with the 2.0 release when it comes out (or pin to param<2 if you don't need any new Param features). For new users, just use the API documented on the website, and you should be ready to go for either 1.12+ or 2.0+.

Thanks to James A. Bednar for the user guide and 2.0 API support, to Philipp Rudiger for improvements and new capabilities for handling dependencies on subobjects, and to Maxime Liquet and Philipp Rudiger for extensive improvements to the website/docs/package-building/testing.

New features:
- Added future-facing API for certain Parameterized().param methods (see Compatibility below; [#556](https://github.com/holoviz/param/pull/556), [#558](https://github.com/holoviz/param/pull/558), [#559](https://github.com/holoviz/param/pull/559))
- New option `on_init=True` for `@depends` decorator, to run the method in the constructor to ensure initial state is consistent when appropriate ([#540](https://github.com/holoviz/param/pull/540))
- Now resolves subobject dependencies dynamically, allowing dependencies on internal parameters of subobjects to resolve appropriately as those objects are replaced. ([#552](https://github.com/holoviz/param/pull/552))
- Added prettyprinting for numbergen expressions ([#525](https://github.com/holoviz/param/pull/525))
- Improved JSON schema generation ([#458](https://github.com/holoviz/param/pull/458))
- Added more-usable script_repr command, availabie in param namespace, with default values, and showing imports ([#522](https://github.com/holoviz/param/pull/522))
- Added Parameterized.param.pprint(); underlying implementation of script_repr but with defaults suitable for interactive usage rather than generating a .py script. ([#522](https://github.com/holoviz/param/pull/522))
- Watchers can now declare precedence so that events are triggered in the desired order ([#552](https://github.com/holoviz/param/pull/552), [#557](https://github.com/holoviz/param/pull/557))

Bug fixes:
- Fix bug setting attributes in some cases before class is initialized ([#544](https://github.com/holoviz/param/pull/544))
- Ensure None is supported on ListSelector ([#511](https://github.com/holoviz/param/pull/511))
- Switched from deprecated `inspect.getargspec` to the py3 version `inspect.getfullargspec`, which is similar but splits `keyword` args into `varkw` (**) and kw-only args. Falls back to getargspec on Python2. ([#521](https://github.com/holoviz/param/pull/521))

Doc improvements (including complete user guide for the first time!):
- Misc comments/docstrings/docs cleanup ([#507](https://github.com/holoviz/param/pull/507), [#518](https://github.com/holoviz/param/pull/518), [#528](https://github.com/holoviz/param/pull/528), [#553](https://github.com/holoviz/param/pull/553))
- Added comparison with pydantic ([#523](https://github.com/holoviz/param/pull/523))
- Added new user guide sections:
    * Dependencies_and_Watchers user guide ([#536](https://github.com/holoviz/param/pull/536))
    * Dynamic Parameters ([#525](https://github.com/holoviz/param/pull/525))
    * Outputs ([#523](https://github.com/holoviz/param/pull/523))
    * Serialization and Persistence ([#523](https://github.com/holoviz/param/pull/523))

Infrastructure:
- Added testing on Python 3.10 and on Mac OS X and removed slow PyPy/pandas/numpy tests ([#548](https://github.com/holoviz/param/pull/548), [#549](https://github.com/holoviz/param/pull/549), [#526](https://github.com/holoviz/param/pull/526))
- Docs/tests/build infrastructure improvements ([#509](https://github.com/holoviz/param/pull/509), [#521](https://github.com/holoviz/param/pull/521), [#529](https://github.com/holoviz/param/pull/529), [#530](https://github.com/holoviz/param/pull/530), [#537](https://github.com/holoviz/param/pull/537), [#538](https://github.com/holoviz/param/pull/538), [#539](https://github.com/holoviz/param/pull/539), [#547](https://github.com/holoviz/param/pull/547), [#548](https://github.com/holoviz/param/pull/548), [#555](https://github.com/holoviz/param/pull/555))

Compatibility (see [#543](https://github.com/holoviz/param/pull/543) for the complete list):
- Calendardate now accepts date values only ([#517](https://github.com/holoviz/param/pull/517))
- No longer allows modifying name of a Parameter once it is in a Parameterized class, to avoid confusion ([#541](https://github.com/holoviz/param/pull/541))
- Renamed (with old name still accepted for compatibility until 2.0):
    * `.param._add_parameter()`: Now public `.param.add_parameter()`; too useful to keep private! ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.params_depended_on`: Now `.param.method_dependencies` to indicate that it accepts a method name and returns its dependencies ([#559](https://github.com/holoviz/param/pull/559))
    * `.pprint`: Now private `._pprint`; use public `.param.pprint` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `batch_watch`: Now `batch_call_watchers`, to declare that it does not set up watching, it just invokes it. Removed unused operation argument  ([#536](https://github.com/holoviz/param/pull/536))

- Deprecated (but not yet warning unless noted):
    * `.param.debug()`: Use `.param.log(param.DEBUG, ...)` instead ([#556](https://github.com/holoviz/param/pull/556))
    * `.param.verbose()`: Use `.param.log(param.VERBOSE, ...)` instead ([#556](https://github.com/holoviz/param/pull/556))
    * `.param.message()`: Use `.param.log(param.MESSAGE, ...)` instead ([#556](https://github.com/holoviz/param/pull/556))
    * `.param.defaults()`: Use `{k:v.default for k,v in p.param.objects().items()}` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.deprecate()`:  To be repurposed or deleted after 2.0 ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.params()`:  Use `.param.values()` or `.param['param']` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.print_param_defaults()`: Use `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.print_param_values()`: Use `for k,v in p.param.values().items(): print(f"{p.name}.{k}={v}")` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.set_default()`: Use `p.param.default=` instead ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.set_param()`: Had tricky API; use `.param.update` instead ([#558](https://github.com/holoviz/param/pull/558))
    * `.param.get_param_values()`: Use `.param.values().items()` instead (or `.param.values()` for the common case of `dict(....param.get_param_values())`) ([#559](https://github.com/holoviz/param/pull/559))
    * `.state_pop()`: Will be renamed to `._state_pop` to make private
    * `.state_push()`: Will be renamed to `._state_push` to make private
    * `.initialized`: Will be renamed to `._initialized` to make private
    * Most methods on Parameterized itself have already been deprecated and warning for some time now; see [#543](https://github.com/holoviz/param/pull/543) for the list. Use the corresponding method on the `.param` accessor instead.

- Added:
    * `.param.watchers`: Read-only version of private `_watchers` ([#559](https://github.com/holoviz/param/pull/559))
    * `.param.log()`: Subsumes .debug/verbose/message; all are logging calls. ([#556](https://github.com/holoviz/param/pull/556))
    * `.param.update()`: Dictionary-style updates to parameter values, as a drop-in replacement for `set_param` except for its optional legacy positional-arg syntax ([#558](https://github.com/holoviz/param/pull/558))
    * `.values()`: Dictionary of name:value pairs for parameter values, replacing `get_param_values` but now a dict since python3 preserves order ([#558](https://github.com/holoviz/param/pull/558))
    * `.param.log()`: General-purpose interface to the logging module functionailty; replaces .debug, .verbose, .message ([#556](https://github.com/holoviz/param/pull/556))

## Version 1.11.1

(including changes in 1.11.0; 1.11.1 adds only a minor change to fix `param.List(None)`.)

Version 1.11 contains entirely new [documentation](https://param.holoviz.org), plus various enhancements and bugfixess. Thanks to James A. Bednar for the documentation, Philipp Rudiger for the website setup and for many of the other fixes and improvements below, and others as noted below.

Documentation:
- Brand-new website, with getting started, user manual, reference manual, and more! Some user guide sections are still under construction. ([#428](https://github.com/holoviz/param/pull/428),[#464](https://github.com/holoviz/param/pull/464),[#479](https://github.com/holoviz/param/pull/479),[#483](https://github.com/holoviz/param/pull/483),[#501](https://github.com/holoviz/param/pull/501),[#502](https://github.com/holoviz/param/pull/502),[#503](https://github.com/holoviz/param/pull/503),[#504](https://github.com/holoviz/param/pull/504))
- New intro video with examples/Promo.ipynb notebook, thanks to Marc Skov Madsen and Egbert Ammicht ([#488](https://github.com/holoviz/param/pull/488))
- Sort docstring by definition order and precedence, thanks to Andrew Huang ([#445](https://github.com/holoviz/param/pull/445))

Enhancements:
- Allow printing representations for recursively nested Parameterized objects ([#499](https://github.com/holoviz/param/pull/499))
- Allow named colors for param.Color ([#472](https://github.com/holoviz/param/pull/472))
- Allow FileSelector and MultiFileSelector to accept initial values ([#497](https://github.com/holoviz/param/pull/497))
- Add Step slot to Range, thanks to Simon Hansen ([#467](https://github.com/holoviz/param/pull/467))
- Update FileSelector and MultiFileSelector parameters when setting path ([#476](https://github.com/holoviz/param/pull/476))
- Improved error messages ([#475](https://github.com/holoviz/param/pull/475))

Bug Fixes:
- Fix Path to allow folders, as documented but previously not supported ([#495](https://github.com/holoviz/param/pull/495))
- Fix previously unimplemented Parameter._on_set ([#484](https://github.com/holoviz/param/pull/484))
- Fix Python2 IPython output parameter precedence ([#477](https://github.com/holoviz/param/pull/477))
- Fix allow_None for param.Series and param.DataFrame ([#473](https://github.com/holoviz/param/pull/473))
- Fix behavior when both `instantiate` and `constant` are `True` ([#474](https://github.com/holoviz/param/pull/474))
- Fix for versioning when param is inside a separate git-controlled repo (port of fix from autover/pull/67) ([#469](https://github.com/holoviz/param/pull/469))

Compatibility:
- Swapped ObjectSelector and Selector in the inheritance hierarchy, to allow ObjectSelector to be deprecated.  ([#497](https://github.com/holoviz/param/pull/497))
- Now `get_soft_bounds`silently crops softbounds to any hard bounds supplied ; previously soft bounds would be returned even if they were outside the hard bounds ([#498](https://github.com/holoviz/param/pull/498))
- Rename `class_` to `item_type` in List parameter, to avoid clashing semantics with ClassSelector and others with a `class_` slot. `class_` is still accepted as a keyword but is stored in `item_type`. ([#456](https://github.com/holoviz/param/pull/456))

## Version 1.10.1

Minor release for Panel-related bugfixes and minor features, from @philippjfr.

- Fix serialization of Tuple, for use in Panel ([#446](https://github.com/holoviz/param/pull/446))
- Declare asynchronous executor for Panel to use ([#449](https://github.com/holoviz/param/pull/449))
- Switch to GitHub Actions ([#450](https://github.com/holoviz/param/pull/450))

## Version 1.10.0

## Version 1.9.3

- Fixed ClassSelector.get_range when a tuple of types is supplied ([#360](https://github.com/holoviz/param/pull/360))

## Version 1.9.2

- Compatibility with Python 3.8
- Add eager option to watch calls ([#351](https://github.com/holoviz/param/pull/351))
- Add Calendar and CalendarDateRange for real date types ([#348](https://github.com/holoviz/param/pull/348))

## Version 1.9.1

Enhancements:

- Allow param.depends to annotate functions ([#334](https://github.com/holoviz/param/pull/334))
- Add context managers to manage events and edit constant parameters

Bug fixes:

- Ensure that Select constructor does not rely on truthiness ([#337](https://github.com/holoviz/param/pull/337))
- Ensure that param.depends allows mixed Parameter types ([#338](https://github.com/holoviz/param/pull/338))
- Date and DateRange now allow dt.date type ([#341](https://github.com/holoviz/param/pull/341))
- Ensure events aren't dropped in batched mode ([#343](https://github.com/holoviz/param/pull/343))

## Version 1.9.0

Full release with new functionality and some fixes.  New features:

- Added support for instance parameters, allowing parameter metadata to be modified per instance and allowing parameter objects to be passed to Panel objects ([#306](https://github.com/holoviz/param/pull/306))
- Added label slot to Parameter, to allow overriding attribute name for display ([#319](https://github.com/holoviz/param/pull/319))
- Added step slot to Parameter, e.g. to control Panel widget step size ([#326](https://github.com/holoviz/param/pull/326))
- Added keywords_to_params utility for deducing Parameter types and ranges automatically ([#317](https://github.com/holoviz/param/pull/317))
- Added support for multiple outputs from a Parameterized ([#312](https://github.com/holoviz/param/pull/312))
- Added Selector as a more user-friendly version of ObjectSelector, accepting a list of options as a positional argument ([#316](https://github.com/holoviz/param/pull/316))

Changes affecting backwards compatibility:

- Changed from root logger to a param-specific logger; no change to API but will change format of error and warning messages ([#330](https://github.com/holoviz/param/pull/330))
- Old abstract class Selector renamed to SelectorBase; should be no change unless user code added custom classes inherited from Selector without providing a constructor ([#316](https://github.com/holoviz/param/pull/316))

Bugfixes and other improvements:

- Various bugfixes ([#320](https://github.com/holoviz/param/pull/320), [#323](https://github.com/holoviz/param/pull/323), [#327](https://github.com/holoviz/param/pull/327), [#329](https://github.com/holoviz/param/pull/329))
- Other improvements ([#315](https://github.com/holoviz/param/pull/315), [#325](https://github.com/holoviz/param/pull/325))

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.8.2...v1.9.0).

## Version 1.8.2

Minor release:

- Added output decorator and outputs lookup method ([#299](https://github.com/holoviz/param/pull/299), [#312](https://github.com/holoviz/param/pull/312))

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.8.2...v1.8.1).

## Version 1.8.1

Minor release:

- Added positional default arguments for nearly all Parameter subclasses (apart from ClassSelector)
- Minor bugfixes for watching callbacks

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.8.1...v1.8.0).

## Version 1.8.0

Major new feature set: comprehensive support for events, watching, callbacks, and dependencies

- Parameterized methods can now declare `@depends(p,q)` to indicate that they depend on parameters `p` and `q` (defaulting to all parameters)
- Parameterized methods can depend on subobjects with `@depends(p.param,q.param.r)`, where `p.param` indicates dependencies on all parameters of `p` and `q.param.r` indicates a dependency on parameter `r` of `q`.
- Functions and methods can `watch` parameter values, re-running when those values change or when an explicit trigger is issued, and can unwatch them later if needed.
- Multiple events can be batched to trigger callbacks only once for a coordinated set of changes

Other new features:

- Added support in ObjectSelector for selecting lists and dicts ([#268](https://github.com/holoviz/param/pull/268))
- Added pandas DataFrame and Series parameter types ([#285](https://github.com/holoviz/param/pull/285))
- Added support for regular expression validation to String Parameter ([#241](https://github.com/holoviz/param/pull/241), [#245](https://github.com/holoviz/param/pull/245))

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.8.0...v1.7.0).

## Version 1.7.0

Since the previous release (1.6.1), there should be no changes that affect existing code, only additions:

* A new param namespace object, which in future will allow subclasses of Parameterized to have much cleaner namespaces ([#230](https://github.com/holoviz/param/pull/230)).
* Started testing on python 3.7-dev ([#223](https://github.com/holoviz/param/pull/223)).
* param.version now provides functions to simplify dependants' setup.py/setup.cfg files (see https://github.com/holoviz-dev/autover/pull/49).

Although param should still work on python 3.3, we are no longer testing against it (unsupported by our test environment; [#234](https://github.com/holoviz/param/pull/234)).

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.6.1...v1.7.0).

## Version 1.6.1

Restores support for the previous versioning system (pre 1.6; see [#225](https://github.com/holoviz/param/pull/225)), and fixes a number of issues with the new versioning system:

* Allow package name to differ from repository name (https://github.com/holoviz-dev/autover/pull/39)
* Allow develop install to work when repository is dirty (https://github.com/holoviz-dev/autover/pull/41)
* Fixed failure to report dirty when commit count is 0 (https://github.com/holoviz-dev/autover/pull/44)

## Version 1.6.0

Notable changes, fixes, and additions since the previous release (1.5.1) are listed below. You can also see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.5.1...v1.6.0).

Changes:
* `param.__version__` is now a string
* `param.version.Version` now supports a tag-based versioning workflow; if using the `Version` class, you will need to update your workflow (see [autover](https://github.com/holoviz-dev/autover) for more details).
* Dropped support for python 2.6 ([#175](https://github.com/holoviz/param/pull/175)).
* No longer attempt to cythonize param during installation via pip ([#166](https://github.com/holoviz/param/pull/166), [#194](https://github.com/holoviz/param/pull/194)).

Fixes:
* Allow `get_param_values()` to work on class ([#162](https://github.com/holoviz/param/pull/162)).
* Fixed incorrect default value for `param.Integer` ([#151](https://github.com/holoviz/param/pull/151)).
* Allow a `String` to be `None` if its default is `None` ([#104](https://github.com/holoviz/param/pull/104)).
* Fixed `ListSelector.compute_default()` ([#212](https://github.com/holoviz/param/pull/212)).
* Fixed checks for `None` in various `Parameter` subclasses ([#208](https://github.com/holoviz/param/pull/208)); fixes problems for subclasses of `Parameterized` that define a custom `__nonzero__` or `__len__`.

Additions:
* Added `DateRange` parameter.

Miscellaneous:
* No longer tested on python 3.2 (unsupported by our test environment; [#218](https://github.com/holoviz/param/pull/218)).

## Version 1.5.1

* Fixed error messages for ClassSelector with tuple of classes
* Added get and contains methods for ParamOverrides

A full list of changes since the previous release is available [here](https://github.com/holoviz/param/compare/v1.5.0...v1.5.1).

## Version 1.5.0

- Added Range, Color, and Date parameters
- Improved ObjectSelector error messages
- Minor bugfixes

A full list of changes since the previous release is available [here](https://github.com/holoviz/param/compare/v1.4.2...v1.5.0).

## Version 1.4.2

- Improved version reporting from version module
- Minor bugfixes

A full list of changes since the previous release is available [here](https://github.com/holoviz/param/compare/v1.4.1...v1.4.2).

## Version 1.4.1

* Selector parameters now respect order of options supplied
* Allowed softbounds to be accessed like an attribute

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.4.0...v1.4.1).

## Version 1.4.0 (2016/07)

* Added support for new [ParamNB](https://github.com/ioam/paramnb) project
* Added new parameter types Action, FileSelector, and ListSelector

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.3.2...v1.4.0).

## Version 1.3.2 (2015/04)

* Added Unicode support for param.String.
* Minor bugfixes.

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.3.1...v1.3.2).

## Version 1.3.1 (2015/03)

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
[on GitHub](https://github.com/holoviz/param/compare/v1.3.0...v1.3.1).

## Version 1.3.0 (2015/03)

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
[on GitHub](https://github.com/holoviz/param/compare/v1.2.1...v1.3.0).

## Version 1.2.1 (2014/06)

* Minor bugfix release to fix issues with version when param is
  installed in a foreign git repository
* Made version module optional
* Improved ClassSelector and ParamOverrides

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.2.0...v1.2.1).

## Version 1.2.0 (2014/06)

* Added support for Python 3 (thanks to Marco Elver).
* Dropped support for Python 2.5.
* Added version module.
* Added optional numbergen package.

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.1.0...v1.2.0).

## Version 1.1.0 (2014/05)

* Switched to Python's own logging module.
* Improved support for time when using Dynamic parameters.
* Optional extension for IPython users.

A full list of changes since the previous release is available
[on GitHub](https://github.com/holoviz/param/compare/v1.0.0...v1.1.0).

## Version 1.0.0 (2012/07)

* First standalone release.

## Pre-1.0 (2003)

* Param was originally developed as part of [Topographica](http://ioam.github.io/topographica/), and has been in heavy usage as part of that project since 2003.
