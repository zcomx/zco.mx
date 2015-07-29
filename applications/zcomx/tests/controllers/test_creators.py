#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/creators.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None

    titles = {
        'creator': '<div id="creator_page">',
        'page_not_found': '<h3>Page not found</h3>',
    }
    url = '/zcomx/creators'

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        email = web.username
        cls._user = db(db.auth_user.email == email).select(limitby=(0, 1)).first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == cls._user.id
        cls._creator = db(query).select(limitby=(0, 1)).first()
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

    def test__creator(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/creator'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')

    def test__index(self):
        # Test: no creator
        self.assertTrue(web.test(
            '{url}/index'.format(
                url=self.url,
            ),
            self.titles['page_not_found']
        ))

        # Test: creator as integer
        self.assertTrue(web.test(
            '{url}/index?creator={cid}'.format(
                url=self.url,
                cid=self._creator.id
            ),
            self.titles['creator']
        ))

        # Test: creator as name
        self.assertTrue(web.test(
            '{url}/index?creator={name}'.format(
                url=self.url,
                name=self._creator.name_for_url
            ),
            self.titles['creator']
        ))

    def test__monies(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/monies'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
