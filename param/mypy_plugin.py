"""Mypy plugin for param.

Works around mypy issue #9758: metaclass __setattr__ is not consulted
for class-level assignment to descriptor attributes. Without this plugin,
``MyClass.flag = True`` on a Boolean parameter raises:

    Incompatible types in assignment
    (expression has type "bool", variable has type "Boolean[bool]")

The fix: intercept class-attribute access via get_class_attribute_hook and,
when it's an lvalue, return the Parameter's value type (the first type arg
of Parameter[_T]) instead of the raw descriptor type.

Usage: add ``plugins = ["param.mypy_plugin"]`` to your mypy configuration.
"""

from __future__ import annotations

import typing as t

from mypy.nodes import TypeInfo, Var
from mypy.plugin import AttributeContext, Plugin
from mypy.types import AnyType, Instance, Type, TypeOfAny, get_proper_type


def _is_parameter_type(typ: Type) -> bool:
    proper = get_proper_type(typ)
    if not isinstance(proper, Instance):
        return False
    return any(
        base.fullname == "param.parameterized.Parameter"
        for base in proper.type.mro
    )


def _is_parameterized_class(info: TypeInfo) -> bool:
    return any(
        base.fullname == "param.parameterized.Parameterized"
        for base in info.mro
    )


def _find_attr_in_mro(info: TypeInfo, name: str) -> Var | None:
    for base in info.mro:
        sym = base.names.get(name)
        if sym is not None and isinstance(sym.node, Var):
            return sym.node
    return None


def _class_attribute_hook(ctx: AttributeContext) -> Type:
    if not ctx.is_lvalue:
        return ctx.default_attr_type

    default_type = get_proper_type(ctx.default_attr_type)
    if not isinstance(default_type, Instance):
        return ctx.default_attr_type

    if not _is_parameter_type(default_type):
        return ctx.default_attr_type

    if default_type.args:
        return default_type.args[0]

    return AnyType(TypeOfAny.special_form)


class _ParamPlugin(Plugin):
    def get_class_attribute_hook(
        self, fullname: str
    ) -> t.Callable[[AttributeContext], Type] | None:
        parts = fullname.rsplit(".", 1)
        if len(parts) != 2:
            return None
        class_fullname, attr_name = parts

        sym = self.lookup_fully_qualified(class_fullname)
        if sym is None or not isinstance(sym.node, TypeInfo):
            return None

        info = sym.node
        if not _is_parameterized_class(info):
            return None

        var = _find_attr_in_mro(info, attr_name)
        if var is None or var.type is None:
            return None
        if not _is_parameter_type(var.type):
            return None

        return _class_attribute_hook


def plugin(version: str) -> type[Plugin]:
    return _ParamPlugin
