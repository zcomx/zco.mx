#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/default.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        '404': 'Page not found',
        'data': '<h2>Not authorized</h2>',
        'index': '<div id="front_page">',
        'login': '<h2>Cartoonist Login</h2>',
        'page_not_found': '<h3>Page not found</h3>',
        'user': [
            'web2py_user_form',
            'web2py_user_form_container',
            'forgot_password_container',
            'register_container'
        ],
    }
    url = '/zcomx/default'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

    def test__call(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/call'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__data(self):
        # Permission is denied here, should redirect to index
        self.assertTrue(
            web.test(
                '{url}/data'.format(url=self.url),
                self.titles['index']
            )
        )
        self.assertTrue(
            web.test(
                '{url}/data/book'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__download(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/download'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

        # Test that settings.conf is respected
        self.assertEqual(auth.settings.expiration, 86400)

    def test__user(self):
        self.assertTrue(web.test(
            '{url}/user/login'.format(url=self.url),
            self.titles['user']
        ))

    def test_routes(self):
        # Test various urls and make sure they behave.
        tests = [
            # (url, expect)
            ('/', 'index'),
            ('/zcomx', 'index'),
            ('/zcomx/default', 'index'),
            ('/zcomx/default/index', 'index'),
            ('/appadmin', 'page_not_found'),
            ('/zcomx/appadmin', 'page_not_found'),
        ]
        for t in tests:
            self.assertTrue(web.test(t[0], self.titles[t[1]]))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
