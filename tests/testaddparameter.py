"""
At the time of adding these tests, the implementation of add_parameter
had not changed since it was committed (f10b324 in July 2012). The tests
are checking that (not fully understood) implementation:

    @classmethod
    def _add_parameter(cls, param_name,param_obj):
        '''
        Add a new Parameter object into this object's class.
        Supposed to result in a Parameter equivalent to one declared
        in the class's source code.
        '''
        # CEBALERT: can't we just do
        # setattr(cls,param_name,param_obj)?  The metaclass's
        # __setattr__ is actually written to handle that.  (Would also
        # need to do something about the params() cache.  That cache
        # is a pain, but it definitely improved the startup time; it
        # would be worthwhile making sure no method except for one
        # "add_param()" method has to deal with it (plus any future
        # remove_param() method.)
        type.__setattr__(cls,param_name,param_obj)
        cls.__metaclass__._initialize_parameter(cls,param_name,param_obj)
        # delete cached params()
        try:
            delattr(cls,'_%s__params'%cls.__name__)
        except AttributeError:
            pass
"""
import param
import pytest


def test_add_parameter_class():

    class P(param.Parameterized):
        x = param.Parameter()

    P.param.add_parameter('y', param.Parameter())

    assert 'y' in P.param
    # Check the name is set
    assert P.param.y.name == 'y'
    assert P.param.y._internal_name == '_y_param_value'


def test_add_parameter_instance():

    class P(param.Parameterized):
        x = param.Parameter()

    p = P()
    p.param.add_parameter('y', param.Parameter())

    assert 'y' in p.param
    assert p.param.y.name == 'y'
    assert p.param.y._internal_name == '_y_param_value'


def test_add_parameter_class_validation():

    class P(param.Parameterized):
        x = param.Parameter()

    P.param.add_parameter('y', param.Number())

    with pytest.raises(ValueError, match=r"Parameter 'y' only takes numeric values, not type <class 'str'>."):
        P.y = 'test'


def test_add_parameter_instance_validation():

    class P(param.Parameterized):
        x = param.Parameter()

    P.param.add_parameter('y', param.Number())

    p = P()

    with pytest.raises(ValueError, match=r"Parameter 'y' only takes numeric values, not type <class 'str'>."):
        p.y = 'test'


def test_add_parameter_cache_cleared():
    # Not sure why it's supposed to delete the Parameters cache, test it anyway

    class P(param.Parameterized):
        x = param.Parameter()

    # Generate the cache
    P.param.objects(instance=True)

    assert 'x' in P._param__private.params

    P.param.add_parameter('y', param.Parameter())

    # Check the cache has been removed (not sure why)
    assert not P._param__private.params


def test_add_parameter_subclass():

    class A(param.Parameterized):
        x = param.Parameter()

    class B(A):
        pass

    B.param.add_parameter('y', param.Parameter())

    assert 'y' not in A.param
    assert 'y' in B.param


def test_add_parameter_override():

    class P(param.Parameterized):
        x = param.Parameter(default=1)

    origin = P.param.x
    new = param.Parameter(default=2)

    P.param.add_parameter('x', new)

    assert P.param.x.default == 2
    assert P.param.x is new
    assert P.param.x is not origin


def test_add_parameter_inheritance():

    class A(param.Parameterized):
        x = param.Parameter(default=1)

    class B(A):
        pass

    B.param.add_parameter('x', param.Parameter(doc='some doc'))

    assert B.param.x.default == 1
    assert B.param.x.doc == 'some doc'


def test_add_parameter_watch_class():
    class P(param.Parameterized):
        x = param.Parameter()

    P.param.add_parameter('y', param.Parameter())

    acc = []
    P.param.watch(lambda e: acc.append(e), 'y')
    P.y = 1
    assert len(acc) == 1


def test_add_parameter_watch_instance():
    class P(param.Parameterized):
        x = param.Parameter()

    P.param.add_parameter('y', param.Parameter())

    p = P()
    acc = []
    p.param.watch(lambda e: acc.append(e), 'y')
    p.y = 1
    assert len(acc) == 1
