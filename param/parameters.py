import glob
import re
import os.path
import datetime as dt
import typing 
import numbers
import sys
import collections.abc
from collections import OrderedDict

from .utils import *
from .exceptions import *
from .parameterized import ParamOverrides, Parameterized, ParameterizedFunction, descendents, dt_types, Parameter



class Infinity(object):
    """
    An instance of this class represents an infinite value. Unlike
    Python's float('inf') value, this object can be safely compared
    with gmpy numeric types across different gmpy versions.

    All operators on Infinity() return Infinity(), apart from the
    comparison and equality operators. Equality works by checking
    whether the two objects are both instances of this class.
    """
    def __eq__  (self, other): return isinstance(other,self.__class__)
    def __ne__  (self, other): return not self == other
    def __lt__  (self, other): return False
    def __le__  (self, other): return False
    def __gt__  (self, other): return True
    def __ge__  (self, other): return True
    def __add__ (self, other): return self
    def __radd__(self, other): return self
    def __ladd__(self, other): return self
    def __sub__ (self, other): return self
    def __iadd_ (self, other): return self
    def __isub__(self, other): return self
    def __repr__(self):       return "Infinity()"
    def __str__ (self):       return repr(self)


 
class String(Parameter):
    """
    A string parameter with a default value and optional regular expression (regex) matching.

    Example of using a regex to implement IPv4 address matching::

      class IPAddress(String):
        '''IPv4 address as a string (dotted decimal notation)'''
       def __init__(self, default="0.0.0.0", allow_None=False, **kwargs):
           ip_regex = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
           super(IPAddress, self).__init__(default=default, regex=ip_regex, **kwargs)
    """

    __slots__ = ['regex']

    def __init__(self, default : typing.Optional[str] = "", *, regex : typing.Optional[str] = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False, 
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None, 
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel,
            precedence=precedence)
        self.regex = regex
    
    def validate_and_adapt(self, value : typing.Any) -> str: 
        self._assert(value, self.regex, self.allow_None)
        return value

    @classmethod
    def _assert(obj, value : typing.Any, regex : typing.Optional[str] = None, allow_None : bool = False) -> None: 
        """
        the method that implements the validator
        """
        if value is None: 
            if allow_None:
                return 
            else:
                raise_ValueError(f"None not allowed for string type", obj)
        if not isinstance(value, str):
            raise_TypeError("given value is not string type, but {}.".format(type(value)), obj)
        if regex is not None:
            match = re.match(regex, value) 
            if match is None or match.group(0) != value:
                # match should be original string, not some substring
                raise_ValueError("given string value {} does not match regex {}.".format(value, regex), obj)

    @classmethod
    def isinstance(cls, value : typing.Any, regex : typing.Optional[str] = None, allow_None : bool = False) -> bool:
        """
        verify if given value is a string confirming to regex. 
        
        Args:
            value (Any): input value
            regex (str, None): regex required to match, leave None if unnecessary
            allow_None (bool): set True if None is tolerated

        Returns:
            bool: True if conformant, else False. Any exceptions due to wrong inputs resulting in TypeError and ValueError
                also lead to False
        """
        try:
            cls._assert(value, regex, allow_None)
            return True
        except (TypeError, ValueError):
            return False

   

class Bytes(String):
    """
    A bytes parameter with a default value and optional regular
    expression (regex) matching.

    Similar to the string parameter, but instead of type basestring
    this parameter only allows objects of type bytes (e.g. b'bytes').
    """

    @classmethod
    def _assert(obj, value : typing.Any, regex : typing.Optional[bytes] = None, allow_None : bool = False) -> None:
        """
        verify if given value is a bytes confirming to regex. 
        
        Args:
            value (Any): input value
            regex (str, None): regex required to match, leave None if unnecessary
            allow_None (bool): set True if None is tolerated

        Raises:
            TypeError: if given type is not bytes
            ValueError: if regex does not match
        """
        if value is None: 
            if allow_None:
                return 
            else:
                raise_ValueError(f"None not allowed for string type", obj)
        if not isinstance(value, bytes):
            raise_TypeError("given value is not bytes type, but {}.".format(type(value)), obj)
        if regex is not None:
            match = re.match(regex, value) 
            if match is None or match.group(0) != value:
                # match should be original string, not some substring
                raise_ValueError("given bytes value {} does not match regex {}.".format(value, regex), obj)
    


