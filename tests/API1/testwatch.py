"""
Unit test for watch mechanism
"""
import copy

import param

from param.parameterized import discard_events

from . import API1TestCase
from .utils import MockLoggingHandler


class Accumulator(object):

    def __init__(self):
        self.args = []
        self.kwargs = []

    def __call__(self, *args, **kwargs):
        self.args.append(args)
        self.kwargs.append(kwargs)

    def call_count(self):
        return max(len(self.args), len(self.kwargs))

    def args_for_call(self, number):
        return self.args[number]

    def kwargs_for_call(self, number):
        return self.kwargs[number]



class SimpleWatchExample(param.Parameterized):
    a = param.Parameter(default=0)
    b = param.Parameter(default=0)
    c = param.Parameter(default=0)
    d = param.Integer(default=0)
    e = param.Event()
    f = param.Event()

    def method(self, event):
        self.b = self.a * 2


class SimpleWatchSubclass(SimpleWatchExample):
    pass


class WatchMethodExample(SimpleWatchSubclass):

    @param.depends('a', watch='queued')
    def _clip_a(self):
        if self.a > 3:
            self.a = 3

    @param.depends('b', watch=True)
    def _clip_b(self):
        if self.b > 10:
            self.b = 10

    @param.depends('b', watch=True)
    def _set_c(self):
        self.c = self.b*2

    @param.depends('c', watch=True)
    def _set_d_bounds(self):
        self.param.d.bounds = (self.c, self.c*2)

    @param.depends('e', watch=True)
    def _e_event_triggered(self):
        assert self.e is True
        self.d = 30

    @param.depends('f', watch=True)
    def _f_event_triggered(self):
        assert self.f is True
        self.b = 420

class WatchSubclassExample(WatchMethodExample):

    pass


