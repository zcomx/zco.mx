#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/contributions.py

"""
import unittest
from applications.zcomx.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _book = None
    _invalid_book_id = None

    titles = {
            'contribute_widget': [
                '<input type="text" id="contribute_amount"',
                ' id="contribute_link">contribute</a>',
                ],
            'contribute_widget_nada': [
                '<div class="row contribute_widget">',
                '</div>',
                ],
            'index': 'zco.mx is a not-for-profit comic-sharing website',
            'paypal': '<form id="paypal_form"',
            }
    url = '/zcomx/contributions'

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
                    db.creator.on(db.book.creator_id==db.creator.id),
                    db.book_page.on(db.book_page.book_id==db.book.id)
                    ]
                ).first()

        if not cls._book:
            raise SyntaxError('Unable to get book.')

        max_book_id = db.book.id.max()
        rows = db().select(max_book_id)
        if rows:
            cls._invalid_book_id = rows[0][max_book_id] + 1
        else:
            cls._invalid_book_id = 1

    def test__contribute_widget(self):
        # Should handle no id, but display nothing.
        self.assertTrue(web.test('{url}/contribute_widget.load'.format(url=self.url),
            self.titles['contribute_widget_nada']))

        # Invalid id, should display nothing.
        self.assertTrue(web.test('{url}/contribute_widget.load/{bid}'.format(url=self.url,
            bid=self._invalid_book_id),
            self.titles['contribute_widget_nada']))

        # Test valid id
        self.assertTrue(web.test('{url}/contribute_widget.load/{bid}'.format(url=self.url,
            bid=self._book.id),
            self.titles['contribute_widget']))

    def test__index(self):
        self.assertTrue(web.test('{url}/index'.format(url=self.url),
            self.titles['index']))

    def test__paypal(self):
        self.assertTrue(web.test('{url}/paypal'.format(url=self.url),
            self.titles['paypal']))

    def test__record(self):
        # Record redirects
        self.assertTrue(web.test('{url}/record'.format(url=self.url),
            self.titles['paypal']))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
