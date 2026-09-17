from __future__ import annotations

import os
import typing as t
import pathlib
from datetime import date, datetime
from typing_extensions import assert_type

import numpy as np
import param
import pandas


class ParameterType(param.Parameterized):
    parameter = param.Parameter()
    optional_parameter = param.Parameter(default=None, allow_None=True)

ptypes = ParameterType()
assert_type(ptypes.parameter, t.Any)
assert_type(ptypes.optional_parameter, t.Any)

ParameterType.parameter = "Foo"
ptypes.parameter = 42

################
# String Types #
################

class StringTypes(param.Parameterized):
    string = param.String()
    optional_string = param.String(allow_None=True)
    implicit_optional_string = param.String(default=None)
    empty_string = param.String()

    nt = param.NumericTuple()

stypes = StringTypes()

assert_type(stypes.string, str)
assert_type(stypes.empty_string, str)
assert_type(stypes.optional_string, str | None)
assert_type(stypes.implicit_optional_string, str | None)

stypes.string = "test"
stypes.optional_string = None

################
# Number Types #
################

class NumberTypes(param.Parameterized):
    number = param.Number(allow_None=False)
    optional_number = param.Number(allow_None=True)
    implicit_optional_number = param.Number(default=None)
    empty_number = param.Number()
ntypes = NumberTypes()

assert_type(ntypes.number, float | int)
assert_type(ntypes.empty_number, float | int)
assert_type(ntypes.optional_number, float | int | None)
assert_type(ntypes.implicit_optional_number, float | int | None)

class MagnitudeTypes(param.Parameterized):
    magnitude = param.Magnitude(allow_None=False)
    optional_magnitude = param.Magnitude(allow_None=True)

mtypes = MagnitudeTypes()
assert_type(mtypes.magnitude, float)
assert_type(mtypes.optional_magnitude, float | None)

#################
# Integer Types #
#################

class IntegerTypes(param.Parameterized):
    integer = param.Integer(allow_None=False)
    optional_integer = param.Integer(allow_None=True)
    implicit_optional_integer = param.Integer(default=None)
    empty_integer = param.Integer()

itypes = IntegerTypes()

assert_type(itypes.integer, int)
assert_type(itypes.empty_integer, int)
assert_type(itypes.optional_integer, int | None)
assert_type(itypes.implicit_optional_integer, int | None)

#################
# Boolean Types #
#################

class BooleanTypes(param.Parameterized):
    boolean = param.Boolean(allow_None=False)
    optional_boolean = param.Boolean(allow_None=True)
    implicit_optional_boolean = param.Boolean(default=None)

btypes = BooleanTypes()

assert_type(btypes.boolean, bool)
assert_type(btypes.optional_boolean, bool | None)
assert_type(btypes.implicit_optional_boolean, bool | None)

class EventTypes(param.Parameterized):
    event = param.Event()

etypes = EventTypes()
assert_type(etypes.event, t.Any)

##############
# List Types #
##############

class ListTypes(param.Parameterized):
    list_param = param.List(allow_None=False)
    optional_list_param = param.List(allow_None=True)
    list_int_param = param.List(item_type=int, allow_None=False)
    optional_list_int_param = param.List(item_type=int, allow_None=True)
    empty_list = param.List()

ListTypes.list_param = []

ltypes = ListTypes()

assert_type(ltypes.empty_list, list[t.Any])
assert_type(ltypes.list_param, list[t.Any])
assert_type(ltypes.optional_list_param, list[t.Any] | None)
assert_type(ltypes.list_int_param, list[int])
assert_type(ltypes.optional_list_int_param, list[int] | None)

class Test(param.Parameterized):
    a = param.Integer()
    b = param.List(item_type=int)

tst = Test()
assert_type(Test.a, int)
assert_type(Test.b, list[int])
assert_type(tst.a, int)
assert_type(tst.b, list[int])

##############
# Dict Types #
##############

class DictTypes(param.Parameterized):
    dict_param = param.Dict(allow_None=False)
    optional_dict_param = param.Dict(allow_None=True)

dtypes = DictTypes()

assert_type(dtypes.dict_param, dict)
assert_type(dtypes.optional_dict_param, dict | None)

###############
# Dynamic Type #
###############

class DynamicTypes(param.Parameterized):
    dynamic = param.Dynamic(default=1)
    optional_dynamic = param.Dynamic(default=None, allow_None=True)

dytypes = DynamicTypes()
assert_type(dytypes.dynamic, t.Any)
assert_type(dytypes.optional_dynamic, t.Any | None)

###############
# Tuple Types #
###############

class TupleTypes(param.Parameterized):
    tuple_param = param.Tuple(length=2, allow_None=False)
    optional_tuple_param = param.Tuple(length=2, allow_None=True)

ttypes = TupleTypes()

