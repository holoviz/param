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

`.rx.overrides` interposes a value on one of a node's inputs, addressed by keyword
name or by positional index. The node then computes as if that input held the
given value:

```python
import param

fx = param.rx(2)
price = param.rx(100)
value = price.rx.pipe(lambda price, fx: price * fx, fx=fx)
value.rx.value  # 200

value.rx.overrides['fx'] = 1
value.rx.value  # 100
```

This is not the same as setting `fx`: the interposition is local to this node's
consumption of the input, so every other consumer of `fx` keeps seeing the live
value, and only this node and the nodes reading its result are invalidated. While
an input is overridden its updates are masked, and unmasking picks up whatever
value arrived in the meantime:

```python
fx.rx.value = 5
value.rx.value  # still 100

value.rx.overrides['fx'] = None  # None unmasks, so it cannot be an override value
value.rx.value  # 500
```

The override replaces the input ahead of every guard the node applies to its
inputs, so it also masks an input that failed, one that has not resolved yet and
one that skipped, without the node having to be wired with `process_failures=True`:

```python
broken = param.rx(0, error_mode="propagate").rx.pipe(lambda divisor: 1 / divisor)
total = param.rx(7).rx.pipe(lambda value, extra: value + extra, extra=broken)
isinstance(total.rx.value, param.ReactiveError)  # True

total.rx.overrides['extra'] = 5
total.rx.value  # 12
```

Overrides are node-local, like `.rx.meta`: a node derived from this one
(`value + 1`) has its own, empty mapping, and only an input the node was wired
with can be overridden, so `value.rx.overrides['unknown'] = 1` raises `KeyError`.
Overriding is a plain replacement; a library that needs to merge an override into
the live value should compute the merged value itself.

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
   ~reactive_ops.overrides
```
