# Reactive API

```{eval-rst}
.. currentmodule:: param.reactive
```

## `bind`

```{eval-rst}
.. autosummary::
   :toctree: generated/

   bind
```

## `current_node`

```{eval-rst}
.. autosummary::
   :toctree: generated/

   current_node
```

## `rx`

`rx` allows wrapping objects and then operating on them interactively while recording any operations applied to them.

`==` and `!=` build a comparison expression rather than compare identity, but `rx`
instances are still hashable by identity, so a node can be used as a `dict` key or
`set` member.

See the [Reactive Expressions user guide](../../user_guide/Reactive_Expressions.ipynb)
for error handling (`error_mode`, `ReactiveError`, `.rx.error`, `.rx.label`,
`process_failures`), `.rx.overrides` for masking an input, `.rx.meta` and
`current_node` for per-node caching and provenance, `.rx.upstream`/
`.rx.downstream` for walking the pipeline graph, and `.rx.watch`/
`.rx.unwatch`/`.rx.dispose` for an expression's lifecycle.

*New in version 2.5.0: `label`, `ReactiveError.label`, `.rx.label`,
`process_failures` on `bind`, `.rx.dispose()`, `.rx.unwatch()`,
`.rx.watch()` returning its watcher(s), `.rx.upstream()`, and
`.rx.downstream()`.*

```{eval-rst}
.. autosummary::
   :toctree: generated/

   rx
   reactive_ops
   ReactiveError
   InputOverrides
```

These methods and properties are available under the `.rx` namespace of reactive expressions ({py:class}`rx`):

```{eval-rst}
.. autosummary::
  :toctree: generated/

   ~reactive_ops.and_
  ~reactive_ops.bool
  ~reactive_ops.buffer
  ~reactive_ops.downstream
  ~reactive_ops.in_
  ~reactive_ops.is_
  ~reactive_ops.is_not
  ~reactive_ops.len
  ~reactive_ops.map
  ~reactive_ops.not_
  ~reactive_ops.or_
  ~reactive_ops.pipe
  ~reactive_ops.resolve
  ~reactive_ops.set
  ~reactive_ops.updating
  ~reactive_ops.upstream
  ~reactive_ops.when
  ~reactive_ops.where
   ~reactive_ops.value
   ~reactive_ops.watch
   ~reactive_ops.unwatch
   ~reactive_ops.dispose
   ~reactive_ops.error
   ~reactive_ops.overrides
   ~reactive_ops.label
   ~reactive_ops.meta
```
