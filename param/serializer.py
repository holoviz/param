"""
Classes used to support string serialization of Parameters and
Parameterized objects.
"""
from __future__ import annotations

import json
import textwrap

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Callable, cast

if TYPE_CHECKING:
    from .parameterized import Parameter, Parameterized
    from .parameters import (
        Tuple,
    )

class UnserializableException(Exception):
    pass

class UnsafeserializableException(Exception):
    pass

def JSONNullable(json_type):
    """Express a JSON schema type as nullable to easily support Parameters that allow_None."""
    return {'anyOf': [ json_type, {'type': 'null'}] }



class Serialization:
    """Base class used to implement different types of serialization."""

    @classmethod
    def schema(
        cls, pobj: Parameterized | type[Parameterized], subset: Iterable[str] | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def serialize_parameters(
        cls, pobj: Parameterized | type[Parameterized], subset: Iterable[str] | None = None
    ) -> str:
        """
        Serialize the parameters on a Parameterized object into a
        single serialized object, e.g. a JSON string.
        """
        raise NotImplementedError

    @classmethod
    def deserialize_parameters(
        cls,
        pobj: Parameterized | type[Parameterized],
        serialized: str,
        subset: Iterable[str] | None = None
    ) -> dict[str, Any]:
        """
        Deserialize a serialized object representing one or
        more Parameters into a dictionary of parameter values.
        """
        raise NotImplementedError

    @classmethod
    def serialize_parameter_value(cls, pobj: Parameterized | type[Parameterized], pname: str) -> str:
        """Serialize a single parameter value."""
        raise NotImplementedError

    @classmethod
    def deserialize_parameter_value(
        cls, pobj: Parameterized | type[Parameterized], pname: str, value: str
    ) -> Any:
        """Deserialize a single parameter value."""
        raise NotImplementedError


class JSONSerialization(Serialization):
    """
    Class responsible for specifying JSON serialization, deserialization
    and JSON schemas for Parameters and Parameterized classes and
    objects.
    """

    unserializable_parameter_types = ['Callable']

    json_schema_literal_types = {
        int:'integer', float:'number', str:'string',
        type(None): 'null'
    }

    @classmethod
    def loads(cls, serialized: str) -> Any:
        return json.loads(serialized)

    @classmethod
    def dumps(cls, obj: Any) -> str:
        return json.dumps(obj)

    @classmethod
    def schema(
        cls,
        pobj: Parameterized | type[Parameterized],
        subset: Iterable[str] | None = None,
        *,
        safe: bool = False
    ) -> dict[str, Any]:
        schema: dict[str, Any] = {}
        params = cast(Any, pobj).param
        for name, p in params.objects('existing').items():
            if subset is not None and name not in subset:
                continue
            schema[name] = p.schema(safe=safe)
            if p.doc:
                schema[name]['description'] = textwrap.dedent(p.doc).replace('\n', ' ').strip()
            if p.label:
                schema[name]['title'] = p.label
        return schema

    @classmethod
    def serialize_parameters(
        cls, pobj: Parameterized | type[Parameterized], subset: Iterable[str] | None = None
    ) -> str:
        components: dict[str, Any] = {}
        params = cast(Any, pobj).param
        for name, p in params.objects('existing').items():
            if subset is not None and name not in subset:
                continue
            value = params.get_value_generator(name)
            components[name] = p.serialize(value)
        return cls.dumps(components)

    @classmethod
    def deserialize_parameters(
        cls,
        pobj: Parameterized | type[Parameterized],
        serialized: str,
        subset: Iterable[str] | None = None
    ) -> dict[str, Any]:
        deserialized = cls.loads(serialized)
        components: dict[str, Any] = {}
        params = cast(Any, pobj).param
        for name, value in deserialized.items():
            if subset is not None and name not in subset:
                continue
            deserialized = params[name].deserialize(value)
            components[name] = deserialized
        return components

    # Parameter level methods

    @classmethod
    def _get_method(cls, ptype: str, suffix: str) -> Callable[..., Any] | None:
        """Return specialized method if available, otherwise None."""
        method_name = ptype.lower()+'_' + suffix
        return getattr(cls, method_name, None)

    @classmethod
    def param_schema(
        cls, ptype: str, p: Parameter, safe: bool = False, subset: Iterable[str] | None = None
    ) -> dict[str, Any]:
        if ptype in cls.unserializable_parameter_types:
            raise UnserializableException
        dispatch_method = cls._get_method(ptype, 'schema')
        if dispatch_method:
            schema = dispatch_method(p, safe=safe)
        else:
            schema = {'type': ptype.lower()}
        return JSONNullable(schema) if p.allow_None else schema

    @classmethod
    def serialize_parameter_value(cls, pobj: Parameterized | type[Parameterized], pname: str) -> str:
        params = cast(Any, pobj).param
        value = params.get_value_generator(pname)
        return cls.dumps(params[pname].serialize(value))

    @classmethod
    def deserialize_parameter_value(
        cls, pobj: Parameterized | type[Parameterized], pname: str, value: str
    ) -> Any:
        value = cls.loads(value)
        params = cast(Any, pobj).param
        return params[pname].deserialize(value)

    # Custom Schemas

    @classmethod
    def class__schema(cls, class_: Any, safe: bool = False) -> dict[str, Any]:
        from .parameterized import Parameterized
        if isinstance(class_, tuple):
            return {'anyOf': [cls.class__schema(cls_) for cls_ in class_]}
        elif class_ in cls.json_schema_literal_types:
            return {'type': cls.json_schema_literal_types[class_]}
        elif issubclass(class_, Parameterized):
            return {'type': 'object', 'properties': class_.param.schema(safe)}
        else:
            return {'type': 'object'}

    @classmethod
    def array_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        if safe is True:
            msg = ('Array is not guaranteed to be safe for '
                   'serialization as the dtype is unknown')
            raise UnsafeserializableException(msg)
        return {'type': 'array'}

    @classmethod
    def classselector_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        return cls.class__schema(p.class_, safe=safe)

    @classmethod
    def dict_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        if safe is True:
            msg = ('Dict is not guaranteed to be safe for '
                   'serialization as the key and value types are unknown')
            raise UnsafeserializableException(msg)
        return {'type': 'object'}

    @classmethod
    def date_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        return {'type': 'string', 'format': 'date-time'}

    @classmethod
    def calendardate_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        return {'type': 'string', 'format': 'date'}

    @classmethod
    def tuple_schema(cls, p: Tuple, safe: bool = False) -> dict[str, Any]:
        schema: dict[str, object] = {'type': 'array'}
        if p.length is not None:
            schema['minItems'] =  p.length
            schema['maxItems'] =  p.length
        return schema

    @classmethod
    def number_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        schema: dict[str, object] = {'type': p.__class__.__name__.lower() }
        return cls.declare_numeric_bounds(schema, p.bounds, p.inclusive_bounds)

    @classmethod
    def declare_numeric_bounds(
        cls,
        schema: dict[str, Any],
        bounds: tuple[Any | None, Any | None] | None,
        inclusive_bounds: tuple[bool, bool],
    ) -> dict[str, Any]:
        """Given an applicable numeric schema, augment with bounds information."""
        if bounds is not None:
            (low, high) = bounds
            if low is not None:
                key = 'minimum' if inclusive_bounds[0] else 'exclusiveMinimum'
                schema[key] = low
            if high is not None:
                key = 'maximum' if inclusive_bounds[1] else 'exclusiveMaximum'
                schema[key] = high
        return schema

    @classmethod
    def integer_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        return cls.number_schema(p)

    @classmethod
    def numerictuple_schema(cls, p: Tuple, safe: bool = False) -> dict[str, Any]:
        schema = cls.tuple_schema(p, safe=safe)
        schema['additionalItems'] = {'type': 'number'}
        return schema

    @classmethod
    def xycoordinates_schema(cls, p: Tuple, safe: bool = False) -> dict[str, Any]:
        return cls.numerictuple_schema(p, safe=safe)

    @classmethod
    def range_schema(cls, p: Tuple, safe: bool = False) -> dict[str, Any]:
        schema = cls.tuple_schema(p, safe=safe)
        bounded_number = cls.declare_numeric_bounds(
            {'type': 'number'}, p.bounds, p.inclusive_bounds)
        schema['additionalItems'] = bounded_number
        return schema

    @classmethod
    def list_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        schema: dict[str, object] = {'type': 'array'}
        if safe is True and p.item_type is None:
            msg = ('List without a class specified cannot be guaranteed '
                   'to be safe for serialization')
            raise UnsafeserializableException(msg)
        if p.item_type is not None:
            schema['items'] = cls.class__schema(p.item_type, safe=safe)
        return schema

    @classmethod
    def objectselector_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        try:
            allowed_types = [{'type': cls.json_schema_literal_types[type(obj)]}
                             for obj in p.objects]
            schema = {'anyOf': allowed_types}
            schema['enum'] = p.objects
            return schema
        except Exception:
            if safe is True:
                msg = ('ObjectSelector cannot be guaranteed to be safe for '
                       'serialization due to unserializable type in objects')
                raise UnsafeserializableException(msg)
            return {}

    @classmethod
    def selector_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        try:
            allowed_types = [{'type': cls.json_schema_literal_types[type(obj)]}
                             for obj in p.objects.values()]
            schema = {'anyOf': allowed_types}
            schema['enum'] = p.objects
            return schema
        except Exception:
            if safe is True:
                msg = ('Selector cannot be guaranteed to be safe for '
                       'serialization due to unserializable type in objects')
                raise UnsafeserializableException(msg)
            return {}

    @classmethod
    def listselector_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        if p.objects is None:
            if safe is True:
                msg = ('ListSelector cannot be guaranteed to be safe for '
                       'serialization as allowed objects unspecified')
            return {'type': 'array'}
        for obj in p.objects:
            if type(obj) not in cls.json_schema_literal_types:
                msg = 'ListSelector cannot serialize type %s' % type(obj)
                raise UnserializableException(msg)
        return {'type': 'array', 'items': {'enum': p.objects}}

    @classmethod
    def dataframe_schema(cls, p: Parameter, safe: bool = False) -> dict[str, Any]:
        schema: dict[str, object] = {'type': 'array'}
        if safe is True:
            msg = ('DataFrame is not guaranteed to be safe for '
                   'serialization as the column dtypes are unknown')
            raise UnsafeserializableException(msg)
        if p.columns is None:
            schema['items'] = {'type': 'object'}
            return schema

        mincols, maxcols = None, None
        if isinstance(p.columns, int):
            mincols, maxcols = p.columns, p.columns
        elif isinstance(p.columns, tuple):
            mincols, maxcols = p.columns

        if isinstance(p.columns, int) or isinstance(p.columns, tuple):
            schema['items'] =  {'type': 'object', 'minItems': mincols,
                                'maxItems': maxcols}

        if isinstance(p.columns, list) or isinstance(p.columns, set):
            literal_types = [{'type':el} for el in cls.json_schema_literal_types.values()]
            allowable_types = {'anyOf': literal_types}
            properties = {name: allowable_types for name in p.columns}
            schema['items'] =  {'type': 'object', 'properties': properties}

        minrows, maxrows = None, None
        if isinstance(p.rows, int):
            minrows, maxrows = p.rows, p.rows
        elif isinstance(p.rows, tuple):
            minrows, maxrows = p.rows

        if minrows is not None:
            schema['minItems'] = minrows
        if maxrows is not None:
            schema['maxItems'] = maxrows

        return schema
