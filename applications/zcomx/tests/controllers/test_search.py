#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/search.py
"""
import json
import unittest
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.tests.helpers import WebTestCase
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE
# pylint: disable=missing-docstring


class WithObjectsTestCase(WebTestCase):
    """Class representing a WithObjectsTestCase"""

    _book = None

    def setUp(self):
        query = (db.book.status == BOOK_STATUS_ACTIVE) & \
                (db.book.release_date != None)
        book_ids = db(query).select(
            db.book.id,
            left=[
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
            orderby=~db.book.release_date,
            limitby=(0, 1)
        )
        if not book_ids:
            self.fail('No book found in db.')

        self._book = Book.from_id(book_ids[0]['id'])


class TestFunctions(WithObjectsTestCase):

    url = '/zcomx/search'

    def test__autocomplete(self):
        web.login()

        # Books
        # No query should return all books
        url = '{url}/autocomplete.json/book'.format(url=self.url)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue('results' in result)
        count = db(db.book.status == BOOK_STATUS_ACTIVE).count()
        self.assertEqual(len(result['results']), count)
        self.assertEqual(
            sorted(result['results'][0].keys()),
            ['id', 'table', 'value']
        )

        # With query
        search_term = 'not'
        url = '{url}/autocomplete.json/book?q={q}'.format(
            url=self.url, q=search_term)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue(len(result['results']) > 0)
        self.assertTrue(len(result['results']) < 10)
        for item in result['results']:
            self.assertTrue(search_term.lower() in item['value'].lower())

        # Creators
        # No query should return all creators
        url = '{url}/autocomplete.json/creator'.format(url=self.url)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue('results' in result)

        query = (db.book.id != None)
        rows = db(query).select(
            db.creator.id,
            left=[
                db.book.on(db.book.creator_id == db.creator.id)
            ],
            distinct=True,
        )
        count = len(rows)

        self.assertEqual(len(result['results']), count)
        self.assertEqual(
            sorted(result['results'][0].keys()),
            ['id', 'table', 'value']
        )

        # With query
        search_term = 'kar'
        url = '{url}/autocomplete.json/creator?q={q}'.format(
            url=self.url, q=search_term)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue(len(result['results']) > 0)
        self.assertTrue(len(result['results']) < 10)
        for item in result['results']:
            self.assertTrue(search_term.lower() in item['value'].lower())

        # No table
        url = '{url}/autocomplete.json'.format(url=self.url)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue('results' in result)
        self.assertEqual(result['results'], [])

        # Invalid table
        url = '{url}/autocomplete.json/_fake_'.format(url=self.url)
        web.post(url)
        result = json.loads(web.text)
        self.assertTrue('results' in result)
        self.assertEqual(result['results'], [])

    def test__autocomplete_selected(self):
        def is_page_not_found(url):
            self.assertRaisesHTTPError(
                404, self.assertWebTest, url, match_page_key='')

        # No args, redirects to page not found
        is_page_not_found('/search/autocomplete_selected')

        # Invalid table, redirects to page not found
        is_page_not_found('/search/autocomplete_selected/_fake_')

        # Invalid record id, redirects to page not found
        is_page_not_found('/search/autocomplete_selected/book/0')

        # Valid book
        self.assertWebTest(
            '/search/autocomplete_selected/book/{id}'.format(id=self._book.id),
            match_page_key='/search/book_page',
        )

        # Valid creator
        self.assertWebTest(
            '/search/autocomplete_selected/creator/{id}'.format(
                id=self._book.creator_id
            ),
            match_page_key='/search/creator_page',
        )

    def test__box(self):
        self.assertWebTest('/search/box.load')

    def test__index(self):
        self.assertWebTest('/search/index', match_page_key='/default/index')

        # Test list view
        self.assertWebTest(
            '/search/index?view=list',
            match_page_key='/search/list_grid',
        )

        # Test tile view
        self.assertWebTest(
            '/search/index?view=tile',
            match_page_key='/search/tile_grid',
        )

        # Test cartoonists table
        # Get a creator with a book.
        query = (db.book.id != None)
        creator_rows = db(query).select(
            db.creator.ALL,
            left=[
                db.book.on(db.book.creator_id == db.creator.id),
                db.auth_user.on(db.creator.auth_user_id == db.auth_user.id),
            ],
            orderby=db.auth_user.name,
            limitby=(0, 1)
        )
        if not creator_rows:
            self.fail('No creator found in db.')

        creator = Creator.from_id(creator_rows[0].id)

        self.assertWebTest(
            '/search/index?view=tile&o=creators',
            match_page_key='/search/tile_grid',
            match_strings=[creator.name_for_url],
        )


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
