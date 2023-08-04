import param
import pytest


def test_callable_validate():
    with pytest.raises(
        ValueError,
        match=r"Callable parameter 'c' only takes a callable object, not objects of <class 'str'>\."
    ):
        c = param.Callable('wrong')  # noqa
