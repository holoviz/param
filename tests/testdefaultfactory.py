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
    class P(param.Parameterized):
        called = False
        a = param.Parameter(default_factory=lambda: 'from factory')

        @param.depends('a', watch=True)
        def cb(self):
            self.called = True

    p = P()

    assert not p.called


def test_default_factory_alternative_instantiate():
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


def test_default_factory_object_after_parameters_initialized():
    def factory(_cls, self, _parameter):
        assert self.a == 'a'
        assert self.c == 'c'

    dfac = DefaultFactory(factory)

    class P(param.Parameterized):
        a = param.Parameter()
        b = param.Parameter(default_factory=dfac)
        c = param.Parameter()

    P(a='a', c='c')


def test_default_factory_object_auto_name():
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
        auto_name = param.Parameter(default_factory=dfac)

    assert P.auto_name == 'P'
    p1 = P()
    p2 = P()
    assert p1.auto_name == 'P00000'
    assert p2.auto_name == 'P00001'

    P.auto_name = 'foo'
    assert P().auto_name == 'foo'
