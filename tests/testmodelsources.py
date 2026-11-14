"""Tests for creating Models from annotated constraints, pydantic models and JSON schemas."""
import datetime as dt
import enum
import typing as t

import param
import pytest


# Annotated constraints

def test_annotated_types_bounds():
    at = pytest.importorskip("annotated_types")

    class P(param.Model):
        a: t.Annotated[int, at.Ge(0), at.Lt(10)] = 1
        b: t.Annotated[float, at.Interval(gt=0, le=1)] = 0.5

    assert P.param.a.bounds == (0, 10)
    assert P.param.a.inclusive_bounds == (True, False)
    assert P.param.b.bounds == (0, 1)
    assert P.param.b.inclusive_bounds == (False, True)
    with pytest.raises(ValueError):
        P(a=10)


def test_annotated_types_bounds_on_optional():
    at = pytest.importorskip("annotated_types")

    class P(param.Model):
        a: t.Annotated[float | None, at.Ge(2)] = None
        b: t.Optional[t.Annotated[float, at.Le(5)]] = None

    assert P.param.a.bounds == (2, None)
    assert P.param.a.allow_None
    assert P.param.b.bounds == (None, 5)


def test_annotated_types_multiple_of_sets_step():
    at = pytest.importorskip("annotated_types")

    class P(param.Model):
        x: t.Annotated[float, at.MultipleOf(0.25)] = 0.5

    assert P.param.x.step == 0.25


def test_annotated_types_length_bounds_list():
    at = pytest.importorskip("annotated_types")

    class P(param.Model):
        items: t.Annotated[list[int], at.MinLen(1), at.MaxLen(3)] = [1]

    assert P.param.items.bounds == (1, 3)
    with pytest.raises(ValueError):
        P(items=[1, 2, 3, 4])


def test_annotated_mapping_bounds_take_precedence():
    at = pytest.importorskip("annotated_types")

    class P(param.Model):
        x: t.Annotated[int, {"bounds": (0, 5)}, at.Le(100)] = 1

    assert P.param.x.bounds == (0, 5)


def test_unrelated_annotated_metadata_is_ignored():
    class Meta:
        ge = 5

    class P(param.Model):
        x: t.Annotated[int, Meta()] = 1

    assert P.param.x.bounds is None


# pydantic

class Level(enum.Enum):
    LOW = "low"
    HIGH = "high"


@pytest.fixture
def models():
    pydantic = pytest.importorskip("pydantic")

    class Address(pydantic.BaseModel):
        city: str = "Berlin"
        zip: str = pydantic.Field("10115", pattern=r"^\d{5}$")

    class Query(pydantic.BaseModel):
        """Run a SQL query."""

        sql: str = pydantic.Field(description="The SQL to run", title="SQL")
        limit: int = pydantic.Field(100, ge=1, le=1000)
        ratio: float | None = pydantic.Field(None, gt=0, lt=1)
        mode: t.Literal["fast", "slow"] = "fast"
        level: Level = Level.LOW
        since: dt.date | None = None
        at: dt.datetime | None = None
        tags: list[str] = pydantic.Field(default_factory=list, max_length=5)
        address: Address = pydantic.Field(default_factory=Address)
        others: list[Address] = []
        token: pydantic.SecretStr | None = None

    return pydantic, Address, Query


def test_from_pydantic_parameter_types(models):
    _, _, Query = models
    P = param.Model.from_pydantic(Query)

    assert issubclass(P, param.Model)
    assert P.__name__ == "Query"
    assert P.__doc__ == "Run a SQL query."
    assert isinstance(P.param.sql, param.String)
    assert isinstance(P.param.limit, param.Integer)
    assert isinstance(P.param.ratio, param.Number)
    assert isinstance(P.param.mode, param.Selector)
    assert isinstance(P.param.level, param.Selector)
    assert isinstance(P.param.since, param.CalendarDate)
    assert isinstance(P.param.at, param.Date)
    assert isinstance(P.param.tags, param.List)
    assert isinstance(P.param.address, param.ClassSelector)
    assert isinstance(P.param.token, param.String)


