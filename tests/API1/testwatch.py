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
        self.switch = False

    def test_triggered_when_changed(self):
        def switcher(*args):
            self.switch = (not self.switch)

        obj = self.SimpleWatchExample()
        obj.param.watch(switcher, 'a')
        obj.a = 1
        self.assertEqual(self.switch, True)
        obj.a = 2
        self.assertEqual(self.switch, False)


    def test_untriggered_when_unchanged(self):
        def switcher(*args):
            self.switch = (not self.switch)

        obj = self.SimpleWatchExample()
        obj.param.watch(switcher, 'a')
        obj.a = 1
        self.assertEqual(self.switch, True)
        obj.a = 1
        self.assertEqual(self.switch, True)

if __name__ == "__main__":
    import nose
    nose.runmodule()

