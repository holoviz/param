"""
Unit test for object selector parameters.

Originally implemented as doctests in Topographica in the file
testEnumerationParameter.txt
"""

import param
from . import API1TestCase
from collections import OrderedDict


opts=dict(A=[1,2],B=[3,4],C=dict(a=1,b=2))


class TestObjectSelectorParameters(API1TestCase):

    def setUp(self):
        super(TestObjectSelectorParameters, self).setUp()
        class P(param.Parameterized):
            e = param.Selector(default=5,objects=[5,6,7])
            f = param.Selector(default=10)
            h = param.Selector(default=None)
            g = param.Selector(default=None,objects=[7,8])
            i = param.Selector(default=7,objects=[9],check_on_set=False)
            s = param.Selector(default=3,objects=OrderedDict(one=1,two=2,three=3))
            d = param.Selector(default=opts['B'],objects=opts)

            changes = []

            @param.depends('e:objects', watch=True)
            def track_e_objects(self):
                self.changes.append(('e', list(self.param.e.objects)))

            @param.depends('s:objects', watch=True)
            def track_s_objects(self):
                self.changes.append(('s', list(self.param.s.objects)))

        self.P = P

    def test_set_object_constructor(self):
        p = self.P(e=6)
        self.assertEqual(p.e, 6)

    def test_get_range_list(self):
        r = self.P.param.params("g").get_range()
        self.assertEqual(r['7'],7)
        self.assertEqual(r['8'],8)

    def test_get_range_dict(self):
        r = self.P.param.params("s").get_range()
        self.assertEqual(r['one'],1)
        self.assertEqual(r['two'],2)

    def test_get_range_mutable(self):
        r = self.P.param.params("d").get_range()
        self.assertEqual(r['A'],opts['A'])
        self.assertEqual(r['C'],opts['C'])
        self.d=opts['A']
        self.d=opts['C']
        self.d=opts['B']

    def test_set_object_outside_bounds(self):
        p = self.P(e=6)
        try:
            p.e = 9
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)


    def test_set_object_not_None(self):
        p = self.P(e=6)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

    def test_set_object_setattr_post_error(self):
        p = self.P(e=6)
        p.f = 9
        self.assertEqual(p.f, 9)
        p.g = 7
        try:
            p.g = None
        except ValueError:
            pass
        else:
            raise AssertionError("Object set outside range.")

        self.assertEqual(p.g, 7)
        p.i = 12
        self.assertEqual(p.i, 12)

    def test_change_objects_list(self):
        p = self.P()
        p.param.e.objects = [8, 9]

        with self.assertRaises(ValueError):
            p.e = 7

        self.assertEqual(p.param.e.objects, [8, 9])
        self.assertEqual(p.changes, [('e', [8, 9])])

    def test_copy_objects_list(self):
        p = self.P()
        eobjs = p.param.e.objects.copy()

        self.assertIsInstance(eobjs, list)
        self.assertFalse(eobjs is p.param.e.objects)
        self.assertEqual(eobjs, [5, 6, 7])

    def test_append_objects_list(self):
        p = self.P()
        p.param.e.objects.append(8)

        p.e = 8

        self.assertEqual(p.param.e.objects, [5, 6, 7, 8])
        self.assertEqual(p.changes, [('e', [5, 6, 7, 8])])

    def test_extend_objects_list(self):
        p = self.P()
        p.param.e.objects.extend([8, 9])

        p.e = 8

        self.assertEqual(p.param.e.objects, [5, 6, 7, 8, 9])
        self.assertEqual(p.changes, [('e', [5, 6, 7, 8, 9])])

    def test_get_objects_list(self):
        p = self.P()
        self.assertEqual(p.param.e.objects.get(5, 'five'), 'five')

    def test_insert_objects_list(self):
        p = self.P()
        p.param.e.objects.insert(0, 8)

        p.e = 8

        self.assertEqual(p.param.e.objects, [8, 5, 6, 7])
        self.assertEqual(p.changes, [('e', [8, 5, 6, 7])])

    def test_pop_objects_list(self):
        p = self.P()
        p.param.e.objects.pop(-1)

        with self.assertRaises(ValueError):
            p.e = 7

        self.assertEqual(p.param.e.objects, [5, 6])
        self.assertEqual(p.changes, [('e', [5, 6])])

    def test_remove_objects_list(self):
        p = self.P()
        p.param.e.objects.remove(7)

        with self.assertRaises(ValueError):
            p.e = 7

        self.assertEqual(p.param.e.objects, [5, 6])
        self.assertEqual(p.changes, [('e', [5, 6])])

    def test_clear_objects_list(self):
        p = self.P()
        p.param.e.objects.clear()

        with self.assertRaises(ValueError):
            p.e = 5

        self.assertEqual(p.param.e.objects, [])
        self.assertEqual(p.changes, [('e', [])])

    def test_clear_setitem_objects_list(self):
        p = self.P()
        p.param.e.objects[:] = []

        with self.assertRaises(ValueError):
            p.e = 5

        self.assertEqual(p.param.e.objects, [])
        self.assertEqual(p.changes, [('e', [])])

    def test_override_setitem_objects_list(self):
        p = self.P()
        p.param.e.objects[0] = 8

        with self.assertRaises(ValueError):
            p.e = 5

        p.e = 8

        self.assertEqual(p.param.e.objects, [8, 6, 7])
        self.assertEqual(p.changes, [('e', [8, 6, 7])])

    def test_setitem_name_objects_list(self):
        p = self.P()

        with self.assertRaises(TypeError):
            p.param.e.objects['A'] = 8

    def test_int_getitem_objects_list(self):
        p = self.P()

        self.assertEqual(p.param.e.objects[0], 5) 

    def test_slice_getitem_objects_list(self):
        p = self.P()

        self.assertEqual(p.param.e.objects[1:3], [6, 7])

    def test_values_objects_list(self):
        p = self.P()

        self.assertEqual(p.param.e.objects.values(), list(p.param.e.objects))
    
    def test_change_objects_dict(self):
        p = self.P()
        p.param.s.objects = {'seven': 7, 'eight': 8}

        with self.assertRaises(ValueError):
            p.s = 1

        self.assertEqual(p.param.s.objects, [7, 8])
        self.assertEqual(p.changes, [('s', [7, 8])])

    def test_getitem_int_objects_dict(self):
        p = self.P()
        with self.assertRaises(KeyError):
            p.param.s.objects[2]

    def test_getitem_objects_dict(self):
        p = self.P()
        self.assertEqual(p.param.s.objects['two'], 2)

    def test_keys_objects_dict(self):
        p = self.P()
        self.assertEqual(list(p.param.s.objects.keys()), ['one', 'two', 'three'])

    def test_items_objects_dict(self):
        p = self.P()

        self.assertEqual(list(p.param.s.objects.items()), [('one', 1), ('two', 2), ('three', 3)])

    def test_cast_to_dict_objects_dict(self):
        p = self.P()
        self.assertEqual(dict(p.param.s.objects), {'one': 1, 'two': 2, 'three': 3})

    def test_cast_to_list_objects_dict(self):
        p = self.P()
        self.assertEqual(list(p.param.s.objects), [1, 2, 3])

    def test_setitem_key_objects_dict(self):
        p = self.P()
        p.param.s.objects['seven'] = 7

        p.s = 7

        self.assertEqual(p.param.s.objects, [1, 2, 3, 7])
        self.assertEqual(p.changes, [('s', [1, 2, 3, 7])])

    def test_objects_dict_equality(self):
        p = self.P()
        p.param.s.objects = {'seven': 7, 'eight': 8}

        self.assertEqual(p.param.s.objects, {'seven': 7, 'eight': 8})
        self.assertNotEqual(p.param.s.objects, {'seven': 7, 'eight': 8, 'nine': 9})

    def test_clear_objects_dict(self):
        p = self.P()
        p.param.s.objects.clear()

        with self.assertRaises(ValueError):
            p.s = 1

        self.assertEqual(p.param.s.objects, [])
        self.assertEqual(p.changes, [('s', [])])

    def test_copy_objects_dict(self):
        p = self.P()
        sobjs = p.param.s.objects.copy()

        self.assertIsInstance(sobjs, dict)
        self.assertEqual(sobjs, {'one': 1, 'two': 2, 'three': 3})

    def test_get_objects_dict(self):
        p = self.P()
        self.assertEqual(p.param.s.objects.get('two'), 2)

    def test_get_default_objects_dict(self):
        p = self.P()
        self.assertEqual(p.param.s.objects.get('four', 'four'), 'four')

    def test_pop_objects_dict(self):
        p = self.P()
        p.param.s.objects.pop('one')

        with self.assertRaises(ValueError):
            p.s = 1

        self.assertEqual(p.param.s.objects, [2, 3])
        self.assertEqual(p.changes, [('s', [2, 3])])

    def test_remove_objects_dict(self):
        p = self.P()
        p.param.s.objects.remove(1)

        with self.assertRaises(ValueError):
            p.s = 1

        self.assertEqual(p.param.s.objects, [2, 3])
        self.assertEqual(p.param.s.names, {'two': 2, 'three': 3})
        self.assertEqual(p.changes, [('s', [2, 3])])

    def test_update_objects_dict(self):
        p = self.P()
        p.param.s.objects.update({'one': '1', 'three': '3'})

        with self.assertRaises(ValueError):
            p.s = 1

        p.s = '3'

        self.assertEqual(p.param.s.objects, ['1', 2, '3'])
        self.assertEqual(p.changes, [('s', ['1', 2, '3'])])

    def test_update_with_list_objects_dict(self):
        p = self.P()
        p.param.s.objects.update([('one', '1'), ('three', '3')])

        with self.assertRaises(ValueError):
            p.s = 1

        p.s = '3'

        self.assertEqual(p.param.s.objects, ['1', 2, '3'])
        self.assertEqual(p.changes, [('s', ['1', 2, '3'])])

    def test_update_with_invalid_list_objects_dict(self):
        p = self.P()
        with self.assertRaises(TypeError):
            p.param.s.objects.update([1, 3])
        with self.assertRaises(ValueError):
            p.param.s.objects.update(['a', 'b'])

    def test_values_objects_dict(self):
        p = self.P()

        self.assertEqual(list(p.param.s.objects.values()), [1, 2, 3])

    def test_initialization_out_of_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Selector(default=5,objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ObjectSelector created outside range.")

    def test_initialization_no_bounds(self):
        try:
            class Q(param.Parameterized):
                q = param.Selector(default=5,objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ObjectSelector created without range.")


    def test_initialization_out_of_bounds_objsel(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=[4])
        except ValueError:
            pass
        else:
            raise AssertionError("ObjectSelector created outside range.")


    def test_initialization_no_bounds_objsel(self):
        try:
            class Q(param.Parameterized):
                q = param.ObjectSelector(5,objects=10)
        except TypeError:
            pass
        else:
            raise AssertionError("ObjectSelector created without range.")
