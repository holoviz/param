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

Pass `label` when constructing an expression, or set `.rx.label` on an existing
one, to attach a human-readable name a `ReactiveError` can report back without
the consumer having to dereference the failing node itself. `label` is
inherited through `.rx.pipe` and operator overloads:

```python
feed = param.rx(0, error_mode="propagate", label="price feed")
result = feed.rx.pipe(divide)
result.rx.error.label  # "price feed"
```

`bind` also accepts `process_failures` (default `False`), matching `.rx.pipe`:
a bound argument that resolves to a `ReactiveError` short-circuits the call,
returning the `ReactiveError` unchanged, unless `process_failures=True`.

*New in version 2.5.0: `label`, `ReactiveError.label`, `.rx.label`, and
`process_failures` on `bind`.*

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

### Disposing an expression

`.rx.watch()` returns the watcher(s) it registers; pass them to `.rx.unwatch()`
to stop just that callback. `.rx.dispose()` releases the watchers an
expression's own construction set up, immediately rather than waiting for it
to be garbage collected, and disposes an input too if the expression being
disposed was its only reader:

```python
a = param.rx(1)
b = a + 1
b.rx.value  # 2
b.rx.dispose()  # releases b's watchers, and a's too, since b was its only reader
```

`.rx.dispose()` raises if the expression still has a reader, whether another
node built from it or a live `.rx.watch()` callback on it, since disposing it
would leave that reader looking at a value that has stopped tracking its
inputs. Pass `cascade=False` to release only the expression's own watchers,
without ever touching its inputs; this matters if an input feeds a consumer
`.rx.dispose()` cannot see, such as a `Parameter` with `allow_refs=True`, or a
`bind`/`pn.bind` consumer. Once disposed, resolving the expression, reading
its value, or building a new expression from it raises rather than silently
returning a stale value.

*New in version 2.5.0: `.rx.dispose()`, `.rx.unwatch()`, and `.rx.watch()`
returning its watcher(s).*

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
   ~reactive_ops.unwatch
   ~reactive_ops.dispose
   ~reactive_ops.error
   ~reactive_ops.overrides
   ~reactive_ops.label
```
