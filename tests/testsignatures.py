import typing

from param import concrete_descendents, Parameter


def test_all_parameters_constructors_are_overloaded():
    for _, p_type in concrete_descendents(Parameter).items():
        init_overloads = typing.get_overloads(p_type.__init__)
        assert len(init_overloads) == 1
