import param
from . import API1TestCase
# TODO: I copied the tests from testobjectselector, although I
# struggled to understand some of them. Both files should be reviewed
# and cleaned up together.

# TODO: tests copied from testobjectselector could use assertRaises
# context manager (and could be updated in testobjectselector too).

class TestListSelectorParameters(API1TestCase):

    def setUp(self):
        super(TestListSelectorParameters, self).setUp()
        class P(param.Parameterized):
            e = param.ListSelector(default=[5],objects=[5,6,7])
            f = param.ListSelector(default=10)
            h = param.ListSelector(default=None)
            g = param.ListSelector(default=None,objects=[7,8])
            i = param.ListSelector(default=[7],objects=[9],check_on_set=False)

        self.P = P

    def test_default_None(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=None)

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


    ##################################################################
    ##################################################################
    ### new tests (not copied from testobjectselector)

    def test_bad_default(self):
        with self.assertRaises(TypeError):
            class Q(param.Parameterized):
                r = param.ListSelector(default=6,check_on_set=True)

    def test_implied_check_on_set(self):
        with self.assertRaises(TypeError):
            class Q(param.Parameterized):
                r = param.ListSelector(default=7,objects=[7,8])

    def test_default_not_checked(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=[6])

    ##########################
    # CEBALERT: not sure it makes sense for ListSelector to be set to
    # a non-iterable value (except None). I.e. I think this first test
    # should fail.
    def test_default_not_checked_to_be_iterable(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=6)

    def test_set_checked_to_be_iterable(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=6,check_on_set=False)

        with self.assertRaises(TypeError):
            Q.r = 6
    ##########################


    def test_compute_default(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=None, compute_default_fn=lambda: [1,2,3])

        self.assertEqual(Q.r, None)
        Q.param.params('r').compute_default()
        self.assertEqual(Q.r, [1,2,3])
        self.assertEqual(Q.param.params('r').objects, [1,2,3])

    def test_bad_compute_default(self):
        class Q(param.Parameterized):
            r = param.ListSelector(default=None,compute_default_fn=lambda:1)

        with self.assertRaises(TypeError):
            Q.param.params('r').compute_default()
