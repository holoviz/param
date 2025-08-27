from __future__ import annotations

import inspect
import typing as t

from collections.abc import AsyncGenerator, Generator
from collections import defaultdict
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, TypeVar, Callable, ParamSpec, Protocol, TypedDict, overload

from .parameterized import (
    Parameter, Parameterized, ParameterizedMetaclass, transform_reference,
)
from ._utils import accept_arguments, iscoroutinefunction

if TYPE_CHECKING:
    Y = TypeVar("Y")
    S = TypeVar("S")
    T = TypeVar("T")

P = ParamSpec("P")
R = TypeVar("R", covariant=True)

Dependency = Parameter | str

class DependencyInfo(TypedDict):
    dependencies: tuple[Dependency, ...]
    kw: dict[str, Dependency]
    watch: bool
    on_init: bool

class DependsFunc(Protocol[P, R]):
    _dinfo: DependencyInfo
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


@overload
def depends(
    *dependencies: str, watch: bool = ..., on_init: bool = ...
) -> Callable[[Callable[P, R]], DependsFunc[P, R]]:
    ...

@overload
def depends(
    *dependencies: Parameter, watch: bool = ..., on_init: bool = ..., **kw: Parameter
) -> Callable[[Callable[P, R]], DependsFunc[P, R]]:
    ...

@overload
def depends(
    *dependencies: str, watch: bool = ..., on_init: bool = ...
) -> Callable[[Callable[P, Awaitable[R]]], DependsFunc[P, Awaitable[R]]]: ...

@overload
def depends(
    *dependencies: Parameter, watch: bool = ..., on_init: bool = ..., **kw: Parameter
) -> Callable[[Callable[P, Awaitable[R]]], DependsFunc[P, Awaitable[R]]]: ...

@overload
def depends(
    *dependencies: str, watch: bool = ..., on_init: bool = ...
)-> Callable[[Callable[P, Generator[Y, S, T]]], DependsFunc[P, Generator[Y, S, T]]]: ...

@overload
def depends(
    *dependencies: Parameter, watch: bool = ..., on_init: bool = ..., **kw: Parameter
)-> Callable[[Callable[P, AsyncGenerator[Y, S]]], DependsFunc[P, AsyncGenerator[Y, S]]]: ...

