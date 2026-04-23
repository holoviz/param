import typing as t

import param
import pytest


def test_literal_annotation_infers_selector():
    class P(param.TypedParameterized):
        mode: t.Literal["read", "write"]

    assert isinstance(P.param.mode, param.Selector)
    assert P.param.mode.objects == ["read", "write"]
    assert P.param.mode.default == "read"

    p = P()
    assert p.mode == "read"
    p.mode = "write"

    with pytest.raises(ValueError):
        p.mode = "delete"


def test_literal_annotation_supports_explicit_default_value():
    class P(param.TypedParameterized):
        mode: t.Literal["read", "write"] = "write"

    assert isinstance(P.param.mode, param.Selector)
    assert P.param.mode.objects == ["read", "write"]
    assert P.param.mode.default == "write"
    assert P().mode == "write"


def test_literal_field_specification_supports_default_and_optional():
    class P(param.TypedParameterized):
        mode: t.Literal["light", "dark"] = param.Field(default="dark")
        optional_mode: t.Literal["auto", "manual"] | None = param.Field(default=None)

    assert isinstance(P.param.mode, param.Selector)
    assert P.param.mode.objects == ["light", "dark"]
    assert P.param.mode.default == "dark"

    assert isinstance(P.param.optional_mode, param.Selector)
    assert P.param.optional_mode.objects == ["auto", "manual"]
    assert P.param.optional_mode.allow_None is True
    assert P.param.optional_mode.default is None
    assert P().optional_mode is None


def test_classvar_annotation_is_not_parameterized():
    class P(param.TypedParameterized):
        shared: t.ClassVar[int] = 7
        value: int = 1

    assert "shared" not in P.param
    assert "value" in P.param
    assert P.shared == 7
    assert P().value == 1


def test_field_parameter_allows_overriding_inferred_parameter_class():
    class P(param.TypedParameterized):
        value: int = param.Field(default=1.5, parameter=param.Number, bounds=(0, None))

    assert isinstance(P.param.value, param.Number)

    p = P()
    assert p.value == 1.5
    p.value = 2.25
    with pytest.raises(ValueError):
        p.value = "not-a-number"


def test_field_parameter_override_can_replace_literal_selector_behavior():
    class P(param.TypedParameterized):
        mode: t.Literal["light", "dark"] = param.Field(
            default="sepia", parameter=param.String
        )

    assert isinstance(P.param.mode, param.String)
    p = P()
    assert p.mode == "sepia"
    p.mode = "custom-theme"