assert_type(ttypes.tuple_param, tuple[t.Any, ...])
assert_type(ttypes.optional_tuple_param, tuple[t.Any, ...] | None)

class NumericTupleTypes(param.Parameterized):
    numeric_tuple = param.NumericTuple(allow_None=False)
    optional_numeric_tuple = param.NumericTuple(allow_None=True)
    empty_numeric_tuple = param.NumericTuple()

nttypes = NumericTupleTypes()
assert_type(nttypes.numeric_tuple, tuple[float, ...])
assert_type(nttypes.optional_numeric_tuple, tuple[float, ...] | None)
assert_type(nttypes.empty_numeric_tuple, tuple[float, ...])

class XYCoordinatesTypes(param.Parameterized):
    xy = param.XYCoordinates(allow_None=False)
    optional_xy = param.XYCoordinates(allow_None=True)

xytypes = XYCoordinatesTypes()
assert_type(xytypes.xy, tuple[float, float])
assert_type(xytypes.optional_xy, tuple[float, float] | None)

class RangeTypes(param.Parameterized):
    range_param = param.Range(allow_None=False)
    optional_range_param = param.Range(allow_None=True)

rtypes = RangeTypes()
assert_type(rtypes.range_param, tuple[float, float])
assert_type(rtypes.optional_range_param, tuple[float, float] | None)

##############
# Date Types #
##############

class DateTypes(param.Parameterized):
    date_param = param.Date(default=datetime(2024, 1, 1), allow_None=False)
    optional_date_param = param.Date(default=None, allow_None=True)
    calendar_date_param = param.CalendarDate(default=date(2024, 1, 1), allow_None=False)
    optional_calendar_date_param = param.CalendarDate(default=None, allow_None=True)

datetypes = DateTypes()
assert_type(datetypes.date_param, datetime | date)
assert_type(datetypes.optional_date_param, datetime | date | None)
assert_type(datetypes.calendar_date_param, date)
assert_type(datetypes.optional_calendar_date_param, date | None)

class DateRangeTypes(param.Parameterized):
    date_range = param.DateRange(
        default=(datetime(2024, 1, 1), datetime(2024, 1, 2)),
        allow_None=False,
    )
    optional_date_range = param.DateRange(default=None, allow_None=True)
    calendar_date_range = param.CalendarDateRange(
        default=(date(2024, 1, 1), date(2024, 1, 2)),
        allow_None=False,
    )
    optional_calendar_date_range = param.CalendarDateRange(default=None, allow_None=True)

drtypes = DateRangeTypes()
assert_type(drtypes.date_range, tuple[datetime | date, datetime | date])
assert_type(drtypes.optional_date_range, tuple[datetime | date, datetime | date] | None)
assert_type(drtypes.calendar_date_range, tuple[date, date])
assert_type(drtypes.optional_calendar_date_range, tuple[date, date] | None)

###############
# Class Types #
###############

class Foo: pass

class ClassTypes(param.Parameterized):
    foo = param.ClassSelector(class_=Foo, allow_None=False, default=Foo())
    optional_foo = param.ClassSelector(class_=Foo, allow_None=True)
    no_none_foo = param.ClassSelector(class_=Foo, allow_None=param.parameters.NoNone)

ctypes = ClassTypes()

assert_type(ctypes.foo, Foo)
assert_type(ctypes.optional_foo, Foo | None)
assert_type(ctypes.no_none_foo, Foo)

class SelectorBaseTypes(param.Parameterized):
    selector_base = param.SelectorBase(default=1, allow_None=False)  # type: ignore[var-annotated]
    optional_selector_base = param.SelectorBase(default=None, allow_None=True)  # type: ignore[var-annotated]

sbtypes = SelectorBaseTypes()
assert_type(sbtypes.selector_base, t.Any)
assert_type(sbtypes.optional_selector_base, t.Any)

##############
# Type
##############

class TypeTypes(param.Parameterized):
    type_param = param.ClassSelector(
        allow_None=False, is_instance=False, class_=Foo, default=Foo
    )
    optional_type_param = param.ClassSelector(
        allow_None=True, is_instance=False, class_=Foo
    )

typtypes = TypeTypes()
assert_type(typtypes.type_param, type[Foo])
assert_type(typtypes.optional_type_param, type[Foo] | None)


##############
# DataFrame  #
##############

class DataFrameTypes(param.Parameterized):
    df = param.DataFrame(default=pandas.DataFrame(), allow_None=False)
    optional_df = param.DataFrame(allow_None=True, rows=3)
    optional_df_by_default = param.DataFrame()

dftypes = DataFrameTypes()
assert_type(dftypes.df, pandas.DataFrame)
assert_type(dftypes.optional_df, pandas.DataFrame | None)
assert_type(dftypes.optional_df_by_default, pandas.DataFrame | None)  # type: ignore

