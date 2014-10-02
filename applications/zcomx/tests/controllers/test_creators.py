#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/creators.py

"""
import unittest
import urllib2
from applications.zcomx.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None

    titles = {
        'books': [
            '<div class="grid_section">',
            'loading...',
        ],
        'books_release': [
            '<div class="grid_section">',
            'loading...',
            '<h4>Released</h4>',
            '<h4>Ongoing</h4>',
        ],
        'creator': '<div id="creator_page">',
        'default': 'zco.mx is a not-for-profit comic-sharing website',
    }
    url = '/zcomx/creators'

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == cls._user.id
        cls._creator = db(query).select().first()
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

    def test__books(self):
        self.assertTrue(web.test(
            '{url}/books.load/{cid}'.format(
                url=self.url,
                cid=self._creator.id
            ),
            self.titles['books']
        ))

        self.assertTrue(web.test(
            '{url}/books.load/{cid}?can_release=1'.format(
                url=self.url,
                cid=self._creator.id
            ),
            self.titles['books_release']
        ))

    def test__creator(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/creator'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__index(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/index'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

        # Test: creator as integer
        self.assertTrue(web.test(
            '{url}/index?creator={cid}'.format(
                url=self.url,
                cid=self._creator.id
            ),
            self.titles['creator']
        ))

        # Test: creator as path_name
        self.assertTrue(web.test(
            '{url}/index?creator={name}'.format(
                url=self.url,
                name=self._creator.path_name
            ),
            self.titles['creator']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
