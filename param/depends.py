import inspect

from collections import defaultdict
from functools import wraps

from .parameterized import (
    Parameter, Parameterized, ParameterizedMetaclass
)
from ._utils import accept_arguments, iscoroutinefunction

# Hooks to apply to depends and bind arguments to turn them into valid parameters

_dependency_transforms = []

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
    handling for depending on object that are not simple Parameters or
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
    Resolves the value current value of a dynamic reference.
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
    if isinstance(reference, (list, tuple)):
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
        return args + kwargs
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
        Wether to invoke the function/method when the dependency is updated,
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
                             'instance not %s.' % owner)

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

def bind(function, *args, watch=False, **kwargs):
    """
    Given a function, returns a wrapper function that binds the values
    of some or all arguments to Parameter values and expresses Param
    dependencies on those values, so that the function can be invoked
    whenever the underlying values change and the output will reflect
    those updated values.

    As for functools.partial, arguments can also be bound to constants,
    which allows all of the arguments to be bound, leaving a simple
    callable object.

    Arguments
    ---------
    function: callable
        The function to bind constant or dynamic args and kwargs to.
    args: object, param.Parameter
        Positional arguments to bind to the function.
    watch: boolean
        Whether to evaluate the function automatically whenever one of
        the bound parameters changes.
    kwargs: object, param.Parameter
        Keyword arguments to bind to the function.

    Returns
    -------
    Returns a new function with the args and kwargs bound to it and
    annotated with all dependencies.
    """
    from .reactive import reactive

    args, kwargs = (
        tuple(transform_dependency(arg) for arg in args),
        {key: transform_dependency(arg) for key, arg in kwargs.items()}
    )
    dependencies = {}

    # If the wrapped function has a dependency add it
    fn_dep = transform_dependency(function)
    if isinstance(fn_dep, Parameter) or hasattr(fn_dep, '_dinfo'):
        dependencies['__fn'] = fn_dep

    # Extract dependencies from args and kwargs
    for i, p in enumerate(args):
        if hasattr(p, '_dinfo'):
            for j, arg in enumerate(p._dinfo['dependencies']):
                dependencies[f'__arg{i}_arg{j}'] = arg
            for kw, kwarg in p._dinfo['kw'].items():
                dependencies[f'__arg{i}_arg_{kw}'] = kwarg
        elif isinstance(p, Parameter):
            dependencies[f'__arg{i}'] = p
    for kw, v in kwargs.items():
        if hasattr(v, '_dinfo'):
            for j, arg in enumerate(v._dinfo['dependencies']):
                dependencies[f'__kwarg_{kw}_arg{j}'] = arg
            for pkw, kwarg in v._dinfo['kw'].items():
                dependencies[f'__kwarg_{kw}_{pkw}'] = kwarg
        elif isinstance(v, Parameter):
            dependencies[kw] = v

    def combine_arguments(wargs, wkwargs, asynchronous=False):
        combined_args = []
        for arg in args:
            if hasattr(arg, '_dinfo'):
                arg = eval_function_with_deps(arg)
            elif isinstance(arg, Parameter):
                arg = getattr(arg.owner, arg.name)
            combined_args.append(arg)
        combined_args += list(wargs)

        combined_kwargs = {}
        for kw, arg in kwargs.items():
            if hasattr(arg, '_dinfo'):
                arg = eval_function_with_deps(arg)
            elif isinstance(arg, Parameter):
                arg = getattr(arg.owner, arg.name)
            combined_kwargs[kw] = arg
        for kw, arg in wkwargs.items():
            if asynchronous:
                if kw.startswith('__arg'):
                    combined_args[int(kw[5:])] = arg
                elif kw.startswith('__kwarg'):
                    combined_kwargs[kw[8:]] = arg
                continue
            elif kw.startswith('__arg') or kw.startswith('__kwarg') or kw.startswith('__fn'):
                continue
            combined_kwargs[kw] = arg
        return combined_args, combined_kwargs

    def eval_fn():
        if callable(function):
            fn = function
        else:
            p = transform_dependency(function)
            if isinstance(p, Parameter):
                fn = getattr(p.owner, p.name)
            else:
                fn = eval_function_with_deps(p)
        return fn

    if inspect.isasyncgenfunction(function):
        async def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            evaled = eval_fn()(*combined_args, **combined_kwargs)
            async for val in evaled:
                yield val
        wrapper_fn = depends(**dependencies, watch=watch)(wrapped)
        wrapped._dinfo = wrapper_fn._dinfo
    elif iscoroutinefunction(function):
        @depends(**dependencies, watch=watch)
        async def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(
                wargs, wkwargs, asynchronous=True
            )
            evaled = eval_fn()(*combined_args, **combined_kwargs)
            return await evaled
    else:
        @depends(**dependencies, watch=watch)
        def wrapped(*wargs, **wkwargs):
            combined_args, combined_kwargs = combine_arguments(wargs, wkwargs)

            return eval_fn()(*combined_args, **combined_kwargs)
    wrapped.__bound_function__ = function
    wrapped.reactive = lambda: reactive(wrapped)
    return wrapped