def test_from_pydantic_field_details(models):
    _, _, Query = models
    P = param.Model.from_pydantic(Query)

    assert P.param.sql.doc == "The SQL to run"
    assert P.param.sql.label == "SQL"
    assert P.param.limit.default == 100
    assert P.param.limit.bounds == (1, 1000)
    assert P.param.ratio.bounds == (0, 1)
    assert P.param.ratio.inclusive_bounds == (False, False)
    assert P.param.ratio.allow_None
    assert P.param.mode.objects == ["fast", "slow"]
    assert P.param.level.objects == [Level.LOW, Level.HIGH]
    assert P.param.level.default is Level.LOW
    assert P.param.tags.item_type is str
    assert P.param.tags.bounds == (0, 5)
    assert P._model_required == {"sql"}


def test_from_pydantic_required_fields(models):
    _, _, Query = models
    P = param.Model.from_pydantic(Query)

    with pytest.raises(TypeError, match="'sql'"):
        P()
    assert P(sql="SELECT 1").sql == "SELECT 1"


def test_from_pydantic_default_factories_are_not_shared(models):
    _, _, Query = models
    P = param.Model.from_pydantic(Query)

    a, b = P(sql="a"), P(sql="b")
    a.tags.append("x")
    assert b.tags == []
    assert a.address is not b.address


def test_from_pydantic_nested_models(models):
    _, Address, Query = models
    P = param.Model.from_pydantic(Query)

    nested = P.param.address.class_
    assert issubclass(nested, param.Model)
    assert nested.__name__ == "Address"
    assert P.param.others.item_type is nested
    assert P(sql="x").address.city == "Berlin"
    assert nested.param.zip.regex == r"^\d{5}$"
    with pytest.raises(ValueError):
        nested(zip="abc")


def test_from_pydantic_reuses_converted_nested_models(models):
    pydantic, Address, _ = models

    class Route(pydantic.BaseModel):
        start: Address
        end: Address

    P = param.Model.from_pydantic(Route)
    assert P.param.start.class_ is P.param.end.class_


def test_from_pydantic_instance(models):
    _, Address, Query = models
    q = Query(sql="SELECT 2", address=Address(city="Paris"), others=[Address(city="Rome")])

    p = param.Model.from_pydantic(q)

    assert isinstance(p, param.Model)
    assert p.sql == "SELECT 2"
    assert p.address.city == "Paris"
    assert isinstance(p.address, type(p).param.address.class_)
    assert [o.city for o in p.others] == ["Rome"]


def test_from_pydantic_custom_name_and_base(models):
    _, _, Query = models

    class Base(param.Model):
        pass

    P = Base.from_pydantic(Query, name="QueryForm")
    assert P.__name__ == "QueryForm"
    assert issubclass(P, Base)
    assert issubclass(P.param.address.class_, Base)


def test_from_pydantic_self_referencing_model():
    pydantic = pytest.importorskip("pydantic")

    class Node(pydantic.BaseModel):
        value: int = 0
        children: list["Node"] = []

    Node.model_rebuild()
    P = param.Model.from_pydantic(Node)
    assert isinstance(P.param.children, param.List)
    assert P().children == []

    tree = param.Model.from_pydantic(Node(value=1, children=[Node(value=2)]))
    assert tree.children[0].value == 2


def test_from_pydantic_unwraps_secret_values():
    pydantic = pytest.importorskip("pydantic")

    class Credentials(pydantic.BaseModel):
        token: pydantic.SecretStr | None = None

    P = param.Model.from_pydantic(Credentials)
    assert isinstance(P.param.token, param.String)
    assert param.Model.from_pydantic(Credentials(token="abc")).token == "abc"


def test_from_pydantic_rejects_param_field_name():
    pydantic = pytest.importorskip("pydantic")

    class Bad(pydantic.BaseModel):
        param: int = 1

    with pytest.raises(ValueError, match="'param'"):
        param.Model.from_pydantic(Bad)


def test_from_pydantic_rejects_non_models():
    pytest.importorskip("pydantic")
    with pytest.raises(TypeError):
        param.Model.from_pydantic(dict)


# JSON schema

