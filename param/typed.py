from __future__ import annotations

import copy
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
    """Field specifier for TypedParameterized attributes."""
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
    origin = t.get_origin(ann)
    if origin is t.Annotated:
        annotated_args = list(t.get_args(ann))
        ann = annotated_args[0] if annotated_args else ann
        for meta in annotated_args[1:]:
            if isinstance(meta, Mapping):
                kwargs.update(dict(meta))
        origin = t.get_origin(ann)

    if origin in (t.Union, types.UnionType):
        union_args = list(t.get_args(ann))
        non_none = [a for a in union_args if a is not type(None)]
        if len(non_none) < len(union_args):
            kwargs["allow_None"] = True
        ann = non_none[0] if len(non_none) == 1 else ann
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

    if origin in (list, t.List):
        list_args = t.get_args(ann)
        if list_args and isinstance(list_args[0], type):
            kwargs["item_type"] = list_args[0]
        return List, kwargs

    if origin in (tuple, t.Tuple):
        tuple_args = t.get_args(ann)
        if tuple_args and tuple_args[-1] is not Ellipsis:
            kwargs["length"] = len(tuple_args)
        return Tuple, kwargs

    if origin in (dict, t.Dict):
        return Dict, kwargs

    if origin in (set, t.Set):
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
) -> Parameter:
    factory_kwargs: dict[str, Any] = {}
    if field_spec is not None and field_spec.parameter is not None:
        factory: type[Parameter] | Callable[..., Parameter] | Parameter | None = field_spec.parameter
    else:
        factory, inferred = _annotation_parameter_factory(annotation)
        factory_kwargs.update(inferred)

    if field_spec is not None:
        factory_kwargs.update(field_spec.kwargs)
        if field_spec.default is not Undefined:
            factory_kwargs["default"] = field_spec.default
        if field_spec.default_factory is not Undefined:
            factory_kwargs["default_factory"] = field_spec.default_factory

    if has_explicit_value:
        factory_kwargs["default"] = explicit_value
    elif "default" not in factory_kwargs and "default_factory" not in factory_kwargs:
        # Checker-facing required semantics for annotation-only declarations.
        factory_kwargs["default"] = Undefined

    if isinstance(factory, Parameter):
        pobj = copy.copy(factory)
        for key, value in factory_kwargs.items():
            setattr(pobj, key, value)
        return pobj
    if factory is None:
        return Parameter(**factory_kwargs)
    return factory(**factory_kwargs)


@dataclass_transform(field_specifiers=(Field,))
class TypedParameterizedMetaclass(ParameterizedMetaclass):

    def __new__(
        mcs, name: str, bases: tuple[type, ...], dict_: dict[str, Any]
    ) -> TypedParameterizedMetaclass:
        namespace = dict_
        annotations = dict(namespace.get("__annotations__", {}))
        module_name = namespace.get("__module__", "")
        module_globals = getattr(sys.modules.get(module_name), "__dict__", {})

        for attr, annotation in annotations.items():
            if isinstance(annotation, str):
                try:
                    annotation = eval(annotation, module_globals, namespace)
                except Exception:
                    pass
            if attr.startswith("_"):
                continue
            origin = t.get_origin(annotation)
            if origin is t.ClassVar:
                continue

            existing = namespace.get(attr, Undefined)
            if isinstance(existing, Parameter):
                continue

            field_spec = existing if isinstance(existing, _FieldSpec) else None
            has_explicit_value = (
                attr in namespace and not isinstance(existing, _FieldSpec)
            )
            explicit_value = existing if has_explicit_value else Undefined
            namespace[attr] = _build_parameter_from_field(
                annotation,
                field_spec=field_spec,
                explicit_value=explicit_value,
                has_explicit_value=has_explicit_value,
            )

        return t.cast(
            "TypedParameterizedMetaclass", super().__new__(mcs, name, bases, namespace)
        )


class TypedParameterized(Parameterized, metaclass=TypedParameterizedMetaclass):
    """A Parameterized subclass that synthesizes Parameters from type annotations."""
