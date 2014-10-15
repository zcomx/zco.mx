#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/search.py

"""

import unittest
from gluon import *
from applications.zcomx.modules.search import Search
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestSearch(LocalTestCase):

    def test____init__(self):
        search = Search()
        self.assertTrue(search)
        self.assertTrue('newest pages' in search.order_fields)
        self.assertTrue('views' in search.order_fields)

    def test__set(self):
        search = Search()
        self.assertFalse(search.grid)
        search.set(db, request)
        self.assertTrue(search.grid)
        query = (db.book.status == True) & \
            (db.book.contributions_remaining > 0) & \
            (db.creator.paypal_email != '')
        rows = db(query).select(
            db.book.id,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id)
            ]
        )
        self.assertEqual(len(search.grid.rows), len(rows))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
