# requested in param:
# - new slot 'visible' (was added below manually for each class but this is
#   not very nice)
# - public method for '_batch_call_watchers'
# - check value again when changing bounds, objects, etc.
# - ObjectSelector default allow_None=False instead of None

import time
import inspect
import traceback
import math
import re
from typing import Tuple, List, Union, Any, Iterable, Dict, Callable
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

import param as pm


# TOOLS

def _error_message(*args):
    """Error message display"""
    msg = '\n'.join([x if isinstance(x, str) else repr(x) for x in args])
    QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Error', msg).exec()


def _noop(x: str):
    """A translation function that does not translate"""
    return x


def _return_false(err: Exception):
    """An error handler that does not handle any error"""
    return False


class InvalidCaseError(Exception):
    """InvalidCaseError should not occur and would be caused by a program bug"""
    pass


def _get_param_base_class(param: pm.Parameter):
    param_base_cls = None
    for cls in inspect.getmro(type(param)):
        if not issubclass(cls, GraphicParameter):
            param_base_cls = cls
            break
    return param_base_cls


def list_all_parameters(x: pm.Parameterized, out='Parameter'):
    """List recursively the parameter instances, including nested ones,
    of a Parameterized class instance.
    - If out flag is 'Parameters', returns a list of (Params instance, list of
      parameter names) tupples
    - If out flag is 'Parameterized', returns a list of (Parameterized
      instance, list of parameter names) tupples
    - If out flag is 'Parameter', returns a list of Param instances."""

    assert out in ['Parameter', 'Parameters', 'Parameterized']
    names = []
    params = []
    for name, value in x.get_param_values():

        # not interested in 'name' parameter
        if name == 'name':
            continue

        if isinstance(value, pm.Parameterized):
            params += list_all_parameters(value, out)
        else:
            if out == 'Parameter':
                params.append(x.param[name])
            else:
                names.append(name)

    if out == 'Parameters':
        params.append((x.param, names))
    elif out == 'Parameterized':
        params.append((x, names))
    return params


_QtColors = {QtGui.QColor(color_name).name(): color_name
            for color_name in QtGui.QColor.colorNames()
            if color_name != 'transparent'}


def q_color_from_hex(str):
    if str[0]=='#':
        str = str[1:]
    rgb = int(str, 16)
    return QtGui.QColor.fromRgb(rgb)


def text_display(value, param: pm.Parameter, translation=_noop):
    '''Format value to text'''

    if isinstance(param, pm.Integer):
        return str(value)
    elif isinstance(param, pm.Number):
        # display a reasonable number of decimals
        a = math.fabs(value)
        if isinstance(value, int):
            fmt = '{}'
        elif a % 1 == 0:
            # integer
            if value < 1e7:
                fmt = '{:.0f}.'
            else:
                fmt = '{:.3g}'
        else:
            # float
            if a < 1:
                fmt = '{:.3g}'
            elif a < 1e3:
                fmt = '{:.4g}'
            elif a < 1e4:
                fmt = '{:.4g}.'
            else:
                fmt = '{:.3g}'
        return fmt.format(value)
    elif isinstance(param, pm.Color):
        if value is None:
            return '(' + translation('none') + ')'
        if value[0] != '#':
            value = '#' + value
        q_color_name = translation(_QtColors.get(value, None))
        if q_color_name:
            return "%s (%s)" % (q_color_name, value)
        else:
            return value
    else:
        return str(value)


# PARAM WRAPPING


class GraphicParameter(pm.Parameter):
    """A subclass Parameters with additional attributes, which for the
    moment will all be stored in the available 'precedence' slot."""

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('precedence', dict())
        # new attribute 'style' (default None)
        user['style'] = kwargs.pop('style', None)
        # any additional attribute can be created
        slots = [key
                 for cls in inspect.getmro(type(self)) if issubclass(cls, pm.Parameter)
                 for key in cls.__slots__]
        slots.append('label')
        user_keys = [key for key in kwargs.keys() if key not in slots]
        for key in user_keys:
            user[key] = kwargs.pop(key)

        super(GraphicParameter, self).__init__(*args, **kwargs)

        self.user = user

    @property
    def user(self):
        return self.precedence

    @user.setter
    def user(self, value):
        self.precedence = value


class GBoolean(GraphicParameter, pm.Boolean):

    # We need a new slot 'visible' so that this new attribute can be watched
    # using pm.Parameterized.watch
    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GBoolean, self).__init__(*args, **kwargs)


class GInteger(GraphicParameter, pm.Integer):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GInteger, self).__init__(*args, **kwargs)


class GNumber(GraphicParameter, pm.Number):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GNumber, self).__init__(*args, **kwargs)


class GString(GraphicParameter, pm.String):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GString, self).__init__(*args, **kwargs)


class GObjectSelector(GraphicParameter, pm.ObjectSelector):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GObjectSelector, self).__init__(*args, **kwargs)


class GList(GraphicParameter, pm.List):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GList, self).__init__(*args, **kwargs)


class GColor(GraphicParameter, pm.Color):

    __slots__ = ['visible']

    def __init__(self, *args, **kwargs):
        self.visible = kwargs.pop('visible', True)
        super(GColor, self).__init__(*args, **kwargs)


# ABSTRACT CLASSES FOR CONTROL OF ONE PARAMETER


class _ActionControlBase:

    def __init__(self, translation: Callable[[str], str]=_noop):
        self._tr = translation

    def set_translation(self, translation):
        self._tr = translation
        self._update_text()

    def _update_text(self):
        raise NotImplementedError