class TestWatch(API1TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestWatch, cls).setUpClass()
        log = param.parameterized.get_logger()
        cls.log_handler = MockLoggingHandler(level='DEBUG')
        log.addHandler(cls.log_handler)

    def setUp(self):
        super(TestWatch, self).setUp()
        self.accumulator = 0
        self.list_accumulator = []

    def test_triggered_when_changed(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)

    def test_discard_events_decorator(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        with discard_events(obj):
            obj.a = 1
        self.assertEqual(self.accumulator, 0)
        obj.a = 2
        self.assertEqual(self.accumulator, 2)

    def test_priority_levels(self):
        def accumulator1(change):
            self.list_accumulator.append('A')
        def accumulator2(change):
            self.list_accumulator.append('B')

        obj = SimpleWatchExample()
        obj.param.watch(accumulator1, 'a', precedence=2)
        obj.param.watch(accumulator2, 'a', precedence=1)

        obj.a = 1
        assert self.list_accumulator == ['B', 'A']

    def test_priority_levels_batched(self):
        def accumulator1(change):
            self.list_accumulator.append('A')
        def accumulator2(change):
            self.list_accumulator.append('B')

        obj = SimpleWatchExample()
        obj.param.watch(accumulator1, 'a', precedence=2)
        obj.param.watch(accumulator2, 'b', precedence=1)

        obj.param.update(a=1, b=2)
        assert self.list_accumulator == ['B', 'A']

    def test_triggered_when_changed_iterator_type(self):
        def accumulator(change):
            self.accumulator = change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = []
        self.assertEqual(self.accumulator, [])
        obj.a = tuple()
        self.assertEqual(self.accumulator, tuple())

    def test_triggered_when_changed_mapping_type(self):
        def accumulator(change):
            self.accumulator = change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = []
        self.assertEqual(self.accumulator, [])
        obj.a = {}
        self.assertEqual(self.accumulator, {})

    def test_untriggered_when_unchanged(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 1
        self.assertEqual(self.accumulator, 1)

    def test_triggered_when_unchanged_complex_type(self):
        def accumulator(change):
            self.accumulator += 1

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        subobj = object()
        obj.a = subobj
        self.assertEqual(self.accumulator, 1)
        obj.a = subobj
        self.assertEqual(self.accumulator, 2)

    def test_triggered_when_unchanged_if_not_onlychanged(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a', onlychanged=False)
        obj.a = 1

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].what, 'value')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 1)
        self.assertEqual(args[0].type, 'set')

        obj.a = 1
        args = accumulator.args_for_call(1)
        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].what, 'value')
        self.assertEqual(args[0].old, 1)
        self.assertEqual(args[0].new, 1)
        self.assertEqual(args[0].type, 'set')

    def test_untriggered_when_unwatched(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.param.unwatch(watcher)
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

    def test_warning_unwatching_when_unwatched(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, 'a')
        obj.param.unwatch(watcher)
        obj.param.unwatch(watcher)
        self.log_handler.assertEndsWith('WARNING',
                            ' to remove.')

    def test_simple_batched_watch_setattr(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a', 'b'])

        obj.a = 2
        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)

        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 2)
        self.assertEqual(args[0].type, 'changed')

        obj.b = 3
        self.assertEqual(accumulator.call_count(), 2)
        args = accumulator.args_for_call(1)

        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'b')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 3)
        self.assertEqual(args[0].type, 'changed')

    def test_batched_watch_context_manager(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a','b'])

        with param.batch_watch(obj):
            obj.a = 2
            obj.b = 3

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)

        self.assertEqual(len(args), 2)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 2)
        self.assertEqual(args[0].type, 'changed')
        self.assertEqual(args[1].name, 'b')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 3)
        self.assertEqual(args[1].type, 'changed')

    def test_nested_batched_watch_setattr(self):

        obj = SimpleWatchExample()

        accumulator = Accumulator()
        obj.param.watch(accumulator, ['a', 'c'])

        def set_c(*events):
            obj.c = 3

        obj.param.watch(set_c, ['a', 'b'])

        obj.param.update(a=2)
        self.assertEqual(obj.c, 3)

        # Change inside watch callback should have triggered
        # second call to accumulator
        self.assertEqual(accumulator.call_count(), 2)

    def test_simple_batched_watch(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a','b'])
        obj.param.update(a=23, b=42)

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 23)
        self.assertEqual(args[0].type, 'changed')

        self.assertEqual(args[1].name, 'b')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 42)
        self.assertEqual(args[1].type, 'changed')

    def test_simple_class_batched_watch(self):

        accumulator = Accumulator()

        obj = SimpleWatchSubclass
        watcher = obj.param.watch(accumulator, ['a','b'])
        obj.param.update(a=23, b=42)

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 23)
        self.assertEqual(args[0].type, 'changed')

        self.assertEqual(args[1].name, 'b')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 42)
        self.assertEqual(args[1].type, 'changed')

        SimpleWatchExample.param.unwatch(watcher)
        obj.param.update(a=0, b=0)

    def test_simple_batched_watch_callback_reuse(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a','b'])
        obj.param.watch(accumulator, ['c'])

        obj.param.update(a=23, b=42, c=99)

        self.assertEqual(accumulator.call_count(), 2)
        # Order may be undefined for Python <3.6
        for args in [accumulator.args_for_call(i) for i in [0,1]]:
            if len(args) == 1: # ['c']
                self.assertEqual(args[0].name, 'c')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 99)
                self.assertEqual(args[0].type, 'changed')

            elif len(args) == 2: # ['a', 'b']
                self.assertEqual(args[0].name, 'a')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 23)
                self.assertEqual(args[0].type, 'changed')

                self.assertEqual(args[1].name, 'b')
                self.assertEqual(args[1].old, 0)
                self.assertEqual(args[1].new, 42)
                self.assertEqual(args[0].type, 'changed')
            else:
                raise Exception('Invalid number of arguments')

    def test_context_manager_batched_watch_reuse(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a','b'])
        obj.param.watch(accumulator, ['c'])

        with param.batch_watch(obj):
            obj.a = 23
            obj.b = 42
            obj.c = 99

        self.assertEqual(accumulator.call_count(), 2)
        # Order may be undefined for Python <3.6
        for args in [accumulator.args_for_call(i) for i in [0, 1]]:
            if len(args) == 1:  # ['c']
                self.assertEqual(args[0].name, 'c')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 99)
                self.assertEqual(args[0].type, 'changed')

            elif len(args) == 2:  # ['a', 'b']
                self.assertEqual(args[0].name, 'a')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 23)
                self.assertEqual(args[0].type, 'changed')

                self.assertEqual(args[1].name, 'b')
                self.assertEqual(args[1].old, 0)
                self.assertEqual(args[1].new, 42)
                self.assertEqual(args[0].type, 'changed')
            else:
                raise Exception('Invalid number of arguments')

    def test_subclass_batched_watch(self):

        accumulator = Accumulator()

        obj = SimpleWatchSubclass()

        obj.param.watch(accumulator, ['b','c'])
        obj.param.update(b=23, c=42)

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'b')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 23)
        self.assertEqual(args[0].type, 'changed')

        self.assertEqual(args[1].name, 'c')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 42)
        self.assertEqual(args[1].type, 'changed')

    def test_nested_batched_watch(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()

        def update(*changes):
            obj.param.update(a=10, d=12)

        obj.param.watch(accumulator, ['a', 'b', 'c', 'd'])
        obj.param.watch(update, ['b', 'c'])
        obj.param.update(b=23, c=42)

        self.assertEqual(accumulator.call_count(), 2)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'b')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 23)
        self.assertEqual(args[0].type, 'changed')

        self.assertEqual(args[1].name, 'c')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 42)
        self.assertEqual(args[1].type, 'changed')

        args = accumulator.args_for_call(1)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 10)
        self.assertEqual(args[0].type, 'changed')

        self.assertEqual(args[1].name, 'd')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 12)
        self.assertEqual(args[1].type, 'changed')

    def test_nested_batched_watch_not_onlychanged(self):
        accumulator = Accumulator()

        obj = SimpleWatchSubclass()

        obj.param.watch(accumulator, ['b','c'], onlychanged=False)
        obj.param.update(b=0, c=0)

        self.assertEqual(accumulator.call_count(), 1)

        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'b')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 0)
        self.assertEqual(args[0].type, 'set')

        self.assertEqual(args[1].name, 'c')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 0)
        self.assertEqual(args[1].type, 'set')

    def test_watch_deepcopy(self):
        obj = SimpleWatchExample()

        obj.param.watch(obj.method, ['a'])

        copied = copy.deepcopy(obj)

        copied.a = 2

        self.assertEqual(copied.b, 4)
        self.assertEqual(obj.b, 0)

    def test_watch_event_value_trigger(self):
        obj = WatchMethodExample()
        obj.e = True
        self.assertEqual(obj.d, 30)
        self.assertEqual(obj.e, False)

    def test_watch_event_trigger_method(self):
        obj = WatchMethodExample()
        obj.param.trigger('e')
        self.assertEqual(obj.d, 30)
        self.assertEqual(obj.e, False)

    def test_watch_event_batched_trigger_method(self):
        obj = WatchMethodExample()
        obj.param.trigger('e', 'f')
        self.assertEqual(obj.d, 30)
        self.b = 420
        self.assertEqual(obj.e, False)
        self.assertEqual(obj.f, False)

