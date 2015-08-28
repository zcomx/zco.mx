#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/search.py

"""
import unittest
import urllib2
from gluon.contrib.simplejson import loads
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    """Class representing a WithObjectsTestCase"""

    _book = None

    def setUp(self):
        query = (db.book.status == BOOK_STATUS_ACTIVE) & \
                (db.book.release_date != None)
        books = db(query).select(
            db.book.ALL,
            left=[
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
            orderby=~db.book.release_date,
            limitby=(0, 1)
        )
        if not books:
            self.fail('No book found in db.')

        self._book = books[0]


class TestFunctions(WithObjectsTestCase):

    titles = {
        'book_page': '<div id="book_page">',
        'box': '<div id="search">',
        'creator_page': '<div id="creator_page">',
        'index': '<div id="front_page">',
        'list_grid': '<div class="web2py_grid grid_view_list ',
        'list_grid_tile': '<div class="web2py_grid grid_view_tile ',
        'tile_grid': '<div class="row tile_view">',
    }
    url = '/zcomx/search'

    def test__autocomplete(self):
        web.login()

        # Books
        # No query should return all books
        url = '{url}/autocomplete.json/book'.format(url=self.url)
        web.post(url)
        result = loads(web.text)
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
        result = loads(web.text)
        self.assertTrue(len(result['results']) > 0)
        self.assertTrue(len(result['results']) < 10)
        for item in result['results']:
            self.assertTrue(search_term.lower() in item['value'].lower())

        # Creators
        # No query should return all creators
        url = '{url}/autocomplete.json/creator'.format(url=self.url)
        web.post(url)
        result = loads(web.text)
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
        result = loads(web.text)
        self.assertTrue(len(result['results']) > 0)
        self.assertTrue(len(result['results']) < 10)
        for item in result['results']:
            self.assertTrue(search_term.lower() in item['value'].lower())

        # No table
        url = '{url}/autocomplete.json'.format(url=self.url)
        web.post(url)
        result = loads(web.text)
        self.assertTrue('results' in result)
        self.assertEqual(result['results'], [])

        # Invalid table
        url = '{url}/autocomplete.json/_fake_'.format(url=self.url)
        web.post(url)
        result = loads(web.text)
        self.assertTrue('results' in result)
        self.assertEqual(result['results'], [])

    def test__autocomplete_selected(self):
        def is_page_not_found(url):
            with self.assertRaises(urllib2.HTTPError) as cm:
                web.test(url, None)
            self.assertEqual(cm.exception.code, 404)
            self.assertEqual(cm.exception.msg, 'NOT FOUND')

        # No args, redirects to page not found
        is_page_not_found(
            '{url}/autocomplete_selected'.format(url=self.url)
        )

        # Invalid table, redirects to page not found
        is_page_not_found(
            '{url}/autocomplete_selected/_fake_'.format(url=self.url)
        )

        # Invalid record id, redirects to page not found
        is_page_not_found(
            '{url}/autocomplete_selected/book/0'.format(url=self.url)
        )

        # Valid book
        self.assertTrue(web.test(
            '{url}/autocomplete_selected/book/{id}'.format(
                url=self.url,
                id=self._book.id
            ),
            self.titles['book_page']
        ))

        # Valid creator
        self.assertTrue(web.test(
            '{url}/autocomplete_selected/creator/{id}'.format(
                url=self.url,
                id=self._book.creator_id
            ),
            self.titles['creator_page']
        ))

    def test__box(self):
        self.assertTrue(web.test(
            '{url}/box.load'.format(url=self.url),
            self.titles['box']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

        # Test list view
        self.assertTrue(web.test(
            '{url}/index?view={v}'.format(url=self.url, v='list'),
            [self.titles['list_grid'], self._book.name]
        ))

        # Test tile view
        self.assertTrue(web.test(
            '{url}/index?view={v}'.format(
                url=self.url, v='tile'),
            [self.titles['tile_grid'], self._book.name]
        ))

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

        self.assertTrue(web.test(
            '{url}/index?view={v}&o={o}'.format(
                url=self.url, v='tile', o='creators'),
            [self.titles['tile_grid'], creator.name]
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
