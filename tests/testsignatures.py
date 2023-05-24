import inspect
import sys
import typing

import param
import pytest

from param import concrete_descendents, Parameter


SKIP_UPDATED = [
    # Not sure how to handle attribs yet
    param.Composite,
    # Not sure how to handle search_paths
    param.Path, param.Filename, param.Foldername,
]


def custom_concrete_descendents(kls):
    return {
        pname: ptype
        for pname, ptype in concrete_descendents(kls).items()
        if ptype.__module__.startswith('param')
    }


@pytest.mark.skipif(sys.version_info <= (3, 11), reason='typing.get_overloads available from Python 3.11')
def test_signature_parameters_constructors_overloaded():
    for _, p_type in custom_concrete_descendents(Parameter).items():
        init_overloads = typing.get_overloads(p_type.__init__)
        assert len(init_overloads) == 1


def test_signature_parameters_constructors_updated():

    base_args = list(inspect.signature(Parameter).parameters.keys())

    for _, p_type in custom_concrete_descendents(Parameter).items():
        if p_type in SKIP_UPDATED:
            continue
        sig = inspect.signature(p_type)
        for parameter in sig.parameters.values():
            assert parameter.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        assert all(arg in sig.parameters for arg in base_args)


@pytest.mark.skipif(sys.version_info <= (3, 11), reason='typing.get_overloads available from Python 3.11')
def test_signature_parameters_constructors_overloaded_updated_match():
    for _, p_type in custom_concrete_descendents(Parameter).items():
        if p_type.__name__.startswith('_') or p_type in SKIP_UPDATED:
            continue
        init_overloads = typing.get_overloads(p_type.__init__)
        osig = inspect.signature(init_overloads[0])
        osig = osig.replace(parameters=[parameter for pname, parameter in osig.parameters.items() if pname != 'self'])
        usig = inspect.signature(p_type)
        assert osig == usig, _
