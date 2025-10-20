from typing import Any
from typing_extensions import dataclass_transform, reveal_type
import param
from typing import overload, Optional

@dataclass_transform(field_specifiers=(param.String, param.Number))
class PatchedParameterizedMetaclass(param.parameterized.ParameterizedMetaclass):
    pass

@overload
def param_string(default: str, doc: Optional[str] = None) -> str: ...
@overload
def param_string(default: None = None, doc: Optional[str] = None) -> Optional[str]: ...

def param_string(default=None, doc=None):
    return param.String(default=default, doc=doc)

def test_string(default: str, doc=None)->str:
    return default

class MyClass(param.Parameterized, metaclass=PatchedParameterizedMetaclass):
    my_parameter = param.String(default="some value", doc="A custom parameter")
    my_optional_parameter = param.String(doc="A custom parameter with None as default")
    my_default_is_None_parameter =  param.String(default=None, doc="A custom parameter with None as default")
    # my_parameter_annotated: str = param.String(default="annotated value", doc="A custom annotated parameter")
    
    my_param_string = param_string(default="default value", doc="A custom string parameter")
    my_pyram_string_none = param_string(default=None, doc="A custom string parameter with None as default")
    my_param_string_no_default = param_string(doc="A custom string parameter with no default")
    my_param_string_annotated: str = param_string(default="annotated value", doc="A custom annotated string parameter")

    my_test_string = test_string("test", doc="A test string parameter")
    my_number = param.Number(default=42.0, doc="A number parameter")
    my_value_annotated: int = 0  # Example of a simple parameter

def test_myclass() -> None:
    reveal_type(MyClass.my_parameter)  # Should be "builtins.str"
    reveal_type(MyClass.my_optional_parameter) # Should be "typing.Optional[str]"
    reveal_type(MyClass.my_default_is_None_parameter) # Should be "typing.Optional[str]"
    
    reveal_type(MyClass.my_param_string)  # Should be "builtins.str"
    reveal_type(MyClass.my_pyram_string_none)  # Should be "typing.Optional[str]"
    reveal_type(MyClass.my_param_string_no_default)  # Should be "typing.Optional[str

    reveal_type(MyClass.my_test_string)  # Should be "builtins.str"
    reveal_type(MyClass.my_number)     # Should be "builtins.float"
    reveal_type(MyClass.my_value_annotated)  # Should be "builtins.int"
    
    reveal_type(MyClass.__init__)  # Should show correct signature
    
    obj = MyClass(my_parameter="hello", my_number=3.14)
    
    reveal_type(obj.my_parameter)  # Should be "builtins.str"
    reveal_type(obj.my_optional_parameter)  # Should be "typing.Optional[str]"
    reveal_type(obj.my_default_is_None_parameter)  # Should be "typing.Optional[str]"

    reveal_type(obj.my_param_string)  # Should be "builtins.str"
    reveal_type(obj.my_pyram_string_none)  # Should be "typing.Optional[str]"
    reveal_type(obj.my_param_string_no_default)  # Should be "typing.Optional[str]"

    reveal_type(obj.my_test_string)  # Should be "builtins.str"
    reveal_type(obj.my_number)     # Should be "builtins.float"
    reveal_type(obj.my_value_annotated)  # Should be "builtins.int"

if __name__ == "__main__":
    test_myclass()