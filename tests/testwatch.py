"""Unit test for watch mechanism."""
import asyncio
import copy
import pickle
import re
import threading
import unittest

import param
import pytest

from param.parameterized import Skip, batch, batch_call_watchers, discard_events

from .utils import MockLoggingHandler


class Accumulator:

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


class TestWatch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        log = param.parameterized.get_logger()
        cls.log_handler = MockLoggingHandler(level='DEBUG')
        log.addHandler(cls.log_handler)

    def setUp(self):
        super().setUp()
        self.accumulator = 0
        self.list_accumulator = []

    def tearDown(self):
        SimpleWatchExample.param.d.bounds = None

    def test_triggered_when_changed(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)

    def test_triggered_ignore_skip(self):
        def accumulator(change):
            if change.new > 1:
                raise Skip()
            self.accumulator += 1

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

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
        obj.a = ()
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
        # Idempotent, not error raised.
        obj.param.unwatch(watcher)

    def test_watcher_remove(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        watcher.remove()
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

    def test_watcher_remove_idempotent(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, 'a')
        watcher.remove()
        # Idempotent, no error raised.
        watcher.remove()

    def test_watcher_remove_class_level(self):
        accumulator = Accumulator()

        obj = SimpleWatchSubclass
        watcher = obj.param.watch(accumulator, ['a', 'b'])
        obj.param.update(a=23, b=42)
        self.assertEqual(accumulator.call_count(), 1)

        watcher.remove()
        obj.param.update(a=0, b=0)
        self.assertEqual(accumulator.call_count(), 1)

    def test_watcher_remove_only_removes_one_registration(self):
        # Two watchers registered with identical fields (same callback,
        # same parameter, same options) are tuple-equal. Removing one
        # must only drop a single registration, not both.
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        watcher1 = obj.param.watch(accumulator, 'a')
        watcher2 = obj.param.watch(accumulator, 'a')
        self.assertEqual(watcher1, watcher2)
        self.assertIsNot(watcher1, watcher2)

        watcher1.remove()
        obj.a = 1
        self.assertEqual(self.accumulator, 1)

        watcher2.remove()
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

    def test_watcher_remove_on_falsy_instance(self):
        # remove() must resolve the owner via `inst is None`, not
        # `inst or cls`: an inst that is falsy (e.g. defines __len__)
        # must not be mistaken for a missing inst and routed to cls.
        class FalsyWatchExample(param.Parameterized):
            a = param.Parameter(default=0)

            def __len__(self):
                return 0

        obj = FalsyWatchExample()
        self.assertFalse(obj)

        def accumulator(change):
            self.accumulator += change.new

        watcher = obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)

        watcher.remove()
        obj.a = 2
        self.assertEqual(self.accumulator, 1)

    def test_watcher_survives_deepcopy_and_can_be_unwatched(self):
        # Parameterized.__setstate__ rebuilds each stored watcher as a
        # new Watcher with the same field values, so a watcher copied
        # alongside its object must still be usable to unwatch it.
        calls = []

        def accumulator(change):
            calls.append(change.new)

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, 'a')

        obj2, watcher2 = copy.deepcopy((obj, watcher))
        self.assertIsNot(watcher2, watcher)
        self.assertIs(watcher2.inst, obj2)

        obj2.param.unwatch(watcher2)
        obj2.a = 1
        self.assertEqual(calls, [])

        # The original watcher and object are unaffected.
        obj.a = 5
        self.assertEqual(calls, [5])

    def test_watcher_survives_pickle_roundtrip_and_can_be_unwatched(self):
        obj = SimpleWatchExample()
        watcher = obj.param.watch(obj.method, 'a')

        obj2, watcher2 = pickle.loads(pickle.dumps((obj, watcher)))
        self.assertIsNot(watcher2, watcher)
        self.assertIs(watcher2.inst, obj2)

        watcher2.remove()
        obj2.a = 1
        self.assertEqual(obj2.b, 0)

        # The original watcher and object are unaffected.
        obj.a = 5
        self.assertEqual(obj.b, 10)

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

        with param.parameterized.batch_call_watchers(obj):
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

        with param.parameterized.batch_call_watchers(obj):
            obj.a = 23
            obj.b = 42
            obj.c = 99

        self.assertEqual(accumulator.call_count(), 2)
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

    def test_watch_param_slot(self):
        obj = SimpleWatchExample()

        cls_events = []
        SimpleWatchExample.param.watch(cls_events.append, 'd', what='bounds')

        obj.param.objects('existing')['d'].bounds = (1, 2)

        assert len(cls_events) == 1
        assert cls_events[0].name == 'd'
        assert cls_events[0].what == 'bounds'
        assert cls_events[0].new == (1, 2)

        inst_events = []
        obj.param.watch(inst_events.append, 'd', what='bounds')

        obj.param.objects('existing')['d'].bounds = (3, 4)

        assert len(cls_events) == 1
        assert len(inst_events) == 1
        assert inst_events[0].name == 'd'
        assert inst_events[0].what == 'bounds'
        assert inst_events[0].new == (3, 4)

    def test_param_watch_no_side_effect(self):
        # Example 1 of https://github.com/holoviz/param/issues/829

        class P(param.Parameterized):
            x = param.Parameter()

        store = []
        P.param.watch(store.append, 'x')

        P.x = 10

        assert len(store) == 1
        assert 'value' in P.param.x.watchers

        p = P()

        assert 'value' in P.param.x.watchers

        # Checking this does not have bad side-effects
        p.param.x

        # Watcher still on the class Parameter
        assert 'value' in P.param.x.watchers
        # Watcher not on the instance
        assert p.param.x.watchers == {}

        P.x = 20
        # Watcher still triggered
        assert len(store) == 2

        p.x = 30
        # Watcher not triggered on instance update
        assert len(store) == 2

    def test_param_watch_multiple_instances(self):
        # Example 4 of https://github.com/holoviz/param/issues/829

        class P(param.Parameterized):
            x = param.Parameter()
            l = param.List([])

            @param.depends('x:constant', watch=True)
            def cb(self):
                self.l.append(self.param.x.constant)

        assert P.param.x.watchers == {}

        p = P()

        # Creating the instance ???
        assert P.param.x.watchers == {}

        p2 = P()

        # Modify constant on p2.param.x
        p2.param.x.constant = True

        # The event should only trigger on p2, not p
        assert p2.l == [True]
        assert p.l == []

    def test_watch_deepcopy(self):
        obj = SimpleWatchExample()

        obj.param.watch(obj.method, ['a'])
        obj.param.watch(lambda x: None, 'd', what='bounds')

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

    def test_watch_watchers_exposed(self):
        obj = SimpleWatchExample()

        obj.param.watch(lambda: '', ['a', 'b'])

        pw = obj.param.watchers
        assert isinstance(pw, dict)
        for pname in ('a', 'b'):
            assert pname in pw
            assert 'value' in pw[pname]
            assert isinstance(pw[pname]['value'], list) and len(pw[pname]['value']) == 1
            assert isinstance(pw[pname]['value'][0], param.parameterized.Watcher)

    def test_watch_watchers_modified(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()

        obj.param.watch(accumulator, ['a', 'b'])

        pw = obj.param.watchers
        del pw['a']

        obj.param.update(a=1, b=1)

        assert accumulator.call_count() == 1
        args = accumulator.args_for_call(0)
        assert len(args) == 1
        assert args[0].name == 'b'

    def test_watch_watchers_setter_public(self):
        accumulator = Accumulator()
        obj = SimpleWatchExample()

        obj.param.watch(accumulator, ['a', 'b'])

        obj.param.watchers = {}

        obj.param.update(a=1, b=1)

        assert accumulator.call_count() == 0

    def test_watch_watchers_class_error(self):
        with pytest.raises(
            TypeError,
            match=r"Accessing `\.param\.watchers` is only supported on a Parameterized instance, not class\."
        ):
            SimpleWatchExample.param.watchers

    def test_watch_watchers_class_set_error(self):
        with pytest.raises(
            TypeError,
            match=r"Setting `\.param\.watchers` is only supported on a Parameterized instance, not class\."
        ):
            SimpleWatchExample.param.watchers = {}

    def test_watch_error_unsafe_before_initialized(self):
        class P(param.Parameterized):

            x = param.Parameter()

            def __init__(self, **params):
                with pytest.raises(
                    RuntimeError,
                    match=re.escape(
                        '(Un)registering a watcher on a partially initialized Parameterized instance '
                        'is not allowed. Ensure you have called super().__init__(**) in the '
                        'Parameterized instance constructor before trying to set up a watcher.',
                    )
                ):
                    self.param.watch(print, 'x')

        P()


    def test_watch_raises_bad_parameter(self):
        obj = SimpleWatchExample()
        with pytest.raises(
            ValueError,
            match="does_not_exist parameter was not found in list of parameters of class SimpleWatchExample"
        ):
            obj.param.watch(lambda e: print(e), 'does_not_exist')


class TestWatchMethod(unittest.TestCase):

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


class TestWatchValues(unittest.TestCase):

    def setUp(self):
        super().setUp()
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
        for kwargs in [accumulator.kwargs_for_call(i) for i in [0,1]]:
            if len(kwargs) == 1: # ['c']
                self.assertEqual(kwargs, {'c':99})
            elif len(kwargs) == 2: # ['a', 'b']
                self.assertEqual(kwargs, {'a':23, 'b':42})
            else:
                raise Exception('Invalid number of arguments')


class TestWatchAttributes(unittest.TestCase):

    def setUp(self):
        super().setUp()
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


class TestTrigger(unittest.TestCase):

    def setUp(self):
        super().setUp()
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
        with param.parameterized.batch_call_watchers(obj):
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

    def test_trigger_error_unsafe_before_initialized(self):
        class P(param.Parameterized):

            x = param.Parameter()

            def __init__(self, **params):
                with pytest.raises(
                    RuntimeError,
                    match=re.escape(
                        'Triggering watchers on a partially initialized Parameterized instance '
                        'is not allowed. Ensure you have called super().__init__(**params) in '
                        'the Parameterized instance constructor before trying to set up a watcher.',
                    )
                ):
                    self.param.trigger('x')

        P()

    def test_watch_multiple_same_parameter_name(self):
        class P(param.Parameterized):
            x = param.Integer()

        p = P()
        runs = []
        p.param.watch(runs.append, ["x", "x"])
        p.x = 1
        assert len(runs) == 1


class TestBatch:

    def test_without_batch_two_objects_glitch(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        calls = []
        param.bind(lambda x, y: calls.append(x + y), a.param.x, b.param.y, watch=True)

        a.x = 2
        b.y = 20

        assert calls == [12, 22]

    def test_batch_across_two_parameterized_instances(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        calls = []
        param.bind(lambda x, y: calls.append(x + y), a.param.x, b.param.y, watch=True)

        with batch():
            a.x = 2
            b.y = 20

        # param.bind registers the same callback separately on each source,
        # but batch() coalesces it into one call, seeing both settled.
        assert calls == [22]

    def test_batch_plain_multi_param_watcher(self):
        class P(param.Parameterized):
            a = param.Number(default=1)
            b = param.Number(default=10)

        p = P()
        calls = []
        p.param.watch(lambda *events: calls.append([e.new for e in events]), ['a', 'b'])

        with batch():
            p.a = 2
            p.b = 20

        assert calls == [[2, 20]]

    def test_batch_depends_watch(self):
        class Q(param.Parameterized):
            a = param.Number(default=1)
            b = param.Number(default=10)
            log = param.List(default=[])

            @param.depends('a', 'b', watch=True)
            def _combine(self):
                self.log.append(self.a + self.b)

        q = Q()
        with batch():
            q.a = 2
            q.b = 20

        assert q.log == [22]

    def test_batch_three_independent_classes(self):
        class C(param.Parameterized):
            p = param.Number(default=1)

        class D(param.Parameterized):
            q = param.Number(default=1)

        class E(param.Parameterized):
            r = param.Number(default=1)

        c, d, e = C(), D(), E()
        calls = []
        param.bind(
            lambda p, q, r: calls.append(p + q + r),
            c.param.p, d.param.q, e.param.r, watch=True,
        )

        with batch():
            c.p = 10
            d.q = 100
            e.r = 1000

        assert calls == [1110]

    def test_batch_nesting_drains_once_at_outermost_exit(self):
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()
        calls = []
        p.param.watch(lambda e: calls.append(e.new), 'x')

        with batch():
            with batch():
                p.x = 5
            assert calls == []
        assert calls == [5]

    def test_batch_composes_with_batch_call_watchers(self):
        class P(param.Parameterized):
            a = param.Number(default=1)
            b = param.Number(default=10)

        p = P()
        calls = []
        p.param.watch(lambda *events: calls.append([e.new for e in events]), ['a', 'b'])

        with batch():
            with param.parameterized.batch_call_watchers(p):
                p.a = 2
                p.b = 20

        assert calls == [[2, 20]]

    def test_batch_exception_still_notifies(self):
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()
        calls = []
        p.param.watch(lambda e: calls.append(e.new), 'x')

        with pytest.raises(ValueError, match='boom'):
            with batch():
                p.x = 7
                raise ValueError('boom')

        assert calls == [7]

    def test_batch_thread_isolation(self):
        class P(param.Parameterized):
            x = param.Number(default=1)

        class Q(param.Parameterized):
            y = param.Number(default=1)

        p, q = P(), Q()
        p_calls, q_calls = [], []
        p.param.watch(lambda e: p_calls.append(e.new), 'x')
        q.param.watch(lambda e: q_calls.append(e.new), 'y')

        # Both threads are inside their own, still-open `batch()` at the
        # same time (forced by the barrier), to prove two concurrent
        # transactions do not share one registry.
        barrier = threading.Barrier(2)

        def worker(obj, attr, value):
            with batch():
                setattr(obj, attr, value)
                barrier.wait(timeout=5)

        t1 = threading.Thread(target=worker, args=(p, 'x', 99))
        t2 = threading.Thread(target=worker, args=(q, 'y', 88))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert p_calls == [99]
        assert q_calls == [88]

    def test_batch_does_not_change_ordinary_unbatched_watch_behavior(self):
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()
        calls = []
        p.param.watch(lambda e: calls.append(e.new), 'x')
        p.x = 2
        assert calls == [2]

    def test_batch_coalesces_watch_values_across_owners(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        calls = []
        cb = lambda **kwargs: calls.append(kwargs)
        a.param.watch_values(cb, 'x')
        b.param.watch_values(cb, 'y')

        with batch():
            a.x = 2
            b.y = 20

        assert calls == [{'x': 2, 'y': 20}]

    def test_batch_respects_precedence_across_owners_and_groups(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        order = []
        shared = lambda *events: order.append('shared')
        early = lambda *events: order.append('early')
        a.param.watch(shared, 'x', precedence=5)
        b.param.watch(shared, 'y', precedence=5)
        a.param.watch(early, 'x', precedence=1)

        with batch():
            a.x = 2
            b.y = 20

        assert order == ['early', 'shared']

    def test_batch_does_not_merge_the_same_callback_registered_with_different_settings(self):
        # `shared` is registered with a different precedence on each
        # owner: merging them would leave one owner's precedence
        # silently overridden, so they stay separate calls instead,
        # each still running at its own precedence.
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        order = []
        shared = lambda *events: order.append('shared')
        middle = lambda *events: order.append('middle')
        a.param.watch(shared, 'x', precedence=5)
        b.param.watch(shared, 'y', precedence=1)
        a.param.watch(middle, 'x', precedence=3)

        with batch():
            a.x = 2
            b.y = 20

        assert order == ['shared', 'middle', 'shared']

    def test_batch_does_not_merge_watchers_with_different_onlychanged(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        calls = []
        shared = lambda *events: calls.append(len(events))
        a.param.watch(shared, 'x')
        b.param.watch(shared, 'y', onlychanged=False)

        with batch():
            a.x = 2
            b.y = 20

        # Two separate calls, not one merged call with two events.
        assert calls == [1, 1]

    def test_batch_does_not_merge_watchers_with_different_modes(self):
        # `a` is watched positionally (`mode='args'`), `b` by keyword
        # (`mode='kwargs'` via `watch_values`); merging would have to
        # guess which mode wins and silently drop the other owner's event.
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        received = []
        shared = lambda *args, **kwargs: received.append((args, kwargs))
        a.param.watch(shared, 'x')
        b.param.watch_values(shared, 'y')

        with batch():
            a.x = 2
            b.y = 20

        assert len(received) == 2
        assert received[0][0][0].new == 2
        assert received[1][1] == {'y': 20}

    def test_batch_keeps_a_keyword_name_collision_across_owners_separate(self):
        # Both `a` and `c` are watched with `watch_values` for a parameter
        # named `x`; merging into one kwargs call would let one owner's
        # value silently overwrite the other's under the same key.
        class A(param.Parameterized):
            x = param.Number(default=1)

        class C(param.Parameterized):
            x = param.Number(default=100)

        a, c = A(), C()
        calls = []
        shared = lambda **kwargs: calls.append(dict(kwargs))
        a.param.watch_values(shared, 'x')
        c.param.watch_values(shared, 'x')

        with batch():
            a.x = 2
            c.x = 200

        assert sorted(calls, key=lambda d: d['x']) == [{'x': 2}, {'x': 200}]

    def test_batch_merges_bound_methods_of_the_same_instance(self):
        # `obj.method` creates a new bound-method object on every access,
        # but two of them referring to the same instance and function
        # compare equal, so they merge like any other shared callback.
        calls = []

        class Logger(param.Parameterized):
            def log(self, *events):
                calls.append(len(events))

        logger = Logger()

        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        a.param.watch(logger.log, 'x')
        b.param.watch(logger.log, 'y')

        with batch():
            a.x = 2
            b.y = 20

        assert calls == [2]

    def test_batch_coalesces_a_queued_watcher_across_owners(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()
        calls = []
        cb = lambda *events: calls.append('cb')
        a.param.watch(cb, 'x', queued=True)
        b.param.watch(cb, 'y', queued=True)

        with batch():
            a.x = 2
            b.y = 20

        assert calls == ['cb']

    @pytest.mark.parametrize('use', [
        lambda obj: batch_call_watchers(obj),
        lambda obj: obj.param.update(x=2),
        lambda obj: discard_events(obj),
    ], ids=['batch_call_watchers', 'update', 'discard_events'])
    def test_batch_does_not_leave_an_object_permanently_batched(self, use):
        # `batch_call_watchers`/`.param.update()`/`discard_events` save
        # `_BATCH_WATCH`, temporarily set it, then restore it. Used inside
        # `batch()`, the saved value must be the real prior flag, not a
        # value that only looks true because a transaction happens to be
        # open, or the object is left permanently "batched" afterwards.
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()
        with batch():
            use(p)

        assert p._param__private.parameters_state['BATCH_WATCH'] is False

        calls = []
        p.param.watch(lambda e: calls.append(e.new), 'x')
        p.x = 5
        assert calls == [5]

    def test_batch_delivers_a_queued_watchers_own_side_effect(self):
        # A `queued=True` watcher that sets another attribute on its own
        # owner queues that new event rather than firing inline; `batch()`
        # must keep draining until that queued event is also delivered,
        # not stop after the first pass.
        class P(param.Parameterized):
            a = param.Number(default=1)
            b = param.Number(default=1)

        p = P()
        log = []
        p.param.watch(lambda *e: (log.append(('a', p.a)), setattr(p, 'b', p.b + 1)), 'a', queued=True)
        p.param.watch(lambda *e: log.append(('b', p.b)), 'b')

        with batch():
            p.a = 5

        assert log == [('a', 5), ('b', 2)]

    def test_batch_delivers_a_cascading_sets_settled_value_not_a_mix(self):
        # A watcher on `a` sets an attribute on an unrelated `b` as a side
        # effect; a callback watching two of `b`'s parameters must see the
        # fully settled state for both, never a value from partway through.
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)
            z = param.Number(default=0)

        a, b = A(), B()
        seen = []
        param.bind(lambda y, z: seen.append((y, z)), b.param.y, b.param.z, watch=True)
        a.param.watch(lambda *e: setattr(b, 'z', 2), 'x')

        with batch():
            a.x = 20
            b.y = 20

        assert all(pair == (20, 2) for pair in seen)

    def test_batch_still_delivers_other_objects_when_one_watcher_raises(self):
        class A(param.Parameterized):
            x = param.Number(default=1)

        class B(param.Parameterized):
            y = param.Number(default=10)

        a, b = A(), B()

        def bad(*events):
            raise ValueError('boom')

        calls = []
        a.param.watch(bad, 'x')
        b.param.watch(lambda *events: calls.append(events[0].new), 'y')

        with pytest.raises(ValueError, match='boom'):
            with batch():
                a.x = 2
                b.y = 20

        assert calls == [20]

    def test_batch_flushes_touched_objects_in_touch_order(self):
        classes = [type(f'_BatchOrder{i}', (param.Parameterized,), {'x': param.Number(default=1)})
                   for i in range(5)]
        objs = [cls() for cls in classes]
        order = []
        for i, obj in enumerate(objs):
            obj.param.watch(lambda e, i=i: order.append(i), 'x')

        with batch():
            for obj in objs:
                obj.x = 2

        assert order == [0, 1, 2, 3, 4]

    def test_batch_ignores_a_transaction_already_closed_by_the_time_it_runs(self):
        # A task started inside the block inherits the same `batch()`
        # transaction through `contextvars` (`asyncio.create_task` copies
        # the current `Context`), but by the time it actually runs, the
        # block may already have exited and flushed. It must fall back to
        # ordinary, immediate behavior rather than queuing into a
        # transaction that will never drain again.
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()
        calls = []
        p.param.watch(lambda e: calls.append(e.new), 'x')

        async def main():
            with batch():
                task = asyncio.ensure_future(asyncio.sleep(0))
                await task

                async def setter():
                    p.x = 99
                deferred = asyncio.ensure_future(setter())
            # `batch()` has already exited and flushed by this point; the
            # task above hasn't run its body yet.
            await deferred

        asyncio.run(main())
        assert calls == [99]

    def test_batch_body_error_is_not_masked_by_a_flush_error(self):
        # A watcher raising during the flush must not replace the error
        # that was already propagating out of the block; it is reported
        # as a warning instead, so it is not silently lost either.
        class P(param.Parameterized):
            x = param.Number(default=1)

        p = P()

        def bad(*events):
            raise RuntimeError('flush boom')

        p.param.watch(bad, 'x')

        with pytest.warns(RuntimeWarning, match='flush boom'):
            with pytest.raises(ValueError, match='body boom'):
                with batch():
                    p.x = 2
                    raise ValueError('body boom')