class _ParameterControlBase(_ActionControlBase):
    """
    Abstract class for controlling parameters graphically. Sub-class will
    implement the actual graphics, either through controls or through menu items
    """

    def __init__(self, obj: pm.Parameterized, name: str,
                 do_label: bool=False,
                 translation: Callable[[str], str]=_noop,
                 set_error_handler: Callable[[Exception], bool]=_return_false,
                 reset_error_handler: Callable[[Exception], bool]=_return_false):

        super(_ParameterControlBase, self).__init__(translation=translation)

        # Object, key, value, specifications
        self.obj = obj
        self.name = name
        self.param = obj.param[name]  # type: pm.Parameter
        self._param_base_cls = _get_param_base_class(self.param)
        self._set_error_handler = set_error_handler
        self._reset_error_handler = reset_error_handler

        # Watch parameter changes
        if not self.param.constant:
            obj.param.watch(self.update_display, name)
            obj.param.watch(self.update_display, name, what='readonly')
            obj.param.watch(self.update_display, name, what='visible')

        # Create label: stored as an attribute (note that this must occur
        # after _create_control, i.e. after super-class __init__() of the
        # accurate QWidget has been called)
        if do_label:
            if self.param.allow_None:
                self.label = QtWidgets.QCheckBox()
                self.label.toggled.connect(self._toggle_None)
            else:
                self.label = QtWidgets.QLabel()
        else:
            self.label = None

        # Create control: will be done in the specialized child class,
        # this will include the call to the QtWidget constructor
        self._create_control()

        # Display text and tooltips
        self._update_text()

        # Init display: update everything
        for what in ['value', 'readonly', 'visible']:
            self.update_display(what, init=True)

    def parameter_value(self):
        value = getattr(self.obj, self.name)
        if self._param_base_cls == pm.Number:
            # if value must be a float, let it be a float! (avoid integers)
            value = float(value)
        return value

    def set_parameter_value(self, value):
        # This method will handle errors due to invalid value but not due to
        # failing watchers

        # Memorize previous value in case we need to switch back
        prev_value = self.parameter_value()

        # Attempt to set the value, do not run the watchers yet (otherwise
        # we would not know whether a ValueError is caused by an invalid
        # value or by a watcher failing)
        try:
            with pm.batch_watch(self.obj, run=False):
                setattr(self.obj, self.name, value)
        except ValueError as err:
            # invalid value, parameter was not changed
            print(repr(err))
            traceback.print_tb(err.__traceback__)
            _error_message(
                self._tr("Cannot set parameter '%s':" % self.name),
                str(err)
            )
            # restore display for the original value
            self._update_value_display()
            return

        # Call the watchers, handle errors
        try:
            self.obj.param._batch_call_watchers()
        except Exception as err:
            # error will be considered handled if returned value is True
            # or None (no returned value)
            error_handled = (self._set_error_handler(err) != False)
            if not error_handled:
                print(repr(err))
                traceback.print_tb(err.__traceback__)
                try:
                    setattr(self.obj, self.name, prev_value)
                    _error_message(
                        self._tr("Setting parameter '%s' failed with "
                                 "error:") % self.name,
                        err,
                        self._tr("Previous value was restored.")
                    )
                except Exception as err2:
                    error_handled = (self._reset_error_handler(err2) != False)
                    if not error_handled:
                        print(repr(err2))
                        traceback.print_tb(err2.__traceback__)
                        _error_message(
                            self._tr("Setting parameter '%s' failed with "
                                     "error:") % self.name,
                            err,
                            self._tr("Restoring previous value also failed "
                                     "with error:"),
                            err2
                        )

    def _create_control(self):
        raise NotImplementedError

    def update_display(self, what, init=False):

        if isinstance(what, pm.parameterized.Event):
            event = what
            what = event.what
        if what == 'value':
            self._update_value_display()
        elif what == 'readonly':
            self.set_enabled(not self.param.readonly)
        elif what == 'visible':
            visible = self.param.visible
            if not (init and visible):
                # at init do not explicitly make the control visible as this
                # would show it alone, i.e. not inside its parent container;
                # but if it should not be visible, set its visibility to
                # False and it will not be shown when the container will be
                # shown
                self.set_visible(visible)
        else:
            print("event of type '%s' not handled yet" % what)

    def _update_value_display(self, _=None):
        value = self.parameter_value()
        if self.param.allow_None and self.label:
            self.label.setChecked(value is not None)
            if value is None:
                return
        self._display_value(value)

    def _display_value(self, value):
        raise NotImplementedError

    def _update_text(self):
        # reimplemented in some child calsses
        tooltip = self._tr(self.param.doc)
        if self.label:
            self.label.setText(self._tr(self.param.label))
            self.label.setToolTip(tooltip)
        else:
            self.setToolTip(tooltip)

    def _control_has_None(self):
        return self.param.allow_None and not self.label

    def _toggle_None(self):
        if self.label.isChecked():
            if self.parameter_value() is None:
                self._set_parameter_from_control()
            self.setEnabled(True)
        else:
            if self.parameter_value() is not None:
                self.set_parameter_value(None)
            self.setEnabled(False)

    def _set_parameter_from_control(self, _=None):
        self.set_parameter_value(self._value_from_control())

    def _value_from_control(self):
        raise NotImplementedError

    def set_enabled(self, value):
        if self.label:
            self.label.setEnabled(value)
            self.setEnabled(value and not (self.parameter_value() is None))
        else:
            self.setEnabled(value)

    def set_visible(self, value):
        if self.label:
            self.label.setVisible(value)
        self.setVisible(value)

    def mouseDoubleClickEvent(self, _=None):
        # reset value to default
        self.set_parameter_value(self.param.default)


class _ColorControlBase(_ParameterControlBase):

    def _choose_color(self, _=None):
        if self.parameter_value() is None:
            dialog = QtWidgets.QColorDialog()
        else:
            q_color = q_color_from_hex(self.parameter_value())
            dialog = QtWidgets.QColorDialog(q_color)

        def finished(_=None):
            q_color = dialog.selectedColor()
            self.set_parameter_value(q_color.name())

        dialog.finished.connect(finished)

        def set_default(_=None):
            dialog.close()
            self.set_parameter_value(self.param.default)

        dialog.mouseDoubleClickEvent = set_default
        dialog.exec()


class _SelectorControlBase(_ParameterControlBase):

    def __init__(self, *args, **kwargs):
        super(_SelectorControlBase, self).__init__(*args, **kwargs)

        # Add watcher on objects
        self.obj.param.watch(self._update_objects_list, self.name, what='names')
        self.obj.param.watch(self._update_value_display, self.name, what='objects')

    def _update_objects_list(self, _=None):
        # will be reimplemented in child classes, unless in fact there is
        # nothing to do (as is the case with CyclingButton)
        pass

    def all_values(self):
        if self._control_has_None():
            return [None] + self.param.objects
        else:
            return self.param.objects

    def all_value_names(self):
        names = self.param.names
        if self._control_has_None():
            return ['-'] + names
        else:
            return names

    def all_value_tooltips(self):
        tooltips = self.param.precedence.get('value_tooltips', None)
        if tooltips is None:
            return [None] * (self._control_has_None() + len(self.param.objects))
        elif self._control_has_None():
            return [None] + tooltips
        else:
            return tooltips


# SPECIALIZED PANEL CONTROLS


class ConstantDisplay(_ParameterControlBase, QtWidgets.QLabel):

    def _create_control(self):
        # Simple text display
        QtWidgets.QLabel.__init__(self, str(self.parameter_value()))
        # prevent label form extending vertically
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                   QtWidgets.QSizePolicy.Maximum)


class PopupMenu(_SelectorControlBase, QtWidgets.QComboBox):

    def _create_control(self):
        QtWidgets.QComboBox.__init__(self)
        # (allow control shrinking!)
        self.minimumSizeHint = lambda: QtCore.QSize(0, 0)
        self._make_combo_items()
        self.activated.connect(self._set_parameter_from_control)

    def _make_combo_items(self):
        '''Fill-in the options for popup list of values'''
        values_txt = [self._tr(x) for x in self.all_value_names()]
        self.clear()
        self.insertItems(0, values_txt)
        if isinstance(self.param, GObjectSelector) and self.all_value_tooltips():
            for i, tooltip in enumerate(self.all_value_tooltips()):
                self.setItemData(i, self._tr(tooltip),
                                 Qt.ToolTipRole)

    def _update_objects_list(self, _=None):
        self._make_combo_items()
        self._update_value_display()

    def _value_from_control(self):
        return self.all_values()[self.currentIndex()]

    def _update_text(self):
        super(PopupMenu, self)._update_text()
        self._make_combo_items()
        self._update_value_display()

    def _display_value(self, value):
        values = self.all_values()
        try:
            self.setCurrentIndex(values.index(value))
        except ValueError:
            # Can happen when list of objects has changed but
            # param.ObjectSelector did not verify again the value
            self.set_parameter_value(values[0])


