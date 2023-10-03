from collections import defaultdict
from functools import wraps

from .parameterized import (
    Parameter, Parameterized, ParameterizedMetaclass, transform_reference,
)
from ._utils import accept_arguments, iscoroutinefunction


@accept_arguments
def depends(func, *dependencies, watch=False, on_init=False, **kw):
    """Annotates a function or Parameterized method to express its dependencies.

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

    if iscoroutinefunction(func):
        @wraps(func)
        async def _depends(*args, **kw):
            return await func(*args, **kw)
    else:
        @wraps(func)
        def _depends(*args, **kw):
            return func(*args, **kw)

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

    if not string_specs and watch: # string_specs case handled elsewhere (later), in Parameterized.__init__
        if iscoroutinefunction(func):
            async def cb(*events):
                args = (getattr(dep.owner, dep.name) for dep in dependencies)
                dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw.items()}
                await func(*args, **dep_kwargs)
        else:
            def cb(*events):
                args = (getattr(dep.owner, dep.name) for dep in dependencies)
                dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw.items()}
                return func(*args, **dep_kwargs)

        grouped = defaultdict(list)
        for dep in deps:
            grouped[id(dep.owner)].append(dep)
        for group in grouped.values():
            group[0].owner.param.watch(cb, [dep.name for dep in group])

    _dinfo = getattr(func, '_dinfo', {})
    _dinfo.update({'dependencies': dependencies,
                   'kw': kw, 'watch': watch, 'on_init': on_init})

    _depends._dinfo = _dinfo

    return _depends
