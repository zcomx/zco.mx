#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/downloads.py

"""
import unittest
import urllib2
from applications.zcomx.modules.creators import formatted_name
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
    }
    url = '/zcomx/downloads'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        # Get a book from a creator with a paypal_email.
        email = web.username
        cls._creator = db(db.creator.email == email).select().first()
        if not cls._creator:
            raise SyntaxError('Unable to get creator.')

        cls._book = db(db.book.creator_id == cls._creator.id).select(
            db.book.ALL,
            orderby=db.book.id,
        ).first()

        if not cls._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            cls._invalid_book_id = rows[0][max_book_id] + 1
        else:
            cls._invalid_book_id = 1


    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__modal(self):
        # No book id
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/modal'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

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