class CyclingButton(_SelectorControlBase, QtWidgets.QPushButton):

    def _create_control(self):
        QtWidgets.QPushButton.__init__(self)

        # if None is allowed: make button checkable, and special
        # timed mechanism to switch between different options when
        # clicking the button fast enough, but switch back to OFF
        # when clicking after a delay
        if self._control_has_None():
            self.setCheckable(True)
            self.toggled.connect(self._value_edited)
        else:
            self.clicked.connect(self._value_edited)
        self._last_click_time = 0

    def _update_text(self):
        super(CyclingButton, self)._update_text()
        self._update_value_display()

    def _value_from_control(self):
        # easier, and not such a big deal, to return the default value
        return self.param.default

    def _value_edited(self, _=None):
        prev_value = getattr(self.obj, self.name)
        try:
            prev_value_idx = self.all_values().index(prev_value)
        except ValueError:
            # can happen because list of objects was changed but
            # param.ObjectSelector did not verify at that time that value
            # was still valid
            prev_value_idx = -1
        if (self._control_has_None() and prev_value is not None
                and (time.time() - self._last_click_time) > 2):
            # go directly back to None
            value = None
        else:
            # cycle through values
            value_idx = (prev_value_idx + 1) % len(self.all_values())
            value = self.all_values()[value_idx]
        self._last_click_time = time.time()

        self.set_parameter_value(value)

    def _display_value(self, value):
        self.setChecked(value is not None)
        value_txt = self._tr(value) if value else self._tr('OFF')
        if not self.label:
            # add label on the button text if there is no label widget
            value_txt = (self._tr(self.param.label) + self._tr(': ') +
                         value_txt)
        self.setText(value_txt)
        # set checked state after a tiny delay, to make sure this
        # happens after the automatic toggling of the toggle button
        QtCore.QTimer.singleShot(
            100, lambda: self.setChecked(bool(value)))


class ToggleButton(_ParameterControlBase, QtWidgets.QPushButton):

    def _create_control(self):
        # push button to cycle between values
        QtWidgets.QPushButton.__init__(self)
        self.setCheckable(True)
        self.toggled.connect(self._set_parameter_from_control)

    def _update_text(self):
        super(ToggleButton, self)._update_text()
        self._update_value_display()

    def _value_from_control(self):
        return self.isChecked()

    def _display_value(self, value):
        self.setChecked(value)
        value_txt = self._tr('ON') if value else self._tr('OFF')
        if not self.label:
            # add label on the button text if there is no label widget
            value_txt = (self._tr(self.param.label) + self._tr(': ') +
                         value_txt)
        self.setText(value_txt)


class CheckBox(_ParameterControlBase, QtWidgets.QCheckBox):

    def _create_control(self):
        QtWidgets.QCheckBox.__init__(self)
        self.toggled.connect(self._set_parameter_from_control)

    def _value_from_control(self):
        return self.isChecked()

    def _display_value(self, value):
        self.setChecked(value)


class Slider(_ParameterControlBase, QtWidgets.QSlider):
    """Slider offers a fast-interacting control for an integer or float
    parameter. Its control of the parameter can be non linear, for example
    logarithmic (e.g. when value can vary between 1 and 1000, one often needs
    fine-grain control near 1, but only coarse-grain control near 1000):
    this can be adjusted with the `mode` user attribute; available modes are
    - linear    linear control between min and max
    - log       logarithmic control between min (needs to be >0) and max
    - left E    finer grain near min, coarser grain near max, value E
                controls the effect strength (typically interval [0 1],
                uses function x -> x^E)
    - right E   finer grain near max
    - middle E  finer grain near interval center (typically 0 or 1)
    - ext E     finer grain near min and max
    - tan X     use tangente function when one or both sides is infinite,
                value X controls the slope near zero if both sides are
                infinite, or near the finite side otherwise
    If `mode` is not set, it is automatically inferred from the bounds."""

    def __init__(self, *args, **kwargs):
        super(Slider, self).__init__(*args, **kwargs)

        # Add watcher on bounds
        self.obj.param.watch(self._update_value_display, self.name,
                             what='bounds')

    def _create_control(self):
        # check that bounds are defined
        bounds = self.param.bounds
        if bounds is None or any([b is None for b in bounds]):
            raise ValueError('bounds need to be defined for slider '
                             'control')
        if self._control_has_None():
            raise ValueError('slider control not available when '
                             'allowing None')
        QtWidgets.QSlider.__init__(self)
        # make (maximum-minimum) divisible by a large number of integers to
        # minimize the chances of rounding errors on float values
        self.setMinimum(0)
        self.setMaximum(6300)  # 6300 = 2^2 * 3^2 * 5^2 * 7
        self.setOrientation(Qt.Horizontal)
        self.valueChanged.connect(self._value_edited)
        self._slider_callback_enabled = True
        self.actionTriggered.connect(self._adjust_slider_step)
        # mechanism to detect double-clicks on the slider handle (see
        # mouseDoubleClickEvent below)
        self._slider_step = None
        self.sliderPressed.connect(lambda: setattr(self, '_slider_step', None))

    def mouseDoubleClickEvent(self, ev):
        # reset value to default when slider handle was double-clicked,
        # otherwise treat double-clicks as normal clicks performing a slider
        # step event
        if self._slider_step is None:
            super(Slider, self).mouseDoubleClickEvent(ev)
        else:
            if self._param_base_cls == pm.Integer:
                self._adjust_slider_step(self._slider_step)
            else:
                QAS = QtWidgets.QAbstractSlider
                if self._slider_step == QAS.SliderPageStepSub:
                    self.setValue(self.value() - self.pageStep())
                elif self._slider_step == QAS.SliderPageStepAdd:
                    self.setValue(self.value() + self.pageStep())

    def _adjust_slider_step(self, ev):
        # memorize event
        self._slider_step = ev
        # When slider is being stepped, step value by one unit if parameter
        # value is integer
        if self._param_base_cls != pm.Integer:
            return
        QAS = QtWidgets.QAbstractSlider
        value = self.parameter_value()
        bounds = self.param.bounds
        step = self.param.step  # 'step' exists as a slot!
        if ev == QAS.SliderPageStepSub:
            value -= step
            if bounds[0]:
                value = max(value, bounds[0])
            self.set_parameter_value(value)
        elif ev == QAS.SliderPageStepAdd:
            value += step
            if bounds[1]:
                value = min(value, bounds[1])
            self.set_parameter_value(value)

    def _slider_conversion(self, x, from_control: bool):
        bounds = self.param.bounds
        b, B = bounds  # type: float
        if b is not None and math.isinf(b):
            b = None
        if B is not None and math.isinf(B):
            B = None

        # determine mode
        mode = self.param.user.get('mode', None)
        if b is None or B is None:
            # at least one bound is infinite
            if mode is not None and 'tan' not in mode:
                raise ValueError("Slider mode must be 'tan' when at least one "
                                 "bound is infinite")
            mode = 'tan'
        elif mode is None:
            if (b == -B) or (b >= 0 and b + B == 2):
                # interval is centered on 0 or on 1, be more fine-grained in
                # the middle
                mode = 'middle'
            elif b > 0 and B >= 50 * b:
                # logarithmic scale
                mode = 'log'
            else:
                mode = 'linear'
        elif mode == 'log' and b <= 0:
            raise ValueError("Slider mode can't be 'log' if lower bound "
                             "isn't positive")
        pattern = '(linear|log|left|right|middle|ext|tan) *(\d*\.?\d*)'
        mode, strength = re.search(pattern, mode).groups()
        strength = float(strength) if strength else 1.

        # initial linear mapping between slider and some interval
        if mode == 'linear':
            map_control = (b, B)
            aff_value = None
        elif mode == 'log':
            map_control = (math.log(b), math.log(B))
            aff_value = None
        elif mode == 'left':
            map_control = (0, 1)
            aff_value = (b, B-b)
        elif mode == 'right':
            map_control = (1, 0)
            aff_value = (B, b-B)
        elif mode in ['middle', 'ext']:
            map_control = (-1, 1)
            aff_value = ((b + B)/2, (B - b)/2)
        elif mode == 'tan':
            if b is None and B is None:
                map_control = (-1, 1)
                aff_value = None
            elif b is None:
                map_control = (-1, 0)
                aff_value = (B, 1)
            elif B is None:
                map_control = (0, 1)
                aff_value = (b, 1)
            else:
                map_control = (math.atan(b), math.atan(B))
                aff_value = None
        else:
            raise InvalidCaseError

        # perform conversion
        m, M = self.minimum(), self.maximum()
        if from_control:
            # avoid rounding error when we are on the bounds
            if x == m:
                return b
            elif x == M:
                return B
            # map [m M] onto [0 1]
            x = (x - m) / (M - m)
            # map [0 1] onto map_control
            x = map_control[0] + (map_control[1] - map_control[0]) * x
            # perform nonlinear operation
            if mode == 'log':
                x = math.exp(x)
            elif mode in ['left', 'right', 'middle', 'ext']:
                x = math.copysign(math.pow(abs(x), (1+strength)), x)
            elif mode == 'tan':
                x = math.tan(math.pi/2 * x) * strength
            # final affinity to map result onto [b B]
            if aff_value:
                x = aff_value[0] + aff_value[1] * x
            # final corrections
            if self._param_base_cls == pm.Integer:
                x = round(x)
            if b is not None and x < b:
                x = b
            elif B is not None and x > B:
                x = B
        else:
            # initial affinity from [b B]
            if aff_value:
                x = (x - aff_value[0]) / aff_value[1]
            # perform nonlinear operation
            if mode == 'log':
                x = math.log(x)
            elif mode in ['left', 'right', 'middle', 'ext']:
                x = math.copysign(math.pow(abs(x), 1/(1+strength)), x)
            elif mode == 'tan':
                x = math.atan(x / strength) / (math.pi / 2)
            # map map_control onto [0 1]
            x = (x - map_control[0]) / (map_control[1] - map_control[0])
            # map [0 1] onto [m M]
            x = round(m + (M - m) * x)

        return x

    def _value_from_control(self):
        return self._slider_conversion(self.value(), from_control=True)

    def _value_edited(self):
        if not self._slider_callback_enabled:
            return
        prev_value = self.parameter_value()
        value = self._value_from_control()
        if value != prev_value:
            self.set_parameter_value(value)
        elif self._param_base_cls == pm.Integer:
            # value is unchanged, but slider position changed and we would
            # like to round it back to the integer marking
            self._display_value(prev_value)

    def _display_value(self, value):
        x = self._slider_conversion(value, from_control=False)

        # update slider display, but prevent its rounding effect to trigger
        # a new value change
        self._slider_callback_enabled = False
        self.setValue(x)
        self._slider_callback_enabled = True

        # update value display
        if self.label:
            value_str = text_display(value, self.param)
            txt = self._tr(self.param.label) + self._tr(': ') + value_str
            self.label.setText(txt)

    def _update_text(self):
        super(Slider, self)._update_text()
        if self.label:
            self._display_value(self.parameter_value())


