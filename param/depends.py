import weakref

from collections import defaultdict
from functools import wraps

from .parameterized import (
    Parameter, Parameterized, ParameterizedMetaclass
)
from ._utils import accept_arguments, iscoroutinefunction

# Hooks to apply to depends and bind arguments to turn them into valid parameters

_reactive_display_objs = weakref.WeakSet()
_display_accessors = {}
_dependency_transforms = []

def register_display_accessor(name, accessor, force=False):
    if name in _display_accessors and not force:
        raise KeyError(
            'Display accessor {name!r} already registered. Override it '
            'by setting force=True or unregister the existing accessor first.')
    _display_accessors[name] = accessor
    for fn in _reactive_display_objs:
        setattr(fn, name, accessor(fn))

def unregister_display_accessor(name):
    if name not in _display_accessors:
        raise KeyError('No such display accessor: {name!r}')
    del _display_accessors[name]
    for fn in _reactive_display_objs:
        delattr(fn, name)

def register_depends_transform(transform):
    """
    Appends a transform to extract potential parameter dependencies
    from an object.

    Arguments
    ---------
    transform: Callable[Any, Any]
    """
    return _dependency_transforms.append(transform)

def transform_dependency(arg):
    """
    Transforms arguments for depends and bind functions applying any
    registered dependency transforms. This is useful for adding
    handling for depending on objects that are not simple Parameters or
    functions with dependency definitions.
    """
    for transform in _dependency_transforms:
        if isinstance(arg, Parameter) or hasattr(arg, '_dinfo'):
            break
        arg = transform(arg)
    return arg

def eval_function_with_deps(function):
    """Evaluates a function after resolving its dependencies.

    Calls and returns a function after resolving any dependencies
    stored on the _dinfo attribute and passing the resolved values
    as arguments.
    """
    args, kwargs = (), {}
    if hasattr(function, '_dinfo'):
        arg_deps = function._dinfo['dependencies']
        kw_deps = function._dinfo.get('kw', {})
        if kw_deps or any(isinstance(d, Parameter) for d in arg_deps):
            args = (getattr(dep.owner, dep.name) for dep in arg_deps)
            kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw_deps.items()}
    return function(*args, **kwargs)

def resolve_value(value):
    """
    Resolves the current value of a dynamic reference.
    """
    if isinstance(value, (list, tuple)):
        return type(value)(resolve_value(v) for v in value)
    elif isinstance(value, dict):
        return type(value)((k, resolve_value(v)) for k, v in value)
    elif isinstance(value, slice):
        return slice(
            resolve_value(value.start),
            resolve_value(value.stop),
            resolve_value(value.step)
        )
    value = transform_dependency(value)
    if hasattr(value, '_dinfo'):
        value = eval_function_with_deps(value)
    elif isinstance(value, Parameter):
        value = getattr(value.owner, value.name)
    return value

def resolve_ref(reference):
    """
    Resolves all parameters a dynamic reference depends on.
    """
    if isinstance(reference, (list, tuple, set)):
        return [r for v in reference for r in resolve_ref(v)]
    elif isinstance(reference, dict):
        return [r for v in reference.values() for r in resolve_ref(v)]
    elif isinstance(reference, slice):
        return [r for v in (reference.start, reference.stop, reference.step) for r in resolve_ref(v)]
    reference = transform_dependency(reference)
    if hasattr(reference, '_dinfo'):
        dinfo = getattr(reference, '_dinfo', {})
        args = list(dinfo.get('dependencies', []))
        kwargs = list(dinfo.get('kw', {}).values())
        refs = []
        for arg in (args + kwargs):
            refs.extend(resolve_ref(arg))
        return refs
    elif isinstance(reference, Parameter):
        return [reference]
    return []

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
        tuple(transform_dependency(arg) for arg in dependencies),
        {key: transform_dependency(arg) for key, arg in kw.items()}
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