def test_from_json_schema_basic_types():
    schema = {
        "title": "Settings",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "default": 3},
            "ratio": {"type": "number", "default": 0.5},
            "enabled": {"type": "boolean", "default": True},
            "extra": {"type": "object"},
            "anything": {},
        },
        "required": ["name"],
    }
    P = param.Model.from_json_schema(schema)

    assert P.__name__ == "Settings"
    assert isinstance(P.param.name, param.String)
    assert isinstance(P.param.count, param.Integer)
    assert isinstance(P.param.ratio, param.Number)
    assert isinstance(P.param.enabled, param.Boolean)
    assert isinstance(P.param.extra, param.Dict)
    assert type(P.param.anything) is param.Parameter
    p = P(name="x")
    assert (p.count, p.ratio, p.enabled) == (3, 0.5, True)


def test_from_json_schema_required_and_optional():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        "required": ["a"],
    }
    P = param.Model.from_json_schema(schema, name="P")

    assert P._model_required == {"a"}
    assert P.param.b.allow_None
    assert P(a="x").b is None


def test_from_json_schema_keeps_property_schema_in_metadata():
    prop = {"type": "string", "format": "password", "title": "Secret"}
    P = param.Model.from_json_schema({"type": "object", "properties": {"secret": prop}})

    assert P.param.secret.metadata["json_schema"] == prop
    assert P.param.secret.label == "Secret"


def test_from_json_schema_numeric_constraints():
    schema = {"type": "object", "properties": {
        "a": {"type": "integer", "minimum": 0, "maximum": 10, "default": 1},
        "b": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1, "multipleOf": 0.1, "default": 0.5},
    }}
    P = param.Model.from_json_schema(schema)

    assert P.param.a.bounds == (0, 10)
    assert P.param.a.inclusive_bounds == (True, True)
    assert P.param.b.bounds == (0, 1)
    assert P.param.b.inclusive_bounds == (False, False)
    assert P.param.b.step == 0.1
    with pytest.raises(ValueError):
        P(a=11)


def test_from_json_schema_string_pattern():
    P = param.Model.from_json_schema({"type": "object", "properties": {
        "zip": {"type": "string", "pattern": r"^\d{5}$", "default": "10115"},
    }})
    assert P.param.zip.regex == r"^\d{5}$"
    with pytest.raises(ValueError):
        P(zip="abc")


def test_from_json_schema_dates():
    schema = {"type": "object", "properties": {
        "day": {"type": "string", "format": "date", "default": "2024-05-01",
                "formatMinimum": "2024-01-01", "formatMaximum": "2024-12-31"},
        "when": {"type": "string", "format": "date-time", "default": "2024-05-01T12:00:00Z"},
    }}
    P = param.Model.from_json_schema(schema)

    assert isinstance(P.param.day, param.CalendarDate)
    assert P.param.day.default == dt.date(2024, 5, 1)
    assert P.param.day.bounds == (dt.date(2024, 1, 1), dt.date(2024, 12, 31))
    assert isinstance(P.param.when, param.Date)
    assert P.param.when.default == dt.datetime(2024, 5, 1, 12, tzinfo=dt.timezone.utc)


def test_from_json_schema_enum_and_const_options():
    schema = {"type": "object", "properties": {
        "mode": {"type": "string", "enum": ["fast", "slow"], "default": "fast"},
        "color": {"type": "string", "enum": ["r", "g"], "enumNames": ["Red", "Green"], "default": "r"},
        "plan": {"type": "string", "oneOf": [{"const": "free", "title": "Free"}, {"const": "pro", "title": "Pro"}],
                 "default": "free"},
    }}
    P = param.Model.from_json_schema(schema)

    assert P.param.mode.objects == ["fast", "slow"]
    assert P.param.color.names == {"Red": "r", "Green": "g"}
    assert P.param.plan.names == {"Free": "free", "Pro": "pro"}
    with pytest.raises(ValueError):
        P(mode="medium")


def test_from_json_schema_nullable_unions():
    schema = {"type": "object", "properties": {
        "a": {"anyOf": [{"type": "integer"}, {"type": "null"}], "default": None},
        "b": {"type": ["string", "null"], "default": "x"},
        "c": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 1},
    }}
    P = param.Model.from_json_schema(schema)

    assert isinstance(P.param.a, param.Integer) and P.param.a.allow_None
    assert isinstance(P.param.b, param.String) and P.param.b.allow_None
    assert isinstance(P.param.c, param.ClassSelector)
    assert set(P.param.c.class_) == {int, str}


