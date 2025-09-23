import asyncio
import threading
import time

import param
import pytest

from param.parameterized import Skip, resolve_ref
from param.reactive import bind, rx

class Parameters(param.Parameterized):

    string = param.String(default="string", allow_refs=True)

    dictionary = param.Dict(default={}, allow_refs=True, nested_refs=True)

    string_list = param.List(default=[], item_type=str, allow_refs=True, nested_refs=True)

    no_refs = param.Parameter(allow_refs=False)

    @param.depends('string')
    def formatted_string(self):
        if self.string.endswith('?'):
            raise Skip()
        return self.string + '!'

    @param.depends('string')
    def formatted_string_skip_return(self):
        if self.string.endswith('?'):
            return Skip
        return self.string + '!'

class Subclass(Parameters):

    no_refs = param.Parameter()

class SubclassOverride(Parameters):

    no_refs = param.Parameter(allow_refs=True)

class Nested(param.Parameterized):

    subobject = param.ClassSelector(class_=Parameters)

    @param.depends('subobject.string')
    def string(self):
        return self.subobject.string + '!'


def test_class_explicit_no_refs():
    assert Parameters._param__private.explicit_no_refs == ['no_refs']

def test_subclass_explicit_no_refs():
    assert Subclass._param__private.explicit_no_refs == ['no_refs']

def test_subclass_explicit_no_refs_override():
    assert SubclassOverride._param__private.explicit_no_refs == []

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

def test_parameter_ref_update_context():
    p = Parameters(string='linked')
    p2 = Parameters(string=p.param.string)

    assert p2.string == 'linked'
    with p2.param.update(string='override'):
        assert p2.string == 'override'
        p.string = 'not yet linked'
        assert p2.string == 'override'
    assert p2.string == 'not yet linked'
    p.string = 'relinked'
    assert p2.string == 'relinked'

def test_bind_ref():
    p = Parameters()
    p2 = Parameters(string=bind(lambda x: x + '!', p.param.string))
    assert p2.string == 'string!'
    p.string = 'new string'
    assert p2.string == 'new string!'

def test_bind_ref_skip():
    p = Parameters()

    def skip_fn(s):
        if s == 'invalid':
            raise Skip()
        return s + '!'
    p2 = Parameters(string=bind(skip_fn, p.param.string))
    assert p2.string == 'string!'
    p.string = 'new string'
    assert p2.string == 'new string!'
    p.string = 'invalid'
    assert p2.string == 'new string!'

def test_reactive_ref():
    string = rx('string')
    rx_string = string+'!'
    p = Parameters(string=rx_string)
    assert p.string == 'string!'
    string.rx.value = 'new string'
    assert p.string == 'new string!'

def test_nested_list_parameter_ref():
    p = Parameters()
    p2 = Parameters(string_list=[p.param.string, 'other'])
    p3 = Parameters(string='foo')

    assert p2.string_list == ['string', 'other']
    p2.string_list = [p3.param.string, 'another']
    assert p2.string_list == ['foo', 'another']

def test_nested_nested_parameter_ref_not_overwritten():
    # Ensure refs are not removed when updating another ref
    p = Parameters(string='bar')
    p2 = Parameters(string='foo')
    p3 = Parameters(string=p.param.string, string_list=[p2.param.string, 'other'])
    p4 = Parameters()

    assert p3.string_list == ['foo', 'other']
    p3.string = p4.param.string
    p.string = 'fizz'
    p2.string = 'buzz'
    assert p3.string == 'string'
    assert p3.string_list == ['buzz', 'other']

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

def test_nested_param_method_skip():
    p = Parameters()
    p2 = Parameters(string=p.formatted_string)

    assert p2.string == 'string!'
    p.string = 'new string?'
    assert p2.string == 'string!'

def test_nested_param_method_skip_return():
    p = Parameters()
    p2 = Parameters(string=p.formatted_string_skip_return)

    assert p2.string == 'string!'
    p.string = 'new string?'
    assert p2.string == 'string!'