class ColorButton(_ColorControlBase, QtWidgets.QLineEdit):

    def _create_control(self):
        if self._control_has_None():
            raise ValueError('color control not available when alllowing None')
        QtWidgets.QLineEdit.__init__(self)
        self.setReadOnly(True)
        self.mousePressEvent = self._choose_color

    def _display_value(self, value):
        # value is a 6-char string specifying a 24-bit value in hex
        # format, optionally preceded by a '#', e.g. '#ff0000' for red

        # display coolor name, including QtColor name if it exist,
        # and in any case hex code
        self.setText(text_display(value, self.param, self._tr))

        # use color for the control background, and make
        # foreground color black or white depending on its luminance
        luminance = np.mean([int(x) for x in bytes.fromhex(value[1:])])
        if luminance > 128:
            foreground = '#000000'
        else:
            foreground = '#ffffff'
        self.setStyleSheet("color:%s; background-color:%s;"
                                   % (foreground, value))

    def _update_text(self):
        super(ColorButton, self)._update_text()
        self._update_value_display()

    def _value_from_control(self):
        value, = re.search('(#\d{6})', self.text()).groups()
        return value

    def setEnabled(self, value):
        # When disabling the control, put background color back to default
        if value:
            self._display_value(self.parameter_value())
        else:
            self.setStyleSheet('')
        super(ColorButton, self).setEnabled(value)


class LineEdit(_ParameterControlBase, QtWidgets.QLineEdit):

    def _create_control(self):
        QtWidgets.QLineEdit.__init__(self)
        self.editingFinished.connect(self._value_edited)

        # Detect when text in control is being changed so that
        # editingFinished events will be discarded when there was no change
        self._text_changed = False
        self.textChanged.connect(
            lambda: setattr(self, '_text_changed', True))

    def _value_from_control(self):
        if self._control_has_None() and self.text().lower() == 'None':
            return None
        elif self._param_base_cls == pm.String:
            return self.text()
        elif self._param_base_cls == pm.Integer:
            return int(self.text())
        elif self._param_base_cls == pm.Number:
            return float(self.text())
        elif self._param_base_cls == pm.List:
            items = self.text().split()
            typ = self.param.class_
            # print('list:', items)
            return [typ(x) for x in items]
        else:
            raise InvalidCaseError

    def _value_edited(self, _=None):
        # Was the text really changed?
        if not self._text_changed:
            return
        else:
            self._text_changed = False

        try:
            value = self._value_from_control()
            self.set_parameter_value(value)

        except ValueError:
            # could not interpret text, do not change value and bring back
            # previous display
            expected = self._tr(
                self._param_base_cls.__name__.replace('param.', ''))
            if self._control_has_None():
                expected += self._tr('or') + '"None"'
            _error_message(self._tr('Invalid Value, %s expected') % expected)
            self._update_value_display()

    def _display_value(self, value):
        if value is None:
            self.setText('auto')
        elif self._param_base_cls == pm.String:
            self.setText(value)
        elif self._param_base_cls in [pm.Integer, pm.Number]:
            self.setText(str(value))
        elif self._param_base_cls == pm.List:
            self.setText(' '.join([str(x) for x in value]))


