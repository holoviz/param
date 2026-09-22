from __future__ import annotations

import copy
import importlib
import sys
import types
import typing as t

from collections.abc import Callable, Mapping
from typing import Any
from typing_extensions import dataclass_transform

from .parameterized import (
    Parameter,
    Parameterized,
    ParameterizedMetaclass,
    String,
    Undefined,
)

FT = t.TypeVar("FT")


class _FieldSpec:

    __slots__ = ("default", "default_factory", "parameter", "kwargs")

    def __init__(
        self,
        *,
        default: Any = Undefined,
        default_factory: Callable[..., Any] | Any = Undefined,
        parameter: type[Parameter] | Callable[..., Parameter] | Parameter | None = None,
        **kwargs: Any,
    ):
        self.default = default
        self.default_factory = default_factory
        self.parameter = parameter
        self.kwargs = kwargs


@t.overload
def Field(
    *,
    default: FT,
    default_factory: Callable[..., Any] | Any = Undefined,
    parameter: type[Parameter] | Callable[..., Parameter] | Parameter | None = None,
    **kwargs: Any,
) -> FT:
    ...


@t.overload
def Field(
    *,
    default: Any = Undefined,
    default_factory: Callable[[], FT],
    parameter: type[Parameter] | Callable[..., Parameter] | Parameter | None = None,
    **kwargs: Any,
) -> FT:
    ...


@t.overload
def Field(
    *,
    default: Any = Undefined,
    default_factory: Callable[..., Any] | Any = Undefined,
    parameter: type[Parameter] | Callable[..., Parameter] | Parameter | None = None,
    **kwargs: Any,
) -> Any:
    ...


def Field(
    *,
    default: Any = Undefined,
    default_factory: Callable[..., Any] | Any = Undefined,
    parameter: type[Parameter] | Callable[..., Parameter] | Parameter | None = None,
    **kwargs: Any,
) -> Any:
    """Field specifier for Model attributes."""
    return t.cast(
        "Any",
        _FieldSpec(
        default=default,
        default_factory=default_factory,
        parameter=parameter,
        **kwargs,
        ),
    )


def _annotation_parameter_factory(annotation: Any) -> tuple[type[Parameter], dict[str, Any]]:
    from .parameters import (
        Boolean,
        ClassSelector,
        Dict,
        Integer,
        List,
        Number,
        Selector,
        Tuple,
    )

    kwargs: dict[str, Any] = {}
    ann = annotation
    # `Annotated` and `Optional`/`Union` can wrap each other in either order
    # (`Annotated[Optional[T], {...}]` or `Optional[Annotated[T, {...}]]`),
    # so unwrap both repeatedly rather than in a single fixed-order pass.
    while True:
        origin = t.get_origin(ann)
        if origin is t.Annotated:
            annotated_args = list(t.get_args(ann))
            for meta in annotated_args[1:]:
                if isinstance(meta, Mapping):
                    kwargs.update(dict(meta))
            ann = annotated_args[0] if annotated_args else ann
            continue

        if origin in (t.Union, types.UnionType):
            union_args = list(t.get_args(ann))
            non_none = [a for a in union_args if a is not type(None)]
            if len(non_none) < len(union_args):
                kwargs["allow_None"] = True
            if len(non_none) == 1 and non_none[0] is not ann:
                ann = non_none[0]
                continue

        break

    origin = t.get_origin(ann)
    if origin is t.Literal:
        kwargs["objects"] = list(t.get_args(ann))
        return Selector, kwargs

    if ann is bool:
        return Boolean, kwargs
    if ann is int:
        return Integer, kwargs
    if ann is float:
        return Number, kwargs
    if ann is str:
        return String, kwargs

    if ann is list or origin in (list, t.List):
        list_args = t.get_args(ann)
        if list_args and isinstance(list_args[0], type):
            kwargs["item_type"] = list_args[0]
        return List, kwargs

    if ann is tuple or origin in (tuple, t.Tuple):
        tuple_args = t.get_args(ann)
        if tuple_args and tuple_args[-1] is not Ellipsis:
            kwargs["length"] = len(tuple_args)
        return Tuple, kwargs

    if ann is dict or origin in (dict, t.Dict):
        return Dict, kwargs

    if ann is set or origin in (set, t.Set):
        kwargs["class_"] = set
        return ClassSelector, kwargs

    if ann in (Any, object):
        return Parameter, kwargs

    return Parameter, kwargs


