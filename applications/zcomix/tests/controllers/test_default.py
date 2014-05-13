#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/default.py

"""
import unittest
import urllib2
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'data': '<h2>Not authorized</h2>',
        'faq': '<h1>FAQ</h1>',
        'index': 'This is a not-for-profit site dedicated to promoting',
        'todo': '<h1>TODO</h1>',
        'user': [
            'web2py_user_form',
            'web2py_user_form_container',
            'forgot_password_container',
            'register_container'
        ],
    }
    url = '/zcomix/default'

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

    def test__faq(self):
        self.assertTrue(web.test(
            '{url}/faq'.format(url=self.url),
            self.titles['faq']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

        # Test that settings.conf is respected
        self.assertEqual(auth.settings.expiration, 86400)

    def test__todo(self):
        self.assertTrue(web.test(
            '{url}/todo'.format(url=self.url),
            self.titles['todo']
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
