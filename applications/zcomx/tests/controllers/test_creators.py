#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/creators.py

"""
import unittest
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
        # Without a creator id, should revert to default page.
        self.assertTrue(web.test(
            '{url}/creator'.format(url=self.url),
            self.titles['default']
        ))

        self.assertTrue(web.test('{url}/creator/{id}'.format(
            url=self.url, id=self._creator.id),
            self.titles['creator']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['default']
        ))

        # With integer should redirect to creator page
        self.assertTrue(web.test(
            '{url}/index/{cid}'.format(
                url=self.url,
                cid=self._creator.id
            ),
            self.titles['creator']
        ))

        # With valid name should redirect to creator page
        name = self._creator.path_name.replace(' ', '_')
        self.assertTrue(web.test(
            '{url}/index/{name}'.format(
                url=self.url,
                name=name
            ),
            self.titles['creator']
        ))

        # With invalid name should redirect to default
        self.assertTrue(web.test(
            '{url}/index/{name}'.format(
                url=self.url,
                name='Invalid_Creator'
            ),
            self.titles['default']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
