"""
Build ``Model`` classes from pydantic models and JSON schemas.

Both sources are translated into type annotations plus ``Field``
specifications, so the resulting Parameters are inferred by the same
machinery as a hand-written ``Model``.
"""
from __future__ import annotations

import copy
import datetime as dt
import keyword
import re
import types
import typing as t

from collections.abc import Mapping
from typing import Any

from .parameters import ListSelector, NumericTuple, Range
from .typed import Field, Model, ModelMetaclass

if t.TYPE_CHECKING:
    from pydantic import BaseModel


def _subscript(form: Any, args: Any) -> Any:
    """Subscript a typing form with arguments only known at runtime."""
    return form[args]


def _check_field_name(name: str, source: str) -> None:
    if name.startswith("_") or name == "param":
        raise ValueError(
            f"Cannot convert field {name!r} of {source}: Model fields may not "
            "start with an underscore or be named 'param'."
        )


def _create_model(
    base: type[Model],
    name: str,
    annotations: dict[str, Any],
    fields: dict[str, Any],
    doc: str | None,
    module: str,
) -> type[Model]:
    namespace: dict[str, Any] = {
        "__annotations__": annotations,
        "__module__": module,
        "__qualname__": name,
        **fields,
    }
    if doc:
        namespace["__doc__"] = doc
    return t.cast("type[Model]", ModelMetaclass(name, (base,), namespace))


# pydantic


def _is_pydantic_model(obj: Any) -> bool:
    try:
        from pydantic import BaseModel
    except ImportError:
        return False
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def _is_secret_str(obj: Any) -> bool:
    return getattr(obj, "__module__", "").startswith("pydantic") and getattr(obj, "__name__", "") == "SecretStr"


class _PydanticConverter:

    def __init__(self, base: type[Model]):
        self.base = base
        self.converted: dict[type, type[Model]] = {}
        self.in_progress: set[type] = set()

    def convert(self, model: type[BaseModel], name: str | None = None) -> type[Model]:
        if model in self.converted:
            return self.converted[model]
        self.in_progress.add(model)
        try:
            annotations: dict[str, Any] = {}
            fields: dict[str, Any] = {}
            for fname, info in model.model_fields.items():
                _check_field_name(fname, model.__name__)
                annotation = self.rewrite(info.annotation)
                if info.metadata:
                    annotation = _subscript(t.Annotated, (annotation, *info.metadata))
                annotations[fname] = annotation
                fields[fname] = self.field(info)
            cls = _create_model(
                self.base, name or model.__name__, annotations, fields,
                model.__doc__, model.__module__,
            )
        finally:
            self.in_progress.discard(model)
        self.converted[model] = cls
        return cls

    def rewrite(self, annotation: Any) -> Any:
        """Replace nested pydantic models with their converted Model classes."""
        if _is_pydantic_model(annotation):
            # A self-referencing model cannot be converted before it exists.
            if annotation in self.in_progress:
                return Any
            return self.convert(annotation)
        if _is_secret_str(annotation):
            return str
        args = t.get_args(annotation)
        if not args:
            return annotation
        origin = t.get_origin(annotation)
        if origin is t.Literal:
            return annotation
        if origin is t.Annotated:
            return _subscript(t.Annotated, (self.rewrite(args[0]), *annotation.__metadata__))
        new_args = tuple(self.rewrite(a) for a in args)
        if new_args == args:
            return annotation
        if origin in (t.Union, types.UnionType):
            return _subscript(t.Union, new_args)
        try:
            return _subscript(origin, new_args)
        except TypeError:
            return annotation

    def value(self, value: Any) -> Any:
        """Convert pydantic model instances (also inside containers) to Model instances."""
        from pydantic import BaseModel

        if _is_secret_str(type(value)):
            return value.get_secret_value()
        if isinstance(value, BaseModel):
            cls = self.convert(type(value))
            return cls(**{k: self.value(getattr(value, k)) for k in type(value).model_fields})
        if isinstance(value, list):
            return [self.value(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self.value(v) for v in value)
        if isinstance(value, dict):
            return {k: self.value(v) for k, v in value.items()}
        return value

    def field(self, info: Any) -> Any:
        from pydantic_core import PydanticUndefined

        kwargs: dict[str, Any] = {}
        if info.description:
            kwargs["doc"] = info.description
        if info.title:
            kwargs["label"] = info.title
        if info.default is not PydanticUndefined:
            default = self.value(info.default)
            if isinstance(default, (list, dict, set, Model)):
                kwargs["default_factory"] = lambda d=default: copy.deepcopy(d)
            else:
                kwargs["default"] = default
        elif info.default_factory is not None and not getattr(info, "default_factory_takes_data", False):
            factory = info.default_factory
            kwargs["default_factory"] = lambda: self.value(factory())
        return Field(**kwargs)


def model_from_pydantic(
    base: type[Model], model: type[BaseModel] | BaseModel, name: str | None = None
) -> type[Model] | Model:
    try:
        from pydantic import BaseModel
    except ImportError as e:
        raise ImportError("Model.from_pydantic requires pydantic to be installed.") from e

    converter = _PydanticConverter(base)
    if isinstance(model, BaseModel):
        cls = converter.convert(type(model), name)
        values = {k: converter.value(getattr(model, k)) for k in type(model).model_fields}
        return cls(**values)
    if not _is_pydantic_model(model):
        raise TypeError(f"Expected a pydantic model class or instance, got {model!r}.")
    return converter.convert(model, name)


# JSON schema

_JSON_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}

