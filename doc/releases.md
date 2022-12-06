# Releases

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
* param.version now provides functions to simplify dependants' setup.py/setup.cfg files (see https://github.com/pyviz-dev/autover/pull/49).

Although param should still work on python 3.3, we are no longer testing against it (unsupported by our test environment; [#234](https://github.com/holoviz/param/pull/234)).

For more details, you can see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.6.1...v1.7.0).

## Version 1.6.1

Restores support for the previous versioning system (pre 1.6; see [#225](https://github.com/holoviz/param/pull/225)), and fixes a number of issues with the new versioning system:

* Allow package name to differ from repository name (https://github.com/pyviz-dev/autover/pull/39)
* Allow develop install to work when repository is dirty (https://github.com/pyviz-dev/autover/pull/41)
* Fixed failure to report dirty when commit count is 0 (https://github.com/pyviz-dev/autover/pull/44)

## Version 1.6.0

Notable changes, fixes, and additions since the previous release (1.5.1) are listed below. You can also see a [full list of changes since the previous release](https://github.com/holoviz/param/compare/v1.5.1...v1.6.0).

Changes:
* `param.__version__` is now a string
* `param.version.Version` now supports a tag-based versioning workflow; if using the `Version` class, you will need to update your workflow (see [autover](https://github.com/holoviz/autover) for more details).
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