def parameter_control(obj: pm.Parameterized, name: str, *args, **kwargs):
    param = obj.param[name]
    param_base_cls = _get_param_base_class(param)

    if param.constant:
        control_cls = ConstantDisplay
    else:
        preferred_style = (param.user['style']
                           if isinstance(param, GraphicParameter)
                           else None)
        if param_base_cls == pm.ObjectSelector:
            # There is a list of possible values
            if preferred_style == 'button':
                control_cls = CyclingButton
            else:
                control_cls = PopupMenu
        elif param_base_cls == pm.Boolean:
            if preferred_style == 'button':
                control_cls = ToggleButton
            else:
                control_cls = CheckBox
        elif (param_base_cls in [pm.Integer, pm.Number]
              and preferred_style == 'slider'):
            control_cls = Slider
        elif param_base_cls == pm.Color:
            control_cls = ColorButton
        elif param_base_cls in [pm.Integer, pm.Number, pm.List,
                                      pm.String, pm.Color]:
            control_cls = LineEdit
        else:
            raise Exception('No control for parameter of type',
                            param_base_cls)

    return control_cls(obj, name, *args, **kwargs)


# SPECIALIZED MENU CONTROLS


class MenuItem(_ActionControlBase, QtWidgets.QAction):

    def __init__(self, label, window, callback,
                 translation: Callable[[str], str] = _noop,
                 checkable=False,
                 dots=False, tooltip=None):

        _ActionControlBase.__init__(self, translation)

        self._dots = '...' if dots else ''
        self._label = label
        self._tooltip = tooltip
        QtWidgets.QAction.__init__(self, '', window)

        self.setCheckable(checkable)
        if checkable:
            self.toggled.connect(callback)
        else:
            self.triggered.connect(callback)

        self._update_text()

    def _update_text(self):
        self.setText(self._tr(self._label) + self._dots)
        # print('action tooltip', self._tr(self._tooltip))
        self.setToolTip(self._tr(self._tooltip))


class _MenuBase(_ParameterControlBase):

    def __init__(self, window, *args, **kwargs):
        self._window = window
        _ParameterControlBase.__init__(self, *args, **kwargs)


class ToggleMenuItem(_MenuBase, QtWidgets.QAction):

    def _create_control(self):
        QtWidgets.QAction.__init__(self, '', self._window)
        self.setCheckable(True)
        self.toggled.connect(self._set_parameter_from_control)

    def _value_from_control(self):
        return self.isChecked()

    def _display_value(self, value):
        self.setChecked(value)

    def _update_text(self):
        self.setText(self._tr(self.param.label))
        self.setToolTip(self._tr(self.param.doc))


class SelectMenu(_MenuBase, _SelectorControlBase, QtWidgets.QMenu):

    def __init__(self, *args, **kwargs):
        # Initialization is a bit complicated:
        # - _MenuBase __init__ is called here, which will call
        #   _ParameterBaseControl __init__, but not the __init__ of other
        #   inheriting classes
        # - _SelectorControlBase __init__ will not be called, but its
        #   content is copied below (except for the call to
        #   _ParameterBaseControl __init__, which already occured)
        # - QtWidgets.QMenu __init__ is called in _create_control

        _MenuBase.__init__(self, *args, **kwargs)

        # Add watcher on objects
        self.obj.param.watch(self._update_objects_list, self.name, what='names')
        self.obj.param.watch(self._update_value_display, self.name, what='objects')

    def _create_control(self):
        # Sub-menu
        QtWidgets.QMenu.__init__(self, '', self._window)

        # Create one menu item per possible value
        for label, value, tooltip in zip(self.all_value_names(),
                                         self.all_values(),
                                         self.all_value_tooltips()):
            def callback(checked, val=value):
                # defining an argument with default value is needed to force
                # early binding, otherwise all callback would use the last
                # value in the values list
                # see https://stackoverflow.com/questions/3431676/creating-functions-in-a-loop
                if checked and self.parameter_value() != val:
                    self.set_parameter_value(val)
            action = MenuItem(label, self._window, callback, checkable=True,
                              tooltip=tooltip)
            action.setData(value)
            self.addAction(action)

    def _display_value(self, value):
        for action in self.actions():
            action.setChecked(action.data() == value)

    def set_translation(self, translation):
        super(SelectMenu, self).set_translation(translation)
        for action in self.actions():  # type: MenuItem
            action.set_translation(translation)

    def _update_text(self):
        self.setTitle(self._tr(self.param.label))
        self.setToolTip(self._tr(self.param.doc))

    def set_visible(self, value):
        # the menu itself is not a graphical element, it is its containing
        # menuAction that must be made visible or not
        self.menuAction().setVisible(value)

    def set_enabled(self, value):
        # the menu itself is not a graphical element, it is its containing
        # menuAction that must be made enabled or not
        self.menuAction().setEnabled(value)


class ControlMenuItem(_MenuBase, QtWidgets.QAction):
    """
    A menu item which, when clicked, will raise a proper control to edit the parameter.
    """

    def _create_control(self):
        # create the menu item...
        QtWidgets.QAction.__init__(self, '', self._window)
        self.triggered.connect(self._raise_control)

        # ... and create a panel control which will be shown only when the
        # menu item will be clicked
        self.control = parameter_control(self.obj, self.name)
        self.control.set_visible = _noop
        self.control.hide()

    def _raise_control(self):
        self.control.show()

    def _display_value(self, value):
        self.setText(self._tr(self.param.label) + self._tr(': ')
                     + text_display(value, self.param, self._tr))

    def _update_text(self):
        self._update_value_display()
        self.setToolTip(self._tr(self.param.doc))


class ColorMenuItem(ControlMenuItem, _ColorControlBase, QtWidgets.QAction):

    def _create_control(self):
        QtWidgets.QAction.__init__(self, '', self._window)
        self.triggered.connect(self._choose_color)


def menu_control(window, obj: pm.Parameterized, name: str, *args, **kwargs):
    param = obj.param[name]
    param_base_cls = _get_param_base_class(param)

    if param.constant:
        raise ValueError('No menu control for constant parameter')
    else:
        preferred_style = (param.user['style']
                           if isinstance(param, GraphicParameter)
                           else None)
        if param_base_cls == pm.ObjectSelector:
            control_cls = SelectMenu
        elif param_base_cls == pm.Boolean:
            control_cls = ToggleMenuItem
        elif param_base_cls == pm.Color:
            control_cls = ColorMenuItem
        else:
            control_cls = ControlMenuItem

    return control_cls(window, obj, name, *args, **kwargs)


# ABSTRACT CLASS FOR CONTROL OF MULTIPLE PARAMETERS


class _PanelBase:

    def __init__(self, translation=_noop):

        # translation
        self._tr = translation

    def _init_panel(self):
        raise NotImplementedError

    def auto_fill(self, obj: pm.Parameterized):
        # Fill the panel by scanning the object's parameters, create
        # sections for nested parameters
        for name, param in obj.param.objects().items():
            if name == 'name':
                # parameter 'name' is created automatically and is not worth
                # being displayed
                continue

            value = getattr(obj, name)
            if isinstance(value, pm.Parameterized):
                # nested parameters
                self.add_section(param.label, tooltip=param.doc)
                self.auto_fill(value)
            else:
                self.add_entry(obj, name)

    def add_section(self, label, *args, tooltip=None, **kwargs):
        raise NotImplementedError

    def add_entry(self, obj: pm.Parameterized, names=None, *args, **kwargs):

        # Multiple names? -> return a list of entries
        if names is None:
            names = obj.param.objects().keys()
        if not isinstance(names, str):
            return [self._add_entry(obj, name, *args, **kwargs) for name in names]

        self._add_entry(obj, names, *args, **kwargs)

    def _add_entry(self, obj: pm.Parameterized, name: str, *args, **kwargs):
        raise NotImplementedError

    def set_translation(self, translation):
        raise NotImplementedError