_DATE_FORMATS: dict[str, Any] = {"date": dt.date, "date-time": dt.datetime}


def _class_name(text: str) -> str:
    name = "".join(part[:1].upper() + part[1:] for part in re.split(r"[^0-9a-zA-Z]+", text) if part)
    if not name or name[0].isdigit() or keyword.iskeyword(name):
        name = f"Model{name}"
    return name


def _parse_date(value: Any, kind: Any) -> Any:
    if not isinstance(value, str):
        return value
    if kind is dt.date:
        return dt.date.fromisoformat(value)
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


class _SchemaConverter:

    def __init__(self, base: type[Model], root: Mapping[str, Any], module: str):
        self.base = base
        self.root = root
        self.module = module
        self.defs: Mapping[str, Any] = root.get("$defs") or root.get("definitions") or {}
        self.converted: dict[str, type[Model]] = {}
        self.in_progress: set[str] = set()

    def resolve(self, node: Mapping[str, Any], seen: frozenset[str] = frozenset()) -> dict[str, Any]:
        node = dict(node)
        ref = node.pop("$ref", None)
        if ref is not None:
            if ref in seen:
                return {**node, "$recursive": ref}
            target = self.lookup(ref)
            node = {**self.resolve(target, seen | {ref}), **node}
            node.setdefault("$name", ref.rsplit("/", 1)[-1])
        all_of = node.pop("allOf", None)
        if all_of:
            merged: dict[str, Any] = {}
            for sub in all_of:
                sub = self.resolve(sub, seen)
                props = {**merged.get("properties", {}), **sub.get("properties", {})}
                required = [*merged.get("required", []), *sub.get("required", [])]
                merged.update(sub)
                if props:
                    merged["properties"] = props
                if required:
                    merged["required"] = required
            node = {**merged, **node}
        return node

    def lookup(self, ref: str) -> Mapping[str, Any]:
        if ref == "#":
            return self.root
        if not ref.startswith("#/"):
            raise ValueError(f"Only local schema references are supported, got {ref!r}.")
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node

    def model(self, schema: Mapping[str, Any], name: str) -> type[Model] | None:
        """Convert an object schema, or return None if it is already being converted."""
        key = schema.get("$name")
        if key and key in self.converted:
            return self.converted[key]
        if key and key in self.in_progress:
            return None
        if key:
            self.in_progress.add(key)
        try:
            schema = self.resolve(schema)
            required = set(schema.get("required", []))
            annotations: dict[str, Any] = {}
            fields: dict[str, Any] = {}
            for pname, prop in schema.get("properties", {}).items():
                _check_field_name(pname, f"schema {name!r}")
                annotations[pname], fields[pname] = self.property(prop, pname, pname in required)
            cls = _create_model(self.base, name, annotations, fields, schema.get("description"), self.module)
        finally:
            if key:
                self.in_progress.discard(key)
        if key:
            self.converted[key] = cls
        return cls

    def property(self, prop: Mapping[str, Any], pname: str, required: bool) -> tuple[Any, Any]:
        original = prop
        prop = self.resolve(prop)
        nullable = False
        kwargs: dict[str, Any] = {"metadata": {"json_schema": dict(original)}}

        for key in ("anyOf", "oneOf"):
            if key not in prop:
                continue
            options = [self.resolve(o) for o in prop[key]]
            non_null = [o for o in options if o.get("type") != "null"]
            nullable = nullable or len(non_null) < len(options)
            outer = {k: v for k, v in prop.items() if k != key}
            if non_null and all("const" in o for o in non_null):
                outer["enum"] = [o["const"] for o in non_null]
                titles = [o.get("title") for o in non_null]
                if all(titles):
                    outer["enumNames"] = titles
                prop = outer
            elif len(non_null) == 1:
                prop = {**non_null[0], **outer}
            elif "enum" in outer:
                # param's own schema export lists the value types next to `enum`.
                prop = outer
            else:
                types_ = [self.annotation(o, pname, kwargs) for o in non_null]
                prop = {**outer, "$annotation": _subscript(t.Union, tuple(types_)) if types_ else Any}

        type_ = prop.get("type")
        if isinstance(type_, list):
            nullable = nullable or "null" in type_
            non_null_types = [ty for ty in type_ if ty != "null"]
            prop = {**prop, "type": non_null_types[0] if len(non_null_types) == 1 else non_null_types or None}

        annotation = prop["$annotation"] if "$annotation" in prop else self.annotation(prop, pname, kwargs)

        if prop.get("description"):
            kwargs["doc"] = prop["description"]
        if prop.get("title"):
            kwargs["label"] = prop["title"]

        if "default" in prop:
            kwargs["default"] = self.default(prop["default"], annotation)
        elif not required:
            nullable = True
            kwargs["default"] = None
        elif isinstance(annotation, type) and issubclass(annotation, Model) and not annotation._model_required:
            kwargs["default_factory"] = annotation

        if nullable:
            annotation = _subscript(t.Optional, annotation) if annotation is not Any else Any
        return annotation, Field(**kwargs)

    def annotation(self, prop: Mapping[str, Any], pname: str, kwargs: dict[str, Any]) -> Any:
        if "$recursive" in prop:
            return Any
        if "const" in prop and "enum" not in prop:
            prop = {**prop, "enum": [prop["const"]]}
        if "enum" in prop:
            values = list(prop["enum"])
            names = prop.get("enumNames")
            if names and len(names) == len(values):
                kwargs["objects"] = dict(zip(names, values))
            return _subscript(t.Literal, tuple(values)) if values else Any

        type_ = prop.get("type")
        if isinstance(type_, list):
            types_ = [self.annotation({**prop, "type": ty}, pname, {}) for ty in type_]
            return _subscript(t.Union, tuple(types_))

        if type_ == "string":
            fmt = prop.get("format")
            if fmt in _DATE_FORMATS:
                kind = _DATE_FORMATS[fmt]
                low = prop.get("formatMinimum", prop.get("formatExclusiveMinimum"))
                high = prop.get("formatMaximum", prop.get("formatExclusiveMaximum"))
                if low is not None or high is not None:
                    kwargs["bounds"] = (_parse_date(low, kind), _parse_date(high, kind))
                    kwargs["inclusive_bounds"] = (
                        "formatExclusiveMinimum" not in prop, "formatExclusiveMaximum" not in prop,
                    )
                return kind
            if "pattern" in prop:
                kwargs["regex"] = prop["pattern"]
            return str

        if type_ in ("integer", "number"):
            low = prop.get("minimum", prop.get("exclusiveMinimum"))
            high = prop.get("maximum", prop.get("exclusiveMaximum"))
            if low is not None or high is not None:
                kwargs["bounds"] = (low, high)
                kwargs["inclusive_bounds"] = ("exclusiveMinimum" not in prop, "exclusiveMaximum" not in prop)
            if "multipleOf" in prop:
                kwargs["step"] = prop["multipleOf"]
            return _JSON_TYPES[type_]

        if type_ == "boolean":
            return bool

        if type_ == "array":
            return self.array(prop, pname, kwargs)

        if type_ == "object" or "properties" in prop:
            if "properties" in prop:
                # A recursive reference to a model still being converted stays unvalidated.
                nested = self.model(prop, _class_name(prop.get("title") or prop.get("$name") or pname))
                return Any if nested is None else nested
            return dict

        if type_ == "null":
            return type(None)
        return Any

    def array(self, prop: Mapping[str, Any], pname: str, kwargs: dict[str, Any]) -> Any:
        prefix = prop.get("prefixItems")
        if prefix is None and isinstance(prop.get("items"), list):
            prefix = prop["items"]
        if prefix is not None:
            item_types = tuple(self.annotation(self.resolve(i), pname, {}) for i in prefix)
            return _subscript(tuple, item_types) if item_types else tuple

        additional = prop.get("additionalItems")
        length = prop.get("minItems") if prop.get("minItems") == prop.get("maxItems") else None
        if isinstance(additional, Mapping) and additional.get("type") in ("number", "integer"):
            bounds_kwargs: dict[str, Any] = {}
            self.annotation(additional, pname, bounds_kwargs)
            if length == 2 and "bounds" in bounds_kwargs:
                kwargs.update(parameter=Range, **bounds_kwargs)
                return tuple
            kwargs["parameter"] = NumericTuple
            if length is not None:
                kwargs["length"] = length
            return tuple
        if length is not None and "items" not in prop:
            return _subscript(tuple, (Any,) * length) if length else tuple

        items = prop.get("items")
        if isinstance(items, Mapping):
            items = self.resolve(items)
            if "enum" in items:
                kwargs.update(parameter=ListSelector, objects=list(items["enum"]))
                return list
            item_type = self.annotation(items, f"{pname}_item", {})
        else:
            item_type = None
        if "minItems" in prop or "maxItems" in prop:
            kwargs["bounds"] = (prop.get("minItems", 0), prop.get("maxItems"))
        return _subscript(list, item_type) if isinstance(item_type, type) else list

    def default(self, value: Any, annotation: Any) -> Any:
        inner = annotation
        if t.get_origin(inner) in (t.Union, types.UnionType):
            non_none = [a for a in t.get_args(inner) if a is not type(None)]
            inner = non_none[0] if len(non_none) == 1 else inner
        if inner in (dt.date, dt.datetime):
            return _parse_date(value, inner)
        if isinstance(value, list) and (inner is tuple or t.get_origin(inner) is tuple):
            return tuple(value)
        if isinstance(inner, type) and issubclass(inner, Model) and isinstance(value, Mapping):
            return inner(**value)
        return value


def model_from_json_schema(
    base: type[Model], schema: Mapping[str, Any], name: str | None = None, module: str | None = None
) -> type[Model]:
    if not isinstance(schema, Mapping):
        raise TypeError(f"Expected a JSON schema mapping, got {type(schema).__name__}.")
    resolved = _SchemaConverter(base, schema, module or __name__).resolve(schema)
    if resolved.get("type", "object") != "object":
        raise ValueError("Model.from_json_schema expects a schema of type 'object'.")
    converter = _SchemaConverter(base, schema, module or __name__)
    return t.cast("type[Model]", converter.model(schema, name or _class_name(schema.get("title") or "Model")))
