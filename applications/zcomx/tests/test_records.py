#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/records.py

"""
import unittest
from gluon import *
from pydal.objects import Row
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.records import Record

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubRecord(Record):
    db_table = 'book'


class TestRecord(LocalTestCase):

    def test____init__(self):
        book = DubRecord(name='My Book')
        self.assertTrue(isinstance(book, Row))
        self.assertEqual(book.name, 'My Book')

    def test__delete(self):
        saved_book = self.add(db.book, dict(
            name='_test__delete_',
        ))
        book = DubRecord.from_id(saved_book.id)
        book.delete()
        self.assertRaises(LookupError, DubRecord.from_id, saved_book.id)

    def test__from_id(self):
        saved_book = self.add(db.book, dict(
            name='_test__from_id_',
        ))

        book = DubRecord.from_id(saved_book.id)
        self.assertEqual(book.id, saved_book.id)
        self.assertEqual(book.name, '_test__from_id_')
        self.assertEqual(
            sorted(book.keys()),
            sorted(db.book.fields)
        )

    def test__save(self):
        book = DubRecord(name='_test__save_')
        book_id = book.save()
        got = db(db.book.id == book_id).select().first()
        self._objects.append(got)
        self.assertEqual(got.id, book_id)
        self.assertEqual(got.name, '_test__save_')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
