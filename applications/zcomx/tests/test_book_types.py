#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_types.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.book_types import \
    BaseBookType, \
    CLASS_BY_NAME, \
    MiniSeriesType, \
    OneShotType, \
    OngoingType, \
    by_name, \
    from_id

from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubBookType(BaseBookType):
    def formatted_number(self, number, of_number):
        return '{num:02d} (of {of:02d})'.format(num=number, of=of_number)

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        return {
            'number': True,
            'of_number': True,
        }


class TestBaseBookType(LocalTestCase):

    def test____init__(self):
        book_type = BaseBookType('name', 'description', 1)
        self.assertTrue(book_type)

    def test__formatted_number(self):
        book_type = BaseBookType('name', 'description', 1)
        self.assertRaises(
            NotImplementedError, book_type.formatted_number, 1, 1)

    def test__is_series(self):
        book_type = DubBookType('name', 'description', 1)
        book_type.number_field_statuses = lambda: {'number': True}
        self.assertTrue(book_type.is_series())

        book_type.number_field_statuses = lambda: {'number': False}
        self.assertFalse(book_type.is_series())

    def test__number_field_statuses(self):
        book_type = BaseBookType('name', 'description', 1)
        self.assertRaises(
            NotImplementedError, book_type.number_field_statuses)


class TestMiniSeriesType(LocalTestCase):

    def test__formatted_number(self):
        book_type = MiniSeriesType('name', 'description', 1)
        self.assertEqual(book_type.formatted_number(1, 4), '01 (of 04)')

    def test__number_field_statuses(self):
        book_type = MiniSeriesType('name', 'description', 1)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': True, 'number': True}
        )


class TestOneShotType(LocalTestCase):

    def test__formatted_number(self):
        book_type = OneShotType('name', 'description', 1)
        self.assertEqual(book_type.formatted_number(1, 1), '')
        self.assertEqual(book_type.formatted_number(999, 999), '')
        self.assertEqual(book_type.formatted_number(None, None), '')

    def test__number_field_statuses(self):
        book_type = OneShotType('name', 'description', 1)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': False, 'number': False}
        )


class TestOngoingType(LocalTestCase):

    def test__formatted_number(self):
        book_type = OngoingType('name', 'description', 1)
        self.assertEqual(book_type.formatted_number(1, 1), '001')
        self.assertEqual(book_type.formatted_number(2, 999), '002')
        self.assertEqual(book_type.formatted_number(3, None), '003')

    def test__number_field_statuses(self):
        book_type = OngoingType('name', 'description', 1)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': False, 'number': True}
        )


class TestConstants(LocalTestCase):
    def test_class_by_name(self):
        self.assertEqual(CLASS_BY_NAME['one-shot'], OneShotType)
        self.assertEqual(CLASS_BY_NAME['ongoing'], OngoingType)
        self.assertEqual(CLASS_BY_NAME['mini-series'], MiniSeriesType)
        self.assertEqual(CLASS_BY_NAME[None], OneShotType)
        self.assertEqual(CLASS_BY_NAME[''], OneShotType)
        self.assertEqual(CLASS_BY_NAME['_fake_'], OneShotType)


class TestFunctions(LocalTestCase):

    def test__by_name(self):
        got = by_name('one-shot')
        self.assertEqual(got.name, 'one-shot')
        self.assertEqual(got.sequence, 3)
        self.assertTrue('One-shot' in got.description)

        got = by_name('ongoing')
        self.assertEqual(got.name, 'ongoing')
        self.assertEqual(got.sequence, 1)
        self.assertTrue('001' in got.description)

        got = by_name('mini-series')
        self.assertEqual(got.name, 'mini-series')
        self.assertEqual(got.sequence, 2)
        self.assertTrue('01 of 04' in got.description)

    def test__from_id(self):
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # Test each type
        got = from_id(types_by_name['one-shot'].id)
        self.assertTrue(isinstance(got, OneShotType))
        self.assertEqual(got.name, 'one-shot')
        self.assertEqual(got.sequence, 3)
        self.assertTrue('One-shot' in got.description)

        got = from_id(types_by_name['ongoing'].id)
        self.assertTrue(isinstance(got, OngoingType))
        self.assertEqual(got.name, 'ongoing')
        self.assertEqual(got.sequence, 1)
        self.assertTrue('001' in got.description)

        got = from_id(types_by_name['mini-series'].id)
        self.assertTrue(isinstance(got, MiniSeriesType))
        self.assertEqual(got.name, 'mini-series')
        self.assertEqual(got.sequence, 2)
        self.assertTrue('01 of 04' in got.description)

        # Test invalid id, no default provided
        got = from_id(-1)
        self.assertTrue(isinstance(got, OneShotType))

        # Test invalid id, default is None
        self.assertRaises(LookupError, from_id, -1, default=None)

        # Test invalid id, default
        got = from_id(-1, default='mini-series')
        self.assertTrue(isinstance(got, MiniSeriesType))

        # Test invalid default
        self.assertRaises(LookupError, from_id, -1, default='_invalid_')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