class TestWatchMethod(API1TestCase):

    def test_dependent_params(self):
        obj = WatchMethodExample()

        obj.b = 3
        self.assertEqual(obj.c, 6)

    def test_multiple_watcher_dispatch_queued(self):
        obj = WatchMethodExample()
        obj2 = SimpleWatchExample()

        def link(event):
            obj2.a = event.new

        obj.param.watch(link, 'a', queued=True)
        obj.a = 4
        self.assertEqual(obj.a, 3)
        self.assertEqual(obj2.a, 3)

    def test_multiple_watcher_dispatch(self):
        obj = WatchMethodExample()
        obj2 = SimpleWatchExample()

        def link(event):
            obj2.b = event.new

        obj.param.watch(link, 'b')
        obj.b = 11
        self.assertEqual(obj.b, 10)
        self.assertEqual(obj2.b, 11)

    def test_multiple_watcher_dispatch_on_param_attribute(self):
        obj = WatchMethodExample()
        accumulator = Accumulator()

        obj.param.watch(accumulator, 'd', 'bounds')
        obj.c = 2
        self.assertEqual(obj.param.d.bounds, (2, 4))
        self.assertEqual(accumulator.call_count(), 1)

        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 1)

        self.assertEqual(args[0].name, 'd')
        self.assertEqual(args[0].what, 'bounds')
        self.assertEqual(args[0].old, None)
        self.assertEqual(args[0].new, (2, 4))
        self.assertEqual(args[0].type, 'changed')

    def test_depends_with_watch_on_subclass(self):
        obj = WatchSubclassExample()

        obj.b = 3
        self.assertEqual(obj.c, 6)

    def test_watcher_method_deepcopy(self):
        obj = WatchMethodExample(b=5)

        copied = copy.deepcopy(obj)

        copied.b = 11
        self.assertEqual(copied.b, 10)
        self.assertEqual(obj.b, 5)


