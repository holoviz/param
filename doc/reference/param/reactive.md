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

### Overriding an input

`.rx.overrides` makes one node compute as if one of its inputs held a different
value, addressed by keyword name or positional index. It does not set the input, so
every other consumer of that input keeps seeing the live value, and only this node
and the nodes reading its result are invalidated. Deleting the key unmasks
the original input:

```python
import param

fx = param.rx(2)
value = param.rx(100).rx.pipe(lambda price, fx: price * fx, fx=fx)
value.rx.value  # 200

value.rx.overrides['fx'] = 1
value.rx.value  # 100

fx.rx.value = 5
value.rx.value  # still 100, the override masks the update

del value.rx.overrides['fx']
value.rx.value  # 500
```

An override may also be a reference, e.g. a `Parameter`, an expression, or a bound
function, the node then follows, so a UI control can drive one
node's view of an input:

```python
class Scenario(param.Parameterized):
    fx = param.Number(default=3)

value.rx.overrides['fx'] = Scenario().param.fx
value.rx.value  # 300
```

The override stands in for the input and is resolved in its place, ahead of the
guards the input would have faced. Any value masks the input, including `None`, so
an override following a reference keeps masking when that reference holds `None`.

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
   ~reactive_ops.overrides
```
