#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/default.py

"""
import unittest
import urllib2
from applications.zcomx.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'index': '<h3>Server error</h3>',
        'page_not_found': '<h3>Page not found</h3>',
    }
    url = '/zcomx/errors'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        # Prevent 'Change session ID' warnings.
        web.sessions = {}

    def test__handler(self):
        self.assertTrue(web.test(
            '{url}/handler'.format(url=self.url),
            self.titles['index']
        ))


    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

    def test__page_not_found(self):
        self.assertTrue(web.test(
            '{url}/page_not_found'.format(url=self.url),
            self.titles['page_not_found']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
