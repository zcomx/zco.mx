#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/torrents.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None
    _book = None

    titles = {
        'download': '<h2>Not authorized</h2>',
        'torrent': '30:http://bt.zco.mx:6969/announce',
    }
    url = '/zcomx/torrents'

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

        query = db.book.creator_id == cls._creator.id
        cls._book = db(query).select().first()
        if not cls._book:
            raise SyntaxError('No book for creator with email: {e}'.format(
                e=email))

    def test__download(self):
        # Test 'all' torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._creator.path_name)
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/download/all'.format(url=self.url),
            expect
        ))

        # Test book torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/download/book/{bid}'.format(
                url=self.url,
                bid=self._book.id
            ),
            expect
        ))

        # Test creator torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._creator.path_name)
        self.assertTrue(web.test(
            '{url}/download/creator/{cid}'.format(
                url=self.url,
                cid=self._creator.id
            ),
            expect
        ))

        def test_invalid(url):
            with self.assertRaises(urllib2.HTTPError) as cm:
                web.test(url, None)
            self.assertEqual(cm.exception.code, 404)
            self.assertEqual(cm.exception.msg, 'NOT FOUND')

        # Test: Invalid, no torrent type provided
        test_invalid('{url}/download'.format(url=self.url))
        # Test: Invalid, invalid torrent type provided
        test_invalid('{url}/download/_fake_'.format(url=self.url))
        # Test: Invalid, book torrent with no id
        test_invalid('{url}/download/book'.format(url=self.url))
        # Test: Invalid, creator torrent with no id
        test_invalid('{url}/download/creator'.format(url=self.url))
        # Test: Invalid, book torrent with invalid id
        test_invalid('{url}/download/book/-1'.format(url=self.url))
        # Test: Invalid, creator torrent with invalid id
        test_invalid('{url}/download/creator/-1'.format(url=self.url))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