# QT PANEL FOR CONTROLLING MULTIPLE PARAMETERS


class _Section:

    def __init__(self, grid, title=None, tooltip=None, unfolded=True,
                 translation=_noop):
        # type: (QtWidgets.QGridLayout, str, str, bool, Callable[[str], str]) -> None
        self.grid = grid
        self.unfolded = unfolded
        self._tr = translation

        # List of widgets (memorize objects to keep them alive)
        self.controls = []
        self.buttons = []

        # Title
        self.button = None  # type: _FoldingLabel
        self.title = None   # type: QtWidgets.QLabel
        self._title = title
        self._tooltip = tooltip
        if title is not None:
            self.display_title()

    def display_title(self):
        # Fold/Unfold button
        self.button = _FoldingLabel(self.unfolded)
        self.button.setVisible(False)  # visibility will be set to True as soon as some child entries will be added
        self.button.toggle_fold.connect(self.toggle_fold)

        # Title label
        self.title = QtWidgets.QLabel()
        self.update_title_text()
        self.update_title_text()
        self.title.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                 QtWidgets.QSizePolicy.Maximum)
        self.title.mouseReleaseEvent = self.button.mouseReleaseEvent  # quite a hack!

        # Show them
        row = self.grid.rowCount()
        self.grid.addWidget(self.button, row, 0)
        self.grid.addWidget(self.title, row, 1)

    def update_title_text(self):
        if self.title is not None:
            self.title.setText('<div style="font-weight: bold; font-size: '
                               '10pt;">' + self._tr(self._title) + '</div>')
            self.title.setToolTip(self._tr(self._tooltip))

    def add_entry(self, obj: pm.Parameterized, names):
        # Multiple names? -> return a list of entries
        if not isinstance(names, str):
            return [self.add_entry(obj, field) for field in names]

        name = names
        control = _SectionControl(obj, name,
                                  parent_section=self, translation=self._tr)
        row = self.grid.rowCount()
        self.grid.addWidget(control.label, row, 1)
        self.grid.addWidget(control.control, row, 2)
        self.controls.append(control)  # keep objects in memory

        # if this is the first "in use" control, this will make the section visible
        self.update_header_visible()

        return control

    def add_button(self, label, action, **kwargs):
        x = _SectionButton(label, action,
                           parent_section=self, translation=self._tr, **kwargs)
        row = self.grid.rowCount()
        self.grid.addWidget(x, row, 1, 1, 2)
        self.buttons[label] = x
        self.update_header_visible()
        return x

    def toggle_fold(self):
        self.unfolded = not self.unfolded

        # Change visibility of entries
        for control in self.controls:
            control.update_actual_visible()
        for button in self.buttons:
            button.setVisible(self.unfolded)

    def set_enabled(self, value):
        for control in self.controls:
            control.set_enabled(value)

    def set_visible(self, value):
        for control in self.controls:
            control.set_visible(value)

    def update_header_visible(self):
        if self.button is not None:
            value = any([control.visible for control in self.controls])
            self.button.setVisible(value)
            self.title.setVisible(value)

    def update_display(self):
        for control in self.controls:
            control.entry._update_value_display()

    def set_translation(self, translation):
        self._tr = translation
        self.update_title_text()
        for x in self.controls:
            x.set_translation(translation)
        for x in self.buttons:
            x.set_translation(translation)


class _SectionElement:
    """A section element has its visibility controlled both by the section
    being folded or unfolded, and its own visibility attribute."""

    def __init__(self, *args, parent_section: _Section=None,  **kwargs):
        self.parent_section = parent_section
        self.visible = True
        super(_SectionElement, self).__init__(*args, **kwargs)

    def set_visible(self, value):
        self.visible = value
        self.update_actual_visible()
        self.parent_section.update_header_visible()

    def update_actual_visible(self):
        value = self.visible and self.parent_section.unfolded
        super(_SectionElement, self).set_visible(value)


class _SectionControl(_SectionElement):
    """A wrapper of _ParameterControl that overrides its set_visible methods."""

    def __init__(self, *args, parent_section: _Section = None, **kwargs):
        _SectionElement.__init__(self, parent_section=parent_section)

        # Control
        self.control = parameter_control(*args, do_label=True, **kwargs)
        self._set_control_actual_visible = self.control.set_visible
        self.control.set_visible = self.set_visible

        # Shortcut on label
        self.label = self.control.label

        # Should the control and label be initialized as not visible?
        if not self.control.param.visible:
            # note that control has already been set as not visible at
            # initialization, but this was before its set_visible
            # function was hacked, so we call self.set_visible to hide also the
            # label
            self.set_visible(False)

    def update_actual_visible(self):
        value = self.visible and self.parent_section.unfolded
        self._set_control_actual_visible(value)

    def set_translation(self, translation):
        self.control.set_translation(translation)


class _Button(QtWidgets.QPushButton):

    def __init__(self, label, action, checkable=False, tooltip=None,
                 translation=_noop):
        super(_Button, self).__init__()
        self.setCheckable(checkable)
        self._label = label
        self._tooltip = tooltip
        self._update_text(translation)
        if checkable:
            self.toggled.connect(action)
        else:
            self.pressed.connect(action)

    def _update_text(self, translation):
        self.setText(translation(self._label))
        self.setToolTip(translation(self._tooltip))


class _SectionButton(_SectionElement, _Button):
    pass


class _FoldingLabel(QtWidgets.QLabel):

    toggle_fold = QtCore.pyqtSignal()

    def __init__(self, unfolded):
        # Create label
        super(_FoldingLabel, self).__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum,
                           QtWidgets.QSizePolicy.Maximum)

        # Fix size so it won't change when symbole will be changed
        self.setText('>')
        self.size = super(_FoldingLabel, self).sizeHint()

        # Update display according to folding state
        self.unfolded = unfolded
        self.update_display()

    def sizeHint(self):
        # Avoid resizing based on content
        return self.size

    def update_display(self):
        symbol = 'V' if self.unfolded else '>'
        self.setText('<div style="font-weight: bold; font-size: '
                           '10pt;">' + symbol + '</div>')
        self.resize(self.size)  # do not change the size

    def mouseReleaseEvent(self, ev):
        self.unfolded = not self.unfolded
        self.update_display()
        self.toggle_fold.emit()


