import operator

from param import Callable, Integer, Number, Parameterized, String, bind

def identity(*args, **kwargs):
    return args, kwargs

class Parameters(Parameterized):

    string = String(default="string")

    integer = Integer(default=7)

    number = Number(default=3.14)

    function = Callable()

def test_bind_constant_arg():
    assert bind(identity, 1)() == ((1,), {})

def test_bind_constant_arg_partial():
    assert bind(identity, 1)(2) == ((1, 2), {})

def test_bind_constant_args():
    assert bind(identity, 1, 2)() == ((1, 2), {})

def test_bind_constant_kwarg():
    assert bind(identity, foo=1)() == ((), {'foo': 1})

def test_bind_constant_kwarg_partial():
    assert bind(identity, foo=1)(bar=2) == ((), {'foo': 1, 'bar': 2})

def test_bind_constant_kwargs():
    assert bind(identity, foo=1, bar=2)() == ((), {'foo': 1, 'bar': 2})

def test_bind_constant_args_and_kwargs():
    assert bind(identity, 1, bar=2)() == ((1,), {'bar': 2})

def test_bind_constant_args_and_kwargs_partial():
    assert bind(identity, 1, bar=3)(2, baz=4) == ((1, 2), {'bar': 3, 'baz': 4})

def test_curry_bind_args():
    assert bind(bind(identity, 1), 2)() == ((1, 2), {})

def test_curry_bind_kwargs():
    assert bind(bind(identity, foo=1), bar=2)() == ((), {'foo': 1, 'bar': 2})

def test_bind_class_param_as_arg():
    bound_fn = bind(identity, Parameters.param.string)
    assert bound_fn() == (('string',), {})

def test_bind_class_params_as_args():
    bound_fn = bind(identity, Parameters.param.string, Parameters.param.number)
    assert bound_fn() == (('string', 3.14), {})

def test_bind_class_param_as_kwarg():
    bound_fn = bind(identity, string=Parameters.param.string)
    assert bound_fn() == ((), {'string': 'string'})

def test_bind_class_params_as_kwargs():
    bound_fn = bind(
        identity, string=Parameters.param.string, num=Parameters.param.number
    )
    assert bound_fn() == ((), {'string': 'string', 'num': 3.14})

def test_bind_class_params_as_args_and_kwargs():
    bound_fn = bind(
        identity, Parameters.param.string, num=Parameters.param.number
    )
    assert bound_fn() == (('string',), {'num': 3.14})

def test_bind_instance_param_as_arg():
    P = Parameters()
    bound_fn = bind(identity, P.param.string)
    assert bound_fn() == (('string',), {})
    P.string = 'baz'
    assert bound_fn() == (('baz',), {})

def test_bind_instance_params_as_args():
    P = Parameters()
    bound_fn = bind(identity, P.param.string, P.param.number)
    assert bound_fn() == (('string', 3.14), {})
    P.string = 'baz'
    assert bound_fn() == (('baz', 3.14), {})
    P.number = 6.28
    assert bound_fn() == (('baz', 6.28), {})

def test_bind_instance_params_and_constant_as_args():
    P = Parameters()
    bound_fn = bind(identity, P.param.string, 'foo', P.param.number)
    assert bound_fn() == (('string', 'foo', 3.14), {})
    P.string = 'baz'
    assert bound_fn() == (('baz', 'foo', 3.14), {})
    P.number = 6.28
    assert bound_fn() == (('baz', 'foo', 6.28), {})

def test_bind_instance_param_as_kwarg():
    P = Parameters()
    bound_fn = bind(identity, string=P.param.string)
    assert bound_fn() == ((), {'string': 'string'})
    P.string = 'baz'
    assert bound_fn() == ((), {'string': 'baz'})

def test_bind_instance_params_as_kwargs():
    P = Parameters()
    bound_fn = bind(
        identity, string=P.param.string, num=P.param.number
    )
    assert bound_fn() == ((), {'string': 'string', 'num': 3.14})
    P.string = 'baz'
    assert bound_fn() == ((), {'string': 'baz', 'num': 3.14})
    P.number = 6.28
    assert bound_fn() == ((), {'string': 'baz', 'num': 6.28})

def test_bind_instance_params_and_constant_as_kwargs():
    P = Parameters()
    bound_fn = bind(
        identity, string=P.param.string, num=P.param.number, foo='bar'
    )
    assert bound_fn() == ((), {'string': 'string', 'num': 3.14, 'foo': 'bar'})
    P.string = 'baz'
    assert bound_fn() == ((), {'string': 'baz', 'num': 3.14, 'foo': 'bar'})
    P.number = 6.28
    assert bound_fn() == ((), {'string': 'baz', 'num': 6.28, 'foo': 'bar'})

def test_bind_instance_params_as_args_and_kwargs():
    P = Parameters()
    bound_fn = bind(
        identity, P.param.string, num=P.param.number
    )
    assert bound_fn() == (('string',), {'num': 3.14})
    P.string = 'baz'
    assert bound_fn() == (('baz',), {'num': 3.14})
    P.number = 6.28
    assert bound_fn() == (('baz',), {'num': 6.28})

def test_bind_instance_params_and_constants_as_args_and_kwargs():
    P = Parameters()
    bound_fn = bind(
        identity, 'foo', P.param.string, num=P.param.number, bar=6
    )
    assert bound_fn() == (('foo', 'string',), {'num': 3.14, 'bar': 6})
    P.string = 'baz'
    assert bound_fn() == (('foo', 'baz',), {'num': 3.14, 'bar': 6})
    P.number = 6.28
    assert bound_fn() == (('foo', 'baz',), {'num': 6.28, 'bar': 6})

def test_bind_curry_function_with_deps():
    P = Parameters()
    bound_fn = bind(
        identity, P.param.string, num=P.param.number
    )
    curried_fn = bind(bound_fn, const=3)
    assert curried_fn() == (('string',), {'num': 3.14, 'const': 3})
    P.string = 'baz'
    assert curried_fn() == (('baz',), {'num': 3.14, 'const': 3})
    P.number = 6.28
    assert curried_fn() == (('baz',), {'num': 6.28, 'const': 3})

def test_bind_bound_function_to_arg():
    P = Parameters(integer=1)

    def add1(value):
        return value + 1

    def divide(value):
        return value / 2

    bound_function = bind(divide, bind(add1, P.param.integer))

    assert bound_function() == 1

    P.integer = 3

    assert bound_function() == 2

def test_bind_bound_function_to_kwarg():
    P = Parameters(integer=1)

    def add1(value):
        return value + 1

    def divide(divisor=2, value=0):
        return value / divisor

    bound_function = bind(divide, value=bind(add1, P.param.integer))

    assert bound_function() == 1

    P.integer = 3

    assert bound_function() == 2

def test_bind_dynamic_function():
    P = Parameters(function=operator.add)

    bound_function = bind(P.param.function, 3, 2)

    assert bound_function() == 5

    P.function = operator.sub

    assert bound_function() == 1

def test_bind_generator():
    P = Parameters(integer=7)

    def gen(arg):
        yield arg
        yield arg + 1
        yield arg + 2

    bound_function = bind(gen, P.param.integer)

    for i, v in enumerate(bound_function()):
        assert v == (7 + i)

    P.integer = 3

    for i, v in enumerate(bound_function()):
        assert v == (3 + i)
