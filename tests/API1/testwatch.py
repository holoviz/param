"""
Unit test for watch mechanism
"""
from . import API1TestCase

from .utils import MockLoggingHandler
import param


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

    def test_triggered_when_changed(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)


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
        def accumulator(change):
            self.accumulator += change.new

        obj = SimpleWatchExample()
        obj.param.watch(accumulator, 'a', onlychanged=False)
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 1
        self.assertEqual(self.accumulator, 2)


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
        watcher = obj.param.watch(accumulator, ['a','b'])

        obj.a = 2
        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)

        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 2)

        obj.b = 3
        self.assertEqual(accumulator.call_count(), 2)
        args = accumulator.args_for_call(1)

        self.assertEqual(len(args), 1)
        self.assertEqual(args[0].name, 'b')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 3)


    def test_simple_batched_watch(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        watcher = obj.param.watch(accumulator, ['a','b'])
        obj.param.set_param(a=23, b=42)

        self.assertEqual(accumulator.call_count(), 1)
        args = accumulator.args_for_call(0)
        self.assertEqual(len(args), 2)

        self.assertEqual(args[0].name, 'a')
        self.assertEqual(args[0].old, 0)
        self.assertEqual(args[0].new, 23)

        self.assertEqual(args[1].name, 'b')
        self.assertEqual(args[1].old, 0)
        self.assertEqual(args[1].new, 42)


    def test_simple_batched_watch_callback_reuse(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        watcher1 = obj.param.watch(accumulator, ['a','b'])
        watcher2 = obj.param.watch(accumulator, ['c'])

        obj.param.set_param(a=23, b=42, c=99)

        self.assertEqual(accumulator.call_count(), 2)
        # Order may be undefined for Python <3.6
        for args in [accumulator.args_for_call(i) for i in [0,1]]:
            if len(args) == 1: # ['c']
                self.assertEqual(args[0].name, 'c')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 99)

            elif len(args) == 2: # ['a', 'b']
                self.assertEqual(args[0].name, 'a')
                self.assertEqual(args[0].old, 0)
                self.assertEqual(args[0].new, 23)

                self.assertEqual(args[1].name, 'b')
                self.assertEqual(args[1].old, 0)
                self.assertEqual(args[1].new, 42)
            else:
                raise Exception('Invalid number of arguments')



class TestWatchValues(API1TestCase):

    def setUp(self):
        super(TestWatchValues, self).setUp()
        self.accumulator = 0

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


    def test_simple_batched_watch_values_setattr(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        watcher = obj.param.watch_values(accumulator, ['a','b'])

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
        watcher = obj.param.watch_values(accumulator, ['a','b'])
        obj.param.set_param(a=23, b=42)

        self.assertEqual(accumulator.call_count(), 1)
        kwargs = accumulator.kwargs_for_call(0)
        self.assertEqual(kwargs, {'a':23, 'b':42})


    def test_simple_batched_watch_values_callback_reuse(self):

        accumulator = Accumulator()

        obj = SimpleWatchExample()
        watcher1 = obj.param.watch_values(accumulator, ['a','b'])
        watcher2 = obj.param.watch_values(accumulator, ['c'])

        obj.param.set_param(a=23, b=42, c=99)

        self.assertEqual(accumulator.call_count(), 2)
        # Order may be undefined for Python <3.6
        for kwargs in [accumulator.kwargs_for_call(i) for i in [0,1]]:
            if len(kwargs) == 1: # ['c']
                self.assertEqual(kwargs, {'c':99})
            elif len(kwargs) == 2: # ['a', 'b']
                self.assertEqual(kwargs, {'a':23, 'b':42})
            else:
                raise Exception('Invalid number of arguments')


if __name__ == "__main__":
    import nose
    nose.runmodule()
