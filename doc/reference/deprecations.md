# Deprecations and Removals

List of currently deprecated APIs:

| Warning | Description |
|-|-|
| `ParamDeprecationWarning` since `2.3.0` | Parameter slots / `Selector.compute_default_fn` slot along with the `Selector.compute_default` method: no replacement |
| `FutureWarning` since `2.3.0` | The whole `param.Version` module is deprecated, use tools like `setuptools-scm`. |
| `ParamDeprecationWarning` since `2.3.0` | Parameter slots / `Parameter.pickle_default_value`: no replacement |
| `ParamFutureWarning` since `2.3.0` | Parameterized `.param` namespace / `.param.watch_values`: the keyword `what` is deprecated |
| `ParamPendingDeprecationWarning` since `2.3.0` | `param.parameterized` module / Setting a parameter value before full instance initialization |

List (created after the release of version `2.2.0`) of removed APIs:

| Removed in | Warning | Description |
|-|-|-|
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | Parameter slots / `List._class`: use instead `item_type` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | Parameter slots / `Number.set_hook`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.produce_value`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.as_unicode`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.is_ordered_dict`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.hashable`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.named_objs`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.normalize_path`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.__init__` module / `param.abbreviate_paths`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.parameterized` module / `param.parameterized.all_equal`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.parameterized` module / `param.parameterized.add_metaclass`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.parameterized` module / `param.parameterized.batch_watch`: use instead `batch_call_watchers` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.parameterized` module / `param.parameterized.recursive_repr`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0` | `param.parameterized` module / `param.parameterized.overridable_property`: no replacement |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.set_default`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param._add_parameter`: use instead `.param.add_parameter` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.params`: use instead `.param.values()` or `.param['param']` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.set_param`: use instead `.param.update` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.get_param_values`: use instead `.param.values().items()` (or `.param.values()` for the common case of `dict(....param.get_param_values())`) |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.params_depended_on`: use instead `.param.method_dependencies` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.defaults`: use instead `{k:v.default for k,v in p.param.objects().items()}` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.print_param_defaults`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.print_param_values`: use instead `for k,v in p.param.objects().items(): print(f"{p.__class__.name}.{k}={repr(v.default)}")` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.message`: use instead `.param.log(param.MESSAGE, ...)` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.verbose`: use instead `.param.log(param.VERBOSE, ...)` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.0.0`, soft-deprecated since `1.12.0` | Parameterized `.param` namespace / `.param.debug`: use instead `.param.log(param.DEBUG, ...)` |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.1.0`, `ParamPendingDeprecationWarning` since `2.0.0` | Instantiating most parameters with positional arguments beyond `default` is deprecated |
| `2.3.0` | `ParamFutureWarning` since `2.2.0`, `ParamDeprecationWarning` since `2.1.0`, `ParamPendingDeprecationWarning` since `2.0.0` | For `Selector` parameters that accept `objects` as first positional argument, and `ClassSelector` parameters that accept `class_` as first positional argument, passing any argument by position is deprecated. |
| `2.3.0` | None | `param.parameterized.print_all_param_defaults` / This functions was undocumented, unused, and broken. |
| `2.2.0` | `ParamFutureWarning` since `2.0.0` | Parameterized namespace / `instance._param_watchers` (getter and setter): use instead the property `inst.param.watchers` |
| `2.2.0` | `ParamFutureWarning` since `2.0.0` | Warn on failed validation of the *default* value of a Parameter after the inheritance mechanism has completed |
| `2.2.0` | `ParamFutureWarning` since `2.0.0` | Running unsafe `instance.param.objects(instance=True)` during Parameterized instance initialization, instead run it after having called `super().__init__(**params)` |
| `2.2.0` | `ParamFutureWarning` since `2.0.0` | Running unsafe `instance.param.objects(instance=True)` during Parameterized instance initialization, instead run it after having called `super().__init__(**params)` |
| `2.2.0` | `ParamFutureWarning` since `2.0.0` | Running unsafe `instance.param.watch(callback, "<param_name>")` during Parameterized instance initialization, instead run it after having called `super().__init__(**params)` |
