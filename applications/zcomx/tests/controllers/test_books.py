#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/books.py

"""
import json
import unittest
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    url = '/zcomx/books'

    def test__book(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/book', match_page_key='')

    def test__index(self):
        self.assertWebTest('/books/index', match_page_key='/default/index')

    def test__reader(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/reader', match_page_key='')

    def test__scroller(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/scroller', match_page_key='')

    def test__set_book_mark(self):
        book = self.add(Book, dict(
            name='test__set_book_mark',
            status=True,
        ))

        url = '{url}/set_book_mark.json'.format(url=self.url)
        data = {
            'book_id': book.id,
            'page_no': 1,
        }
        web.post(url, data=data)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'ok')

        # Invalid tests
        tests = [
            # (book_id, page_no, expect msg)
            (None, 1, 'No book_id provided'),
            (book.id, None, 'No page_no provided'),
            ('aaa', 1, 'Invalid book_id: aaa'),
            (book.id, 'bbb', 'Invalid page_no: bbb'),
            (-1, 1, 'Book not found, id: -1.'),
        ]

        for t in tests:
            data = {}
            if t[0] is not None:
                data['book_id'] = t[0]
            if t[1] is not None:
                data['page_no'] = t[1]

            web.post(url, data=data)
            result = json.loads(web.text)
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['msg'], t[2])

    def test__slider(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/slider', match_page_key='')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
