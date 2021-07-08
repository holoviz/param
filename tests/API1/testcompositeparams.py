"""
Unit test for composite parameters.

Originally implemented as doctests in Topographica in the file
testCompositeParameter.txt
"""

import param
from . import API1TestCase

class TestCompositeParameters(API1TestCase):

    def setUp(self):
        super(TestCompositeParameters, self).setUp()
        # initialize a class with a compound parameter
        class A(param.Parameterized):
            x = param.Number(default=0)
            y = param.Number(default=0)
            xy = param.Composite(attribs=['x','y'])

        self.A = A
        self.a = self.A()

        class SomeSequence(object):
            "Can't use iter with Dynamic (doesn't pickle, doesn't copy)"
            def __init__(self,sequence):
                self.sequence=sequence
                self.index=0
            def __call__(self):
                val=self.sequence[self.index]
                self.index+=1
                return val

        self.SomeSequence = SomeSequence

    def test_initialization(self):
        "Make an instance and do default checks"
        self.assertEqual(self.a.x, 0)
        self.assertEqual(self.a.y, 0)
        self.assertEqual(self.a.xy, [0,0])


    def test_set_component(self):
        self.a.x = 1
        self.assertEqual(self.a.xy, [1,0])

    def test_set_compound(self):
        self.a.xy = (2,3)
        self.assertEqual(self.a.x, 2)
        self.assertEqual(self.a.y, 3)

    def test_compound_class(self):
        " Get the compound on the class "
        self.assertEqual(self.A.xy, [0,0])

    def test_set_compound_class_set(self):
        self.A.xy = (5,6)
        self.assertEqual(self.A.x, 5)
        self.assertEqual(self.A.y, 6)

    def test_set_compound_class_instance(self):
        self.A.xy = (5,6)
        # # Make a new instance
        b = self.A()
        self.assertEqual(b.x, 5)
        self.assertEqual(b.y, 6)

    def test_set_compound_class_instance_unchanged(self):
        self.a.xy = (2,3)
        self.A.xy = (5,6)
        self.assertEqual(self.a.x, 2)
        self.assertEqual(self.a.y, 3)

    def test_composite_dynamic(self):
        """
        Check CompositeParameter is ok with Dynamic
        CB: this test is really of Parameterized.
        """
        a2 = self.A(x=self.SomeSequence([1,2,3]),
                    y=self.SomeSequence([4,5,6]))

        a2.x, a2.y # Call of x and y params
        # inspect should not advance numbers
        self.assertEqual(a2.param.inspect_value('xy'), [1, 4])

    def test_composite_dynamic_generator(self):

        a2 = self.A(x=self.SomeSequence([1,2,3]),
                    y=self.SomeSequence([4,5,6]))

        a2.x, a2.y # Call of x and y params
        ix,iy = a2.param.get_value_generator('xy')
        # get_value_generator() should give the objects
        self.assertEqual(ix(), 2)
        self.assertEqual(iy(), 5)
