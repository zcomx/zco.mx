#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/default.py

"""
import unittest
from applications.zcomx.modules.tests.helpers import \
    WebTestCase, \
    skip_if_quick


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    def test__call(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/default/call', match_page_key='')

    def test__data(self):
        # Permission is denied here, should redirect to index

        self.assertWebTest('/default/data', match_page_key='/default/index')
        self.assertWebTest(
            '/default/data/book', match_page_key='/default/index')

    def test__download(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/default/download', match_page_key='')

    def test__index(self):
        self.assertWebTest('/default/index')

        # Test that settings.conf is respected
        self.assertEqual(auth.settings.expiration, 86400)

    def test__user(self):
        self.assertWebTest('/default/user/login')

    @skip_if_quick
    def test_routes(self):
        # Test various urls and make sure they behave.
        tests = [
            # (url, match_page_key)
            ('/', '/default/index'),
            ('/zcomx', '/default/index'),
            ('/zcomx/default', '/default/index'),
            ('/zcomx/default/index', '/default/index'),
        ]
        for t in tests:
            self.assertWebTest(t[0], app='', match_page_key=t[1])

        # Test pages that should not exist
        tests = [
            # (url, match_page_key)
            ('/appadmin', '/errors/page_not_found'),
            ('/zcomx/appadmin', '/errors/page_not_found'),
        ]
        for t in tests:
            self.assertRaisesHTTPError(
                404,
                self.assertWebTest,
                t[0],
                match_page_key=t[1],
            )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
