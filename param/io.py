from functools import partial
import json

import param

__all__ = ['serialize', 'deserialize',
           'to_yaml', 'to_json',
           'from_yaml', 'from_yaml',]

def from_params_dict(parameter, obj=None):
    if hasattr(parameter, 'params'):
        for k, p in parameter.params().items():
            if k in obj:
                v = obj[k]
                args = (p, v)
            else:
                continue
            if isinstance(p, param.List):
                if getattr(p, 'class_'):
                    setattr(parameter, k, [from_params_dict(p.class_(), vi) for vi in v])
                else:
                    p = v
            elif hasattr(p, 'params'):
                setattr(parameter, k, from_params_dict(*args))
            else:
                p = v
    else:
        parameter = obj
    return parameter


def deserialize(parameter, fname, ftype='yaml'):
    with open(fname) as f:
        if ftype == 'yaml':
            import yaml
            obj = yaml.safe_load(f.read())
        elif ftype == 'json':
            obj = json.load(f)
        else:
            raise ValueError('Expected ftype in ("yaml", "json")')
    from_params_dict(parameter, obj)
    return parameter

from_yaml = partial(deserialize, ftype='yaml')
from_json = partial(deserialize, ftype='json')

def serialize(parameter):

    output = {}
    def handle_dict_type(parameter, current_key):
        for key in parameter.params():
            value = getattr(parameter, key)
            for item in switch_data_types(value, current_key + (key,)):
                yield (current_key, item)

    def handle_list_type(parameter, current_key):
        for item in parameter:
            for item in switch_data_types(item, current_key):
                yield (current_key, item)

    def switch_data_types(parameter, current_key):
        if hasattr(parameter, 'params'):
            for item in handle_dict_type(parameter, current_key):
                yield item
        elif isinstance(parameter, (list, param.List)):
            for item in handle_list_type(parameter, current_key):
                yield item
        elif isinstance(parameter, param.Parameterized):
            tuple(switch_data_types(parameter, current_key))
        else:
            if current_key:
                d = output
                for key in current_key[:-1]:
                    if key not in d:
                        d[key] = {}
                    d = d[key]
                d[current_key[-1]] = parameter
            yield output

    list(switch_data_types(parameter, ()))
    return dict(output)


def to_yaml(parameter, fname):
    import yaml
    converted = serialize(parameter)
    with open(fname, 'w') as f:
        f.write(yaml.safe_dump(converted))

def to_json(parameter, fname):
    converted = serialize(parameter)
    with open(fname, 'w') as f:
        json.dump(converted, indent=2)