class TestWatchValues(API1TestCase):

    def setUp(self):
        super(TestWatchValues, self).setUp()
        self.accumulator = 0
        self.list_accumulator = []

    def test_triggered_when_values_changed(self):
        def accumulator(a):
            self.accumulator += a

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)

    def test_untriggered_when_values_unchanged(self):
        def accumulator(a):
            self.accumulator += a

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 1
        self.assertEqual(self.accumulator, 1)

    def test_untriggered_when_values_unwatched(self):
        def accumulator(a):
            self.accumulator += a

        obj = SimpleWatchExample()
        watcher = obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.param.unwatch(watcher)
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

    def test_priority_levels(self):
        def accumulator1(**kwargs):
            self.list_accumulator.append('A')
        def accumulator2(**kwargs):
            self.list_accumulator.append('B')

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator1, 'a', precedence=2)
        obj.param.watch_values(accumulator2, 'a', precedence=1)

        obj.a = 1
        assert self.list_accumulator == ['B', 'A']

    def test_priority_levels_batched(self):
        def accumulator1(**kwargs):
            self.list_accumulator.append('A')
        def accumulator2(**kwargs):
            self.list_accumulator.append('B')

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator1, 'a', precedence=2)
        obj.param.watch_values(accumulator2, 'b', precedence=1)

        obj.param.update(a=1, b=2)
        assert self.list_accumulator == ['B', 'A']

    def test_simple_batched_watch_values_setattr(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator, ['a','b'])

        obj.a = 2
        self.assertEqual(accumulator.call_count(), 1)
        kwargs = accumulator.kwargs_for_call(0)

        self.assertEqual(len(kwargs), 1)
        self.assertEqual(kwargs, {'a':2})

        obj.b = 3
        self.assertEqual(accumulator.call_count(), 2)
        kwargs = accumulator.kwargs_for_call(1)
        self.assertEqual(kwargs, {'b':3})

    def test_simple_batched_watch_values(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator, ['a','b'])
        obj.param.update(a=23, b=42)

        self.assertEqual(accumulator.call_count(), 1)
        kwargs = accumulator.kwargs_for_call(0)
        self.assertEqual(kwargs, {'a':23, 'b':42})

    def test_simple_batched_watch_values_callback_reuse(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        obj.param.watch_values(accumulator, ['a','b'])
        obj.param.watch_values(accumulator, ['c'])

        obj.param.update(a=23, b=42, c=99)

        self.assertEqual(accumulator.call_count(), 2)
        # Order may be undefined for Python <3.6
        for kwargs in [accumulator.kwargs_for_call(i) for i in [0,1]]:
            if len(kwargs) == 1: # ['c']
                self.assertEqual(kwargs, {'c':99})
            elif len(kwargs) == 2: # ['a', 'b']
                self.assertEqual(kwargs, {'a':23, 'b':42})
            else:
                raise Exception('Invalid number of arguments')


class TestWatchAttributes(API1TestCase):

    def setUp(self):
        super(TestWatchAttributes, self).setUp()
        self.accumulator = []

    def tearDown(self):
        SimpleWatchExample.param['d'].bounds = None

    def test_watch_class_param_attribute(self):
        def accumulator(a):
            self.accumulator += [a.new]

        SimpleWatchExample.param.watch(accumulator, ['d'], 'bounds')
        SimpleWatchExample.param['d'].bounds = (0, 3)
        assert self.accumulator == [(0, 3)]

    def test_watch_instance_param_attribute(self):
        def accumulator(a):
            self.accumulator += [a.new]

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['d'], 'bounds')

        # Ensure watching an instance parameter makes copy
        assert obj.param.objects('current')['d'] is not SimpleWatchExample.param['d']

        obj.param['d'].bounds = (0, 3)
        assert SimpleWatchExample.param['d'].bounds is None
        assert self.accumulator == [(0, 3)]


