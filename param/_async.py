"""
Module that implements async/def function wrappers to be used
by param internal callbacks. These are defined in a separate file due
to py2 incompatibility with both `async/await` and `yield from` syntax.
"""

def generate_depends(func):
    async def _depends(*args, **kw):
        await func(*args, **kw)
    return _depends

def generate_caller(function, what='value', changed=None, callback=None, skip_event=None):
    async def caller(*events):
        if callback:
            callback(*events)
        if not skip_event or not skip_event(*events, what=what, changed=changed):
            await function()
    return caller

def generate_callback(func, dependencies, kw):
    async def cb(*events):
        args = (getattr(dep.owner, dep.name) for dep in dependencies)
        dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw.items()}
        await func(*args, **dep_kwargs)
    return cb
