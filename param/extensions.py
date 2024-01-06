import typing
import numpy
from types import FunctionType

from .parameterized import Parameterized, ParameterizedMetaclass
from .parameters import *



class NumpyArray(ClassSelector):
    """
    Parameter whose value is a numpy array.
    """

    def __init__(self, default=None, doc : typing.Union[str, None] = None, 
            constant : bool = False, readonly : bool = False, allow_None : bool = False,
            label : typing.Union[str, None] = None,  per_instance : bool = False, deep_copy : bool = False, 
            class_member : bool = False, fget : FunctionType = None, fset : FunctionType = None,
            precedence : float = None) -> None:
        
        super(NumpyArray, self).__init__(class_=numpy.ndarray, default=default,  doc=doc, 
            constant=constant, readonly=readonly, allow_None=allow_None, label=label, per_instance=per_instance, 
            deep_copy=deep_copy, class_member=class_member, fget=fget, fset=fset, precedence=precedence)

    @typing.overload
    def __get__(self, obj : typing.Union[Parameterized, typing.Any], 
                objtype: typing.Union[ParameterizedMetaclass, typing.Any]) -> numpy.ndarray:
        ...

    @classmethod
    def serialize(cls, value : typing.Union[numpy.ndarray, None]):
        if value is None:
            return None
        return value.tolist()

    @classmethod
    def deserialize(cls, value):
        if value == 'null' or value is None:
            return None
        return numpy.asarray(value)
    

from pandas import DataFrame as pdDFrame
     

class DataFrame(ClassSelector):
    """
    Parameter whose value is a pandas DataFrame.

    The structure of the DataFrame can be constrained by the rows and
    columns arguments:

    rows: If specified, may be a number or an integer bounds tuple to
    constrain the allowable number of rows.

    columns: If specified, may be a number, an integer bounds tuple, a
    list or a set. If the argument is numeric, constrains the number of
    columns using the same semantics as used for rows. If either a list
    or set of strings, the column names will be validated. If a set is
    used, the supplied DataFrame must contain the specified columns and
    if a list is given, the supplied DataFrame must contain exactly the
    same columns and in the same order and no other columns.
    """

    __slots__ = ['rows', 'columns', 'ordered']

    def __init__(self, default=None, rows=None, columns=None, ordered=None, **params):
        self.rows = rows
        self.columns = columns
        self.ordered = ordered
        super(DataFrame,self).__init__(pdDFrame, default=default, **params)
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = '{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(message.format(name=name, length=length, bounds=bounds))
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(message.format(name=name,length=length, bounds=bounds))

    def _validate(self, val):
        super(DataFrame, self)._validate(val)

        if isinstance(self.columns, set) and self.ordered is True:
            raise ValueError('Columns cannot be ordered when specified as a set')

        if self.allow_None and val is None:
            return

        if self.columns is None:
            pass
        elif (isinstance(self.columns, tuple) and len(self.columns)==2
              and all(isinstance(v, (type(None), numbers.Number)) for v in self.columns)): # Numeric bounds tuple
            self._length_bounds_check(self.columns, len(val.columns), 'Columns')
        elif isinstance(self.columns, (list, set)):
            self.ordered = isinstance(self.columns, list) if self.ordered is None else self.ordered
            difference = set(self.columns) - set([str(el) for el in val.columns])
            if difference:
                msg = 'Provided DataFrame columns {found} does not contain required columns {expected}'
                raise ValueError(msg.format(found=list(val.columns), expected=sorted(self.columns)))
        else:
            self._length_bounds_check(self.columns, len(val.columns), 'Column')

        if self.ordered:
            if list(val.columns) != list(self.columns):
                msg = 'Provided DataFrame columns {found} must exactly match {expected}'
                raise ValueError(msg.format(found=list(val.columns), expected=self.columns))

        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'Row')

    @classmethod
    def serialize(cls, value):
        if value is None:
            return 'null'
        return value.to_dict('records')

    @classmethod
    def deserialize(cls, value):
        if value == 'null':
            return None
        from pandas import DataFrame as pdDFrame
        return pdDFrame(value)
    


class Series(ClassSelector):
    """
    Parameter whose value is a pandas Series.

    The structure of the Series can be constrained by the rows argument
    which may be a number or an integer bounds tuple to constrain the
    allowable number of rows.
    """

    __slots__ = ['rows']

    def __init__(self, default=None, rows=None, allow_None=False, **params):
        from pandas import Series as pdSeries
        self.rows = rows
        super(Series,self).__init__(pdSeries, default=default, allow_None=allow_None,
                                    **params)
        self._validate(self.default)

    def _length_bounds_check(self, bounds, length, name):
        message = '{name} length {length} does not match declared bounds of {bounds}'
        if not isinstance(bounds, tuple):
            if (bounds != length):
                raise ValueError(message.format(name=name, length=length, bounds=bounds))
            else:
                return
        (lower, upper) = bounds
        failure = ((lower is not None and (length < lower))
                   or (upper is not None and length > upper))
        if failure:
            raise ValueError(message.format(name=name,length=length, bounds=bounds))

    def _validate(self, val):
        super(Series, self)._validate(val)

        if self.allow_None and val is None:
            return

        if self.rows is not None:
            self._length_bounds_check(self.rows, len(val), 'Row')
