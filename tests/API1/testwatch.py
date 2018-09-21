"""
Unit test for watch mechanism
"""
from . import API1TestCase

from .utils import MockLoggingHandler
import param


class TestWatch(API1TestCase):

    class SimpleWatchExample(param.Parameterized):
        a = param.Integer(default=0)


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

        obj = self.SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)


    def test_untriggered_when_unchanged(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = self.SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 1
        self.assertEqual(self.accumulator, 1)


    def test_untriggered_when_unwatched(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = self.SimpleWatchExample()
        obj.param.watch(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.param.unwatch(accumulator, 'a')
        obj.a = 2
        self.assertEqual(self.accumulator, 1)


    def test_warning_unwatching_when_unwatched(self):
        def accumulator(change):
            self.accumulator += change.new

        obj = self.SimpleWatchExample()

        obj.param.unwatch(accumulator, 'a')
        self.log_handler.assertEndsWith('WARNING',
                            'No effect unwatching subscriber that was not being watched')



class TestWatchValues(API1TestCase):

    class SimpleWatchExample(param.Parameterized):
        a = param.Integer(default=0)

    def setUp(self):
        super(TestWatchValues, self).setUp()
        self.accumulator = 0

    def test_triggered_when_values_changed(self):
        def accumulator(a):
            self.accumulator += a

        obj = self.SimpleWatchExample()
        obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 2
        self.assertEqual(self.accumulator, 3)


    def test_untriggered_when_values_unchanged(self):
        def accumulator(a):
            self.accumulator += a

        obj = self.SimpleWatchExample()
        obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.a = 1
        self.assertEqual(self.accumulator, 1)


    def test_untriggered_when_values_unwatched(self):
        def accumulator(a):
            self.accumulator += a

        obj = self.SimpleWatchExample()
        obj.param.watch_values(accumulator, 'a')
        obj.a = 1
        self.assertEqual(self.accumulator, 1)
        obj.param.unwatch(accumulator, 'a')
        obj.a = 2
        self.assertEqual(self.accumulator, 1)


if __name__ == "__main__":
    import nose
    nose.runmodule()

