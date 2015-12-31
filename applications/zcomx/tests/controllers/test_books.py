#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/books.py

"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    def test__book(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/book', match_page_key='')

    def test__index(self):
        self.assertWebTest('/books/index', match_page_key='/default/index')

    def test__reader(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/reader', match_page_key='')

    def test__scroller(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/scroller', match_page_key='')

    def test__slider(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/books/slider', match_page_key='')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
