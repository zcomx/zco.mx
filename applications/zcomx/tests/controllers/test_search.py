#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/search.py

"""
import unittest
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'box': '<div id="search">',
        'brick_grid': '<div class="row brick_view">',
        'index': 'zco.mx is a not-for-profit comic-sharing website',
        'list_grid': '<div class="web2py_grid grid_view_list ',
        'list_grid_tile': '<div class="web2py_grid grid_view_tile ',
        'tile_grid': '<div class="row tile_view">',
    }
    url = '/zcomx/search'

    def test__box(self):
        self.assertTrue(web.test('{url}/box.load'.format(
            url=self.url),
            self.titles['box'])
        )

    def test__index(self):
        self.assertTrue(
            web.test('{url}/index'.format(
                url=self.url),
                self.titles['index']
            )
        )

    def test__brick_grid(self):
        query = (db.book.status == True) & \
                (db.book.contributions_remaining > 0) & \
                (db.creator.paypal_email != '')
        books = db(query).select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id)
            ],
            orderby=db.book.contributions_remaining,
            limitby=(0, 1)
        )
        if not books:
            self.fail('No book found in db.')

        book = books[0]

        self.assertTrue(
            web.test('{url}/brick_grid.load'.format(
                url=self.url),
                [self.titles['brick_grid'], book.name]
            )
        )

    def test__list_grid(self):
        query = (db.book.status == True) & \
                (db.book.contributions_remaining > 0) & \
                (db.creator.paypal_email != '')
        books = db(query).select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id)
            ],
            orderby=db.book.contributions_remaining,
            limitby=(0, 1)
        )
        if not books:
            self.fail('No book found in db.')

        book = books[0]

        # No request.vars.view, defaults to tile
        self.assertTrue(web.test('{url}/list_grid.load'.format(
            url=self.url),
            [self.titles['list_grid_tile'], book.name])
        )

        self.assertTrue(web.test('{url}/list_grid.load?view={v}'.format(
            url=self.url, v='list'),
            [self.titles['list_grid'], book.name])
        )

    def test__tile_grid(self):
        query = (db.book.status == True) & \
                (db.book.contributions_remaining > 0) & \
                (db.creator.paypal_email != '')
        books = db(query).select(
            db.book.ALL,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id)
            ],
            orderby=db.book.contributions_remaining,
            limitby=(0, 1)
        )
        if not books:
            self.fail('No book found in db.')

        book = books[0]

        self.assertTrue(
            web.test('{url}/tile_grid.load'.format(
                url=self.url),
                [self.titles['tile_grid'], book.name]
            )
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