@accept_arguments
def depends(
    func: Callable[P, R], /, *dependencies: Dependency, watch: bool = False, on_init: bool = False, **kw: Dependency
) -> DependsFunc[P, R]:
    """
    Annotates a function or Parameterized method to express its dependencies.

    The specified dependencies can be either be Parameter instances or if a
    method is supplied they can be defined as strings referring to Parameters
    of the class, or Parameters of subobjects (Parameterized objects that are
    values of this object's parameters). Dependencies can either be on
    Parameter values, or on other metadata about the Parameter.

    Parameters
    ----------
    watch : bool, optional
        Whether to invoke the function/method when the dependency is updated,
        by default False
    on_init : bool, optional
        Whether to invoke the function/method when the instance is created,
        by default False

    """
    dependencies, kw = (
        tuple(transform_reference(arg) for arg in dependencies),
        {key: transform_reference(arg) for key, arg in kw.items()}
    )

    if inspect.isgeneratorfunction(func):
        @wraps(func)
        def _depends_gen(*args, **kw):
            for val in func(*args, **kw):
                yield val
        _depends = t.cast(Callable[P, R], _depends_gen)
    elif inspect.isasyncgenfunction(func):
        @wraps(func)
        async def _depends_async_gen(*args, **kw):
            async for val in func(*args, **kw):
                yield val
        _depends = t.cast(Callable[P, R], _depends_async_gen)
    elif iscoroutinefunction(func):
        F = t.cast(Callable[P, Awaitable[R]], func)
        @wraps(func)
        async def _depends_coro(*args, **kw):
            return await F(*args, **kw)
        _depends = t.cast(Callable[P, R], _depends_coro)
    else:
        @wraps(func)
        def _depends_sync(*args, **kw):
            return func(*args, **kw)
        _depends = t.cast(Callable[P, R], _depends_sync)

    deps = list(dependencies)+list(kw.values())
    string_specs = False
    for dep in deps:
        if isinstance(dep, str):
            string_specs = True
        elif hasattr(dep, '_dinfo'):
            pass
        elif not isinstance(dep, Parameter):
            raise ValueError('The depends decorator only accepts string '
                             'types referencing a parameter or parameter '
                             'instances, found %s type instead.' %
                             type(dep).__name__)
        elif not (isinstance(dep.owner, Parameterized) or
                  (isinstance(dep.owner, ParameterizedMetaclass))):
            owner = 'None' if dep.owner is None else '%s class' % type(dep.owner).__name__
            raise ValueError('Parameters supplied to the depends decorator, '
                             'must be bound to a Parameterized class or '
                             'instance, not %s.' % owner)

    if (any(isinstance(dep, Parameter) for dep in deps) and
        any(isinstance(dep, str) for dep in deps)):
        raise ValueError('Dependencies must either be defined as strings '
                         'referencing parameters on the class defining '
                         'the decorated method or as parameter instances. '
                         'Mixing of string specs and parameter instances '
                         'is not supported.')
    elif string_specs and kw:
        raise AssertionError('Supplying keywords to the decorated method '
                             'or function is not supported when referencing '
                             'parameters by name.')

    _dinfo = getattr(func, '_dinfo', {})
    _dinfo.update({'dependencies': dependencies,
                   'kw': kw, 'watch': watch, 'on_init': on_init})

    typed_depends = t.cast(DependsFunc[P, R], _depends)
    typed_depends._dinfo = _dinfo  # type: ignore[attr-defined]

    if string_specs or not watch:
         # string_specs case handled elsewhere (later), in Parameterized.__init__
         return typed_depends
    param_args = [dep for dep in dependencies if isinstance(dep, Parameter)]
    param_kwargs = {n: dep for n, dep in kw.items() if isinstance(dep, Parameter)}
    param_deps = list(param_args) + list(param_kwargs.values())
    if inspect.isgeneratorfunction(func):
        def cb_gen(*events):
            args: tuple[Any, ...] = tuple(getattr(dep.owner, dep.name) for dep in param_args if dep.name)
            dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in param_kwargs.items() if dep.name}
            func_gen = t.cast(Callable[P, Generator[Any, Any, Any]], func)
            for val in func_gen(*args, **dep_kwargs):
                yield val
        cb = cb_gen
    elif inspect.isasyncgenfunction(func):
        async def cb_async_gen(*events):
            args: tuple[Any, ...] = tuple(getattr(dep.owner, dep.name) for dep in param_args if dep.name)
            dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in param_kwargs.items() if dep.name}
            func_agen = t.cast(Callable[P, AsyncGenerator[Any, Any]], func)
            async for val in func_agen(*args, **dep_kwargs):
                yield val
        cb = cb_async_gen
    elif iscoroutinefunction(func):
        async def cb_coro(*events):
            args: tuple[Any, ...] = tuple(getattr(dep.owner, dep.name) for dep in param_args if dep.name)
            dep_kwargs: dict[str, Any] = {n: getattr(dep.owner, dep.name) for n, dep in param_kwargs.items() if dep.name}
            func_coro = t.cast(Callable[P, Awaitable[Any]], func)
            await func_coro(*args, **dep_kwargs)
        cb = cb_coro
    else:
        def cb_sync(*events):
            args: tuple[Any, ...] = tuple(getattr(dep.owner, dep.name) for dep in param_args if dep.name)
            dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in param_kwargs.items() if dep.name}
            return func(*args, **dep_kwargs)
        cb = cb_sync

    grouped = defaultdict(list)
    for dep in param_deps:
        grouped[id(dep.owner)].append(dep)
    for group in grouped.values():
        group[0].owner.param.watch(cb, [dep.name for dep in group])

    return typed_depends
