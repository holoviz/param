import param

from param.parameterized import _parameterized_repr_html


def test_repr_html_ClassSelector_tuple():
    class P(param.Parameterized):
        c = param.ClassSelector(class_=(str, int))

    rhtml = _parameterized_repr_html(P, True)
    assert 'None | str | int' in rhtml
