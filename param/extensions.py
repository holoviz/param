from collections.abc import MutableSequence, MutableMapping
from typing import List, Any, Dict
from copy import deepcopy

from .utils import wrap_error_text


class AbstractConstrainedList(MutableSequence):

    # Need to check mul
    
    def __init__(self, default : List[Any] = [], constant : bool = False, bounds : tuple = (0, None), 
                        allow_None : bool = True, set_direct : bool = False, skip_validate : bool = False) -> None:
        super().__init__()
        self.allow_None = allow_None
        self.constant   = constant
        self.bounds     = bounds
        self._validate(default, False, skip_validate)    
        self._initialize_set(default, set_direct)
        
    
    def _initialize_set(self, value : List[Any], set_direct : bool = False) -> None:
        """
        uses deepcopy if setDirect = True
        """
        if set_direct:
            self._inner = value
        else:
            self._inner = deepcopy(value) 
  
    def _validate(self, value : Any, for_extending : bool = False, skip_validate : bool = False) -> None:
        if skip_validate:
            return
        if value is None and self.allow_None: 
            return
        if self.constant:
            raise ValueError("List {} is a constant, cannot be modified.".format(self.__repr__()))
        self._validate_bounds(value, for_extending)
        self._validate_value(value)
        self._validate_item(value)

    def _validate_value(self, value : Any) -> None:
        if not isinstance(value, list):
            raise TypeError("Given value is not a list") 
           
    def _validate_item(self, value : Any) -> None:
        raise NotImplementedError("Please implement this function in the child of AbstractContrainedList.")

    def _validate_bounds(self, value : Any, for_extending : bool = False) -> None:
        if for_extending:
            if self._inner.__len__() + value.__len__() >= self.bounds[0]:
                if self.bounds[1] is not None: 
                    if self._inner.__len__() + value.__len__() <= self.bounds[1]:
                        return 
        else:
            if value.__len__() >= self.bounds[0]:
                if self.bounds[1] is not None: 
                    if value.__len__() <= self.bounds[1]:
                        return 

    def __json__(self) -> List[Any]:        
        return self._inner 
    
    def __len__(self) -> int:
        return self._inner.__len__()

    def __iter__(self) -> Any:
        return self._inner.__iter__()

    def __str__(self) -> str:
        return self._inner.__str__()

    def __contains__(self, item : Any) -> bool:
        return item in self._inner

    def __getitem__(self, index : int) -> Any:
        return self._inner[index]

    def __setitem__(self, index : int, value : Any) -> None:
        if self.constant:
            raise ValueError("List is a constant, cannot be modified.")
        self._validate_item(value)
        self._inner[index] = value

    def __delitem__(self, index : int) -> None:
        del self._inner[index]

    def __repr__(self) -> str:
        return repr(self._inner)
    
    def __imul__(self, value : Any) -> List[Any]:
        return self._inner.__imul__(value)

    def __mul__(self, value : Any) -> List[Any]:
        return self._inner.__mul__(value)

    def __sizeof__(self) -> int:
        return self._inner.__sizeof__()

    def __lt__(self, __x : List[Any]) -> bool:
        return self._inner.__lt__(__x)
    
    def __le__(self, __x : List[Any]) -> bool:
        return self._inner.__le__(__x)
    
    def __eq__(self, __x : List[Any]) -> bool:  
        return self._inner.__eq__(__x)
    
    def __ne__(self, __x : List[Any]) -> bool:
        return self._inner.__ne__(__x)
    
    def __gt__(self, __x : List[Any]) -> bool:
        return  self._inner.__gt__(__x)
    
    def __ge__(self, __x : List[Any]) -> bool:
        return self._inner.__ge__(__x)
       
    def __rmul__(self, __n : int) -> List[Any]:
        return self._inner.__rmul__(__n)

    def __reversed__(self) -> List[Any]:
        return self._inner.__reversed__()

    def __add__(self, __x : List[Any]) -> List[Any]: 
        return self._inner.__add__(__x)

    def __iadd__(self, values : List[Any] ) -> List[Any]:
        raise NotImplementedError("Please implement this function in the child of ContrainedList.")

    def insert(self, __index : int, __object : Any) -> None:
        self._validate([__object], for_extending=True)
        self._inner.insert(__index, __object)

    def append(self, __object : Any) -> None:
        self._validate([__object], for_extending=True)
        self._inner.append(__object)
        
    def extend(self, __iterable) -> None:
        self._validate(__iterable, for_extending=True)
        self._inner.extend(__iterable)

    def reverse(self) -> None:
        self._inner.reverse()
    
    def pop(self, __index: int) -> Any:
        return self._inner.pop(__index)

    def count(self, __value : Any) -> int:
        return self._inner.count(__value)

    def clear(self) -> None: 
        self._inner.clear()

    def index(self, __value : Any, __start : int, __stop : int) -> int:
        return self._inner.index(__value, __start, __stop)

    def pop(self, __index : int) -> Any:
        return self._inner.pop(__index)

    def remove(self, __value : Any) -> None:
        self._inner.remove(__value)

    def sort(self, key : Any, reverse : bool):
        self._inner.sort(key, reverse)

    def copy(self, return_as_typed_dict : bool = False):
        raise NotImplementedError("Please implement this function in the child of ContrainedList.")


       
