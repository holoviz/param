"""
Classes used to support string serialization of Parameters and
Parameterized objects.
"""

import json


class UnserializableException(Exception):
    pass

def JSONNullable(json_type):
    "Express a JSON schema type as nullable to easily support Parameters that allow_None"
    return { "anyOf": [ json_type, { "type": "null"}] }



class Serialization(object):
    """
    Base class used to implement different types of serialization.
    """

    @classmethod
    def schema(cls, pobj):
        raise NotImplementedError

    @classmethod
    def serialize_parameters(cls, pobj):
        raise NotImplementedError



class JSONSerialization(Serialization):
    """
    Class responsible for specifying JSON serialization, deserialization
    and JSON schemas for Parameters and Parameterized classes and
    objects.
    """

    unserializable_parameter_types = ['Callable']

    json_schema_literal_types = {int:'integer', float:'number', str:'string'}


    @classmethod
    def schema(cls, pobj):
        schema = {}
        for name, p in pobj.param.objects('existing').items():
            schema[name] = p._schema()
            if p.doc:
                schema[name]["description"] = p.doc.strip()
        return schema

    @classmethod
    def serialize_parameters(cls, pobj):
        components = {}
        json_string = ''
        for name, p in pobj.param.objects('existing').items():
            value = pobj.param.get_value_generator(name)
            components[name] = p._serialize(value)

        contents = ', '.join('"%s":%s' % (name, sval) for name, sval in components.items())
        return '{{{contents}}}'.format(contents=contents)

    # Parameter level methods

    @classmethod
    def _get_method(cls, ptype, suffix):
        "Returns specialized method if available, otherwise None"
        method_name = ptype.lower()+'_' + suffix
        return getattr(cls, method_name, None)

    @classmethod
    def parameter_schema(cls, ptype, p):
        if ptype in cls.unserializable_parameter_types:
            raise UnserializableException
        dispatch_method = cls._get_method(ptype, 'schema')
        if dispatch_method:
            return dispatch_method(p)
        else:
            return { "type": ptype.lower()}

    @classmethod
    def serialize(cls, ptype, value):
        dispatch_method = cls._get_method(ptype, 'serialize')
        if dispatch_method:
            return dispatch_method(value)
        else:
            return json.dumps(value)

    @classmethod
    def deserialize(cls, ptype, string):
        dispatch_method = cls._get_method(ptype, 'deserialize')
        if dispatch_method:
            return dispatch_method(value)
        else:
            return json.loads(string)

    # Custom Serializers

    @classmethod
    def date_serialize(cls, value):
        string = value.replace(microsecond=0).isoformat() # Test *with* microseconds.
        return json.dumps(string)

    # Custom Deserializers

    @classmethod
    def date_deserialize(cls, string):
        return dt.datetime.fromisoformat(string)  # FIX: 3.7+ only

    @classmethod
    def tuple_deserialize(cls, string):
        return tuple(json.loads(string))

    # Custom Schemas

    @classmethod
    def date_schema(cls, p):
        return { "type": "string", "format": "date-time"}

    @classmethod
    def tuple_schema(cls, p):
        return { "type": "array"}

    @classmethod
    def number_schema(cls, p):
        schema = { "type": p.__class__.__name__.lower() }
        if p.bounds is not None:
            (low, high) = p.bounds
            if low is not None:
                key = 'minimum' if p.inclusive_bounds[0] else 'exclusiveMinimum'
                schema[key] = low
            if high is not None:
                key = 'maximum' if p.inclusive_bounds[0] else 'exclusiveMaximum'
                schema[key] = high

        return JSONNullable(schema) if p.allow_None else schema

    @classmethod
    def integer_schema(cls, p):
        return cls.number_schema(p)

    @classmethod
    def numerictuple_schema(cls, p):
        return {"type": "array",
                "additionalItems": { "type": "number" }}

    @classmethod
    def xycoordinates_schema(cls, p):
        return  {
            "type": "array",
            "items": [
                {"type": "number"}, {"type": "number"}],
            "additionalItems": False
        }

    @classmethod
    def range_schema(cls, p):
        return  {
            "type": "array",
            "items": [{"type": "number"},{"type": "number"}],
        }

    @classmethod
    def list_schema(cls, p):
        schema =  { "type": "array"}
        if p.class_ is not None and p.class_ in cls.json_schema_literal_types:
            schema['items'] = {"type": cls.json_schema_literal_types[p.class_]}
        return schema
