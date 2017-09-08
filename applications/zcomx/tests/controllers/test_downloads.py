#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/downloads.py

"""
import json
import unittest
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):
    _book = None
    _creator = None
    _invalid_book_id = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book from a creator with a paypal_email.
        self._creator = Creator.by_email(web.username)
        self._book = Book.from_key(dict(creator_id=self._creator.id))

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            self._invalid_book_id = rows[0][max_book_id] + 1
        else:
            self._invalid_book_id = 1

    def test__download_click_handler(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

        book = self.add(Book, dict(
            name='test__download_click_handler',
            creator_id=self._creator.id,
        ))

        url_fmt = '/zcomx/downloads/download_click_handler.json?no_queue=1'
        url = url_fmt + '&record_table={t}&record_id={i}'.format(
            t='book',
            i=str(book.id),
        )
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'ok')
        click_id = int(result['id'])
        self.assertTrue(click_id > 0)
        download_click = DownloadClick.from_id(click_id)
        self.assertTrue(download_click)
        self._objects.append(download_click)
        self.assertEqual(download_click.record_table, 'book')
        self.assertEqual(download_click.record_id, book.id)
        self.assertEqual(download_click.loggable, True)
        self.assertEqual(download_click.completed, False)

        # Second post shouldn't be loggable.
        web.sessions = {}
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'ok')
        click_id = int(result['id'])
        self.assertTrue(click_id > 0)
        download_click = DownloadClick.from_id(click_id)
        self.assertTrue(download_click)
        self._objects.append(download_click)
        self.assertEqual(download_click.record_table, 'book')
        self.assertEqual(download_click.record_id, book.id)
        self.assertEqual(download_click.loggable, False)
        self.assertEqual(download_click.completed, True)

        def test_invalid(url):
            web.sessions = {}
            web.post(url)
            result = json.loads(web.text)
            self.assertEqual(
                result,
                {'status': 'error', 'msg': 'Invalid data provided'}
            )

        # Missing record_table
        url = url_fmt + '&record_id={i}'.format(
            i=str(book.id),
        )
        test_invalid(url)

        # Invalid record_table
        url = url_fmt + '&record_table={t}&record_id={i}'.format(
            t='_fake_',
            i=str(book.id),
        )
        test_invalid(url)

        # Missing record_id
        url = url_fmt + '&record_table={t}'.format(
            t='book',
        )
        test_invalid(url)

        # Invalid record_id
        url = url_fmt + '&record_table={t}&record_id={i}'.format(
            t='book',
            i='_invalid_id_',
        )
        test_invalid(url)

    def test__index(self):
        self.assertWebTest('/downloads/index', match_page_key='/default/index')

    def test__modal(self):
        # No book id
        self.assertWebTest(
            '/downloads/modal',
            match_page_key='',
            match_strings=['Invalid data provided']
        )

        # Test with book_id
        self.assertTrue(self._book.cbz)
        self.assertWebTest(
            '/downloads/modal/{bid}'.format(bid=self._book.id),
            match_page_key='/downloads/modal',
            match_strings=[self._book.name]
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
