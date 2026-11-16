from __future__ import annotations

import copy
import datetime as dt
import enum
import importlib
import sys
import types
import typing as t

from collections.abc import Callable, Mapping
from typing import Any, dataclass_transform

from .parameterized import (
    Parameter,
    Parameterized,
    ParameterizedMetaclass,
    String,
    Undefined,
)
from .parameters import (
    Boolean,
    CalendarDate,
    ClassSelector,
    Date,
    Dict,
    Integer,
    List,
    Number,
    Selector,
    Tuple,
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


_CONSTRAINT_MODULES = ("annotated_types", "pydantic")


def _collect_constraints(annotation: Any) -> dict[str, Any]:
    """Gather annotated-types style constraints (e.g. ``Ge``, ``MaxLen``) from ``Annotated`` metadata."""
    constraints: dict[str, Any] = {}
    ann = annotation
    while True:
        origin = t.get_origin(ann)
        if origin is t.Annotated:
            for meta in t.get_args(ann)[1:]:
                if type(meta).__module__.split(".")[0] not in _CONSTRAINT_MODULES:
                    continue
                for attr in ("gt", "ge", "lt", "le", "multiple_of", "min_length", "max_length", "pattern"):
                    value = getattr(meta, attr, None)
                    if value is not None:
                        constraints[attr] = value
            ann = t.get_args(ann)[0]
        elif origin in (t.Union, types.UnionType):
            non_none = [a for a in t.get_args(ann) if a is not type(None)]
            if len(non_none) != 1:
                break
            ann = non_none[0]
        else:
            break
    return constraints


def _apply_constraints(
    ptype: type[Parameter], kwargs: dict[str, Any], constraints: dict[str, Any]
) -> None:
    if issubclass(ptype, (Number, Date, CalendarDate)) and "bounds" not in kwargs:
        low = constraints.get("ge", constraints.get("gt"))
        high = constraints.get("le", constraints.get("lt"))
        if low is not None or high is not None:
            kwargs["bounds"] = (low, high)
            kwargs["inclusive_bounds"] = ("gt" not in constraints, "lt" not in constraints)
    if issubclass(ptype, Number) and "multiple_of" in constraints:
        kwargs.setdefault("step", constraints["multiple_of"])
    if issubclass(ptype, List) and "bounds" not in kwargs:
        if "min_length" in constraints or "max_length" in constraints:
            kwargs["bounds"] = (constraints.get("min_length", 0), constraints.get("max_length"))
    if issubclass(ptype, String) and "pattern" in constraints:
        kwargs.setdefault("regex", constraints["pattern"])


def _annotation_parameter_factory(annotation: Any) -> tuple[type[Parameter], dict[str, Any]]:
    ptype, kwargs = _infer_parameter(annotation)
    constraints = _collect_constraints(annotation)
    if constraints and isinstance(ptype, type):
        _apply_constraints(ptype, kwargs, constraints)
    return ptype, kwargs


def _infer_parameter(annotation: Any) -> tuple[type[Parameter], dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    ann = annotation
    # `Annotated` and `Optional` can occur in either order.
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
            if all(
                isinstance(a, type) and t.get_origin(a) is None and a not in (Any, object)
                for a in non_none
            ):
                kwargs["class_"] = tuple(non_none)
                return ClassSelector, kwargs

        break

    origin = t.get_origin(ann)
    if origin is t.Literal:
        kwargs["objects"] = list(t.get_args(ann))
        return Selector, kwargs

    if isinstance(ann, type) and issubclass(ann, enum.Enum):
        kwargs["objects"] = list(ann)
        return Selector, kwargs

    if ann is bool:
        return Boolean, kwargs
    if ann is int:
        return Integer, kwargs
    if ann is float:
        return Number, kwargs
    if ann is str:
        return String, kwargs
    # datetime subclasses date, so it has to be checked first.
    if ann is dt.datetime:
        return Date, kwargs
    if ann is dt.date:
        return CalendarDate, kwargs

    if ann is list or origin in (list, t.List):
        list_args = t.get_args(ann)
        if list_args:
            elem = list_args[0]
            # `Any` is a class on Python 3.11+ but cannot be used with isinstance.
            if isinstance(elem, type) and elem not in (Any, object):
                kwargs["item_type"] = elem
            elif t.get_origin(elem) in (t.Union, types.UnionType):
                elem_types = tuple(a for a in t.get_args(elem) if isinstance(a, type))
                if elem_types:
                    kwargs["item_type"] = elem_types
        return List, kwargs

    if ann is tuple or origin in (tuple, t.Tuple):
        tuple_args = t.get_args(ann)
        if tuple_args and tuple_args[-1] is Ellipsis:
            kwargs["class_"] = tuple
            return ClassSelector, kwargs
        if tuple_args and tuple_args[-1] is not Ellipsis:
            kwargs["length"] = len(tuple_args)
        return Tuple, kwargs

    if ann is dict or origin in (dict, t.Dict):
        return Dict, kwargs

    if ann is set or origin in (set, t.Set):
        kwargs["class_"] = set
        return ClassSelector, kwargs

    if isinstance(ann, type) and ann not in (Any, object):
        kwargs["class_"] = ann
        return ClassSelector, kwargs

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
        # Preserve optionality when an explicit parameter bypasses inference.
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
        if not isinstance(factory, Parameter):
            factory_kwargs["default"] = Undefined
            is_required = True

    if isinstance(factory, Parameter):
        if not factory_kwargs:
            return copy.copy(factory), is_required
        initial = factory.__getstate__()
        for key in ("name", "owner", "watchers"):
            initial.pop(key, None)
        initial["label"] = initial.pop("_label")
        initial.update(factory_kwargs)
        return type(factory)(**initial), is_required
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
            if attr.startswith("_"):
                continue
            if isinstance(annotation, str):
                annotation = eval(annotation, module_globals, namespace)
            origin = t.get_origin(annotation)
            if origin is t.ClassVar or annotation is t.ClassVar:
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

    @classmethod
    def construct(cls, **params) -> t.Self:
        """
        Create an instance without requiring values for required fields.

        Required fields that are not supplied hold their Parameter's
        default until they are set, and ``missing_required`` lists the
        ones that are still unset. Like pydantic's ``model_construct``,
        this bypasses ``__init__``; it is meant for values that are filled
        in incrementally, e.g. by a form.

        Parameters
        ----------
        **params
            Parameter values to set on the new instance.

        Returns
        -------
        Model
            The new instance.
        """
        inst = cls.__new__(cls)
        Parameterized.__init__(inst, **params)
        unset = set(cls._model_required - params.keys())
        inst._model_unset = unset
        if unset:
            def mark_set(*events):
                unset.difference_update(event.name for event in events)
            inst.param.watch(mark_set, sorted(unset), onlychanged=False)
        return inst

    def missing_required(self) -> list[str]:
        """
        Return the required fields that have not been given a value.

        Only instances created with ``construct`` can have unset required
        fields; for any other instance the result is empty.

        Returns
        -------
        list[str]
            Names of the unset required fields, sorted.
        """
        return sorted(getattr(self, "_model_unset", ()))

    @classmethod
    def from_pydantic(cls, model: Any, *, name: str | None = None) -> Any:
        """
        Create a Model subclass mirroring a pydantic model.

        Field annotations, defaults, default factories, descriptions,
        titles and constraints (e.g. ``ge``, ``max_length``) are carried
        over, and nested pydantic models become nested Model classes.

        Parameters
        ----------
        model : type[pydantic.BaseModel] | pydantic.BaseModel
            The pydantic model class to convert. If an instance is given,
            an instance of the converted class holding its values is
            returned instead.
        name : str, optional
            Name of the generated class; defaults to the model's name.

        Returns
        -------
        type[Model] | Model
            The generated subclass of ``cls``, or an instance of it.
        """
        from ._model_sources import model_from_pydantic
        return model_from_pydantic(cls, model, name)

    @classmethod
    def from_json_schema(
        cls, schema: Mapping[str, Any], *, name: str | None = None
    ) -> type[Model]:
        """
        Create a Model subclass from a JSON schema of type ``object``.

        Local ``$ref``/``$defs`` and ``allOf`` are resolved, nullable
        ``anyOf``/``oneOf`` unions set ``allow_None``, ``enum`` and
        ``const`` options become selectors, string formats ``date`` and
        ``date-time`` become date parameters and numeric bounds,
        ``pattern`` and ``multipleOf`` are applied. Nested objects become
        nested Model classes. Properties listed in ``required`` without a
        default are required, others default to ``None``. The original
        property schema is kept in each Parameter's
        ``metadata["json_schema"]``.

        Parameters
        ----------
        schema : Mapping[str, Any]
            A JSON schema describing an object.
        name : str, optional
            Name of the generated class; defaults to the schema title.

        Returns
        -------
        type[Model]
            The generated subclass of ``cls``.
        """
        from ._model_sources import model_from_json_schema
        return model_from_json_schema(cls, schema, name)
