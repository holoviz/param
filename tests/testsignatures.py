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


def test_signature_position_keywords():
    NO_POSITIONAL = [
        # class_ is first
        param.ClassSelector,
        # objects is first
        param.Selector,
        # attribs is first
        param.Composite,
    ]

    for ptype in custom_concrete_descendents(Parameter).values():
        if ptype.__name__.startswith('_'):
            continue
        sig = inspect.signature(ptype)
        parameters = dict(sig.parameters)
        parameters.pop('self', None)
        if ptype in NO_POSITIONAL:
            assert all(
                p.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD)
                for pname, p in parameters.items()
                if pname != 'self'
            )
        else:
            positional_or_kw = [
                p
                for p in parameters.values()
                if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
            ]
            assert len(positional_or_kw) == 1
            assert positional_or_kw[0].name == 'default'
            del parameters['default']

            assert all(
                p.kind in (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD)
                for p in parameters.values()
            )


def test_signature_warning_by_position():
    # Simple test as it's tricky to automatically test all the Parameters
    with pytest.warns(
        param._utils.ParamPendingDeprecationWarning,
        match=r"Passing 'objects' as positional argument\(s\) to 'param.Selector' has been deprecated since Param 2.0.0 and will raise an error in a future version, please pass them as keyword arguments"
    ):
        param.Selector([0, 1])  # objects
    with pytest.warns(
        param._utils.ParamPendingDeprecationWarning,
        match=r"Passing 'class_' as positional argument\(s\) to 'param.ClassSelector' has been deprecated since Param 2.0.0 and will raise an error in a future version, please pass them as keyword arguments"
    ):
        param.ClassSelector(int)  # class_
    with pytest.warns(
        param._utils.ParamPendingDeprecationWarning,
        match=r"Passing 'bounds, softbounds' as positional argument\(s\) to 'param.Number' has been deprecated since Param 2.0.0 and will raise an error in a future version, please pass them as keyword arguments"
    ):
        param.Number(1, (0, 2), (0, 2))  # default (OK), bounds (not OK), softbounds (not OK)