class TestTrigger(API1TestCase):

    def setUp(self):
        super(TestTrigger, self).setUp()
        self.accumulator = 0

    def test_simple_trigger_one_param(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a'])
        obj.param.trigger('a')
        self.assertEqual(accumulator.call_count(), 1)

        args = accumulator.args_for_call(0)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 0)
        self.assertEqual(args[0].type, 'triggered')

    def test_simple_trigger_when_batched(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a'])
        with param.batch_watch(obj):
            obj.param.trigger('a')
        self.assertEqual(accumulator.call_count(), 1)

        args = accumulator.args_for_call(0)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 0)
        # Note: This is not strictly correct
        self.assertEqual(args[0].type, 'changed')

    def test_simple_trigger_one_param_change(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a'])
        obj.a = 42
        self.assertEqual(accumulator.call_count(), 1)

        obj.param.trigger('a')
        self.assertEqual(accumulator.call_count(), 2)

        args = accumulator.args_for_call(0)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 42)
        self.assertEqual(args[0].type, 'changed')

        args = accumulator.args_for_call(1)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 42)
        self.assertEqual(args[0].new, 42)
        self.assertEqual(args[0].type, 'triggered')

    def test_simple_trigger_two_params(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()
        obj.param.watch(accumulator, ['a','b'])
        obj.param.trigger('a','b')
        self.assertEqual(accumulator.call_count(), 1)

        args = accumulator.args_for_call(0)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 0)
        self.assertEqual(args[0].type, 'triggered')

        self.assertEqual(args[1].name, 'b')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 0)
        self.assertEqual(args[1].type, 'triggered')

    def test_sensitivity_of_widget_name(self):
        # From: https://github.com/holoviz/param/issues/614

        class ExampleWidget(param.Parameterized):
            value = param.Number(default=1)


        class Example(param.Parameterized):
            da = param.Number(default=1)
            date_picker = param.Parameter(ExampleWidget())
            picker = param.Parameter(ExampleWidget())

            @param.depends(
                "date_picker.value",
                "picker.value",
                watch=True,
            )
            def load_data(self):
                self.da += 1  # To trigger plot_time

            @param.depends("da")
            def plot_time(self):
                return self.da


        example = Example()
        example.picker.value += 1
        assert example.da == 2

        example.picker.value += 1
        assert example.da == 3
