import param
import pytest

from param.reactive import bind, rx

class Parameters(param.Parameterized):

    string = param.String(default="string", allow_refs=True)

    dictionary = param.Dict(default={}, allow_refs=True, nested_refs=True)

    string_list = param.List(default=[], item_type=str, allow_refs=True, nested_refs=True)


class Nested(param.Parameterized):

    subobject = param.ClassSelector(class_=Parameters)

    @param.depends('subobject.string')
    def string(self):
        return self.subobject.string + '!'


def test_parameterized_warns_explicit_no_ref():
    class ImplicitRefsParameters(param.Parameterized):
        parameter = param.Parameter(default="string")

    p = Parameters()
    with pytest.raises(Exception) as e:
        ImplicitRefsParameters(parameter=p.param.string)
    assert f"Parameter 'parameter' on {ImplicitRefsParameters} is being given a valid parameter reference <param.parameterized.String" in str(e.value)

def test_parameter_ref():
    p = Parameters()
    p2 = Parameters(string=p.param.string)

    assert p.string == p2.string
    p.string = 'new_string'
    assert p2.string == 'new_string'

def test_parameter_ref_update():
    p = Parameters()
    p2 = Parameters(string=p.param.string)
    p3 = Parameters(string='new string')

    p2.string = p3.param.string
    assert p2.string == 'new string'
    p.string = 'still linked'
    assert p2.string != 'still linked'
    p3.string = 'newly linked'
    assert p2.string == 'newly linked'

def test_bind_ref():
    p = Parameters()
    p2 = Parameters(string=bind(lambda x: x + '!', p.param.string))
    assert p2.string == 'string!'
    p.string = 'new string'
    assert p2.string == 'new string!'

def test_reactive_ref():
    string = rx('string')
    rx_string = string+'!'
    p = Parameters(string=rx_string)
    assert p.string == 'string!'
    string.rx.set_input('new string')
    assert p.string == 'new string!'

def test_nested_list_parameter_ref():
    p = Parameters()
    p2 = Parameters(string_list=[p.param.string, 'other'])
    p3 = Parameters(string='foo')

    assert p2.string_list == ['string', 'other']
    p2.string_list = [p3.param.string, 'another']
    assert p2.string_list == ['foo', 'another']

def test_nested_dict_key_parameter_ref():
    p = Parameters()
    p2 = Parameters(dictionary={p.param.string: 'value'})
    p3 = Parameters(string='foo')

    assert p2.dictionary == {'string': 'value'}
    p2.dictionary = {p3.param.string: 'new_value'}
    assert p2.dictionary == {'foo': 'new_value'}

def test_nested_dict_value_parameter_ref():
    p = Parameters()
    p2 = Parameters(dictionary={'key': p.param.string})
    p3 = Parameters(string='foo')

    assert p2.dictionary == {'key': 'string'}
    p2.dictionary = {'new key': p3.param.string}
    assert p2.dictionary == {'new key': 'foo'}

def test_nested_param_method_ref():
    p = Parameters()
    nested = Nested(subobject=p)
    p2 = Parameters(string=nested.string)

    assert p2.string == 'string!'
    p.string = 'new string'
    assert p2.string == 'new string!'