async def test_async_function_ref():
    async def gen_strings():
        await asyncio.sleep(0.02)
        return 'string!'

    p = Parameters(string=gen_strings)

    await asyncio.sleep(0.1)
    assert p.string == 'string!'

async def test_async_bind_ref():
    p = Parameters()

    async def exclaim(string):
        await asyncio.sleep(0.05)
        return string + '!'

    p2 = Parameters(string=bind(exclaim, p.param.string))
    await asyncio.sleep(0.1)
    assert p2.string == 'string!'
    p.string = 'new string'
    await asyncio.sleep(0.1)
    assert p2.string == 'new string!'

async def test_async_generator_ref():
    async def gen_strings():
        yield 'string?'
        await asyncio.sleep(0.02)
        yield 'string!'

    p = Parameters(string=gen_strings)

    await asyncio.sleep(0.01)
    assert p.string == 'string?'
    await asyncio.sleep(0.1)
    assert p.string == 'string!'

async def test_generator_ref():
    def gen_strings():
        yield 'string?'
        time.sleep(0.05)
        yield 'string!'

    p = Parameters(string=gen_strings)

    await asyncio.sleep(0.02)
    assert p.string == 'string?'
    for _ in range(5):
        await asyncio.sleep(0.05)
        if p.string == 'string!':
            break
    assert p.string == 'string!'

async def test_async_generator_ref_cancelled():
    tasks = []
    async def gen_strings1():
        tasks.append(asyncio.current_task())
        i = 0
        while True:
            yield str(i)
            await asyncio.sleep(0.01)

    async def gen_strings2():
        tasks.append(asyncio.current_task())
        i = 0
        while True:
            yield str(i)
            await asyncio.sleep(0.01)

    p = Parameters(string=gen_strings1)
    await asyncio.sleep(0.02)
    assert p.string is not None
    p.string = gen_strings2
    await asyncio.sleep(0.02)
    assert len(tasks) == 2
    task1, task2 = tasks
    assert task1.done()
    assert not task2.done()
    assert p._param__private.async_refs['string'] is task2

async def test_generator_ref_cancelled():
    threads = []
    def gen_strings1():
        threads.append(threading.current_thread())
        i = 0
        while True:
            yield str(i)
            time.sleep(0.01)

    def gen_strings2():
        threads.append(threading.current_thread())
        i = 0
        while True:
            yield str(i)
            time.sleep(0.01)

    p = Parameters(string=gen_strings1)
    await asyncio.sleep(0.02)
    task1 = p._param__private.async_refs['string']
    assert p.string is not None
    p.string = gen_strings2
    await asyncio.sleep(0.02)
    task2 = p._param__private.async_refs['string']
    assert task1 is not task2
    assert task1.done()
    assert not task2.done()
    assert len(threads) == 2

def test_resolve_ref_parameter():
    p = Parameters()
    refs = resolve_ref(p.param.string)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_depends_method():
    p = Parameters()
    refs = resolve_ref(p.formatted_string)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_recursive_list():
    p = Parameters()
    nested = [[p.param.string]]
    refs = resolve_ref(nested, recursive=True)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_recursive_set():
    p = Parameters()
    nested = {(p.param.string,)}  # Parameters aren't hashable
    refs = resolve_ref(nested, recursive=True)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_recursive_tuple():
    p = Parameters()
    nested = ((p.param.string,),)
    refs = resolve_ref(nested, recursive=True)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_recursive_dict():
    p = Parameters()
    nested = {'0': {'0': p.param.string}}
    refs = resolve_ref(nested, recursive=True)
    assert len(refs) == 1
    assert refs[0] is p.param.string

def test_resolve_ref_recursive_slice():
    p = Parameters()
    nested = [slice(p.param.string)]
    refs = resolve_ref(nested, recursive=True)
    assert len(refs) == 1
    assert refs[0] is p.param.string
