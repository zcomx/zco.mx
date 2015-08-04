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

    def test__delete_record(self):
        saved_book = self.add(db.book, dict(
            name='_test__delete_',
        ))
        book = DubRecord.from_id(saved_book.id)
        book.delete_record()
        # db.commit()
        self.assertRaises(LookupError, DubRecord.from_id, saved_book.id)

    def test__from_add(self):
        data = dict(
            name='_test__from_add_',
            name_for_url='_TestFromAdd_',
            name_for_search='_test-from-add_',
        )
        book = DubRecord.from_add(data)
        self.assertTrue(book.id)
        self.assertEqual(book.name, data['name'])
        self.assertEqual(book.name_for_url, data['name_for_url'])
        self.assertEqual(book.name_for_search, data['name_for_search'])
        self._objects.append(book)

        # Test data with validate errors
        invalid_data = dict(name='')
        self.assertRaises(
            SyntaxError, DubRecord.from_add, invalid_data, validate=True)

        # Test validate=False
        book = DubRecord.from_add(invalid_data, validate=False)
        self.assertTrue(book.id)
        self.assertEqual(book.name, '')
        self._objects.append(book)

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

    def test__from_query(self):
        data = dict(
            name='_test__from_query_',
            name_for_url='_TestFromQuery_',
            name_for_search='_test-from-query_',
        )
        saved_book = self.add(db.book, data)

        query = (db.book.name == saved_book.name)
        book = DubRecord.from_query(query)
        self.assertEqual(book.id, saved_book.id)

        # Test multiple queries
        query = (db.book.name == saved_book.name) & \
            (db.book.name_for_url == saved_book.name_for_url) & \
            (db.book.name_for_search == saved_book.name_for_search)
        self.assertEqual(book.id, saved_book.id)

        # Test no matches
        query = (db.book.name == '_fake__name_')
        self.assertRaises(LookupError, DubRecord.from_query, query)

    def test__from_updated(self):
        data = dict(
            name='_test__from_update_',
            name_for_url='_TestFromUpdate_',
            name_for_search='_test-from-update_',
        )
        book = DubRecord.from_add(data)
        self.assertTrue(book.id)
        self.assertEqual(book.name_for_url, data['name_for_url'])
        self.assertEqual(book.name_for_search, data['name_for_search'])
        self._objects.append(book)

        new_data = dict(
            name_for_url='_TestFromUpdate_2_',
            name_for_search='_test-from-update_2_',
        )
        new_book = DubRecord.from_updated(book, new_data)
        self.assertEqual(new_book.id, book.id)
        self.assertEqual(new_book.name_for_url, new_data['name_for_url'])
        self.assertEqual(new_book.name_for_search, new_data['name_for_search'])

        # Test data with validate errors
        invalid_data = dict(name='')
        self.assertRaises(
            SyntaxError, DubRecord.from_updated, book, invalid_data)

        # Test validate=False
        new_book = DubRecord.from_updated(book, invalid_data, validate=False)
        self.assertEqual(new_book.id, book.id)
        self.assertEqual(new_book.name, '')

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