class ControlPanel(_PanelBase, QtWidgets.QWidget):

    def __init__(self, obj: pm.Parameterized=None, *args, **kwargs):
        _PanelBase.__init__(self, *args, **kwargs)
        QtWidgets.QWidget.__init__(self)

        # 2-columns grid layout + a vertical spacer that maintains the grid
        # on top
        v_layout = QtWidgets.QVBoxLayout()
        self.setLayout(v_layout)
        self.grid = QtWidgets.QGridLayout()
        v_layout.addLayout(self.grid)
        spacer = QtWidgets.QWidget()
        v_layout.addWidget(spacer)

        # List of widgets: organized by sections (first section has no label)
        self.current_section = _Section(self.grid)
        self.sections = {'': self.current_section}

        # Then init the parameter control, this might fill the widget if a
        # Paramterized object input is provided
        # automatic layout to control parameter argument
        if obj is not None:
            self.auto_fill(obj)

    def add_section(self, name, obj=None, names=None,
                    tooltip=None, unfolded=True):
        # Create new section
        self.current_section = _Section(self.grid, name,
                                        tooltip=tooltip, unfolded=unfolded,
                                        translation=self._tr)
        self.sections[name] = self.current_section
        label = self.current_section.title

        # Add entry(ies) to this section
        if obj is not None:
            entries = self.current_section.add_entry(obj, names)
        else:
            entries = None

        return label, entries

    def _add_entry(self, obj: pm.Parameterized, name: str):
        # Add entry(ies) to the current section

        return self.current_section.add_entry(obj, name)

    def add_button(self, label, action, **kwargs):
        return self.current_section.add_button(label, action, **kwargs)

    def update_display(self):
        for section in self.sections.values():
            if isinstance(section, _Section):
                section.update_display()

    def set_translation(self, translation):
        if translation is None:
            translation = _noop
        self._tr = translation
        for section in self.sections.values():
            section.set_translation(translation)


# MENU FOR CONTROLLING MULTIPLE PARAMETERS

class ControlMenu(_PanelBase, QtWidgets.QMenu):

    def __init__(self, window, title,
                 obj: pm.Parameterized=None, *args, **kwargs):
        super(ControlMenu, self).__init__(*args, **kwargs)
        QtWidgets.QMenu.__init__(self, self._tr(title), window)

        # Remember title for when translation will be changed
        self._title = title

        # Add immediately the menu to the window
        self._window = window
        window.menuBar().addMenu(self)

        # List of sections and entries
        self.sections = {}
        self.entries = []

        # Auto-fill if an object is provided
        if obj is not None:
            if title is None:
                RuntimeError('Please provide a menu title')
            self.auto_fill(obj)

    def add_section(self, label, *args, tooltip=None, **kwargs):
        self.addSeparator()
        section = self.addSection(self._tr(label))
        self.sections[label] = section

    def _add_entry(self, obj: pm.Parameterized, name: str, *args, **kwargs):
        entry = menu_control(self._window, obj, name, *args, **kwargs)
        self.entries.append(entry)
        if isinstance(entry, QtWidgets.QMenu):
            self.addMenu(entry)
        else:
            self.addAction(entry)

    def add_action(self, label, callback, **kwargs):
        action = MenuItem(label, self._window, callback, **kwargs)
        self.entries.append(action)
        self.addAction(action)

    def set_translation(self, translation):
        if translation is None:
            translation = _noop

        # store translation
        self._tr = translation

        # update title and entries
        self.setTitle(translation(self._title))
        for label, section in self.sections.items():
            section.setText(translation(label))
        for x in self.entries:
            x.set_translation(translation)


# DEMO