def _build_parameter_from_field(
    annotation: Any,
    *,
    field_spec: _FieldSpec | None,
    explicit_value: Any = Undefined,
    has_explicit_value: bool = False,
) -> tuple[Parameter, bool]:
    factory_kwargs: dict[str, Any] = {}
    if field_spec is not None and field_spec.parameter is not None:
        factory: type[Parameter] | Callable[..., Parameter] | Parameter | None = field_spec.parameter
        # Overriding the parameter class/instance bypasses the rest of the
        # inferred kwargs (e.g. `objects`, `item_type`), which may not apply
        # to the chosen parameter, but `allow_None` derived from `T | None` /
        # `Optional[T]` is universally applicable and should still be honored
        # unless the caller already specified it explicitly.
        _, inferred = _annotation_parameter_factory(annotation)
        if inferred.get("allow_None"):
            factory_kwargs["allow_None"] = True
    else:
        factory, inferred = _annotation_parameter_factory(annotation)
        factory_kwargs.update(inferred)

    if field_spec is not None:
        factory_kwargs.update(field_spec.kwargs)
        if field_spec.default is not Undefined:
            factory_kwargs["default"] = field_spec.default
        if field_spec.default_factory is not Undefined:
            factory_kwargs["default_factory"] = field_spec.default_factory

    is_required = False
    if has_explicit_value:
        factory_kwargs["default"] = explicit_value
    elif "default" not in factory_kwargs and "default_factory" not in factory_kwargs:
        if isinstance(factory, Parameter):
            # A `Parameter` *instance* passed via `Field(parameter=...)`
            # already carries its own default (explicit or inherited from
            # its own class), just like a `Parameter` instance assigned
            # directly in a class body. Leave it untouched rather than
            # clobbering it with `Undefined` and marking the field required.
            pass
        else:
            from .parameters import Selector

            # No default was supplied anywhere (annotation, Field, or class body).
            # `Selector` is the one built-in Parameter that computes its own
            # sensible default (the first entry of `objects`) when none is given
            # — e.g. for `Literal["read", "write"]` — so it's exempt from being
            # treated as required. Everything else is required at __init__ time.
            # `default` is left as `Undefined` so the underlying Parameter still
            # falls back to its own slot default for introspection (e.g.
            # `P.param.name.default`), but `Model.__init__` enforces that a
            # value must be passed explicitly for required fields.
            factory_kwargs["default"] = Undefined
            is_required = not (factory is Selector and factory_kwargs.get("objects"))

    if isinstance(factory, Parameter):
        pobj = copy.copy(factory)
        for key, value in factory_kwargs.items():
            setattr(pobj, key, value)
        return pobj, is_required
    if factory is None:
        return Parameter(**factory_kwargs), is_required
    return factory(**factory_kwargs), is_required


def _extract_namespace_annotations(namespace: dict[str, Any]) -> dict[str, Any]:
    annotations = dict(namespace.get("__annotations__", {}))
    if annotations:
        return annotations

    # Python 3.14 may defer class annotation materialization to __annotate_func__.
    annotate_func = namespace.get("__annotate_func__")
    if not callable(annotate_func):
        return {}

    try:
        annotationlib = importlib.import_module("annotationlib")
        format_value = getattr(getattr(annotationlib, "Format", None), "VALUE", 1)
    except ImportError:
        # annotationlib is unavailable on this runtime; VALUE format is 1.
        format_value = 1

    # Let genuine evaluation errors (e.g. a broken forward reference) raise
    # rather than silently producing an empty annotation set.
    evaluated = annotate_func(format_value)

    return dict(evaluated) if isinstance(evaluated, Mapping) else {}


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class ModelMetaclass(ParameterizedMetaclass):

    def __new__(
        mcs, name: str, bases: tuple[type, ...], dict_: dict[str, Any]
    ) -> ModelMetaclass:
        namespace = dict_
        annotations = _extract_namespace_annotations(namespace)
        module_name = namespace.get("__module__", "")
        module_globals = getattr(sys.modules.get(module_name), "__dict__", {})

        required: set[str] = set()
        for base in bases:
            required |= getattr(base, "_model_required", frozenset())

        for attr, annotation in annotations.items():
            if isinstance(annotation, str):
                # Let genuine evaluation errors (e.g. a typo'd or undefined
                # forward reference) raise, matching the PEP 649 path in
                # `_extract_namespace_annotations`, rather than silently
                # falling through to an unvalidated bare `Parameter`. This
                # matters most under `from __future__ import annotations`,
                # since every annotation is a string on that path, not just
                # genuine forward references.
                annotation = eval(annotation, module_globals, namespace)
            if attr.startswith("_"):
                continue
            origin = t.get_origin(annotation)
            if origin is t.ClassVar:
                continue

            existing = namespace.get(attr, Undefined)
            if isinstance(existing, Parameter):
                required.discard(attr)
                continue

            field_spec = existing if isinstance(existing, _FieldSpec) else None
            has_explicit_value = (
                attr in namespace and not isinstance(existing, _FieldSpec)
            )
            explicit_value = existing if has_explicit_value else Undefined
            namespace[attr], is_required = _build_parameter_from_field(
                annotation,
                field_spec=field_spec,
                explicit_value=explicit_value,
                has_explicit_value=has_explicit_value,
            )
            if is_required:
                required.add(attr)
            else:
                required.discard(attr)

        namespace["_model_required"] = frozenset(required)

        return t.cast(
            "ModelMetaclass", super().__new__(mcs, name, bases, namespace)
        )


class Model(Parameterized, metaclass=ModelMetaclass):
    """A Parameterized subclass that synthesizes Parameters from type annotations."""

    _model_required: t.ClassVar[frozenset[str]] = frozenset()

    # No return annotation: ParameterizedMetaclass.__get_signature only expands
    # __init__ into per-parameter keywords for introspection/tab-completion
    # when it matches DEFAULT_SIGNATURE exactly, including the (empty) return
    # annotation.
    def __init__(self, **params):
        missing = sorted(self._model_required - params.keys())
        if missing:
            missing_str = ", ".join(repr(name) for name in missing)
            raise TypeError(
                f"{type(self).__name__}.__init__() missing required "
                f"argument(s): {missing_str}"
            )
        super().__init__(**params)