def test_from_json_schema_arrays():
    schema = {"type": "object", "properties": {
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 3, "default": []},
        "choices": {"type": "array", "items": {"enum": ["a", "b", "c"]}, "default": []},
        "pair": {"type": "array", "prefixItems": [{"type": "integer"}, {"type": "string"}], "default": [1, "a"]},
    }}
    P = param.Model.from_json_schema(schema)

    assert isinstance(P.param.tags, param.List)
    assert P.param.tags.item_type is str
    assert P.param.tags.bounds == (0, 3)
    assert isinstance(P.param.choices, param.ListSelector)
    assert P.param.choices.objects == ["a", "b", "c"]
    assert isinstance(P.param.pair, param.Tuple)
    assert P.param.pair.length == 2


def test_from_json_schema_refs_and_nested_objects():
    schema = {
        "type": "object",
        "$defs": {"Address": {"type": "object", "properties": {
            "city": {"type": "string", "default": "Berlin"},
        }}},
        "properties": {
            "home": {"$ref": "#/$defs/Address"},
            "work": {"allOf": [{"$ref": "#/$defs/Address"}], "description": "Office"},
            "inline": {"type": "object", "properties": {"x": {"type": "integer", "default": 1}}},
        },
        "required": ["home"],
    }
    P = param.Model.from_json_schema(schema)

    Address = P.param.home.class_
    assert issubclass(Address, param.Model)
    assert Address.__name__ == "Address"
    assert P.param.work.class_ is Address
    assert P.param.work.doc == "Office"
    assert P.param.inline.class_.__name__ == "Inline"
    assert P().home.city == "Berlin"
    assert P().work is None


def test_from_json_schema_recursive_ref_does_not_loop():
    schema = {
        "type": "object",
        "$defs": {"Node": {"type": "object", "properties": {
            "value": {"type": "integer", "default": 0},
            "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}, "default": []},
        }}},
        "properties": {"root": {"$ref": "#/$defs/Node"}},
    }
    P = param.Model.from_json_schema(schema)
    assert issubclass(P.param.root.class_, param.Model)


def test_from_json_schema_param_export_round_trip():
    class Orig(param.Parameterized):
        n = param.Integer(5, bounds=(0, 10))
        x = param.Number(0.5, bounds=(0, 1), inclusive_bounds=(False, True))
        s = param.Selector(objects=["a", "b"])
        r = param.Range((1, 2), bounds=(0, 10))
        nt = param.NumericTuple((1, 2, 3), length=3)
        lst = param.List([1], item_type=int)
        when = param.Date(dt.datetime(2024, 1, 1))
        day = param.CalendarDate(dt.date(2024, 1, 1))
        flag = param.Boolean(False)

    schema = {"type": "object", "properties": Orig.param.schema()}
    P = param.Model.from_json_schema(schema, name="Orig")

    for pname in ("n", "x", "s", "r", "nt", "lst", "when", "day", "flag"):
        assert type(P.param[pname]) is type(Orig.param[pname]), pname
    assert P.param.n.bounds == (0, 10)
    assert P.param.x.inclusive_bounds == (False, True)
    assert P.param.s.objects == ["a", "b"]
    assert P.param.r.bounds == (0, 10)
    assert P.param.nt.length == 3
    assert P.param.lst.item_type is int


def test_from_json_schema_matches_from_pydantic(models):
    _, _, Query = models
    from_model = param.Model.from_pydantic(Query)
    from_schema = param.Model.from_json_schema(Query.model_json_schema())

    for pname in ("sql", "limit", "ratio", "mode", "since", "at", "tags", "address", "others", "token"):
        assert type(from_schema.param[pname]) is type(from_model.param[pname]), pname
    assert from_schema.param.limit.bounds == from_model.param.limit.bounds
    assert from_schema._model_required == from_model._model_required


def test_from_json_schema_rejects_invalid_input():
    with pytest.raises(TypeError):
        param.Model.from_json_schema("not a schema")
    with pytest.raises(ValueError, match="object"):
        param.Model.from_json_schema({"type": "string"})
    with pytest.raises(ValueError, match="underscore"):
        param.Model.from_json_schema({"type": "object", "properties": {"_x": {"type": "string"}}})
