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

## `rx`

`rx` allows wrapping objects and then operating on them interactively while recording any operations applied to them.

### Error handling

By default, exceptions raised while evaluating an expression are cached and
re-raised when the expression is read. Pass `error_mode="propagate"` when
constructing an expression to represent failures as falsy {py:class}`ReactiveError`
values instead:

```python
import param

def divide(value):
    return 10 / value

value = param.rx(0, error_mode="propagate")
result = value.rx.pipe(divide)

isinstance(result.rx.value, param.ReactiveError)  # True
str(result.rx.value)                      # "division by zero"
result.rx.error is result.rx.value        # True
```

`ReactiveError` carries the original exception and a weak reference to the node that failed. Reactive
operations receiving a `ReactiveError` pass it through without being called. Use
`process_failures=True` with `.rx.pipe` when an operation should inspect or
transform the failure:

```python
handled = result.rx.pipe(
    lambda error: f"failed: {error.exception}",
    process_failures=True,
)
handled.rx.value  # "failed: division by zero"
```

The `.rx.error` property returns the current `ReactiveError` or exception, and `None`
for an expression without a failure.

```{eval-rst}
.. autosummary::
   :toctree: generated/

   rx
   reactive_ops
   ReactiveError
```

These methods and properties are available under the `.rx` namespace of reactive expressions ({py:class}`rx`):

```{eval-rst}
.. autosummary::
  :toctree: generated/

   ~reactive_ops.and_
  ~reactive_ops.bool
  ~reactive_ops.buffer
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
  ~reactive_ops.when
  ~reactive_ops.where
  ~reactive_ops.value
   ~reactive_ops.watch
   ~reactive_ops.error
```
