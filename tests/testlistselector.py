import unittest
import param

# TODO: I copied the tests from testobjectselector, although I
# struggled to understand some of them. Both files should be reviewed
# and cleaned up together.

# TODO: tests copied from testobjectselector could use assertRaises
# context manager (and could be updated in testobjectselector too).

class TestListSelectorParameters(unittest.TestCase):

    def setUp(self):

        class P(param.Parameterized):
            e = param.ListSelector(default=[5],objects=[5,6,7])
            f = param.ListSelector(default=10)
            h = param.ListSelector(default=None)
            g = param.ListSelector(default=None,objects=[7,8])
            i = param.ListSelector(default=[7],objects=[9],check_on_set=False)

        self.P = P

    def test_set_object_constructor(self):
        p = self.P(e=[6])
        self.assertEqual(p.e, [6])

    def test_set_object_outside_bounds(self):
        p = self.P(e=[6])
        try:
            p.e = [9]
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr(self):
        p = self.P(e=[6])
        p.f = [9]
        self.assertEqual(p.f, [9])
        p.g = [7]
        self.assertEqual(p.g, [7])
        p.i = [12]
        self.assertEqual(p.i, [12])


    def test_set_object_not_None(self):
        p = self.P(e=[6])
        p.g = [7]
        try:
            p.g = None
        except TypeError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_one_object_not_None(self):
        p = self.P(e=[6])
        p.g = [7]
        try:
            p.g = [None]
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

        
    def test_set_object_setattr_post_error(self):
        p = self.P(e=[6])
        p.f = [9]
        self.assertEqual(p.f, [9])
        p.g = [7]
        try:
            p.g = [None]
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

        self.assertEqual(p.g, [7])
        p.i = [12]
        self.assertEqual(p.i, [12])

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.ListSelector([5],objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ListSelector created outside range.")


    def test_initialization_no_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.ListSelector([5],objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ListSelector created without range.")


if __name__ == "__main__":
    import nose
    nose.runmodule()
