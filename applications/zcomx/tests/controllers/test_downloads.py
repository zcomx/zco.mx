#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/downloads.py
"""
import json
import unittest
from applications.zcomx.modules.books import (
    Book,
    cbz_url,
    downloadable as downable_books,
    formatted_name,
    magnet_uri,
    torrent_url as book_torrent_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    downloadable as downable_creators,
    torrent_url as creator_torrent_url,
)
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


class TestFunctions(WebTestCase):
    _book = None
    _creator = None
    _invalid_book_id = None

    # pylint: disable=invalid-name
    def setUp(self):
        # Get a book from a creator with a paypal_email.
        self._creator = Creator.by_email(web.username)
        query = (db.book.creator_id == self._creator.id) & \
            (db.book.name == 'Test Do Not Delete')
        self._book = Book.from_query(query)

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
        # Test user agent will be interpreted as bot.
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

    def test__downloadable_books(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

        downable = list(
            downable_books(creator_id=self._creator.id, orderby=db.book.name))

        url_fmt = '/zcomx/downloads/downloadable_books.json/{i}'
        url = url_fmt.format(i=self._creator.id)
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'ok')
        books = result['books']
        self.assertEqual(len(books), len(downable))
        keys = ['id', 'title', 'torrent_url', 'magnet_uri', 'cbz_url']
        self.assertEqual(list(books[0].keys()), keys)

        self.assertEqual(books[0]['id'], downable[0].id)

        self.assertEqual(
            books[0]['title'],
            formatted_name(
                self._book,
                include_publication_year=(self._book.release_date != None)
            )
        )

        self.assertEqual(
            books[0]['torrent_url'],
            book_torrent_url(self._book, extension=False)
        )
        self.assertEqual(
            books[0]['magnet_uri'],
            magnet_uri(self._book)
        )
        self.assertEqual(
            books[0]['cbz_url'],
            cbz_url(self._book, extension=False)
        )

        # Test no creator
        web.sessions = {}
        url = '/zcomx/downloads/downloadable_books.json'
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['msg'], 'Unable to get list of books.')

        # Test invalid creator
        url = url_fmt.format(i=-1)
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['msg'], 'Unable to get list of books.')

    def test__downloadable_creators(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

        downable = list(downable_creators(orderby=db.creator.name_for_search))

        url = '/zcomx/downloads/downloadable_creators.json'
        web.post(url)
        result = json.loads(web.text)
        self.assertEqual(result['status'], 'ok')
        creators = result['creators']
        self.assertEqual(len(creators), len(downable))
        keys = ['id', 'name', 'torrent_url']
        self.assertEqual(list(creators[0].keys()), keys)

        self.assertEqual(creators[0]['id'], downable[0].id)
        self.assertEqual(creators[0]['name'], downable[0].name)
        self.assertEqual(
            creators[0]['torrent_url'],
            creator_torrent_url(downable[0], extension=False)
        )

    def test__index(self):
        self.assertWebTest('/downloads/index', match_page_key='/default/index')

    def test__modal(self):
        # No book id, no creator id
        creators = downable_creators(
            orderby=db.creator.name_for_search,
            limitby=(0, 1)
        )
        expect_creator = creators[0]

        books = downable_books(
            creator_id=expect_creator.id,
            orderby=db.book.name,
            limitby=(0, 1)
        )
        expect_book = books[0]

        self.assertWebTest(
            '/downloads/modal',
            match_page_key='/downloads/modal',
            match_strings=[
                "'default_creator_id': {i}".format(i=expect_creator.id),
                "'default_book_id': {i}".format(i=expect_book.id),
            ]
        )

        # Test with book_id
        self.assertWebTest(
            '/downloads/modal/book/{i}'.format(i=self._book.id),
            match_page_key='/downloads/modal',
            match_strings=[
                "'default_creator_id': {i}".format(i=self._creator.id),
                "'default_book_id': {i}".format(i=self._book.id),
            ]
        )

        # Test with creator
        self.assertWebTest(
            '/downloads/modal/creator/{i}'.format(i=self._creator.id),
            match_page_key='/downloads/modal',
            match_strings=[
                "'default_creator_id': {i}".format(i=self._creator.id),
                "'default_book_id': {i}".format(i=self._book.id),
            ]
        )


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
