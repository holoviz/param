# Releases

## Version 1.12.2

Date: 2022-06-14

The `1.12.2` release fixes a number of bugs and adds support again for Python 2.7, which was unfortunately no longer supported in the last release. Note however that Param 2.0 will still drop support of Python 2.7 as already announced. Many thanks to @Hoxbro and the maintainers @jbednar, @jlstevens, @maximlt and @philippjfr for contributing to this release.

Bug fixes:

* Match against complete spec name when determining dynamic watchers ([615](https://github.com/holoviz/param/pull/615))
* Ensure async functionality does not cause python2 syntax errors ([624](https://github.com/holoviz/param/pull/624))
* Allow (de)serializing `CalendarRange` and `DateRange` `Parameters` ([625](https://github.com/holoviz/param/pull/625))
* Improve `DateRange` validation ([627](https://github.com/holoviz/param/pull/627))
* Fix regression in `@param.depends` execution ordering ([628](https://github.com/holoviz/param/pull/628))
* Ensure `named_objs` does not fail on unhashable objects ([632](https://github.com/holoviz/param/pull/632))
* Support comparing date-like objects ([629](https://github.com/holoviz/param/pull/629))
* Fixed `BinaryPower` example in the docs to use the correct name `EvenInteger`([634](https://github.com/holoviz/param/pull/634))
