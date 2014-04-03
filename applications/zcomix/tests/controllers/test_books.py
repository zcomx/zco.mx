#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/books.py

"""
import unittest
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _book = None
    _invalid_book_id = None

    titles = {
        'book': '<div id="book_page">',
        'carousel': '<div id="carousel_page">',
        'default': 'This is a not-for-profit site dedicated to promoting',
        'gallery': '<div id="blueimp-gallery-carousel"',
        'reader': '<div id="reader_section">',
        'scroller': '<div id="scroller_page">',
        'slider': '<div id="slider_page">',
    }
    url = '/zcomix/books'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book with pages.
        count = db.book_page.book_id.count()
        book_page = db().select(db.book_page.book_id, count,
                groupby=db.book_page.book_id, orderby=~count).first()
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
        # No id, redirects to default page
        self.assertTrue(web.test('{url}/book'.format(url=self.url),
            self.titles['default']))

        # Invalid id, redirects to default page
        self.assertTrue(web.test('{url}/book/{bid}'.format(url=self.url,
            bid=self._invalid_book_id),
            self.titles['default']))

        # Test valid id
        self.assertTrue(web.test('{url}/book/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['book']))

    def test__carousel(self):
        self.assertTrue(web.test('{url}/carousel/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['carousel']))

    def test__gallery(self):
        self.assertTrue(web.test('{url}/gallery/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['gallery']))

    def test__index(self):
        self.assertTrue(web.test('{url}/index'.format(url=self.url),
            self.titles['default']))

    def test__reader(self):
        # No id, redirects to default page
        self.assertTrue(web.test('{url}/reader'.format(url=self.url),
            self.titles['default']))

        # Invalid id, redirects to default page
        self.assertTrue(web.test('{url}/reader/{bid}'.format(url=self.url,
            bid=self._invalid_book_id),
            self.titles['default']))

        # Test valid id
        self.assertTrue(web.test('{url}/reader/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['reader']))

    def test__scroller(self):
        self.assertTrue(web.test('{url}/scroller/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['scroller']))

    def test__slider(self):
        self.assertTrue(web.test('{url}/slider/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['slider']))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