class TypeConstrainedList(AbstractConstrainedList):

    def __init__(self, default : List[Any] = [], item_type : Any = None, bounds : tuple = (0,None), 
                       constant : bool = False, allow_None : bool = True, set_direct : bool = False, 
                       skip_validate : bool = False) -> None:
        self.item_type = item_type
        super().__init__(default, constant, bounds, allow_None)
        
    def _validate_item(self, value : Any):
        if self.item_type is not None:
            for val in value:  
                if not isinstance(val, self.item_type):
                    raise TypeError(
                        wrap_error_text(
                            """
                            Not all elements givenare of allowed item type(s), which are : {}. 
                            Given type {}.""".format(self.item_type, type(val))
                    ))
      
    def __iadd__(self, value : List[Any]):
        self._validate(value)
        return TypeConstrainedList(self._inner.__iadd__(value), self.item_type, self.bounds,
                                    self.constant, self.allow_None, True, True)
    
    def copy(self, return_as_typed_dict : bool = False) -> List[Any]: 
        if return_as_typed_dict:
            return TypeConstrainedList(self._inner.copy(), self.item_type, self.bounds, self.constant, 
                                                    self.allow_None, True, True)
        else:
            return self._inner.copy()
      


class TypeConstrainedDict(MutableMapping):
    """ A dictionary which contains only ``NewDict`` values. """

    def __init__(self, default : Dict[Any, Any] = {}, key_type : tuple = None, item_type : tuple = None, 
                        bounds : tuple = (0, None), constant : bool = False, allow_None : bool = True, 
                        set_direct : bool = False):
        super().__init__()
        # _inner value set in update()
        self._inner = None # or collections.OrderedDict, etc.
        self.key_type   = key_type
        self.item_type  = item_type
        self.allow_None = allow_None
        self.bounds     = bounds 
        self.constant   = constant 
        self._validate(default)
        self._set(default, set_direct)

    def _validate(self, value : Dict[Any, Any]) -> None:
        if self.allow_None and value is None:
            return 
        if self.constant:
            raise ValueError("")
        self._validate_value(value)
        self._validate_bounds(value)
        self._validate_item(value)

    def _validate_value(self, value) -> None:
        if not isinstance(value, dict):
            raise TypeError("")

    def _validate_bounds(self, value : Dict[Any, Any], for_updating : bool = False) -> None:
        if for_updating:
            if not (self.bounds[0] < self._inner.__len__() + value.__len__() < self.bounds[1]):
                raise ValueError("")
        else:
            if not (self.bounds[0] < value.__len__() < self.bounds[1]):
                raise ValueError("")
            
    def _validate_item(self, value : Dict[Any, Any]) -> None:
        keys = value.keys()
        values = value.values()
        if self.key_type is not None and len(keys) != 0:                    
            for key in keys:
                if not isinstance(key, self.key_type):
                    raise TypeError("keys contain incompatible types. Allowed types : {}.".format(self.key_type))
        if self.item_type is not None and values != []: 
            for value in values:
                if not isinstance(value, self.item_type):
                    raise TypeError("values contain incompatible types. Allowed types : {}.".format(self.item_type))
       
    def _validate_key_value_pair(self, __key : Any, __value : Any) -> None:
        if self.key_type is not None:
            if not isinstance(__key, self.key_type):
                raise TypeError("given key {} is not of {}.".format(__key, self.key_type))
        if self.item_type is not None: 
            if not isinstance(__value, self.item_type):
                raise TypeError("given item {} is not of {}.".format(__value, self.item_type))

    def __sizeof__(self):
        return self._inner.__sizeof__()

    def __iter__(self):
        return self._inner.__iter__()

    def __setitem__(self, __key : Any, __value : Any) -> None:
        self._validate_key_value_pair(__key, __value)
        if not (self.bounds[0] < self._inner.__len__() + 1 < self.bounds[1]):
            raise ValueError("")
        self._inner.__setitem__(__key, __value)

    def __delitem__(self, __v : Any) -> None:
        self._inner.__delitem__(__v)

    def __getitem__(self, __k : Any):
        return self._inner.__getitem__(__k)

    def __json__(self):
        return self._inner
    
    def __str__(self) -> str:
        return self._inner.__str__()

    def __len__(self) -> int:
        return self._inner.__len__()

    def __contains__(self, __o : object) -> bool:
        return self._inner.__contains__(__o)

    def __eq__(self, __o: object) -> bool:
        return self._inner.__eq__(__o) 

    def __ne__(self, __o: object) -> bool:
        return self._inner.__ne__(__o)
    
    def __format__(self, __format_spec: str) -> str:
        return self._inner.__format__(__format_spec)        
    
    def __sizeof__(self) -> int:
        return self._inner.__sizeof__()
        
    def __repr__(self) -> str:
        return self._inner.__repr__()
        
    def fromkeys(self, __iterable, __value : Any):
        return self._inner.fromkeys(__iterable, __value)

    def keys(self):
        return self._inner.keys()

    def items(self):
        return self._inner.items()

    def values(self):
        return self._inner.values()

    def get(self, __key : Any, __default : Any):
        return self._inner.get(__key, __default)

    def setdefault(self, __key : Any) -> None:
        self._inner.setdefault(__key)       

    def clear(self) -> None:
        self._inner.clear()

    def copy(self, return_as_typed_dict : bool = False) -> Dict[Any, Any]:
        if return_as_typed_dict:
            pass 
        else:
            return self._inner.copy()

    def popitem(self) -> tuple:
        return self._inner.popitem()
    
    def pop(self, __key : Any) -> Any:
        return self._inner.pop(__key)
    
    def _set(self, __o : Any, update_direct) -> None:
        if self._inner is None:
            self._inner = dict()
        if update_direct:
            self._inner.update(__o)
        else:
            self.update(__o)

    def update(self, __o : Any) -> None:
        if self._inner is None: 
            self._inner = dict()
        self._validate(__o)
        self._inner.update(__o)
        


__all__ = ['TypeConstrainedList', 'TypeConstrainedDict']