if __name__ == "__main__":

    import numpy as np
    import math

    # define dummy 'translation' functions
    def to_upper_case(s: str):
        if s is None:
            return None
        else:
            return s.upper()

    def caesar_cipher(s: str):
        if s is None:
            return None
        x = np.frombuffer(bytes(s, 'ascii'), dtype='uint8').copy()
        index_up = np.logical_or(np.logical_and(97 <= x, x < 122),
                                 np.logical_and(65 <= x, x < 90))
        index_z = (x == 122)
        index_Z = (x == 90)
        x[index_up] += 1  # a-y -> b-z, A-Y -> B-Z
        x[index_z] = 97   # z -> a
        x[index_Z] = 65   # Z -> A
        return bytes(x).decode()


    # Example Parameterized object
    class PosParam(pm.Parameterized):

        shape = GObjectSelector('star',
                                ['circle', 'polygon', 'star'],
                                style='button',
                                doc="select drawing's shape",
                                allow_None=True)
        n_edge = GInteger(31,
                          bounds=[3, 1000], style='slider', step=2,
                          label="Number of edges",
                          doc="select number of edges of the polygon or star")
        sharpness = GNumber(.65,
                          bounds=[0, 1], style='slider',
                          doc="choose how far edge connections should go")

        x = GNumber(0., bounds=[-1, 1], style='slider',
                    doc="horizontal cooordinate of the shape center",
                    expert=True)
        y = GNumber(0., bounds=[-1, 1], style='slider',
                    doc="vertical cooordinate of the shape center",
                    expert=True)
        zoom = GNumber(150., bounds=[10, 1e4], style='slider')

        def __init__(self):
            super(PosParam, self).__init__()

    class EdgeParam(pm.Parameterized):

        color = GColor('#000000', allow_None=True)
        width = GNumber(1., bounds=[0, 20], style='slider', mode='left')
        join_style = GObjectSelector(QtGui.QPen().joinStyle(),
                                     objects={'bevel': Qt.BevelJoin,
                                              'miter': Qt.MiterJoin,
                                              'round': Qt.RoundJoin},
                                     expert=True)
        miter_limit = GNumber(math.inf, #bounds=[0, None],
                              style='edit', expert=True)

        @pm.depends('color', watch=True)
        def change_color(self):
            active = self.color is not None
            for name in ['width', 'join_style']:
                param = self.param[name]
                param.user['active'] = active
                show = param.user.get('show', True)
                param.visible = active and show
            self.set_meter_limit_active()

        @pm.depends('join_style', watch=True)
        def set_meter_limit_active(self):
            active = self.color is not None and (self.join_style == Qt.MiterJoin)
            param = self.param['miter_limit']
            param.user['active'] = active
            show = param.user.get('show', True)
            param.visible = active and show

        def __init__(self):
            super(EdgeParam, self).__init__()
            self.change_color()

    class FillParam(pm.Parameterized):

        color = GColor('#008080', allow_None=True)
        fill_rule = GObjectSelector(Qt.OddEvenFill,
                                    objects={'full': Qt.WindingFill,
                                             'odd-even': Qt.OddEvenFill},
                                    expert=True)

        @pm.depends('color', watch=True)
        def change_color(self):
            active = self.color is not None
            for name in ['fill_rule']:
                param = self.param[name]
                param.user['active'] = active
                show = param.user.get('show', True)
                param.visible = active and show

        def __init__(self):
            super(FillParam, self).__init__()
            self.change_color()

    class ShapeParam(pm.Parameterized):

        antialiasing = GBoolean(True, expert=True)

        pos = pm.Parameter(pm.Parameterized(),
                           label='Position',
                           doc='Shape position parameters')
        edge = pm.Parameter(pm.Parameterized())
        fill = pm.Parameter(pm.Parameterized())

        def __init__(self):
            super(ShapeParam, self).__init__()
            self.pos = PosParam()
            self.edge = EdgeParam()
            self.fill = FillParam()

    class MenuParam(pm.Parameterized):

        show_expert = GBoolean(False, label='Show expert parameters')
        translation = GObjectSelector(_noop,
                                      objects={'Default': _noop,
                                               'Upper case': to_upper_case,
                                               'Caesar cipher': caesar_cipher})

    class AllParam(pm.Parameterized):

        shape_par = pm.Parameter(pm.Parameterized())
        menu_par = pm.Parameter(pm.Parameterized())

        def __init__(self):
            super(AllParam, self).__init__()
            self.shape_par = ShapeParam()
            self.menu_par = MenuParam()

            self.menu_par.param.watch(self.show_expert_parameters,
                                      'show_expert')
            self.show_expert_parameters()

        def show_expert_parameters(self, _=None):
            show = self.menu_par.show_expert

            for param in list_all_parameters(self.shape_par):
                is_expert = param.user.get('expert', False)
                if is_expert:
                    param.user['show'] = show
                    active = param.user.get('active', True)
                    param.visible = active and show

    # instantiate parameters
    all_par = AllParam()
    shape_par = all_par.shape_par
    menu_par = all_par.menu_par

    # This function will test the modification of some parameter attributes
    def test_watcher():
        p = shape_par.pos.param.n_edge
        p.bounds = ([3, 8]
                    if p.bounds == [3, 1000]
                    else [3, 1000])
        p = shape_par.pos.param.shape
        p.objects = (['circle', 'polygon']
                     if p.objects == ['circle', 'polygon', 'star']
                     else ['circle', 'polygon', 'star'])
        p = shape_par.edge.param.join_style
        objects_dict = {'bevel': Qt.BevelJoin,
                        'miter': Qt.MiterJoin,
                        'round': Qt.RoundJoin}
        names = list(objects_dict.keys())
        objects = list(objects_dict.values())
        if p.objects == objects:
            p.names = names[1:]
            p.objects = objects[1:]
        else:
            p.names = names
            p.objects = objects

    # This function resets all parameters to their default values
    def reset_parameters():
        par_list = list_all_parameters(all_par, out='Parameterized')
        for obj, names in par_list:  # type: pm.Parameterized, List[str]
            # with pm.batch_watch(obj, run=True):
            for name in names:
                setattr(obj, name, obj.param[name].default)

    # When no shape is selected, all controls (except shape itself) are
    # disabled, otherwise some position parameters visibility depend on
    # shape value
    @pm.depends(shape_par.pos.param.shape, watch=True)
    def check_shape(_=None):
        # enable/disable all parameters
        pos_par = shape_par.pos
        no_shape = pos_par.shape is None
        for param in list_all_parameters(shape_par, 'Parameter'):
            param.readonly = no_shape
        # re-enable shape if necessary
        if no_shape:
            pos_par.param.shape.readonly = False
            return
        # n_edge visibility
        param = pos_par.param.n_edge
        active = pos_par.shape in ['polygon', 'star']
        param.user['active'] = active
        show = param.user.get('show', True)
        param.visible = active and show
        # sharpness visibility
        param = pos_par.param.sharpness
        active = pos_par.shape in ['star']
        param.user['active'] = active
        show = param.user.get('show', True)
        param.visible = active and show

    check_shape()

    # Some drawing controlled by the parameters
    class ShapeWidget(QtWidgets.QWidget):

        def __init__(self):
            super(ShapeWidget, self).__init__()

            # self.setGeometry(0, 0, 280, 170)

            # redraw on any parameter change
            params = list_all_parameters(shape_par, out='Parameters')
            for param, names in params:
                param.watch(self.redraw, names)

        def sizeHint(self) -> QtCore.QSize:
            return QtCore.QSize(400, 400)

        def paintEvent(self, ev: QtGui.QPaintEvent) -> None:

            # no drawing
            pos_par = shape_par.pos
            if pos_par.shape is None:
                return

            qp = QtGui.QPainter()
            qp.begin(self)

            if shape_par.antialiasing:
                qp.setRenderHint(QtGui.QPainter.Antialiasing)

            edge_par = shape_par.edge
            pen = qp.pen()
            if edge_par.color is None:
                pen.setStyle(Qt.NoPen)
            else:
                pen.setColor(q_color_from_hex(edge_par.color))
                pen.setWidthF(edge_par.width)
                pen.setJoinStyle(edge_par.join_style)
                pen.setMiterLimit(edge_par.miter_limit)
            qp.setPen(pen)

            fill_par = shape_par.fill
            if fill_par.color is not None:
                qp.setBrush(q_color_from_hex(fill_par.color))

            x = self.width()/2 + pos_par.x * pos_par.zoom
            y = self.height()/2 + pos_par.y * pos_par.zoom
            if pos_par.shape == 'circle':
                qp.drawEllipse(QtCore.QPoint(x, y),
                               pos_par.zoom, pos_par.zoom)
            else:
                if pos_par.shape == 'polygon':
                    n_draw = 1
                    step = 1
                elif pos_par.shape == 'star':
                    m = 1
                    M = (pos_par.n_edge - 1) // 2
                    step = int(np.round(m + (M-m) * pos_par.sharpness))
                    # it might be necessary to draw several polygons because a
                    # single polygon does not pass through all the edges
                    n_draw = math.gcd(step, pos_par.n_edge)
                else:
                    raise ValueError('invalid pos_par')
                for k in range(n_draw):
                    steps = k + step * np.arange(pos_par.n_edge // n_draw + 1)
                    theta = (2 * np.pi / pos_par.n_edge * steps)
                    points = np.column_stack((
                        x + np.sin(theta)*pos_par.zoom,
                        y - np.cos(theta)*pos_par.zoom))
                    points = [QtCore.QPointF(*point) for point in points]
                    polygon = QtGui.QPolygonF(points)
                    qp.drawPolygon(polygon,
                                   fillRule=fill_par.fill_rule)

            qp.end()

        @pm.depends(shape_par.param.pos, watch=True)
        def redraw(self, *args, **kwargs):
            self.repaint()

    # Example Main Window program
    class ShapeWindow(QtWidgets.QMainWindow):

        def __init__(self):
            super(ShapeWindow, self).__init__()

            # Central widget
            self.setCentralWidget(QtWidgets.QSplitter())

            # Panel to control parameters
            self.control_panel = ControlPanel(shape_par)
            self.centralWidget().addWidget(self.control_panel)

            # Menus
            # (menus generated automatically from menu_par)
            self.menus = ControlMenu(self, 'General', menu_par)
            # (additional menus call custom functions)
            self.menus.add_section('Actions')
            self.menus.add_action('Change some attributes', test_watcher,
                                  tooltip='This will change n_edge bounds '
                                          'and shape and join_style objects lists')
            self.menus.add_action('Reset all parameters to default values',
                                  reset_parameters)
            # # (try a second automatic menu controlling shape parameters!)
            self.second_menus = ControlMenu(self, 'Shape', shape_par)

            # Translation
            menu_par.param.watch(self._update_translation, 'translation')

            # Shape panel
            self.paint = ShapeWidget()
            self.centralWidget().addWidget(self.paint)

        def test_translation(self, do_translate):
            def tr(x):
                return None if x is None else '[' + x + ']'
            if do_translate:
                self.control_panel.set_translation(tr)
            else:
                self.control_panel.set_translation(None)

        def _update_translation(self, event):
            tr = menu_par.translation
            self.control_panel.set_translation(tr)
            self.menus.set_translation(tr)

    # Display main window
    app = QtWidgets.QApplication([])
    window = ShapeWindow()
    # window.control_panel.add_button('Change some attributes', test_watcher,
    #                                 tooltip='This will change n_edge bounds '
    #                                         'and shape and join_style '
    #                                         'objects lists')
    window.show()

    app.exec()

