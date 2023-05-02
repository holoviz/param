"""
Unit test for object selector parameters.

Originally implemented as doctests in Topographica in the file
testEnumerationParameter.txt
"""

import unittest

from collections import OrderedDict

import param

from .utils import check_defaults

opts=dict(A=[1,2],B=[3,4],C=dict(a=1,b=2))


class TestObjectSelectorParameters(unittest.TestCase):

    def setUp(self):
        super().setUp()
        class P(param.Parameterized):
            e = param.ObjectSelector(default=5,objects=[5,6,7])
            f = param.ObjectSelector(default=10)
            h = param.ObjectSelector(default=None)
            g = param.ObjectSelector(default=None,objects=[7,8])
            i = param.ObjectSelector(default=7,objects=[9],check_on_set=False)
            s = param.ObjectSelector(default=3,objects=OrderedDict(one=1,two=2,three=3))
            d = param.ObjectSelector(default=opts['B'],objects=opts)

            changes = []

            @param.depends('e:objects', watch=True)
            def track_e_objects(self):
                self.changes.append(('e', list(self.param.e.objects)))

            @param.depends('s:objects', watch=True)
            def track_s_objects(self):
                self.changes.append(('s', list(self.param.s.objects)))

        self.P = P

    def _check_defaults(self, p):
        assert p.default is None
        assert p.allow_None is None
        assert p.objects == []
        assert p.compute_default_fn is None
        assert p.check_on_set is False
        assert p.names == {}

    def test_defaults_class(self):
        class P(param.Parameterized):
            s = param.ObjectSelector()

        check_defaults(P.param.s, label='S')
        self._check_defaults(P.param.s)

    def test_defaults_inst(self):
        class P(param.Parameterized):
            s = param.ObjectSelector()

        p = P()

        check_defaults(p.param.s, label='S')
        self._check_defaults(p.param.s)

    def test_defaults_unbound(self):
        s = param.ObjectSelector()

        check_defaults(s, label=None)
        self._check_defaults(s)

    def test_unbound_default_inferred(self):
        s = param.ObjectSelector(objects=[0, 1, 2])

        assert s.default is None

    def test_unbound_default_explicit(self):
        s = param.ObjectSelector(default=1, objects=[0, 1, 2])

        assert s.default == 1

    def test_unbound_default_check_on_set_inferred(self):
        s1 = param.ObjectSelector(objects=[0, 1, 2])
        s2 = param.ObjectSelector(objects=[])
        s3 = param.ObjectSelector(objects={})
        s4 = param.ObjectSelector()

        assert s1.check_on_set is True
        assert s2.check_on_set is False
        assert s3.check_on_set is False
        assert s4.check_on_set is False

    def test_unbound_default_check_on_set_explicit(self):
        s1 = param.ObjectSelector(check_on_set=True)
        s2 = param.ObjectSelector(check_on_set=False)

        assert s1.check_on_set is True
        assert s2.check_on_set is False

    def test_unbound_allow_None_not_dynamic(self):
        s = param.ObjectSelector(objects=[0, 1, 2])

        assert s.allow_None is None

    def test_set_object_constructor(self):
        p = self.P(e=6)
        self.assertEqual(p.e, 6)

    def test_allow_None_is_None(self):
        p = self.P()
        assert p.param.e.allow_None is None
        assert p.param.f.allow_None is None
        assert p.param.g.allow_None is None
        assert p.param.h.allow_None is None
        assert p.param.i.allow_None is None
        assert p.param.s.allow_None is None
        assert p.param.d.allow_None is None

    def test_get_range_list(self):
        r = self.P.param['g'].get_range()
        self.assertEqual(r['7'],7)
        self.assertEqual(r['8'],8)

    def test_get_range_dict(self):
        r = self.P.param['s'].get_range()
        self.assertEqual(r['one'],1)
        self.assertEqual(r['two'],2)

    def test_get_range_mutable(self):
        r = self.P.param['d'].get_range()
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
        self.assertEqual(p.param.e.objects.get('5'), 5)
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

        p.param.e.objects['A'] = 8

        self.assertEqual(p.param.e.objects, {'5': 5, '6': 6, '7': 7, 'A': 8})
        self.assertEqual(len(p.changes), 1)

    def test_update_objects_list(self):
        p = self.P()

        p.param.e.objects.update({'A': 8})

        self.assertEqual(p.param.e.objects, {'5': 5, '6': 6, '7': 7, 'A': 8})
        self.assertEqual(len(p.changes), 1)

    def test_int_getitem_objects_list(self):
        p = self.P()

        self.assertEqual(p.param.e.objects[0], 5)

    def test_slice_getitem_objects_list(self):
        p = self.P()

        self.assertEqual(p.param.e.objects[1:3], [6, 7])

    def test_items_objects_list(self):
        p = self.P()

        self.assertEqual(list(p.param.e.objects.items()), [('5', 5), ('6', 6), ('7', 7)])

    def test_keys_objects_list(self):
        p = self.P()

        self.assertEqual(list(p.param.e.objects.keys()), ['5', '6', '7'])

    def test_values_objects_list(self):
        p = self.P()

        self.assertEqual(list(p.param.e.objects.values()), list(p.param.e.objects))

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

    def test_compute_default_fn_in_objects(self):
        class P(param.Parameterized):
            o = param.ObjectSelector(objects=[0, 1], compute_default_fn=lambda: 1)

        assert P.param.o.default is None

        P.param.o.compute_default()

        assert P.param.o.default == 1

        p = P()

        assert p.o == 1


    def test_compute_default_fn_not_in_objects(self):
        class P(param.Parameterized):
            o = param.ObjectSelector(objects=[0, 1], compute_default_fn=lambda: 2)

        assert P.param.o.default is None

        P.param.o.compute_default()

        assert P.param.o.default == 2

        p = P()

        assert p.o == 2

    def test_inheritance_behavior1(self):
        class A(param.Parameterized):
            p = param.ObjectSelector()

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.default is None
        assert B.param.p.objects == []
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.default is None
        assert b.param.p.objects == []
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior2(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1])

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default is None
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default is None
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior3(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(default=1, objects=[0, 1])

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior4(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1], check_on_set=False)

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default is None
        assert B.param.p.check_on_set is False

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default is None
        assert b.param.p.check_on_set is False

    def test_inheritance_behavior5(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(objects=[0, 1], check_on_set=True)

        class B(A):
            p = param.ObjectSelector()

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default is None
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default is None
        assert b.param.p.check_on_set is True

    def test_inheritance_behavior6(self):
        class A(param.Parameterized):
            p = param.ObjectSelector(default=0, objects=[0, 1])

        class B(A):
            p = param.ObjectSelector(default=1)

        assert B.param.p.objects == [0, 1]
        assert B.param.p.default == 1
        assert B.param.p.check_on_set is True

        b = B()

        assert b.param.p.objects == [0, 1]
        assert b.param.p.default == 1
        assert b.param.p.check_on_set is True
