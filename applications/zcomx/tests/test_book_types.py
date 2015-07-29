#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_types.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.book_types import \
    BookType, \
    MiniSeriesType, \
    OneShotType, \
    OngoingType

from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithDataTestCase(LocalTestCase):
    """Class representing a test case with preset data."""
    book_type_data = dict(
        name='name',
        description='description',
        sequence=1,
    )


class DubBookType(BookType):
    def formatted_number(self, number, of_number):
        return '{num:02d} (of {of:02d})'.format(num=number, of=of_number)

    @staticmethod
    def number_field_statuses():
        """Return the use statuses of number related fields."""
        return {
            'number': True,
            'of_number': True,
        }


class TestBookType(WithDataTestCase):

    def test__by_name(self):
        got = BookType.by_name('one-shot')
        self.assertEqual(got.name, 'one-shot')
        self.assertEqual(got.sequence, 3)
        self.assertTrue('One-shot' in got.description)
        self.assertTrue(isinstance(got, OneShotType))

        got = BookType.by_name('ongoing')
        self.assertEqual(got.name, 'ongoing')
        self.assertEqual(got.sequence, 1)
        self.assertTrue('001' in got.description)
        self.assertTrue(isinstance(got, OngoingType))

        got = BookType.by_name('mini-series')
        self.assertEqual(got.name, 'mini-series')
        self.assertEqual(got.sequence, 2)
        self.assertTrue('01 of 04' in got.description)
        self.assertTrue(isinstance(got, MiniSeriesType))

    def test__formatted_number(self):
        book_type = BookType(self.book_type_data)
        self.assertRaises(
            NotImplementedError, book_type.formatted_number, 1, 1)

    def test__from_id(self):
        tests = [
            # (type name, expect class)
            ('one-shot', OneShotType),
            ('ongoing', OngoingType),
            ('mini-series', MiniSeriesType),
        ]
        for t in tests:
            book_type = db(db.book_type.name == t[0]).select(limitby=(0, 1)).first()
            self.assertTrue(book_type)
            got = BookType.from_id(book_type.id)
            self.assertEqual(got, book_type)
            self.assertTrue(isinstance(got, t[1]))
            self.assertEqual(got.name, book_type.name)
            self.assertEqual(got.description, book_type.description)
            self.assertEqual(got.sequence, book_type.sequence)

    def test__is_series(self):
        book_type = DubBookType(self.book_type_data)
        book_type.number_field_statuses = lambda: {'number': True}
        self.assertTrue(book_type.is_series())

        book_type.number_field_statuses = lambda: {'number': False}
        self.assertFalse(book_type.is_series())

    def test__number_field_statuses(self):
        book_type = BookType(self.book_type_data)
        self.assertRaises(
            NotImplementedError, book_type.number_field_statuses)


class TestMiniSeriesType(WithDataTestCase):

    def test__formatted_number(self):
        book_type = MiniSeriesType(self.book_type_data)
        self.assertEqual(book_type.formatted_number(1, 4), '01 (of 04)')

    def test__number_field_statuses(self):
        book_type = MiniSeriesType(self.book_type_data)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': True, 'number': True}
        )


class TestOneShotType(WithDataTestCase):

    def test__formatted_number(self):
        book_type = OneShotType(self.book_type_data)
        self.assertEqual(book_type.formatted_number(1, 1), '')
        self.assertEqual(book_type.formatted_number(999, 999), '')
        self.assertEqual(book_type.formatted_number(None, None), '')

    def test__number_field_statuses(self):
        book_type = OneShotType(self.book_type_data)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': False, 'number': False}
        )


class TestOngoingType(WithDataTestCase):

    def test__formatted_number(self):
        book_type = OngoingType(self.book_type_data)
        self.assertEqual(book_type.formatted_number(1, 1), '001')
        self.assertEqual(book_type.formatted_number(2, 999), '002')
        self.assertEqual(book_type.formatted_number(3, None), '003')

    def test__number_field_statuses(self):
        book_type = OngoingType(self.book_type_data)
        self.assertEqual(
            book_type.number_field_statuses(),
            {'of_number': False, 'number': True}
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
