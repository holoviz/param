import param
from param.parameterized import DefaultFactory

import pytest


@pytest.fixture
def P():
    class P(param.Parameterized):
        a = param.Parameter(default_factory=lambda: 'from factory')
    yield P


@pytest.fixture
def p(P):
    yield P()


def test_default_factory_slot_default():
    class P(param.Parameterized):
        a = param.Parameter()

    assert P.param.a.default_factory is None
    assert P().param.a.default_factory is None


def test_default_factory_bad_input_type():
    with pytest.raises(
        TypeError,
        match="default_factory must be a callable, not <class 'list'>.",
    ):
        param.Parameter(default_factory=[])


def test_default_factory_no_warning_with_default():
    # Constructing a Parameter with both default and default_factory could emit
    # a warning or raise an error. However, sub classes of Parameter may
    # call super().__init__ with a specific default. So adding a warning/error
    # would push some complexity down the Parameter hierarchy tree. Chose
    # not to.
    param.Parameter(default='a', default_factory=lambda: 'from factory')


def test_default_factory_called_on_instance_creation(p):
    # The factory is called on instance creation.
    assert p.a == "from factory"


def test_default_factory_called_set_after_instantiation(p):
    # Overriding the parameter value is allowed.
    p.a = "new"
    assert p.a == "new"


def test_default_factory_called_constructor_override(P):
    # Setting the parameter value in the constructor is possible too.
    p2 = P(a='overridden')
    assert p2.a == "overridden"


def test_default_factory_validation_error():
    # The usual parameter run-time validation works as usual, an error
    # is raised if the value returned by the factory isn't valid.
    class P(param.Parameterized):
        s = param.String(default_factory=lambda: 1)

    with pytest.raises(
        ValueError,
        match="String parameter 'P.s' only takes a string value, not value of <class 'int'>."
    ):
        P()


def test_default_factory_set_default_attribute_no_effect(P):
    # Setting the parameter default on the class or instance is a no-op.
    P.param['a'].default = 'something'
    p = P()
    p.param['a'].default = 'something'

    assert p.a == "from factory"


def test_default_factory_set_on_class_no_warning_or_error(P):
    # A simple factory callable only sets the instance value, not class.
    # Getting/setting the class value could raise an error (e.g. AttributeError),
    # however, it means all the functions iterating over the Parameters of a class
    # would fail (e.g. MyClass.param.values(), MyClass.param.serialize_parameters()).
    # Chose not to and let users get/set values, it's just that default_factory
    # takes precedence anyway.
    assert P.a is None
    P.a = 'something'
    assert P.a == 'something'


def test_default_factory_param_values(P):
    assert P.param.values()['a'] is None
    assert P().param.values()['a']


def test_default_factory_disable_with_None(P):
    P.param['a'].default_factory = None
    assert P().a is None


def test_default_factory_inheritance():
    class X(param.Parameterized):
        a = param.Parameter(default_factory=lambda: 'from factory')
        b = param.Parameter(default_factory=lambda: 'from factory')

    class Y(X):
        a = param.Parameter()

    y = Y()
    assert y.a == 'from factory'
    assert y.b == 'from factory'


def test_default_factory_inheritance_parameter_slot_defaults():

    class MyParameter(param.Parameter):

        _slot_defaults = dict(
            param.Parameter._slot_defaults,
            default_factory=lambda: 'from factory'
        )

    class X(param.Parameterized):
        a = MyParameter()

    class Y(X):
        a = MyParameter(default_factory=lambda: 'from other')

    y = Y()
    assert y.a == 'from other'
    x = X()
    assert x.a == 'from factory'


def test_default_factory_inheritance_override():
    class X(param.Parameterized):
        a = param.Parameter(default_factory=lambda: 'from X factory')

    class Y(X):
        a = param.Parameter()

    class Z(Y):
        a = param.Parameter(default_factory=lambda: 'from Z factory')

    assert Z().a == 'from Z factory'
    assert Y().a == 'from X factory'
    assert X().a == 'from X factory'


