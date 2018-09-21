"""
Unit test for watch mechanism
"""
from . import API1TestCase

import param

class TestWatch(API1TestCase):

    class SimpleWatchExample(param.Parameterized):
        a = param.Integer(default=0)

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
if __name__ == "__main__":
    import nose
    nose.runmodule()

