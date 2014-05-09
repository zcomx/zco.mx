#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/search.py

"""
import unittest
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
            'box': 'search: creator/title',
            'cover_grid': '<div class="col-sm-12 col-md-6 item_container odd">',
            'index': 'zcomix.com is a not-for-profit comic-sharing website',
            'list_grid': 'records found',
            }
    url = '/zcomix/search'

    def test__box(self):
        self.assertTrue(web.test('{url}/box.load'.format(url=self.url),
            self.titles['box']))

    def test__cover_grid(self):
        books = db(db.book).select(db.book.ALL,
                orderby=~db.book.contributions_year, limitby=(0, 1))
        if not books:
            self.fail('No book found in db.')
        book = books[0]
        self.assertTrue(web.test('{url}/cover_grid.load'.format(url=self.url),
            [self.titles['cover_grid'], book.name]))

    def test__index(self):
        self.assertTrue(web.test('{url}/index'.format(url=self.url),
            self.titles['index']))

    def test__list_grid(self):
        books = db(db.book).select(db.book.ALL,
                orderby=~db.book.contributions_year, limitby=(0, 1))
        if not books:
            self.fail('No book found in db.')
        book = books[0]
        self.assertTrue(web.test('{url}/list_grid.load'.format(url=self.url),
            [self.titles['list_grid'], book.name]))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
