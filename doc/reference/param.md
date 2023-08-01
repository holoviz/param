# Param API reference

## Main objects

```{eval-rst}
.. currentmodule:: param
```

```{eval-rst}
.. autosummary::
  :toctree: generated/
  :nosignatures:

  Parameterized
  ParameterizedFunction
  ParamOverrides
```

## `.param` namespace

```{eval-rst}
.. currentmodule:: param.parameterized
```

```{eval-rst}
.. autosummary::
  :toctree: generated/

  ~Parameters.add_parameter
  ~Parameters.debug
  ~Parameters.defaults
  ~Parameters.deserialize_parameters
  ~Parameters.deserialize_value
  ~Parameters.force_new_dynamic_value
  ~Parameters.get_param_values
  ~Parameters.get_value_generator
  ~Parameters.inspect_value
  ~Parameters.log
  ~Parameters.message
  ~Parameters.method_dependencies
  ~Parameters.objects
  ~Parameters.outputs
  ~Parameters.params
  ~Parameters.params_depended_on
  ~Parameters.pprint
  ~Parameters.print_param_defaults
  ~Parameters.print_param_values
  ~Parameters.schema
  ~Parameters.set_default
  ~Parameters.set_dynamic_time_fn
  ~Parameters.set_param
  ~Parameters.serialize_parameters
  ~Parameters.serialize_value
  ~Parameters.trigger
  ~Parameters.unwatch
  ~Parameters.update
  ~Parameters.values
  ~Parameters.verbose
  ~Parameters.warning
  ~Parameters.watch
  ~Parameters.watch_values
  ~Parameters.watchers
```

## Parameterized helpers

```{eval-rst}
.. currentmodule:: param
```

```{eval-rst}
.. autosummary::
  :toctree: generated/

  param.parameterized.Event
  param.parameterized.Watcher
  batch_watch
  param.parameterized.batch_call_watchers
  concrete_descendents
  depends
  discard_events
  edit_constant
  output
  script_repr
```

## Logging

```{eval-rst}
.. autosummary::
  :toctree: generated/

  param.parameterized.get_logger
  param.parameterized.logging_level
```

## Parameters

```{eval-rst}
.. autosummary::
  :toctree: generated/
  :nosignatures:

  Parameter
  String
  Bytes
  Color
  Boolean
  Event
  Dynamic
  Number
  Integer
  Magnitude
  Tuple
  NumericTuple
  XYCoordinates
  Range
  DateRange
  CalendarDateRange
  List
  HookList
  Path
  Filename
  Foldername
  CalendarDateRange
  Selector
  FileSelector
  ListSelector
  MultiFileSelector
  ClassSelector
  Dict
  Array
  Series
  DataFrame
  Callable
  Action
  Composite
```

## Parameter helpers

```{eval-rst}
.. autosummary::
  :toctree: generated/

  get_soft_bounds
  guess_bounds
  guess_param_types
  param_union
```

## Serialization



```{eval-rst}
.. automodule :: param.serializer
  :members:
  :undoc-members:
```