###########
# Series  #
###########

class SeriesTypes(param.Parameterized):
    series = param.Series(allow_None=False)
    optional_series = param.Series(allow_None=True)

sertypes = SeriesTypes()
assert_type(sertypes.series, pandas.Series)
assert_type(sertypes.optional_series, pandas.Series | None)

###########
# Array   #
###########

class ArrayTypes(param.Parameterized):
    array = param.Array(allow_None=False)
    optional_array = param.Array(default=None)

atypes = ArrayTypes()
assert_type(atypes.array, np.ndarray)
assert_type(atypes.optional_array, np.ndarray | None)

##################
# Callable Types #
##################

def _callback() -> int:
    return 1

class CallableTypes(param.Parameterized):
    callable_param = param.Callable(default=_callback, allow_None=False)
    optional_callable_param = param.Callable(default=None, allow_None=True)
    action = param.Action(default=_callback, allow_None=False)
    optional_action = param.Action(default=None, allow_None=True)

catypes = CallableTypes()
assert_type(catypes.callable_param, t.Callable[..., t.Any])
assert_type(catypes.optional_callable_param, t.Callable[..., t.Any] | None)
assert_type(catypes.action, t.Callable[[], t.Any])
assert_type(catypes.optional_action, t.Callable[[], t.Any] | None)

##################
# Composite Type #
##################

class CompositeTypes(param.Parameterized):
    value = param.Number(default=1)
    comp = param.Composite(attribs=["value"])

comptypes = CompositeTypes()
assert_type(comptypes.comp, list[t.Any])

##################
# Selector Types #
##################

class SelectorTypes(param.Parameterized):
    selector = param.Selector(objects=[1,2,3], allow_None=False)  # type: ignore[var-annotated]
    optional_selector = param.Selector(objects=[1,2,3], allow_None=True)  # type: ignore[var-annotated]

seltypes = SelectorTypes()
assert_type(seltypes.selector, t.Any)
assert_type(seltypes.optional_selector, t.Any)

class ObjectSelectorTypes(param.Parameterized):
    object_selector = param.ObjectSelector(default=1, objects=[1, 2, 3], allow_None=False)
    optional_object_selector = param.ObjectSelector(
        default=None, objects=[1, 2, 3], allow_None=True
    )

ostypes = ObjectSelectorTypes()
assert_type(ostypes.object_selector, t.Any)
assert_type(ostypes.optional_object_selector, t.Any)

class FileSelectorTypes(param.Parameterized):
    file_selector = param.FileSelector(path="*")
    list_selector = param.ListSelector(objects=["a", "b"], allow_None=True)
    multi_file_selector = param.MultiFileSelector(path="*")

fstypes = FileSelectorTypes()
assert_type(fstypes.file_selector, t.Any)
assert_type(fstypes.list_selector, t.Any)
assert_type(fstypes.multi_file_selector, t.Any)

##############
# Path Types #
##############

class PathTypes(param.Parameterized):
    path_param = param.Path(default=pathlib.Path("."), allow_None=False)
    optional_path_param = param.Path(default=None, allow_None=True)
    filename = param.Filename(default=pathlib.Path("type_tests.py"), allow_None=False)
    optional_filename = param.Filename(default=None, allow_None=True)
    foldername = param.Foldername(default=pathlib.Path("."), allow_None=False)
    optional_foldername = param.Foldername(default=None, allow_None=True)

pathtypes = PathTypes()
assert_type(pathtypes.path_param, os.PathLike | str)
assert_type(pathtypes.optional_path_param, os.PathLike | str | None)
assert_type(pathtypes.filename, os.PathLike | str)
assert_type(pathtypes.optional_filename, os.PathLike | str | None)
assert_type(pathtypes.foldername, os.PathLike | str)
assert_type(pathtypes.optional_foldername, os.PathLike | str | None)

##############
# List Types #
##############

class HookListTypes(param.Parameterized):
    hook_list = param.HookList(default=[], allow_None=False)
    optional_hook_list = param.HookList(default=None, allow_None=True)

hltypes = HookListTypes()
assert_type(hltypes.hook_list, t.Any)
assert_type(hltypes.optional_hook_list, t.Any)

#####################
# String-like Types #
#####################

class ColorAndBytesTypes(param.Parameterized):
    color = param.Color(allow_None=False)
    optional_color = param.Color(allow_None=True)
    bytes_param = param.Bytes(allow_None=False)
    optional_bytes_param = param.Bytes(allow_None=True)

cbtypes = ColorAndBytesTypes()
assert_type(cbtypes.color, str)
assert_type(cbtypes.optional_color, str | None)
assert_type(cbtypes.bytes_param, bytes)
assert_type(cbtypes.optional_bytes_param, bytes | None)
