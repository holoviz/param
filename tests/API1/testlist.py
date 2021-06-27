import param
from . import API1TestCase
# TODO: I copied the tests from testobjectselector, although I
# struggled to understand some of them. Both files should be reviewed
# and cleaned up together.

# TODO: tests copied from testobjectselector could use assertRaises
# context manager (and could be updated in testobjectselector too).

class TestListParameters(API1TestCase):

    def setUp(self):
        super(TestListParameters, self).setUp()
        class P(param.Parameterized):
            e = param.List([5,6,7], item_type=int)
            l = param.List(["red","green","blue"], item_type=str, bounds=(0,10))

        self.P = P

    def test_default_None(self):
        class Q(param.Parameterized):
            r = param.List(default=[])  #  Also check None)

    def test_set_object_constructor(self):
        p = self.P(e=[6])
        self.assertEqual(p.e, [6])

    def test_set_object_outside_bounds(self):
        p = self.P()
        try:
            p.l=[6]*11
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_wrong_type(self):
        p = self.P()
        try:
            p.e=['s']
        except TypeError:
            pass
        else:
            raise AssertionError("Object allowed of wrong type.")

    def test_set_object_not_None(self):
        p = self.P(e=[6])
        try:
            p.e = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")


if __name__ == "__main__":
    import nose
    nose.runmodule()
