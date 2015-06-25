#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/downloads.py

"""
import unittest
from gluon.contrib.simplejson import loads
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _book = None
    _creator = None
    _invalid_book_id = None

    titles = {
        'index': '<div id="front_page">',
        'modal_book': [
            '<div id="download_modal_page">',
            'magnet:?xt=urn:tree:tiger',
        ],
        'modal_invalid': 'Invalid data provided',
    }
    url = '/zcomx/downloads'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book from a creator with a paypal_email.
        email = web.username
        self._creator = db(db.creator.email == email).select().first()
        if not self._creator:
            raise SyntaxError('Unable to get creator.')

        self._book = db(db.book.creator_id == self._creator.id).select(
            db.book.ALL,
            orderby=db.book.id,
        ).first()

        if not self._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            self._invalid_book_id = rows[0][max_book_id] + 1
        else:
            self._invalid_book_id = 1

    def test__download_click_handler(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

        book = self.add(db.book, dict(
            name='test__download_click_handler',
            creator_id=self._creator.id,
        ))

        url_fmt = '{url}/download_click_handler.json?no_queue=1'.format(
            url=self.url)

        url = url_fmt + '&record_table={t}&record_id={i}'.format(
            t='book',
            i=str(book.id),
        )
        web.post(url)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        click_id = int(result['id'])
        self.assertTrue(click_id > 0)
        download_click = db(db.download_click.id == click_id).select().first()
        self.assertTrue(download_click)
        self._objects.append(download_click)
        self.assertEqual(download_click.record_table, 'book')
        self.assertEqual(download_click.record_id, book.id)
        self.assertEqual(download_click.loggable, True)
        self.assertEqual(download_click.completed, False)

        # Second post shouldn't be loggable.
        web.sessions = {}
        web.post(url)
        result = loads(web.text)
        self.assertEqual(result['status'], 'ok')
        click_id = int(result['id'])
        self.assertTrue(click_id > 0)
        download_click = db(db.download_click.id == click_id).select().first()
        self.assertTrue(download_click)
        self._objects.append(download_click)
        self.assertEqual(download_click.record_table, 'book')
        self.assertEqual(download_click.record_id, book.id)
        self.assertEqual(download_click.loggable, False)
        self.assertEqual(download_click.completed, True)

        def test_invalid(url):
            web.sessions = {}
            web.post(url)
            result = loads(web.text)
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

        web.sessions = {}

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__modal(self):
        # No book id
        self.assertTrue(
            web.test(
                '{url}/modal'.format(
                    url=self.url,
                ),
                self.titles['modal_invalid']
            )
        )

        # Test with book_id
        self.assertTrue(self._book.cbz)
        expect = list(self.titles['modal_book'])
        expect.append(self._book.name)
        self.assertTrue(
            web.test(
                '{url}/modal/{bid}'.format(
                    url=self.url,
                    bid=self._book.id
                ),
                expect
            )
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