def test_default_factory_called_in_declaration_order():
    # The factories are called in the order of the parameter declarations,
    # from top to bottom
    orders = []
    idx = 0
    def collect():
        nonlocal idx
        orders.append(idx)
        idx += 1

    class X(param.Parameterized):
        a = param.Parameter(default_factory=collect)
        b = param.Parameter()
        c = param.Parameter(default_factory=collect)
        d = param.Parameter()

    class Y(param.Parameterized):
        e = param.Parameter()
        f = param.Parameter(default_factory=collect)

    X()
    assert orders == [0, 1]

    Y()
    assert orders == [0, 1, 2]


def test_default_factory_called_before_on_init():
    # factories are called before on_init
    order = []

    def factory():
        order.append('factory')
        return 'from factory'

    class P(param.Parameterized):
        a = param.Parameter(default_factory=factory)

        @param.depends('a', watch=True, on_init=True)
        def cb(self):
            order.append('on_init')

    P()

    assert order == ['factory', 'on_init']


def test_default_factory_no_event():
    # Value set from a factory doesn't trigger any event
    class P(param.Parameterized):
        called = False
        a = param.Parameter(default_factory=lambda: 'from factory')

        @param.depends('a', watch=True)
        def cb(self):
            self.called = True

    p = P()

    assert not p.called


def test_default_factory_alternative_instantiate():
    # Using a factory is an alternative to instantiate=True for mutable objects
    class P(param.Parameterized):
        l = param.List(default_factory=list)

    p1 = P()
    p2 = P()
    assert p1.l is not p2.l


def test_default_factory_object_is_callable():
    d = DefaultFactory(lambda _, __, ___: 0)
    assert callable(d)


def test_default_factory_object_correct_args_passed_to_factory():
    def factory(cls, self, parameter):
        return cls, self, parameter

    dfac = DefaultFactory(factory, on_class=True)

    class P(param.Parameterized):
        a = param.Parameter(default_factory=dfac)

    assert P.a[0] is P
    assert P.a[1] is None
    # Class parameter
    assert P.a[2] is P.param['a']

    p = P()
    assert p.a[0] is P
    assert p.a[1] is p
    assert 'a' in p._param__private.params
    assert p.a[2] is p._param__private.params['a']
    assert p.a[2] is p.param['a']


def test_default_factory_object_after_instance_initialized():
    def factory(cls, self, parameter):
        if self:
            # Factories are called after the instance is initialized, which means
            # (1) they have access to the values of all the other parameters,
            # (2) the parameter argument is an instance-level parameter
            assert self.a == 'a'
            assert self.c == 'c'
            assert parameter is self._param__private.params['b']
        else:
            # When called at the class-level, the parameter is the class-level one
            assert cls.a == 'A'
            assert cls.c == 'C'
            assert parameter is cls._param__parameters._cls_parameters['b']

    dfac = DefaultFactory(factory, on_class=True)

    class P(param.Parameterized):
        a = param.Parameter(default='A')
        b = param.Parameter(default_factory=dfac)
        c = param.Parameter(default='C')

    P(a='a', c='c')


def test_default_factory_object_auto_name():
    # Re-implementation of the behavior of the name String parameter with a
    # default_factory
    name_counter = 0

    def factory(cls, self, parameter):
        if self:
            # When the class value is overriden.
            if parameter and getattr(cls, parameter.name) != cls.__name__:
                return getattr(cls, parameter.name)
            else:
                nonlocal name_counter
                name = f'{cls.__name__}{name_counter:05d}'
                name_counter += 1
                return name
        elif cls:
            return cls.__name__
        else:
            raise ValueError('cls or self must be passed')

    dfac = DefaultFactory(factory, on_class=True)

    class P(param.Parameterized):
        auto_name = param.String(default_factory=dfac)

    assert P.auto_name == 'P'
    p1 = P()
    p2 = P()
    assert p1.auto_name == 'P00000'
    assert p2.auto_name == 'P00001'

    P.auto_name = 'foo'
    assert P().auto_name == 'foo'
