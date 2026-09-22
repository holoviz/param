import sys
import typing as t

import param
import pytest


def test_literal_annotation_infers_selector():
    class P(param.Model):
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
    class P(param.Model):
        mode: t.Literal["read", "write"] = "write"

    assert isinstance(P.param.mode, param.Selector)
    assert P.param.mode.objects == ["read", "write"]
    assert P.param.mode.default == "write"
    assert P().mode == "write"


def test_literal_field_specification_supports_default_and_optional():
    class P(param.Model):
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
    class P(param.Model):
        shared: t.ClassVar[int] = 7
        value: int = 1

    assert "shared" not in P.param
    assert "value" in P.param
    assert P.shared == 7
    assert P().value == 1


def test_bare_classvar_annotation_is_not_parameterized():
    # `t.get_origin(t.ClassVar)` is None -- unlike the subscripted form
    # `ClassVar[int]` -- so the bare form needs its own identity check.
    class P(param.Model):
        shared: t.ClassVar = 7
        value: int = 1

    assert "shared" not in P.param
    assert "value" in P.param
    assert P.shared == 7
    assert P().value == 1


def test_annotated_metadata_sets_doc_and_parameter_attributes():
    class P(param.Model):
        title: t.Annotated[str, {"doc": "Title text", "constant": True}] = "hello"

    assert isinstance(P.param.title, param.String)
    assert P.param.title.doc == "Title text"
    assert P.param.title.constant is True
    assert P().title == "hello"


def test_annotated_metadata_supports_inferred_parameter_kwargs():
    class P(param.Model):
        value: t.Annotated[int, {"bounds": (0, 10)}] = 4

    assert isinstance(P.param.value, param.Integer)
    assert P.param.value.bounds == (0, 10)
    assert P().value == 4


def test_annotated_and_optional_unwrap_regardless_of_nesting_order():
    # `Annotated` wrapping `Optional` and `Optional` wrapping `Annotated`
    # are equally idiomatic and must infer the same Parameter, metadata,
    # and allow_None.
    class AnnotatedThenOptional(param.Model):
        value: t.Annotated[t.Optional[int], {"bounds": (0, 10)}] = None

    class OptionalThenAnnotated(param.Model):
        value: t.Optional[t.Annotated[int, {"bounds": (0, 10)}]] = None

    for cls in (AnnotatedThenOptional, OptionalThenAnnotated):
        assert isinstance(cls.param.value, param.Integer)
        assert cls.param.value.allow_None is True
        assert cls.param.value.bounds == (0, 10)
        assert cls().value is None


def test_field_parameter_allows_overriding_inferred_parameter_class():
    class P(param.Model):
        value: int = param.Field(default=1.5, parameter=param.Number, bounds=(0, None))

    assert isinstance(P.param.value, param.Number)

    p = P()
    assert p.value == 1.5
    p.value = 2.25
    with pytest.raises(ValueError):
        p.value = "not-a-number"


def test_field_parameter_override_can_replace_literal_selector_behavior():
    class P(param.Model):
        mode: t.Literal["light", "dark"] = param.Field(
            default="sepia", parameter=param.String
        )

    assert isinstance(P.param.mode, param.String)
    p = P()
    assert p.mode == "sepia"
    p.mode = "custom-theme"


def test_field_parameter_instance_override_preserves_its_own_default():
    # Reusing a fully-configured `Parameter` instance via `parameter=`
    # should honor that instance's own default without requiring callers
    # to redundantly repeat it via `Field(default=...)`.
    shared = param.String(default="reused", regex=r"^r")

    class P(param.Model):
        value: str = param.Field(parameter=shared)

    assert P.param.value.default == "reused"
    assert P().value == "reused"


def test_field_parameter_instance_override_is_not_treated_as_required():
    shared = param.String(default="reused")

    class P(param.Model):
        value: str = param.Field(parameter=shared)

    P()  # should not raise


def test_annotation_only_field_is_required():
    class P(param.Model):
        name: str
        count: int = 0

    with pytest.raises(TypeError, match="name"):
        P()

    p = P(name="bob")
    assert p.name == "bob"
    assert p.count == 0


def test_field_without_default_is_required():
    class P(param.Model):
        value: int = param.Field(bounds=(0, None))

    with pytest.raises(TypeError, match="value"):
        P()

    assert P(value=1).value == 1


def test_multiple_missing_required_fields_are_all_reported():
    class P(param.Model):
        a: str
        b: int
        c: float = 1.0

    with pytest.raises(TypeError, match="'a', 'b'"):
        P()

    assert P(a="x", b=1).a == "x"


def test_required_fields_are_inherited_by_subclasses():
    class Base(param.Model):
        name: str

    class Sub(Base):
        extra: int

    with pytest.raises(TypeError, match="extra"):
        Sub(name="ok")

    with pytest.raises(TypeError, match="name"):
        Sub(extra=1)

    s = Sub(name="ok", extra=1)
    assert s.name == "ok"
    assert s.extra == 1


def test_subclass_can_satisfy_inherited_required_field_with_a_default():
    class Base(param.Model):
        name: str

    class Sub(Base):
        name: str = "default-name"

    assert Sub().name == "default-name"


def test_literal_annotation_remains_not_required():
    # Selector infers a usable default (the first `objects` entry) from the
    # annotation alone, so it should never be treated as a required field.
    class P(param.Model):
        mode: t.Literal["read", "write"]

    P()  # should not raise


@pytest.mark.parametrize(
    "annotation,expected_type,extra_check",
    [
        (list, param.List, None),
        (dict, param.Dict, None),
        (tuple, param.Tuple, None),
        (set, param.ClassSelector, lambda p: p.class_ is set),
    ],
)
def test_bare_container_annotations_infer_typed_parameters(annotation, expected_type, extra_check):
    class P(param.Model):
        value: annotation = param.Field(default_factory=annotation)

    assert isinstance(P.param.value, expected_type)
    if extra_check is not None:
        assert extra_check(P.param.value)


def test_parameter_override_preserves_optional_derived_allow_none():
    class P(param.Model):
        value: int | None = param.Field(default=1, parameter=param.Number)

    assert isinstance(P.param.value, param.Number)
    assert P.param.value.allow_None is True

    p = P()
    p.value = None
    assert p.value is None


def test_parameter_override_explicit_allow_none_takes_precedence():
    class P(param.Model):
        value: int | None = param.Field(
            default=1, parameter=param.Number, allow_None=False
        )

    assert P.param.value.allow_None is False


def test_broken_string_annotation_raises_instead_of_silently_dropping_validation():
    # Exercises the plain-string eval() path in ModelMetaclass.__new__
    # directly (via an explicit string annotation), independent of Python
    # version or `from __future__ import annotations`. A typo'd/undefined
    # forward reference must raise rather than silently falling through to
    # an unvalidated bare `Parameter`.
    with pytest.raises(NameError):
        class P(param.Model):
            value: "DoesNotExist"  # noqa: F821


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="__annotate_func__ deferred evaluation is Python 3.14+ (PEP 649)",
)
def test_broken_forward_reference_raises_instead_of_silently_dropping_fields():
    with pytest.raises(NameError):
        class P(param.Model):
            value: DoesNotExist  # noqa: F821
