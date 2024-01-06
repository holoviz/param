"""
Module that implements asyncio.coroutine function wrappers to be used
by param internal callbacks. These are defined in a separate file due
to py2 incompatibility with both `async/await` and `yield from` syntax.
"""

# import asyncio

# def generate_depends(func):
#     @asyncio.coroutine
#     def _depends(*args, **kw):
#         yield from func(*args, **kw) # noqa: E999
#     return _depends



# def generate_callback(func, dependencies, kw):
#     @asyncio.coroutine
#     def cb(*events):
#         args = (getattr(dep.owner, dep.name) for dep in dependencies)
#         dep_kwargs = {n: getattr(dep.owner, dep.name) for n, dep in kw.items()}
#         yield from func(*args, **dep_kwargs) # noqa: E999
#     return cb
