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


class DubInvalidTableRecord(Record):
    db_table = '_fake_'


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

    def test__delete_record(self):
        saved_book = self.add(db.book, dict(
            name='_test__delete_',
        ))
        book = DubRecord.from_id(saved_book.id)
        book.delete_record()
        # db.commit()
        self.assertRaises(LookupError, DubRecord.from_id, saved_book.id)

    def test__from_id(self):
        saved_book = self.add(db.book, dict(
            name='_test__from_id_',
        ))

        book = DubRecord.from_id(saved_book.id)
        self.assertEqual(book.id, saved_book.id)
        self.assertEqual(book.name, '_test__from_id_')
        ignore = ['delete_record', 'update_record']
        book_keys = [x for x in sorted(book.keys()) if x not in ignore]
        self.assertEqual(
            book_keys,
            sorted(db.book.fields)
        )

        # Test db_table parameter.
        self.assertRaises(
            AttributeError, DubInvalidTableRecord.from_id, saved_book.id)
        book = DubInvalidTableRecord.from_id(saved_book.id, db_table='book')
        self.assertEqual(book.id, saved_book.id)
        self.assertEqual(book.name, '_test__from_id_')

    def test__from_key(self):
        data = dict(
            name='_test__from_key_',
            name_for_url='_TestFromKey_',
            name_for_search='_test-from-key_',
        )
        saved_book = self.add(db.book, data)

        mismatch_data = dict(
            name='_test__from_key_',
            name_for_url='_TestFromKey_X_',
            name_for_search='_test-from-key_',
        )

        tests = [
            # (key, match)
            (dict(name='_test__from_key_'), True),
            (data, True),
            (dict(name='_test__from_key_x_'), False),
            (mismatch_data, False),
        ]
        for t in tests:
            if t[1]:
                book = DubRecord.from_key(t[0])
                self.assertEqual(book.id, saved_book.id)
                ignore = ['delete_record', 'update_record']
                book_keys = [x for x in sorted(book.keys()) if x not in ignore]
                self.assertEqual(
                    book_keys,
                    sorted(db.book.fields)
                )
            else:
                self.assertRaises(LookupError, DubRecord.from_key, t[0])

        # Test db_table parameter.
        self.assertRaises(
            AttributeError, DubInvalidTableRecord.from_key, data)
        book = DubInvalidTableRecord.from_key(data, db_table='book')
        self.assertEqual(book.id, saved_book.id)
        self.assertEqual(book.name, '_test__from_key_')

    def test__save(self):
        book = DubRecord(name='_test__save_')
        book_id = book.save()
        got = db(db.book.id == book_id).select().first()
        self._objects.append(got)
        self.assertEqual(got.id, book_id)
        self.assertEqual(got.name, '_test__save_')

    def test__update_record(self):
        saved_book = self.add(db.book, dict(
            name='_test__delete_',
            name_for_url='N001',
        ))
        book = DubRecord.from_id(saved_book.id)
        book.update_record(**{'name_for_url': 'N002'})
        # db.commit()
        updated_book = DubRecord.from_id(saved_book.id)
        self.assertEqual(updated_book.id, book.id)
        self.assertEqual(updated_book.name, book.name)
        self.assertEqual(book.name_for_url, 'N001')
        self.assertEqual(updated_book.name_for_url, 'N002')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
