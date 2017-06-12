import contextlib
import json
import os
import shutil
import tempfile

import pytest
import yaml

import param
from param.io import *

class ServiceMetadata(param.Parameterized):
    file_format = param.String()
    parameters = param.List()
    unmapped_parameters_available = param.Boolean()


class Features(param.Parameterized):
    file = param.String()
    format = param.String()

class Service(param.Parameterized):
    service_folder = param.List()
    service_id = param.String()
    metadata = param.ObjectSelector(default=ServiceMetadata())
    features = param.ObjectSelector(default=Features())


class ProjectMetadata(param.Parameterized):
    display_name = param.String()
    description = param.String(allow_None=True)

class ConfigSpec(param.Parameterized):
    metadata = ProjectMetadata()
    env = param.Dict()
    cmd_args = param.Dict()
    services = param.List(class_=Service, instantiate=True)


EXAMPLE = yaml.safe_load("""
cmd_args: null
env: null
services:
  datasets: {mapping: '', save_folder: ''}
  features: {file: ''}
  metadata: {parameters: [],
    file_format: '', unmapped_parameters_available: false}
  service_id: ''
""")

@contextlib.contextmanager
def dump_file(contents, typ):
    tmp = tempfile.mkdtemp()
    try:
        fname = os.path.join(tmp, 'test_param_file.{}'.format(typ))
        with open(fname, 'w') as f:
            if typ == 'yaml':
                f.write(yaml.safe_dump(contents))
            elif typ == 'json':
                json.dump(contents, f)
        yield fname
    finally:
        shutil.rmtree(tmp)

ext_func = tuple(zip(('yaml', 'json'),
                     (from_yaml, from_json),
                     (to_yaml, to_json)))
@pytest.mark.parametrize('typ, from_func, to_func', ext_func)
def test_serialize_deserialize(typ, from_func, to_func):
    with dump_file(EXAMPLE, typ) as fname:
        config = from_func(ConfigSpec(), fname)
        new_fname = fname + 'test'
        to_func(config, new_fname)
        config2 = from_func(ConfigSpec(), new_fname)
        assert config == config2
        assert serialize(config) == serialize(config2)
        assert deserialize(serialize(config)) == config

