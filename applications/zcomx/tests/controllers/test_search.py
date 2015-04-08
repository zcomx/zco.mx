#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/search.py

"""
import unittest
from applications.zcomx.modules.creators import formatted_name
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'box': '<div id="search">',
        'index': '<div id="front_page">',
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

        query = (db.book.status == BOOK_STATUS_ACTIVE) & \
                (db.book.release_date == None)
        books = db(query).select(
            db.book.ALL,
            left=[
                db.book_page.on(db.book_page.book_id == db.book.id)
            ],
            orderby=~db.book_page.created_on,
            limitby=(0, 1)
        )
        if not books:
            self.fail('No book found in db.')

        book = books[0]

        # Test list view
        self.assertTrue(web.test('{url}/index?view={v}'.format(
            url=self.url, v='list'),
            [self.titles['list_grid'], book.name])
        )

        # Test tile view
        self.assertTrue(web.test('{url}/index?view={v}'.format(
            url=self.url, v='tile'),
            [self.titles['tile_grid'], book.name])
        )

        # Test cartoonists table
        query = (db.book.id != None)
        creators = db(query).select(
            db.creator.ALL,
            left=[
                db.book.on(db.book.creator_id == db.creator.id),
                db.auth_user.on(db.creator.auth_user_id == db.auth_user.id),
            ],
            orderby=db.auth_user.name,
            limitby=(0, 1)
        )
        if not creators:
            self.fail('No creator found in db.')

        creator_name = formatted_name(creators[0])

        self.assertTrue(web.test('{url}/index?view={v}&o={o}'.format(
            url=self.url, v='tile', o='creators'),
            [self.titles['tile_grid'], creator_name])
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
