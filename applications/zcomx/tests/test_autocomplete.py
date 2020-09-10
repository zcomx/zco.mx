#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/autocomplete.py

"""
import os
import shutil
import unittest
from gluon import *
from pydal.objects import Row
from applications.zcomx.modules.autocomplete import \
    BaseAutocompleter, \
    BookAutocompleter, \
    CreatorAutocompleter, \
    autocompleter_class
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUSES

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DumpTestCase(LocalTestCase):

    _tmp_dir = '/tmp/test_autocomplete'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls._tmp_dir):
            os.makedirs(cls._tmp_dir)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._tmp_dir):
            shutil.rmtree(cls._tmp_dir)


class DubAutocompleter(BaseAutocompleter):
    def __init__(self, keyword=''):
        db = current.app.db
        super().__init__(db.book, keyword=keyword)

    def row_to_json(self, row):
        return {'id': str(row)}

    def search_rows(self):
        return [1, 2, 3]


class TestBaseAutocompleter(DumpTestCase):

    def test____init__(self):
        autocompleter = BaseAutocompleter(None)
        self.assertTrue(autocompleter)

    def test__dump(self):
        autocompleter = DubAutocompleter()
        output = os.path.join(self._tmp_dir, 'output.json')
        autocompleter.dump(output)
        with open(output) as f:
            content = f.read()
        self.assertEqual(
            content,
            '[{"id": "1"}, {"id": "2"}, {"id": "3"}]'
        )

    def test__filters(self):
        autocompleter = BaseAutocompleter(db.book)

        # No keyword
        self.assertEqual(autocompleter.filters(), [])

        # With keyword
        autocompleter.keyword = 'Abc Def'
        queries = autocompleter.filters()
        self.assertEqual(len(queries), 1)
        # pylint: disable=line-too-long
        self.assertEqual(
            str(queries[0]),
            """(LOWER("book"."name_for_search") LIKE '%abc-def%' ESCAPE '\\')"""
        )

    def test__formatted_value(self):
        autocompleter = BaseAutocompleter(None)
        self.assertEqual(autocompleter.formatted_value(123), '123')

    def test__id_field(self):
        autocompleter = BaseAutocompleter(db.book)
        self.assertEqual(autocompleter.id_field(), db.book.id)

    def test__left_join(self):
        autocompleter = BaseAutocompleter(db.book)
        self.assertEqual(autocompleter.left_join(), None)

    def test__orderby(self):
        autocompleter = BaseAutocompleter(db.book)
        self.assertEqual(autocompleter.orderby(), db.book.name_for_search)

    def test__row_to_json(self):

        book = self.add(Book, dict(
            name='My Book',
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
            name_for_search='azbycxazbycx-001',
            status=BOOK_STATUS_ACTIVE,
        ))

        autocompleter = BaseAutocompleter(db.book)
        row = Row({'id': book.id})
        expect = {
            'id': book.id,
            'table': 'book',
            'value': '{i}'.format(i=book.id),
        }
        self.assertEqual(autocompleter.row_to_json(row), expect)

    def test__search(self):
        autocompleter = DubAutocompleter()
        self.assertEqual(
            autocompleter.search(),
            [{'id': '1'}, {'id': '2'}, {'id': '3'}]
        )

    def test__search_rows(self):
        autocompleter = BaseAutocompleter(db.book)
        book_count = db(db.book).count()
        results = autocompleter.search_rows()
        self.assertEqual(len(results), book_count)
        self.assertTrue(isinstance(results[0], Row))

    def test__search_field(self):
        autocompleter = BaseAutocompleter(db.book)
        self.assertEqual(autocompleter.search_field(), db.book.name_for_search)


class TestBookAutocompleter(LocalTestCase):

    def test____init__(self):
        autocompleter = BookAutocompleter()
        self.assertTrue(autocompleter)

    def test__filters(self):
        autocompleter = BookAutocompleter()

        # No keyword
        queries = autocompleter.filters()
        self.assertEqual(len(queries), 1)
        self.assertEqual(
            str(queries[0]),
            """("book"."status" = 'a')"""
        )

        # With keyword
        autocompleter.keyword = 'Abc Def'
        queries = autocompleter.filters()
        self.assertEqual(len(queries), 2)
        # pylint: disable=line-too-long
        self.assertEqual(
            str(queries[0]),
            """(LOWER("book"."name_for_search") LIKE '%abc-def%' ESCAPE '\\')"""
        )
        self.assertEqual(
            str(queries[1]),
            """("book"."status" = 'a')"""
        )

    def test__formatted_value(self):
        book = self.add(Book, dict(
            name='My Book',
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
        ))
        autocompleter = BookAutocompleter()
        self.assertEqual(autocompleter.formatted_value(book.id), 'My Book 001')

    def test__orderby(self):
        autocompleter = BookAutocompleter()
        self.assertEqual(autocompleter.orderby(), db.book.name)

    def test_search(self):
        book = self.add(Book, dict(
            name='My Book',
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
            name_for_search='azbycxazbycx-001',
            status=BOOK_STATUS_ACTIVE,
        ))

        book_as_item = {
            'id': book.id,
            'table': 'book',
            'value': 'My Book 001'
        }

        # No keyword
        autocompleter = BookAutocompleter()
        results = autocompleter.search()
        active_book_count = db(db.book.status == BOOK_STATUS_ACTIVE).count()
        self.assertEqual(len(results), active_book_count)
        self.assertTrue(book_as_item in results)

        # Matching keyword
        autocompleter = BookAutocompleter(keyword='azbycx')
        self.assertEqual(autocompleter.search(), [book_as_item])

        # No matches
        autocompleter = BookAutocompleter(keyword='zzzzazbycxxxxx')
        self.assertEqual(autocompleter.search(), [])

        # Test variations on status
        autocompleter = BookAutocompleter(keyword='azbycx')
        for status in BOOK_STATUSES:
            book.update_record(status=status)
            db.commit()
            if status == BOOK_STATUS_ACTIVE:
                expect = [book_as_item]
            else:
                expect = []
            self.assertEqual(autocompleter.search(), expect)

        # Test multiple matches and order of results.
        book.update_record(status=BOOK_STATUS_ACTIVE)
        db.commit()
        book_2 = self.add(Book, dict(
            name='Another Book',
            number=2,
            of_number=4,
            book_type_id=BookType.by_name('mini-series').id,
            name_for_search='my-azbycxazbycx-02-of-04',
            status=BOOK_STATUS_ACTIVE,
        ))
        book_2_as_item = {
            'id': book_2.id,
            'table': 'book',
            'value': 'Another Book 02 (of 04)'
        }
        autocompleter = BookAutocompleter(keyword='azbycx')
        expect = [book_2_as_item, book_as_item]
        self.assertEqual(autocompleter.search(), expect)


class TestCreatorAutocompleter(LocalTestCase):

    def test____init__(self):
        autocompleter = CreatorAutocompleter()
        self.assertTrue(autocompleter)

    def test__filters(self):
        autocompleter = CreatorAutocompleter()

        # No keyword
        queries = autocompleter.filters()
        self.assertEqual(len(queries), 1)
        self.assertEqual(
            str(queries[0]),
            """("book"."id" IS NOT NULL)"""
        )

        # With keyword
        autocompleter.keyword = 'Abc Def'
        queries = autocompleter.filters()
        self.assertEqual(len(queries), 2)
        # pylint: disable=line-too-long
        self.assertEqual(
            str(queries[0]),
            """(LOWER("creator"."name_for_search") LIKE '%abc-def%' ESCAPE '\\')"""
        )
        self.assertEqual(
            str(queries[1]),
            """("book"."id" IS NOT NULL)"""
        )

    def test__formatted_value(self):
        auth_user = self.add(AuthUser, dict(
            name='First Last'
        ))

        creator = self.add(Creator, dict(
            auth_user_id=auth_user.id,
            name_for_search='azbycxazbycx',
        ))
        autocompleter = CreatorAutocompleter()
        self.assertEqual(
            autocompleter.formatted_value(creator.id), 'First Last')

    def test__left_join(self):
        autocompleter = CreatorAutocompleter()
        got = autocompleter.left_join()
        self.assertEqual(len(got), 1)
        self.assertEqual(
            str(got[0]),
            '"book" ON ("book"."creator_id" = "creator"."id")'
        )

    def test_search(self):
        auth_user = self.add(AuthUser, dict(
            name='First Last'
        ))

        creator = self.add(Creator, dict(
            auth_user_id=auth_user.id,
            name_for_search='azbycxazbycx',
        ))

        creator_as_item = {
            'id': creator.id,
            'table': 'creator',
            'value': 'First Last'
        }

        # No keyword
        query = (db.book.id != None)
        rows = db(query).select(
            db.creator.id,
            left=[
                db.book.on(db.book.creator_id == db.creator.id)
            ],
            distinct=True,
        )
        creators_with_book_count = len(rows)
        autocompleter = CreatorAutocompleter()
        results = autocompleter.search()
        self.assertEqual(len(results), creators_with_book_count)

        # creator does not have book
        self.assertFalse(creator_as_item in results)

        self.add(Book, dict(
            creator_id=creator.id
        ))
        results = autocompleter.search()
        self.assertTrue(creator_as_item in results)

        # Matching keyword
        autocompleter = CreatorAutocompleter(keyword='azbycx')
        self.assertEqual(autocompleter.search(), [creator_as_item])

        # No matches
        autocompleter = CreatorAutocompleter(keyword='zzzzazbycxxxxx')
        self.assertEqual(autocompleter.search(), [])

        # Test multiple matches and order of results.
        auth_user_2 = self.add(AuthUser, dict(
            name='Second Prime'
        ))

        creator_2 = self.add(Creator, dict(
            auth_user_id=auth_user_2.id,
            name_for_search='aaa-azbycxazbycx-lld',
        ))

        creator_2_as_item = {
            'id': creator_2.id,
            'table': 'creator',
            'value': 'Second Prime'
        }

        self.add(Book, dict(
            creator_id=creator_2.id
        ))

        autocompleter = CreatorAutocompleter(keyword='azbycx')
        expect = [creator_2_as_item, creator_as_item]
        self.assertEqual(autocompleter.search(), expect)


class TestFunctions(LocalTestCase):

    def test__autocompleter_class(self):
        self.assertEqual(autocompleter_class('book'), BookAutocompleter)
        self.assertEqual(autocompleter_class('creator'), CreatorAutocompleter)
        self.assertEqual(autocompleter_class('_fake_'), None)
        self.assertEqual(autocompleter_class(None), None)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
