import ast
import inspect

import param


def walk_modules(pkg):
    modules = [pkg]
    for name, submodule in inspect.getmembers(pkg, inspect.ismodule):
        if submodule.__package__.startswith(pkg.__name__):
            modules.extend(walk_modules(submodule))
    return modules

def walk_parameterized(module):
    parameterizeds = []
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, param.Parameterized) and cls.__module__ == module.__name__ and walk_parameters(cls):
            parameterizeds.append(cls)
    return parameterizeds

def walk_parameters(parameterized):
    return [obj for obj in parameterized.param.objects().values() if obj.owner is parameterized]

class ExtractClassDefs(ast.NodeTransformer):
    
    def __init__(self, parameterizeds):
        self.nodes = {p: None for p in parameterizeds}
        self._lookup = {p.__name__: p for p in parameterizeds}
    
    def visit_ClassDef(self, node):
        p = self._lookup.get(node.name)
        if p is not None:
            self.nodes[p] = node
        return node
    
class ExtractParameterDefs(ast.NodeTransformer):
    
    def __init__(self, params):
        self.nodes = {p: None for p in params}
        self._lookup = {p.name: p for p in params}
    
    def record(self, node):
        targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
        for t in targets:
            if not isinstance(t, ast.Name):
                continue
            p = self._lookup.get(t.id)
            if p is not None:
                self.nodes[p] = node
    
    def visit_AnnAssign(self, node):
        self.record(node)
        return node
    
    def visit_Assign(self, node):
        self.record(node)
        return node

def extra_param_assigns(parameterized, cls_def):
    params = walk_parameters(parameterized)
    param_defs = ExtractParameterDefs(params)
    param_defs.visit(cls_def)
    return param_defs.nodes

TYPES = {
    bool: 'bool',
    int: 'int',
    float: 'float',
    bytes: 'bytes'
}

def format_type(pytype):
    if pytype in TYPES:
        return TYPES[pytype]
    return str(pytype)

def add_types(module):
    with open(module.__file__) as f:
        code = f.read()
    parsed = ast.parse(code, module.__file__)

    parameterized = walk_parameterized(module)

    class_defs = ExtractClassDefs(parameterized)
    class_defs.visit(parsed)

    parameter_definitions = {}
    for pzd in parameterized:
        cls_def = class_defs.nodes[pzd]
        param_defs = extra_param_assigns(pzd, cls_def)
        for p, pdef in param_defs.items():
            if pdef is None:
                continue
            src_code = ast.get_source_segment(code, pdef, padded=True)
            transformed = src_code.split('\n')
            pytype = format_type(p.pytype)
            transformed[0] = transformed[0].replace(f'{p.name} =', f'{p.name}: {pytype} =')
            code = code.replace(src_code, '\n'.join(transformed))
    return code
