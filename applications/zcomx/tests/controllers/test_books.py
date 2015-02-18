#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/books.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _book = None
    _invalid_book_id = None

    titles = {
        'book': '<div id="book_page">',
        'default': '<div id="front_page">',
        'reader': '<div id="reader_section">',
        'scroller': '<div id="scroller_page">',
        'slider': '<div id="slider_page">',
    }
    url = '/zcomx/books'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book with pages.
        count = db.book_page.book_id.count()
        book_page = db().select(
            db.book_page.book_id,
            count,
            groupby=db.book_page.book_id,
            orderby=~count
        ).first()
        query = (db.book.id == book_page.book_page.book_id)
        cls._book = db(query).select(db.book.ALL).first()
        if not cls._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            cls._invalid_book_id = rows[0][max_book_id] + 1
        else:
            cls._invalid_book_id = 1

    def test__book(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/book'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['default']
            )
        )

    def test__reader(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/reader'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__scroller(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/scroller'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__slider(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/slider'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
