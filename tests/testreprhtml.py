import param
import pytest

from param.parameterized import _parameterized_repr_html


class TestHTMLRepr:

    @pytest.fixture
    def Sub(self):
        class Sub(param.Parameterized):
            xsub = param.Parameter()

        return Sub

    @pytest.fixture
    def P(self, Sub):
        class P(param.Parameterized):
            constant = param.Parameter(constant=True)
            readonly = param.Parameter(readonly=True)
            allow_None = param.Parameter(1, allow_None=False)
            bounds = param.Number(bounds=(-10, 10))
            objects_list = param.Selector(objects=[1, 2])
            objects_dict = param.Selector(objects=dict(a=1, b=2))
            sub = param.ClassSelector(default=Sub(xsub=1), class_=Sub)

        return P

    def test_repr_in_place(self):
        assert hasattr(param.Parameterized.param, '_repr_html_')
        assert hasattr(param.Parameterized().param, '_repr_html_')

    def test_html_repr_class_str(self, P):
        html = P.param._repr_html_()
        assert isinstance(html, str)

    def test_html_repr_inst_str(self, P):
        html = P().param._repr_html_()
        assert isinstance(html, str)

    def test_html_repr_class_sub(self, P):
        html = P.param._repr_html_()
        assert '<details >\n <summary style="display:list-item; outline:none;">\n  <tt>Sub' in html

    def test_html_repr_inst_sub(self, P):
        html = P().param._repr_html_()
        assert '<details >\n <summary style="display:list-item; outline:none;">\n  <tt>Sub' in html

    def test_html_repr_ClassSelector_tuple(self):
        class P(param.Parameterized):
            c = param.ClassSelector(class_=(str, int))

        rhtml = _parameterized_repr_html(P, True)
        assert 'str | int' in rhtml

    def test_html_repr_title_class(self, P):
        html = P.param._repr_html_()
        assert '<tt>P</tt>' in html

    def test_html_repr_title_instance(self, P):
        html = P().param._repr_html_()
        assert '<tt>P()</tt>' in html
