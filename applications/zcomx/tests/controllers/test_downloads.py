#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/downloads.py

"""
import datetime
import unittest
import urllib
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
        'modal': [
            '<div id="contribute_modal_page">',
            'Your donations help cover the'
        ],
        'modal_book': [
            '<div id="contribute_modal_page">',
            'Contributions go directly to the cartoonist',
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
        cls._book = db(db.creator.paypal_email != '').select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id),
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
        ).first()

        if not cls._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            cls._invalid_book_id = rows[0][max_book_id] + 1
        else:
            cls._invalid_book_id = 1

        cls._creator = db(db.creator.paypal_email != '').select().first()
        if not cls._creator:
            raise SyntaxError('Unable to get creator.')

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__modal(self):
        self.assertTrue(
            web.test(
                '{url}/modal'.format(url=self.url),
                self.titles['modal']
            )
        )

        return
        # Test with book_id
        expect = list(self.titles['modal_book'])
        expect.append(self._book.name)
        self.assertTrue(
            web.test(
                '{url}/modal?book_id={bid}'.format(
                    url=self.url,
                    bid=self._book.id
                ),
                expect
            )
        )
        # Test with creator_id
        expect = list(self.titles['modal_book'])
        expect.append(formatted_name(self._creator))
        self.assertTrue(
            web.test(
                '{url}/modal?creator_id={cid}'.format(
                    url=self.url,
                    cid=self._creator.id
                ),
                expect
            )
        )
        # Book is not found.
        self.assertFalse(
            web.test(
                '{url}/modal?creator_id={cid}'.format(
                    url=self.url,
                    cid=self._creator.id
                ),
                self._book.name
            )
        )

        # Test with book_id and creator_id
        expect = list(self.titles['modal_book'])
        expect.append(self._book.name)
        self.assertTrue(
            web.test(
                '{url}/modal?book_id={bid}'.format(
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