class IPAddress(Parameter):

    __slots__ = ['allow_localhost', 'allow_ipv4', 'allow_ipv6']
    
    def __init__(self, default : typing.Optional[str] = "0.0.0.0", *, allow_ipv4 : bool = True, allow_ipv6 : bool = True, 
            allow_localhost : bool = True,
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            allow_None : bool = False, per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.allow_localhost = allow_localhost 
        self.allow_ipv4 = allow_ipv4
        self.allow_ipv6 = allow_ipv6

    def validate_and_adapt(self, value: typing.Any) -> str:
        self._assert(value, self.allow_ipv4, self.allow_ipv6, self.allow_localhost, self.allow_None)
        return value
    
    @classmethod
    def _assert(obj, value : typing.Any, allow_ipv4 : bool = True, allow_ipv6 : bool = True,
                allow_localhost : bool = True, allow_None : bool = False) -> None:
        if value is None and allow_None:
            return
        if not isinstance(value, str):
            raise_TypeError('given value for IP address not a string, but type {}'.format(type(value)), obj)
        if allow_localhost and value == 'localhost':
            return
        if not ((allow_ipv4 and (obj.isipv4(value) or obj.isipv4cidr(value))) 
                        or (allow_ipv6 and (obj.isipv6(value) or obj.isipv6cidr(value)))):
            raise_ValueError("Given value {} is not a valid IP address.".format(value), obj)
        
    @classmethod
    def isinstance(obj, value : typing.Any, allow_ipv4 : bool = True, allow_ipv6 : bool = True ,
                allow_localhost : bool = True, allow_None : bool = False) -> bool:
        try:
            obj._assert(value, allow_ipv4, allow_ipv6, allow_localhost, allow_None)
            return True
        except (TypeError, ValueError):
            return False
        
    @classmethod
    def isipv4(obj, value : str) -> bool:
        """
        Return whether a given value is a valid IP version 4 address.

        This validator is based on `WTForms IPAddress validator`_

        .. _WTForms IPAddress validator:
        https://github.com/wtforms/wtforms/blob/master/wtforms/validators.py

        Args:
            value (str): IP address string to validate, other types will raise unexpected errors (mostly attribute error)
        
        Returns:
            bool : True if conformant
        """
        groups = value.split(".")
        if (
            len(groups) != 4
            or any(not x.isdigit() for x in groups)
            or any(len(x) > 3 for x in groups)
        ):
            return False
        return all(0 <= int(part) < 256 for part in groups)
        
    
    @classmethod
    def isipv4cidr(obj, value : str) -> bool:
        """
        Return whether a given value is a valid CIDR-notated IP version 4
        address range.

        This validator is based on RFC4632 3.1.

        Args:
            value (str): IP address string to validate, other types will raise unexpected errors (mostly attribute error)
        
        Returns:
            bool : True if conformant
        """
        try:
            prefix, suffix = value.split('/', 2)
        except ValueError:
            return False
        if not obj.is_ipv4(prefix) or not suffix.isdigit():
            return False
        return 0 <= int(suffix) <= 32
    
    @classmethod
    def isipv6(obj, value : str) -> bool:
        """
        Return whether a given value is a valid IP version 6 address
        (including IPv4-mapped IPv6 addresses).

        This validator is based on `WTForms IPAddress validator`_.

        .. _WTForms IPAddress validator:
        https://github.com/wtforms/wtforms/blob/master/wtforms/validators.py

        Examples::

            >>> ipv6('abcd:ef::42:1')
            True

            >>> ipv6('::ffff:192.0.2.128')
            True

            >>> ipv6('::192.0.2.128')
            True

            >>> ipv6('abc.0.0.1')
            ValidationFailure(func=ipv6, args={'value': 'abc.0.0.1'})

        .. versionadded:: 0.2

        :param value: IP address string to validate
        """
        ipv6_groups = value.split(':')
        if len(ipv6_groups) == 1:
            return False
        ipv4_groups = ipv6_groups[-1].split('.')

        if len(ipv4_groups) > 1:
            if not obj.is_ipv4(ipv6_groups[-1]):
                return False
            ipv6_groups = ipv6_groups[:-1]
        else:
            ipv4_groups = []

        count_blank = 0
        for part in ipv6_groups:
            if not part:
                count_blank += 1
                continue
            try:
                num = int(part, 16)
            except ValueError:
                return False
            else:
                if not 0 <= num <= 65536 or len(part) > 4:
                    return False

        max_groups = 6 if ipv4_groups else 8
        part_count = len(ipv6_groups) - count_blank
        if count_blank == 0 and part_count == max_groups:
            # no :: -> must have size of max_groups
            return True
        elif count_blank == 1 and ipv6_groups[-1] and ipv6_groups[0] and part_count < max_groups:
            # one :: inside the address or prefix or suffix : -> filter least two cases
            return True
        elif count_blank == 2 and part_count < max_groups and (
                ((ipv6_groups[0] and not ipv6_groups[-1]) or (not ipv6_groups[0] and ipv6_groups[-1])) or ipv4_groups):
            # leading or trailing :: or : at end and begin -> filter last case
            # Check if it has ipv4 groups because they get removed from the ipv6_groups
            return True
        elif count_blank == 3 and part_count == 0:
            # :: is the address -> filter everything else
            return True
        return False

    @classmethod
    def isipv6cidr(obj, value : str) -> bool:
        """
        Returns whether a given value is a valid CIDR-notated IP version 6
        address range.

        This validator is based on RFC4632 3.1.

        Examples::

            >>> ipv6_cidr('::1/128')
            True

            >>> ipv6_cidr('::1')
            ValidationFailure(func=ipv6_cidr, args={'value': '::1'})
        """
        try:
            prefix, suffix = value.split('/', 2)
        except ValueError:
            return False
        if not obj.is_ipv6(prefix) or not suffix.isdigit():
            return False
        return 0 <= int(suffix) <= 128



class Number(Parameter):
    """
    A numeric parameter with a default value and optional bounds.

    There are two types of bounds: ``bounds`` and
    ``softbounds``. ``bounds`` are hard bounds: the parameter must
    have a value within the specified range.  The default bounds are
    (None,None), meaning there are actually no hard bounds.  One or
    both bounds can be set by specifying a value
    (e.g. bounds=(None,10) means there is no lower bound, and an upper
    bound of 10). Bounds are inclusive by default, but exclusivity
    can be specified for each bound by setting inclusive_bounds
    (e.g. inclusive_bounds=(True,False) specifies an exclusive upper
    bound).

    Using a default value outside the hard
    bounds, or one that is not numeric, results in an exception.

    As a special case, if allow_None=True (which is true by default if
    the parameter has a default of None when declared) then a value
    of None is also allowed.

    A separate function set_in_bounds() is provided that will
    silently crop the given value into the legal range, for use
    in, for instance, a GUI.

    ``softbounds`` are present to indicate the typical range of
    the parameter, but are not enforced. Setting the soft bounds
    allows, for instance, a GUI to know what values to display on
    sliders for the Number.

    Example of creating a Number::
        AB = Number(default=0.5, bounds=(None,10), softbounds=(0,1), doc='Distance from A to B.')

    """

    __slots__ = ['bounds', 'inclusive_bounds', 'crop_to_bounds', 'dtype', 'step']

    def __init__(self, default : typing.Optional[typing.Union[float, int]] = 0.0, *, bounds : typing.Optional[typing.Tuple] = None, 
            crop_to_bounds : bool = False, inclusive_bounds : typing.Tuple = (True,True), step : typing.Any = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.bounds = bounds
        self.crop_to_bounds = crop_to_bounds
        self.inclusive_bounds = inclusive_bounds
        self.dtype = (float, int)
        self.step = step

    def set_in_bounds(self, obj : typing.Union[Parameterized, typing.Any], value : typing.Union[float, int]) -> None:
        """
        Set to the given value, but cropped to be within the legal bounds.
        See crop_to_bounds for details on how cropping is done.
        """
        self._assert(value, self.dtype, None, (False, False), self.allow_None)
        bounded_value = self._crop_to_bounds(value) 
        super().__set__(obj, bounded_value)

    def _crop_to_bounds(self, value : typing.Union[int, float]) -> typing.Union[int, float]:
        """
        Return the given value cropped to be within the hard bounds
        for this parameter.

        If a numeric value is passed in, check it is within the hard
        bounds. If it is larger than the high bound, return the high
        bound. If it's smaller, return the low bound. In either case, the
        returned value could be None.  If a non-numeric value is passed
        in, set to be the default value (which could be None).  In no
        case is an exception raised; all values are accepted.
        """
        # Values outside the bounds are silently cropped to
        # be inside the bounds.
        assert self.bounds is not None, "Cannot crop to bounds when bounds is None"
        vmin, vmax = self.bounds
        incmin, incmax = self.inclusive_bounds
        if vmin is not None:
            if value < vmin:
                if incmin: 
                    return vmin
                else: 
                    return vmin + self.step 
        if vmax is not None:
            if value > vmax:
                if incmax:
                    return vmax
                else:
                    return vmax - self.step
        return value
    
    def validate_and_adapt(self, value: typing.Any) -> typing.Union[int, float]:
        self._assert(value, self.dtype, None if self.crop_to_bounds else self.bounds, 
                    self.inclusive_bounds, self.allow_None)
        if self.crop_to_bounds and self.bounds and value is not None:
            return self._crop_to_bounds(value)
        return value
        
    @classmethod
    def _assert(obj, value, dtype : typing.Tuple, bounds : typing.Optional[typing.Tuple] = None, 
               inclusive_bounds : typing.Tuple[bool, bool] = (True, True), allow_None : bool = False):
        if allow_None and value is None:
            return
        if dtype is None:
            if not obj.isnumber(value):
                raise_TypeError("given value not of number type, but type {}.".format(type(value)), 
                                obj)
        elif not isinstance(value, dtype):
            raise_TypeError("given value not of type {}, but type {}.".format(dtype, type(value)), obj)
        if bounds:
            vmin, vmax = bounds
            incmin, incmax = inclusive_bounds   
            if vmax is not None:
                if incmax is True:
                    if not value <= vmax:
                        raise_ValueError("given value must be at most {}, not {}.".format(vmax, value), obj)
                else:
                    if not value < vmax:
                        raise_ValueError("Parameter must be less than {}, not {}.".format(vmax, value), obj)

            if vmin is not None:
                if incmin is True:
                    if not value >= vmin:
                        raise_ValueError("Parameter must be at least {}, not {}.".format(vmin, value), obj)
                else:
                    if not value > vmin:
                        raise_ValueError("Parameter must be greater than {}, not {}.".format(vmin, value), obj)
            return value 
    
    def _validate_step(self, value : typing.Any) -> None:
        if value is not None:
            if self.dtype: 
                if not isinstance(value, self.dtype):
                    raise_ValueError("Step can only be None or {}, not type {}.".format(self.dtype, type(value)), self)
            elif not self.isnumber(self.step):
                raise_ValueError("Step can only be None or numeric value, not type {}.".format(type(value)), self)

    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        if slot == 'step': 
            self._validate_step(value)
        return super()._post_slot_set(slot, old, value)

    @classmethod
    def isinstance(obj, value, dtype : typing.Tuple, bounds : typing.Optional[typing.Tuple] = None, 
               inclusive_bounds : typing.Tuple[bool, bool] = (True, True), allow_None : bool = False):
        try:
            obj._assert(value, dtype, bounds, inclusive_bounds, allow_None)
            return True
        except (ValueError, TypeError):
            return False 
    	
    @classmethod
    def isnumber(cls, value : typing.Any) -> bool:
        if isinstance(value, numbers.Number): return True
        # The extra check is for classes that behave like numbers, such as those
        # found in numpy, gmpy, etc.
        elif (hasattr(value, '__int__') and hasattr(value, '__add__')): return True
        # This is for older versions of gmpy
        elif hasattr(value, 'qdiv'): return True
        else: return False



class Integer(Number):
    """Numeric Parameter required to be an Integer"""

    def __init__(self, default : typing.Optional[int] = 0, *, bounds : typing.Optional[typing.Tuple] = None, 
            crop_to_bounds : bool = False, inclusive_bounds : typing.Tuple = (True,True), step : typing.Any = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, bounds=bounds, crop_to_bounds=crop_to_bounds, inclusive_bounds=inclusive_bounds, 
            doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.dtype = (int,)

    def _validate_step(self, step : int):
        if step is not None and not isinstance(step, int):
            raise_ValueError("Step can only be None or an integer value, not type {}".format(type(step)), self)



class Boolean(Parameter):
    """Binary or tristate Boolean Parameter."""

    def __init__(self, default : typing.Optional[bool] = False, *, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)

    def validate_and_adapt(self, value : typing.Any) -> bool:
        if self.allow_None and value is None:
            return 
        elif not isinstance(value, bool): 
            raise_ValueError("given value not boolean type, but type {}".format(type(value)), self)
        return value



class Iterable(Parameter):
    """A tuple or list Parameter (e.g. ('a',7.6,[3,5])) with a fixed tuple length."""

    __slots__ = ['bounds', 'length', 'item_type', 'dtype']

    def __init__(self, default : typing.Any, *, bounds : typing.Optional[typing.Tuple[int, int]] = None, 
            length : typing.Optional[int] = None, item_type : typing.Optional[typing.Tuple] = None, deepcopy_default : bool = False, 
            allow_None : bool = False, doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            per_instance_descriptor : bool = False,  class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        """
        Initialize a tuple parameter with a fixed length (number of
        elements).  The length is determined by the initial default
        value, if any, and must be supplied explicitly otherwise.  The
        length is not allowed to change after instantiation.
        """
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.bounds = bounds 
        self.length = length
        self.item_type = item_type
        self.dtype = (list, tuple)

    def validate_and_adapt(self, value: typing.Any) -> typing.Union[typing.List, typing.Tuple]:
        self._assert(value, self.bounds, self.length, self.dtype, self.item_type, self.allow_None)
        return value
        
    @classmethod
    def _assert(obj, value : typing.Any, bounds : typing.Optional[typing.Tuple[int, int]] = None, 
            length : typing.Optional[int] = None, dtype :  typing.Union[type, typing.Tuple] = (list, tuple), 
            item_type : typing.Any = None, allow_None : bool = False) -> None:
        if value is None and allow_None:
            return
        if not isinstance(value, dtype):
            raise_ValueError("given value not of iterable type {}, but {}.".format(dtype, type(value)), obj)
        if bounds is not None:
            if not (len(value) >= bounds[0] and len(value) <= bounds[1]):
                raise_ValueError("given iterable is not of the correct length ({} instead of between {} and {}).".format(
                                len(value), 0 if not bounds[0] else bounds[0], bounds[1]), obj) 
        elif length is not None and len(value) != length:
            raise_ValueError("given iterable is not of correct length ({} instead of {})".format(len(value), length), 
                             obj)
        if item_type is not None: 
            for val in value:
                if not isinstance(val, item_type):
                    raise_TypeError("not all elements of given iterable of item type {}, found object of type {}".format(
                        item_type, type(val)), obj)

    @classmethod
    def isinstance(obj, value : typing.Any, bounds : typing.Optional[typing.Tuple[int, int]], 
                length : typing.Optional[int] = None, dtype : typing.Union[type, typing.Tuple] = (list, tuple), 
                item_type : typing.Any = None, allow_None : bool = False) -> bool:
        try: 
            obj._assert(value, bounds, length, dtype, item_type, allow_None)
            return True 
        except (ValueError, TypeError):
            return False



class Tuple(Iterable):

    __slots__ = ['accept_list', 'accept_item']

    def __init__(self, default : typing.Any, *, bounds : typing.Optional[typing.Tuple[int, int]] = None, 
            length: typing.Optional[int] = None, item_type : typing.Optional[typing.Tuple] = None, 
            accept_list : bool = False, accept_item : bool = False, deepcopy_default : bool = False, 
            allow_None : bool = False, doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False,
            per_instance_descriptor : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, bounds=bounds, length=length, item_type=item_type, doc=doc, constant=constant, 
            readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.accept_list = accept_list
        self.accept_item = accept_item
        self.dtype = (tuple,) # re-assigned
      
    def validate_and_adapt(self, value: typing.Any) -> typing.Tuple:
        if self.accept_list and isinstance(value, list):
            value = tuple(value) 
        if self.accept_item and not isinstance(value, (list, tuple, type(None))):
            value = (value,)
        self._assert(value, self.bounds, self.length, self.dtype, self.item_type, self.allow_None)
        return value 
    
    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return list(value) # As JSON has no tuple representation

    @classmethod
    def deserialize(cls, value):
        if value == 'null':
            return None
        return tuple(value) # As JSON has no tuple representation



class List(Iterable):
    """
    Parameter whose value is a list of objects, usually of a specified type.

    The bounds allow a minimum and/or maximum length of
    list to be enforced.  If the item_type is non-None, all
    items in the list are checked to be of that type.

    `class_` is accepted as an alias for `item_type`, but is
    deprecated due to conflict with how the `class_` slot is
    used in Selector classes.
    """

    __slots__ = ['accept_tuple']

    def __init__(self, default: typing.Any, *, bounds : typing.Optional[typing.Tuple[int, int]] = None, 
            length : typing.Optional[int] = None, item_type : typing.Optional[typing.Tuple] = None, 
            accept_tuple : bool = False, deepcopy_default : bool = False, 
            allow_None : bool = False, doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            per_instance_descriptor : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None,
            fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None,
            precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, bounds=bounds, length=length, item_type=item_type,
            doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, 
            per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.accept_tuple = accept_tuple
        self.dtype = list

    def validate_and_adapt(self, value: typing.Any) -> typing.Tuple:
        if self.accept_tuple and isinstance(value, tuple):
            value = list(value)
        self._assert(value, self.bounds, self.length, self.dtype, self.item_type, self.allow_None)
        return value 



class Callable(Parameter):
    """
    Parameter holding a value that is a callable object, such as a function.

    A keyword argument instantiate=True should be provided when a
    function object is used that might have state.  On the other hand,
    regular standalone functions cannot be deepcopied as of Python
    2.4, so instantiate must be False for those values.
    """

    def validate_and_adapt(self, value : typing.Any) -> typing.Callable:
        if (self.allow_None and value is None) or callable(value):
            return value
        raise_ValueError("given value not a callable object, but type {}.".format(type(value)), self)
       


class Composite(Parameter):
    """
    A Parameter that is a composite of a set of other attributes of the class.

    The constructor argument 'attribs' takes a list of attribute
    names, which may or may not be Parameters.  Getting the parameter
    returns a list of the values of the constituents of the composite,
    in the order specified.  Likewise, setting the parameter takes a
    sequence of values and sets the value of the constituent
    attributes.

    This Parameter type has not been tested with watchers and
    dependencies, and may not support them properly.
    """

    __slots__ = ['attribs']

    def __init__(self, attribs : typing.List[typing.Union[str, Parameter]], *, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(None, doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, 
            per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.attribs = [] 
        if attribs is not None:
            for attrib in attribs:
                if isinstance(attrib, Parameter):
                    self.attribs.append(attrib.name)
                else:
                    self.attribs.append(attrib)            
        
    def __get__(self, obj, objtype) -> typing.List[typing.Any]:
        """
        Return the values of all the attribs, as a list.
        """
        return [getattr(obj, attr) for attr in self.attribs]

    def validate_and_adapt(self, value):
        if not len(value) == len(self.attribs):
            raise_ValueError("Compound parameter got the wrong number of values (needed {}, but got {}).".format(
                        len(self.attribs), len(value)), self)
        return value

    def _post_setter(self, obj, val):
        for a, v in zip(self.attribs, val):
            setattr(obj, a, v)



class SelectorBase(Parameter):
    """
    Parameter whose value must be chosen from a list of possibilities.

    Subclasses must implement get_range().
    """

    __abstract = True

    @property
    def range(self):
        raise NotImplementedError("get_range() must be implemented in subclasses.")



class Selector(SelectorBase):
    """
    Parameter whose value must be one object from a list of possible objects.

    By default, if no default is specified, picks the first object from
    the provided set of objects, as long as the objects are in an
    ordered data collection.

    check_on_set restricts the value to be among the current list of
    objects. By default, if objects are initially supplied,
    check_on_set is True, whereas if no objects are initially
    supplied, check_on_set is False. This can be overridden by
    explicitly specifying check_on_set initially.

    If check_on_set is True (either because objects are supplied
    initially, or because it is explicitly specified), the default
    (initial) value must be among the list of objects (unless the
    default value is None).

    The list of objects can be supplied as a list (appropriate for
    selecting among a set of strings, or among a set of objects with a
    "name" parameter), or as a (preferably ordered) dictionary from
    names to objects.  If a dictionary is supplied, the objects
    will need to be hashable so that their names can be looked
    up from the object value.
    """

    __slots__ = ['objects', 'names']

    # Selector is usually used to allow selection from a list of
    # existing objects, therefore instantiate is False by default.
    def __init__(self, *, objects : typing.List[typing.Any], default : typing.Any, empty_default : bool = False,  
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
            fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
            precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        if objects is None:
            objects = []
            autodefault = None
        elif isinstance(objects, collections.abc.Mapping):
            self.names = objects
            self.objects = list(objects.values())
            autodefault = self.objects[0]
        elif isinstance(objects, (list, tuple)):
            self.names = None
            self.objects = objects
            autodefault = objects[0]
        else:
            raise TypeError("objects should be a list, tuple, mapping or None. Given type : {}".format(type(objects)))
        default = autodefault if (not empty_default and default is None) else default

    def validate_and_adapt(self, value: typing.Any) -> typing.Any:
        """
        val must be None or one of the objects in self.objects.
        """
        if not (value in self.objects or (self.allow_None and value is None)):
            raise_ValueError("given value not in list of possible objects, valid options include {}".format(
                get_iterable_printfriendly_repr(self.objects)), self)
        return value

    @property
    def range(self):
        """
        Return the possible objects to which this parameter could be set.

        (Returns the dictionary {object.name:object}.)
        """
        if self.names is not None:
            return named_objs(self.objects, self.names)
        else:
            return self.objects



class ClassSelector(SelectorBase):
    """
    Parameter allowing selection of either a subclass or an instance of a given set of classes.
    By default, requires an instance, but if isinstance=False, accepts a class instead.
    Both class and instance values respect the instantiate slot, though it matters only
    for isinstance=True.
    """

    __slots__ = ['class_', 'isinstance']

    def __init__(self, *, class_ , default : typing.Any, isinstance : bool = True, deepcopy_default : bool = False,  
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default, 
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, precedence=precedence)
        self.class_ = class_
        self.isinstance = isinstance

    def _get_class_name(self):
        if isinstance(self.class_, tuple):
            return ('(%s)' % ', '.join(cl.__name__ for cl in self.class_))
        else:
            return self.class_.__name__

    def validate_and_adapt(self, value): 
        if (value is None and self.allow_None):
            return
        if self.isinstance:
            if not isinstance(value, self.class_):
                raise_ValueError("{} parameter {} value must be an instance of {}, not {}.".format(
                    self.__class__.__name__, self.name, self._get_class_name(), value), self)
        else:
            if not issubclass(value, self.class_):
               raise_ValueError("{} parameter {} must be a subclass of {}, not {}.".format(
                    self.__class__.__name__, self.name, self._get_class_name(), value.__name__), self)
        return value

    @property
    def range(self):
        """
        Return the possible types for this parameter's value.

        (I.e. return `{name: <class>}` for all classes that are
        concrete_descendents() of `self.class_`.)

        Only classes from modules that have been imported are added
        (see concrete_descendents()).
        """
        classes = self.class_ if isinstance(self.class_, tuple) else (self.class_,)
        all_classes = {}
        for cls in classes:
            all_classes.update(concrete_descendents(cls))
        d = OrderedDict((name, class_) for name,class_ in all_classes.items())
        if self.allow_None:
            d['None'] = None
        return d



class TupleSelector(Selector):
    """
    Variant of Selector where the value can be multiple objects from
    a list of possible objects.
    """

    # Changed from ListSelector. Iterables need to be frozen to prevent spurious addition. 
    # To prevent duplicates, use frozen set selector

    __slots__ = ['accept_list']

    def __init__(self, *, objects : typing.List, default : typing.Any, accept_list : bool = True,
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(objects=objects, default=default, empty_default=True, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.accept_list = accept_list

    def validate_and_adapt(self, value : typing.Any):
        if value is None and self.allow_None:
            return
        if value not in self.objects: 
            # i.e. without iterating, we check that the value is not present in the objects
            # This is useful to have list or iterables themselves as part of objects
            # let objects = [[1,2], 3 ,4], if [1,2] is passed, then we should try to accept it plainly before moving to iterating
            # and checking
            if isinstance(value, list) and self.accept_list:
                value = tuple(value)
            if not isinstance(value, tuple):
                raise_ValueError(f"object {value} not specified as a valid member of list of objects.", self)
            else:
                for obj in value:
                    if obj not in self.objects: 
                        raise_ValueError("object {} not specified as a valid member of list of objects.".format(obj), self)
        return value


# For portable code:
#   - specify paths in unix (rather than Windows) style;
#   - use resolve_path(path_to_file=True) for paths to existing files to be read,
#   - use resolve_path(path_to_file=False) for paths to existing folders to be read,
#     and normalize_path() for paths to new files to be written.

class resolve_path(ParameterizedFunction):
    """
    Find the path to an existing file, searching the paths specified
    in the search_paths parameter if the filename is not absolute, and
    converting a UNIX-style path to the current OS's format if
    necessary.

    To turn a supplied relative path into an absolute one, the path is
    appended to paths in the search_paths parameter, in order, until
    the file is found.

    An IOError is raised if the file is not found.

    Similar to Python's os.path.abspath(), except more search paths
    than just os.getcwd() can be used, and the file must exist.
    """

    search_paths = List(default=[os.getcwd()], doc="""
        Prepended to a non-relative path, in order, until a file is
        found.""")

    path_to_file = Boolean(default=True, 
                           allow_None=True, doc="""
        String specifying whether the path refers to a 'File' or a
        'Folder'. If None, the path may point to *either* a 'File' *or*
        a 'Folder'.""")

    def __call__(self, path : str, **params) -> str:
        p = ParamOverrides(self, params)
        path = os.path.normpath(path)
        ftype = "File" if p.path_to_file is True \
            else "Folder" if p.path_to_file is False else "Path"

        if not p.search_paths:
            p.search_paths = [os.getcwd()]

        if os.path.isabs(path):
            if ((p.path_to_file is None  and os.path.exists(path)) or
                (p.path_to_file is True  and os.path.isfile(path)) or
                (p.path_to_file is False and os.path.isdir( path))):
                return path
            raise IOError("%s '%s' not found." % (ftype,path))

        else:
            paths_tried = []
            for prefix in p.search_paths:
                try_path = os.path.join(os.path.normpath(prefix), path)

                if ((p.path_to_file is None  and os.path.exists(try_path)) or
                    (p.path_to_file is True  and os.path.isfile(try_path)) or
                    (p.path_to_file is False and os.path.isdir( try_path))):
                    return try_path

                paths_tried.append(try_path)

            raise IOError(ftype + " " + os.path.split(path)[1] + " was not found in the following place(s): " + str(paths_tried) + ".")


class normalize_path(ParameterizedFunction):
    """
    Convert a UNIX-style path to the current OS's format,
    typically for creating a new file or directory.

    If the path is not already absolute, it will be made absolute
    (using the prefix parameter).

    Should do the same as Python's os.path.abspath(), except using
    prefix rather than os.getcwd).
    """

    prefix = String(default=os.getcwd(),doc="""
        Prepended to the specified path, if that path is not
        absolute.""")

    def __call__(self, path : str = "", **params):
        p = ParamOverrides(self,params)

        if not os.path.isabs(path):
            path = os.path.join(os.path.normpath(p.prefix), path)

        return os.path.normpath(path)



class Path(Parameter):
    """
    Parameter that can be set to a string specifying the path of a file or folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system. Please use
    the Filename or Foldername classes if you require discrimination
    between the two possibilities.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
       search_paths is not None);

    or

    * any of the paths searched by resolve_path() (if search_paths
      is None).
    """

    __slots__ = ['search_paths']

    def __init__(self, default : typing.Any = '', *, search_paths : typing.Optional[str] = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False, 
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        if isinstance(search_paths, str):
            self.search_paths = [search_paths]
        elif isinstance(search_paths, list):
            self.search_paths = search_paths
        else: 
            self.search_paths = []

    def _resolve(self, path):
        return resolve_path(path, path_to_file=None, search_paths=self.search_paths)

    def validate_and_adapt(self, value : typing.Any) -> typing.Any:
        if value is None and self.allow_None:
            return 
        else:
            return self._resolve(value)
         
    def __get__(self, obj, objtype) -> str:
        """
        Return an absolute, normalized path (see resolve_path).
        """
        raw_path = super().__get__(obj, objtype)
        return None if raw_path is None else self._resolve(raw_path)

    def __getstate__(self):
        # don't want to pickle the search_paths
        state = super().__getstate__()
        if 'search_paths' in state:
            state['search_paths'] = []
        return state



class Filename(Path):
    """
    Parameter that can be set to a string specifying the path of a file.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
      search_paths is not None);

    or

    * any of the paths searched by resolve_path() (if search_paths
      is None).
    """

    def _resolve(self, path):
        return resolve_path(path, path_to_file=True, search_paths=self.search_paths)


class Foldername(Path):
    """
    Parameter that can be set to a string specifying the path of a folder.

    The string should be specified in UNIX style, but it will be
    returned in the format of the user's operating system.

    The specified path can be absolute, or relative to either:

    * any of the paths specified in the search_paths attribute (if
      search_paths is not None);

    or

    * any of the paths searched by resolve_dir_path() (if search_paths
      is None).
    """

    def _resolve(self, path):
        return resolve_path(path, path_to_file=False, search_paths=self.search_paths)



def abbreviate_paths(pathspec,named_paths):
    """
    Given a dict of (pathname,path) pairs, removes any prefix shared by all pathnames.
    Helps keep menu items short yet unambiguous.
    """

    prefix = os.path.commonprefix([os.path.dirname(name)+os.path.sep for name in named_paths.keys()]+[pathspec])
    return OrderedDict([(name[len(prefix):],path) for name,path in named_paths.items()])



class FileSelector(Selector):
    """
    Given a path glob, allows one file to be selected from those matching.
    """
    __slots__ = ['path']

    def __init__(self, default : typing.Any, *, objects : typing.List, path : str = "", 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False, 
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, objects=objects, empty_default=True, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.path = path # update is automatically called

    def _post_slot_set(self, slot: str, old : typing.Any, value : typing.Any) -> None:
        super()._post_slot_set(slot, old, value)
        if slot == 'path':
            self.update()

    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default in self.objects:
            return
        self.default = self.objects[0] if self.objects else None

    @property
    def range(self):
        return abbreviate_paths(self.path, super().range)



class MultiFileSelector(FileSelector):
    """
    Given a path glob, allows multiple files to be selected from the list of matches.
    """
    __slots__ = ['path']

    def __init__(self, default : typing.Any, *, path : str = "", 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False, 
            label : typing.Optional[str] = None, per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, objects=None, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, 
            fdel=fdel, precedence=precedence)
       
    def update(self):
        self.objects = sorted(glob.glob(self.path))
        if self.default and all([o in self.objects for o in self.default]):
            return
        self.default = self.objects



class Date(Number):
    """
    Date parameter of datetime or date type.
    """

    def __init__(self, default, *, bounds : typing.Union[typing.Tuple, None] = None, 
            crop_to_bounds : bool = False, inclusive_bounds : typing.Tuple = (True,True), step : typing.Any = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, bounds=bounds, crop_to_bounds=crop_to_bounds,
            inclusive_bounds=inclusive_bounds, step=step, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.dtype = dt_types

    def _validate_step(self, val):
        if self.step is not None and not isinstance(self.step, dt_types):
            raise ValueError(f"Step can only be None, a datetime or datetime type, not type {type(val)}")

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        if not isinstance(value, (dt.datetime, dt.date)): # i.e np.datetime64, note numpy is imported only on requirement
            value = value.astype(dt.datetime)
        return value.strftime("%Y-%m-%dT%H:%M:%S.%f")

    @classmethod
    def deserialize(cls, value):
        if value == None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")



class CalendarDate(Number):
    """
    Parameter specifically allowing dates (not datetimes).
    """

    def __init__(self, default, *, bounds : typing.Union[typing.Tuple, None] = None, 
            crop_to_bounds : bool = False, inclusive_bounds : typing.Tuple = (True,True), step : typing.Any = None, 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, bounds=bounds, crop_to_bounds=crop_to_bounds,
            inclusive_bounds=inclusive_bounds, step=step, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)
        self.dtype = dt.date

    def _validate_step(self, step):
        if step is not None and not isinstance(step, self.dtype):
            raise ValueError("Step can only be None or a date type.")

    @classmethod
    def serialize(cls, value):
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")

    @classmethod
    def deserialize(cls, value):
        if value is None:
            return None
        return dt.datetime.strptime(value, "%Y-%m-%d").date()



class CSS3Color(Parameter):
    """
    Color parameter defined as a hex RGB string with an optional #
    prefix or (optionally) as a CSS3 color name.
    """

    # CSS3 color specification https://www.w3.org/TR/css-color-3/#svg-color
    _named_colors = [ 'aliceblue', 'antiquewhite', 'aqua',
        'aquamarine', 'azure', 'beige', 'bisque', 'black',
        'blanchedalmond', 'blue', 'blueviolet', 'brown', 'burlywood',
        'cadetblue', 'chartreuse', 'chocolate', 'coral',
        'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'darkblue',
        'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey',
        'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen',
        'darkorange', 'darkorchid', 'darkred', 'darksalmon',
        'darkseagreen', 'darkslateblue', 'darkslategray',
        'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink',
        'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue',
        'firebrick', 'floralwhite', 'forestgreen', 'fuchsia',
        'gainsboro', 'ghostwhite', 'gold', 'goldenrod', 'gray',
        'grey', 'green', 'greenyellow', 'honeydew', 'hotpink',
        'indianred', 'indigo', 'ivory', 'khaki', 'lavender',
        'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue',
        'lightcoral', 'lightcyan', 'lightgoldenrodyellow',
        'lightgray', 'lightgrey', 'lightgreen', 'lightpink',
        'lightsalmon', 'lightseagreen', 'lightskyblue',
        'lightslategray', 'lightslategrey', 'lightsteelblue',
        'lightyellow', 'lime', 'limegreen', 'linen', 'magenta',
        'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid',
        'mediumpurple', 'mediumseagreen', 'mediumslateblue',
        'mediumspringgreen', 'mediumturquoise', 'mediumvioletred',
        'midnightblue', 'mintcream', 'mistyrose', 'moccasin',
        'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab',
        'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen',
        'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff',
        'peru', 'pink', 'plum', 'powderblue', 'purple', 'red',
        'rosybrown', 'royalblue', 'saddlebrown', 'salmon',
        'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',
        'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow',
        'springgreen', 'steelblue', 'tan', 'teal', 'thistle',
        'tomato', 'turquoise', 'violet', 'wheat', 'white',
        'whitesmoke', 'yellow', 'yellowgreen']

    __slots__ = ['allow_named']

    def __init__(self, default, *, allow_named : bool = True,  doc : typing.Optional[str] = None, constant : bool = False, 
            readonly : bool = False, allow_None : bool = False,
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        super().__init__(default=default, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel,  
            precedence=precedence)
        self.allow_named = allow_named
    
    def validate_and_adapt(self, value : typing.Any):
        if (self.allow_None and value is None):
            return
        if not isinstance(value, str):
            raise ValueError("Color parameter %r expects a string value, "
                             "not an object of type %s." % (self.name, type(value)))
        if self.allow_named and value in self._named_colors:
            return 
        is_hex = re.match('^#?(([0-9a-fA-F]{2}){3}|([0-9a-fA-F]){3})$', value)
        if not is_hex:
            raise ValueError("Color '%s' only takes RGB hex codes "
                                 "or named colors, received '%s'." % (self.name, value))
      


class Range(Tuple):
    """
    A numeric range with optional bounds and softbounds.
    """

    __slots__ = ['bounds', 'inclusive_bounds', 'softbounds', 'step']

    def __init__(self, default : typing.Optional[typing.Tuple] = None, *, bounds: typing.Optional[typing.Tuple[int, int]] = None, 
            length : typing.Optional[int] = None, item_type : typing.Optional[typing.Tuple] = None, 
            softbounds=None, inclusive_bounds=(True,True), step=None, 
            doc : typing.Optional[str] = None, constant : bool = False, 
            readonly : bool = False, allow_None : bool = False, label : typing.Optional[str] = None,  
            per_instance_descriptor : bool = False, deepcopy_default : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        self.inclusive_bounds = inclusive_bounds
        self.softbounds = softbounds
        self.step = step
        super().__init__(default=default, bounds=bounds, item_type=item_type, length=length, doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, 
            deepcopy_default=deepcopy_default, class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            precedence=precedence)

    def validate_and_adapt(self, value : typing.Any) -> typing.Tuple:
        raise NotImplementedError("Range validation not implemented")
        super()._validate(val)
        self._validate_bounds(val, self.bounds, self.inclusive_bounds)

    def _validate_bounds(self, val, bounds, inclusive_bounds):
        if bounds is None or (val is None and self.allow_None):
            return
        vmin, vmax = bounds
        incmin, incmax = inclusive_bounds
        for bound, v in zip(['lower', 'upper'], val):
            too_low = (vmin is not None) and (v < vmin if incmin else v <= vmin)
            too_high = (vmax is not None) and (v > vmax if incmax else v >= vmax)
            if too_low or too_high:
                raise ValueError("Range parameter %r's %s bound must be in range %s."
                                 % (self.name, bound, self.rangestr()))

    @property
    def rangestr(self):
        vmin, vmax = self.bounds
        incmin, incmax = self.inclusive_bounds
        incmin = '[' if incmin else '('
        incmax = ']' if incmax else ')'
        return '%s%s, %s%s' % (incmin, vmin, vmax, incmax)



class DateRange(Range):
    """
    A datetime or date range specified as (start, end).

    Bounds must be specified as datetime or date types (see param.dt_types).
    """

    def _validate_value(self, val, allow_None):
        # Cannot use super()._validate_value as DateRange inherits from
        # NumericTuple which check that the tuple values are numbers and
        # datetime objects aren't numbers.
        if allow_None and val is None:
            return

        if not isinstance(val, tuple):
            raise ValueError("DateRange parameter %r only takes a tuple value, "
                             "not %s." % (self.name, type(val).__name__))
        for n in val:
            if isinstance(n, dt_types):
                continue
            raise ValueError("DateRange parameter %r only takes date/datetime "
                             "values, not type %s." % (self.name, type(n).__name__))

        start, end = val
        if not end >= start:
            raise ValueError("DateRange parameter %r's end datetime %s "
                             "is before start datetime %s." %
                             (self.name, val[1], val[0]))

    @classmethod
    def serialize(cls, value):
        if value is None:
            return 'null'
        # List as JSON has no tuple representation
        serialized = []
        for v in value:
            if not isinstance(v, (dt.datetime, dt.date)): # i.e np.datetime64
                v = v.astype(dt.datetime)
            # Separate date and datetime to deserialize to the right type.
            if type(v) == dt.date:
                v = v.strftime("%Y-%m-%d")
            else:
                v = v.strftime("%Y-%m-%dT%H:%M:%S.%f")
            serialized.append(v)
        return serialized

    def deserialize(cls, value):
        if value == 'null':
            return None
        deserialized = []
        for v in value:
            # Date
            if len(v) == 10:
                v = dt.datetime.strptime(v, "%Y-%m-%d").date()
            # Datetime
            else:
                v = dt.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%f")
            deserialized.append(v)
        # As JSON has no tuple representation
        return tuple(deserialized)



class CalendarDateRange(Range):
    """
    A date range specified as (start_date, end_date).
    """
    def _validate_value(self, val, allow_None):
        if allow_None and val is None:
            return

        for n in val:
            if not isinstance(n, dt.date):
                raise ValueError("CalendarDateRange parameter %r only "
                                 "takes date types, not %s." % (self.name, val))

        start, end = val
        if not end >= start:
            raise ValueError("CalendarDateRange parameter %r's end date "
                             "%s is before start date %s." %
                             (self.name, val[1], val[0]))

    @classmethod
    def serialize(cls, value):
        if value is None:
            return 'null'
        # As JSON has no tuple representation
        return [v.strftime("%Y-%m-%d") for v in value]

    @classmethod
    def deserialize(cls, value):
        if value == 'null':
            return None
        # As JSON has no tuple representation
        return tuple([dt.datetime.strptime(v, "%Y-%m-%d").date() for v in value])
    



def get_typed_iterable_bounds(bounds : tuple) -> tuple:
    if bounds[0] is None and bounds[1] is None:
        bounds = (0, 2*sys.maxsize + 1)
    elif bounds[0] is None: 
        bounds = (0, bounds[1])
    elif bounds[1] is None:
        bounds = (bounds[0], 2*sys.maxsize + 1)
    return bounds


class BaseConstrainedList(collections.abc.MutableSequence):

    # Need to check mul
    
    def __init__(self, default : typing.List[typing.Any], *, bounds : tuple = (0, None), 
                constant : bool = False, skip_validate : bool = False) -> None:
        super().__init__()
        self.constant = constant
        self.bounds   = get_typed_iterable_bounds(bounds)
        if not skip_validate:
            self._validate_for_set(default)    
        self._inner = default
  
    def _validate_for_set(self, value : typing.Any) -> None:
        self._validate_value(value)
        self._validate_bounds_for_set(value)
        self._validate_items(value)

    def _validate_for_extension(self, value : typing.List) -> None:
        if self.constant:
            raise ValueError(f"List {get_iterable_printfriendly_repr(self._inner)} is a constant, cannot be modified.")
        self._validate_value(value)
        self._validate_bounds_for_extension(value)
        self._validate_items(value)

    def _validate_for_insertion(self, value : typing.Any) -> None:
        if self.constant:
            raise ValueError(f"List {get_iterable_printfriendly_repr(self._inner)} is a constant, cannot be modified.")
        self._validate_bounds_for_extension()
        self._validate_item(value)

    def _validate_value(self, value : typing.Any) -> None:
        if not isinstance(value, list):
            raise TypeError(f"Given value for a constrained list is not a list, but type {type(value)}") 
           
    def _validate_items(self, value : typing.Any) -> None:
        raise NotImplementedError("Please implement _validate_item in the child of BaseConstrainedList.")

    def _validate_item(self, value : typing.Any):
        raise NotImplementedError("Please implement _validate_single_item in the child of BaseConstrainedList.")

    def _validate_bounds_for_set(self, value : typing.Any) -> None:
        if not (value.__len__() >= self.bounds[0] and value.__len__() <= self.bounds[1]):
            raise ValueError(wrap_error_text(
                f"""given list {get_iterable_printfriendly_repr(value)} has length out of bounds {self.bounds}. 
                given length : {value.__len__()}"""))
               
    def _validate_bounds_for_extension(self,  value : typing.Any = [None]) -> None:
        if not (self._inner.__len__() + value.__len__() >= self.bounds[0] and 
                            self._inner.__len__() + value.__len__() <= self.bounds[1]):
            raise ValueError(wrap_error_text(
                f"""given list for extending {get_iterable_printfriendly_repr(value)} extends existing list longer 
                than bounds {self.bounds}. given length : {self._inner.__len__() + value.__len__()}"""))         

    def __len__(self) -> int:
        return self._inner.__len__()

    def __iter__(self) -> typing.Any:
        return self._inner.__iter__()

    def __str__(self) -> str:
        return self._inner.__str__()

    def __contains__(self, item : typing.Any) -> bool:
        return item in self._inner

    def __getitem__(self, index : int):
        return self._inner[index]

    def __setitem__(self, index : int, value : typing.Any) -> None:
        if self.constant:
            raise ValueError(f"List {get_iterable_printfriendly_repr(self._inner)} is a constant, cannot be modified.")
        self._validate_item(value)
        self._inner[index] = value

    def __delitem__(self, index : int) -> None:
        del self._inner[index]

    def __repr__(self) -> str:
        return self._inner.__repr__()
    
    def __imul__(self, value : typing.Any) -> typing.List:
        return self._inner.__imul__(value)

    def __mul__(self, value : typing.Any) -> typing.List:
        return self._inner.__mul__(value)

    def __sizeof__(self) -> int:
        return self._inner.__sizeof__()

    def __lt__(self, __x : typing.List[typing.Any]) -> bool:
        return self._inner.__lt__(__x)
    
    def __le__(self, __x : typing.List[typing.Any]) -> bool:
        return self._inner.__le__(__x)
    
    def __eq__(self, __x : typing.List[typing.Any]) -> bool:  
        return self._inner.__eq__(__x)
    
    def __ne__(self, __x : typing.List[typing.Any]) -> bool:
        return self._inner.__ne__(__x)
    
    def __gt__(self, __x : typing.List[typing.Any]) -> bool:
        return  self._inner.__gt__(__x)
    
    def __ge__(self, __x : typing.List[typing.Any]) -> bool:
        return self._inner.__ge__(__x)
       
    def __rmul__(self, __n : int) -> typing.List:
        return self._inner.__rmul__(__n)

    def __reversed__(self) -> typing.Iterator:
        return self._inner.__reversed__()

    def __add__(self, __x : typing.List[typing.Any]) -> typing.List: 
        if isinstance(__x, self.__class__):
            return self._inner.__add__(__x._inner)
        else:
            return self._inner.__add__(__x)

    def __iadd__(self, values : typing.List[typing.Any] ) -> typing.List:
        raise NotImplementedError("Please implement __iadd__ in the child of BaseConstrainedList.")

    def insert(self, __index : int, __object : typing.Any) -> None:
        self._validate_for_insertion(__object)
        self._inner.insert(__index, __object)

    def append(self, __object : typing.Any) -> None:
        self._validate_for_insertion(__object)
        self._inner.append(__object)
        
    def extend(self, __iterable) -> None:
        self._validate_for_extension(__iterable)
        self._inner.extend(__iterable)

    def reverse(self) -> None:
        self._inner.reverse()
    
    def pop(self, __index: int) -> typing.Any:
        return self._inner.pop(__index)

    def count(self, __value : typing.Any) -> int:
        return self._inner.count(__value)

    def clear(self) -> None: 
        self._inner.clear()

    def index(self, __value : typing.Any, __start : int, __stop : int) -> int:
        return self._inner.index(__value, __start, __stop)

    def remove(self, __value : typing.Any) -> None:
        self._inner.remove(__value)

    def sort(self, key : typing.Any, reverse : bool):
        self._inner.sort(key=key, reverse=reverse)

    def copy(self, return_as_typed_list : bool = False):
        raise NotImplementedError("Please implement copy() in the child of BaseConstrainedList.")


       
class TypeConstrainedList(BaseConstrainedList):
 
    def __init__(self, default : typing.List, *, item_type : typing.Any = None, 
                bounds : tuple = (0,None), constant : bool = False, skip_validate : bool = False) -> None:
        self.item_type = item_type
        super().__init__(default=default, bounds=bounds, constant=constant, skip_validate=skip_validate)
        
    def _validate_items(self, value : typing.Any) -> None:
        if self.item_type is not None:
            for val in value:  
                if not isinstance(val, self.item_type):
                    raise TypeError(
                        wrap_error_text(f"""
                        Not all elements of list {get_iterable_printfriendly_repr(value)} given are of allowed item type(s), 
                        which are : {self.item_type}. Given type {type(val)}. Cannot set or extend typed list."""
                    ))
                
    def _validate_item(self, value : typing.Any):
        if self.item_type is not None and not isinstance(value, self.item_type):
            raise TypeError(
                wrap_error_text(f"""
                    Not all elements given are of allowed item type(s), which are : {self.item_type}. 
                    Given type {type(value)}. Cannot append or insert in typed list."""
            ))
      
    def __iadd__(self, value : typing.List[typing.Any]):
        self._validate_for_extension(value)
        return TypeConstrainedList(default=self._inner.__iadd__(value), item_type=self.item_type, bounds=self.bounds,
                                constant=self.constant, skip_validate=True)
    
    def copy(self, return_as_typed_list : bool = False) -> typing.Union["TypeConstrainedList", typing.List[typing.Any]]: 
        if return_as_typed_list:
            return TypeConstrainedList(default=self._inner.copy(), item_type=self.item_type, bounds=self.bounds, 
                            constant=self.constant, skip_validate=True)
        else:
            return self._inner.copy()
      


class TypedList(ClassSelector):
    
    __slots__ = ['item_type', 'bounds', 'accept_nonlist_object']

    def __init__(self, default : typing.Optional[typing.List[typing.Any]] = None, *, item_type : typing.Any = None, 
            deepcopy_default : bool = True, accept_nonlist_object : bool = False, 
            allow_None : bool = True,  bounds : tuple = (0,None), 
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            per_instance_descriptor : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        if default is not None:
            default = TypeConstrainedList(default=default, item_type=item_type, bounds=bounds, constant=constant, 
                               skip_validate=False) # type: ignore    
        super().__init__(class_ = TypeConstrainedList, default=default, isinstance=True, deepcopy_default=deepcopy_default, 
            doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, 
            per_instance_descriptor=per_instance_descriptor, class_member=class_member, fget=fget, fset=fset, 
            fdel=fdel, precedence=precedence)
        self.item_type = item_type
        self.bounds    = bounds 
        self.accept_nonlist_object = accept_nonlist_object

    # @instance_descriptor - super().__set__ takes care of instance descriptors 
    def validate_and_adapt(self, value : typing.Any):
        if self.allow_None and value is None:
            return
        if value is not None and self.accept_nonlist_object and not isinstance(value, list):
            value = [value]   
        return TypeConstrainedList(default=value, item_type=self.item_type, bounds=self.bounds, 
                        constant=self.constant, skip_validate=False)        
            
    @classmethod
    def serialize(cls, value : TypeConstrainedList) -> typing.Any:
        if value is None:
            return None
        return value._inner

    # no need for deserialize, when __set__ is called TypeConstrainedList is automatically created  
    

class TypeConstrainedDict(collections.abc.MutableMapping):
    """ A dictionary which contains only ``NewDict`` values. """

    def __init__(self, default : typing.Dict, *, key_type : typing.Optional[typing.Union[type, typing.Tuple]] = None, 
                item_type : typing.Optional[typing.Union[type, typing.Tuple]] = None, 
                bounds : typing.Tuple = (0, None), constant : bool = False, skip_validate : bool = False):
        super().__init__()
        self.key_type  = key_type
        self.item_type = item_type
        self.bounds    = get_typed_iterable_bounds(bounds)
        self.constant  = constant 
        if not skip_validate:
            self._validate_for_set(default)
        self._inner = default

    def _validate_for_set(self, value : typing.Dict) -> None:
        self._validate_value(value)
        self._validate_bounds_for_set(value)
        self._validate_items(value)

    def _validate_for_insertion(self, value : typing.Dict) -> None:
        if self.constant:
            raise ValueError(f"Dict {get_iterable_printfriendly_repr(self._inner)} is a constant and cannot be modified.")
        self._validate_value(value)
        self._validate_bounds_for_extension(value)
        self._validate_items(value)

    def _validate_value(self, value) -> None:
        if not isinstance(value, dict):
            raise TypeError(wrap_error_text(f"""
                Given value for typed dictionary is not a dictionary. Given type : {type(value)}. Expected dictionary."""))

    def _validate_bounds_for_set(self, value : typing.Dict) -> None:
        if not (self.bounds[0] <= value.__len__() <= self.bounds[1]):
            raise ValueError(wrap_error_text(f"""
                Given dictionary length outside bounds. Given length {value.__len__()}, expected length : {self.bounds}"""))
                
    def _validate_bounds_for_extension(self, value : typing.Dict = {"dummy" : "dummy"}) -> None:
        if not (self.bounds[0] <= self._inner.__len__() + value.__len__() <= self.bounds[1]):
            raise ValueError(wrap_error_text(f"""
                Extending dictionary crosses bounds. Existing length {self._inner.__len__()}, 
                length of items to be added : {value.__len__()}, allowed bounds : {self.bounds}"""))
            
    def _validate_items(self, value : typing.Dict[typing.Any, typing.Any]) -> None:
        keys = value.keys()
        values = value.values()
        if self.key_type is not None and len(keys) != 0:                    
            for key in keys:
                if not isinstance(key, self.key_type):
                    raise TypeError(wrap_error_text(f"""
                            Keys for typed dictionary contain incompatible types. 
                            Allowed types : {self.key_type}, given type : {type(key)}"""))
        if self.item_type is not None and len(values) != 0: 
            for value in values:
                if not isinstance(value, self.item_type):
                    raise TypeError(wrap_error_text(f"""
                            Values for typed dictionary contain incompatible types. 
                            Allowed types : {self.item_type}. given type : {type(value)}"""))
       
    def _validate_key_value_pair(self, __key : typing.Any, __value : typing.Any) -> None:
        if self.key_type is not None:
            if not isinstance(__key, self.key_type):
                raise TypeError("given key {} is not of {}.".format(__key, self.key_type))
        if self.item_type is not None: 
            if not isinstance(__value, self.item_type):
                raise TypeError("given item {} is not of {}.".format(__value, self.item_type))

    def __iter__(self) -> typing.Iterator:
        return self._inner.__iter__()

    def __setitem__(self, __key : typing.Any, __value : typing.Any) -> None:
        if self.constant:
            raise ValueError(f"Dict {get_iterable_printfriendly_repr(self._inner)} is a constant and cannot be modified.")
        if __key not in self._inner:
            self._validate_bounds_for_extension()
        self._validate_key_value_pair(__key, __value)
        self._inner.__setitem__(__key, __value)

    def __delitem__(self, __v : typing.Any) -> None:
        self._inner.__delitem__(__v)

    def __getitem__(self, __k : typing.Any) -> typing.Any:
        return self._inner.__getitem__(__k)

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
        
    def fromkeys(self, __iterable, __value : typing.Any):
        return self._inner.fromkeys(__iterable, __value)

    def keys(self) -> typing.Any:
        return self._inner.keys()

    def items(self) -> typing.Any:
        return self._inner.items()

    def values(self) -> typing.Any:
        return self._inner.values()

    def get(self, __key : typing.Any, __default : typing.Any = None):
        return self._inner.get(__key, __default)

    def setdefault(self, __key : typing.Any) -> None:
        self._inner.setdefault(__key)       

    def clear(self) -> None:
        self._inner.clear()

    def copy(self, return_as_typed : bool = False) -> typing.Union["TypeConstrainedDict", typing.Dict]:
        if return_as_typed:
            return TypeConstrainedDict(default=self._inner.copy(), key_type=self.key_type, item_type=self.item_type, 
                bounds=self.bounds, constant=self.constant, skip_validate=True)
        else:
            return self._inner.copy()

    def popitem(self) -> tuple:
        return self._inner.popitem()
    
    def pop(self, __key : typing.Any) -> typing.Any:
        return self._inner.pop(__key)
    
    def update(self, __o : typing.Any) -> None:
        self._validate_for_insertion(__o)
        self._inner.update(__o)
        

class TypedKeyMappingsConstrainedDict(TypeConstrainedDict):

    def __init__(self, default: typing.Dict, *, type_mapping : typing.Dict, 
            allow_unspecified_keys : bool = False, bounds : tuple = (0, None), constant : bool = False, 
            skip_validate : bool = False) -> None:
        self.type_mapping = type_mapping
        self.allow_unspecified_keys = allow_unspecified_keys
        self.key_list = self.type_mapping.keys()
        super().__init__(default, key_type = None, item_type = None, bounds = bounds, constant = constant,
                skip_validate=skip_validate)

    def _validate_items(self, value: typing.Dict) -> None:
        for key, val in value.items():
            self._validate_key_value_pair(key, val)
                
    def _validate_key_value_pair(self, __key: typing.Any, __value: typing.Any) -> None:
        if __key not in self.key_list:
            if self.allow_unspecified_keys:
                pass 
            else: 
                raise KeyError(f"Keys except {self.key_list} not allowed for typed dictionary. Given key : {__key}.")
        elif not isinstance(__value, self.type_mapping[__key]):
            raise TypeError(wrap_error_text(f""" 
                Value for key {__key} not of expected type : {self.type_mapping[__key]}. Given type : {type(__value)}."""))
        
    def copy(self, return_as_typed : bool = False) -> typing.Union["TypedKeyMappingsConstrainedDict", typing.Dict]:
        if return_as_typed:
            return TypedKeyMappingsConstrainedDict(default=self._inner.copy(), type_mapping=self.type_mapping,  
                bounds=self.bounds, constant=self.constant, skip_validate=True)
        else:
            return self._inner.copy()
           

class TypedDict(ClassSelector):

    __slots__ = ['key_type', 'item_type', 'bounds']
    
    def __init__(self, default : typing.Optional[typing.Dict] = None, *, key_type : typing.Any = None, 
            item_type : typing.Any = None, deepcopy_default : bool = True, allow_None : bool = True,
            bounds : tuple = (0, None), doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            per_instance_descriptor : bool = False, 
            class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
            fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None,
            precedence : typing.Optional[float] = None) -> None:
        if default is not None:
            default = TypeConstrainedDict(default, key_type=key_type, item_type=item_type, bounds=bounds,
                        constant=constant, skip_validate=False) # type: ignore
        self.key_type = key_type
        self.item_type = item_type
        self.bounds = bounds 
        super().__init__(class_=TypeConstrainedDict, default=default, isinstance=True, deepcopy_default=deepcopy_default, 
            doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, fget=fget, fset=fset, fdel=fdel, 
            per_instance_descriptor=per_instance_descriptor, class_member=class_member, precedence=precedence)

    def __set__(self, obj, value):
        if value is not None:
            container = TypeConstrainedDict(default=value, key_type=self.key_type, item_type=self.item_type,
                                bounds=self.bounds, constant=self.constant, skip_validate=False)     
            return super().__set__(obj, container) # re-set it to trigger param related activities
        else:
            return super().__set__(obj, value) # re-set it to trigger param related activities
     
    @classmethod
    def serialize(cls, value: TypeConstrainedDict) -> typing.Any:
        if value is None:
            return None
        return value._inner
  

class TypedKeyMappingsDict(ClassSelector):

    __slots__ = ['type_mapping', 'allow_unspecified_keys', 'bounds']
    
    def __init__(self, default : typing.Optional[typing.Dict[typing.Any, typing.Any]] = None, *, 
            type_mapping : typing.Dict, 
            allow_unspecified_keys : bool = True, bounds : tuple = (0, None), 
            deepcopy_default : bool = True, allow_None : bool = True,
            doc : typing.Optional[str] = None, constant : bool = False, readonly : bool = False, 
            per_instance_descriptor : bool = False, class_member : bool = False, 
            fget : typing.Optional[typing.Callable] = None, fset : typing.Optional[typing.Callable] = None,
            fdel : typing.Optional[typing.Callable] = None, precedence : typing.Optional[float] = None) -> None:
        if default is not None:
            default = TypedKeyMappingsConstrainedDict(default=default, type_mapping=type_mapping, 
                        allow_unspecified_keys=allow_unspecified_keys, bounds=bounds, constant=constant, 
                        skip_validate=False) # type: ignore 
        self.type_mapping = type_mapping
        self.allow_unspecified_keys = allow_unspecified_keys
        self.bounds = bounds 
        super().__init__(class_=TypedKeyMappingsConstrainedDict, default=default, 
            isinstance=True, deepcopy_default=deepcopy_default, doc=doc, constant=constant, readonly=readonly, 
            allow_None=allow_None, per_instance_descriptor=per_instance_descriptor, class_member=class_member, 
            fget=fget, fset=fset, fdel=fdel, precedence=precedence) 
                       
    def __set__(self, obj, value):
        if value is not None:
            container = TypedKeyMappingsConstrainedDict(default=value, type_mapping=self.type_mapping, 
                    allow_unspecified_keys=self.allow_unspecified_keys, bounds=self.bounds, constant=self.constant,
                    skip_validate=False)
            return super().__set__(obj, container) 
        else:
            return super().__set__(obj, value) # re-set it to trigger param related activities
        
    @classmethod
    def serialize(cls, value: TypeConstrainedDict) -> typing.Any:
        if value is None:
            return None
        return value._inner


def hashable(x):
    """
    Return a hashable version of the given object x, with lists and
    dictionaries converted to tuples.  Allows mutable objects to be
    used as a lookup key in cases where the object has not actually
    been mutated. Lookup will fail (appropriately) in cases where some
    part of the object has changed.  Does not (currently) recursively
    replace mutable subobjects.
    """
    if isinstance(x, collections.abc.MutableSequence):
        return tuple(x)
    elif isinstance(x, collections.abc.MutableMapping):
        return tuple([(k,v) for k,v in x.items()])
    else:
        return x


def named_objs(objlist, namesdict=None):
    """
    Given a list of objects, returns a dictionary mapping from
    string name for the object to the object itself. Accepts
    an optional name,obj dictionary, which will override any other
    name if that item is present in the dictionary.
    """
    objs = OrderedDict()

    objtoname = {}
    unhashables = []
    if namesdict is not None:
        for k, v in namesdict.items():
            try:
                objtoname[hashable(v)] = k
            except TypeError:
                unhashables.append((k, v))

    for obj in objlist:
        if objtoname and hashable(obj) in objtoname:
            k = objtoname[hashable(obj)]
        elif any(obj is v for (_, v) in unhashables):
            k = [k for (k, v) in unhashables if v is obj][0]
        elif hasattr(obj, "name"):
            k = obj.name
        elif hasattr(obj, '__name__'):
            k = obj.__name__
        else:
            k = str(obj)
        objs[k] = obj
    return objs


def _is_abstract(class_):
    try:
        return class_.__abstract
    except AttributeError:
        return False


# Could be a method of ClassSelector.
def concrete_descendents(parentclass):
    """
    Return a dictionary containing all subclasses of the specified
    parentclass, including the parentclass.  Only classes that are
    defined in scripts that have been run or modules that have been
    imported are included, so the caller will usually first do ``from
    package import *``.

    Only non-abstract classes will be included.
    """
    return dict((c.__name__, c) for c in descendents(parentclass)
                if not _is_abstract(c))



__all__ = [ 
            'String', 'Bytes', 'IPAddress', 'Number', 'Integer', 'Boolean', 'Iterable', 'Tuple', 'List', 'Callable', 
            'CSS3Color', 'Composite', 'Selector', 'ClassSelector', 'TupleSelector', 
            'Filename', 'Foldername', 'Path', 'FileSelector', 'MultiFileSelector', 
            'Date', 'CalendarDate',  'Range', 'DateRange', 'CalendarDateRange', 
            'TypeConstrainedList', 'TypeConstrainedDict', 'TypedKeyMappingsConstrainedDict', 
            'TypedList', 'TypedDict', 'TypedKeyMappingsDict', 
        ]
