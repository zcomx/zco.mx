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
        'contribute': '<form id="paypal_form"',
        'data': '<h2>Not authorized</h2>',
        'faq': '<h1>FAQ</h1>',
        'faqc': '<h1>Creator FAQ</h1>',
        'files': '<div id="files_page">',
        'goodwill': '<h1>Goodwill</h1>',
        'index': 'zco.mx is a not-for-profit comic-sharing website',
        'logos': '<h1>Logos</h1>',
        'overview': '<h1>Overview</h1>',
        'todo': '<h1>TODO</h1>',
        'top': '<h2>Top</h2>',
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
    @classmethod
    def setUp(cls):
        # Prevent 'Change session ID' warnings.
        web.sessions = {}

    def test__call(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/call'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__contribute(self):
        self.assertTrue(web.test(
            '{url}/contribute'.format(url=self.url),
            self.titles['contribute']
        ))

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

    def test__faq(self):
        self.assertTrue(web.test(
            '{url}/faq'.format(url=self.url),
            self.titles['faq']
        ))

    def test__faqc(self):
        self.assertTrue(web.test(
            '{url}/faqc'.format(url=self.url),
            self.titles['faqc']
        ))

    def test__files(self):
        self.assertTrue(web.test(
            '{url}/files'.format(url=self.url),
            self.titles['files']
        ))

    def test__goodwill(self):
        web.sessions = {}
        self.assertTrue(web.test(
            '{url}/goodwill'.format(url=self.url),
            self.titles['goodwill']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

        # Test that settings.conf is respected
        self.assertEqual(auth.settings.expiration, 86400)

    def test__logos(self):
        self.assertTrue(web.test(
            '{url}/logos'.format(url=self.url),
            self.titles['logos']
        ))

    def test__overview(self):
        self.assertTrue(web.test(
            '{url}/overview'.format(url=self.url),
            self.titles['overview']
        ))

    def test__todo(self):
        self.assertTrue(web.test(
            '{url}/todo'.format(url=self.url),
            self.titles['todo']
        ))

    def test__top(self):
        self.assertTrue(web.test(
            '{url}/top'.format(url=self.url),
            self.titles['top']
        ))

    def test__user(self):
        self.assertTrue(web.test(
            '{url}/user/login'.format(url=self.url),
            self.titles['user']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
