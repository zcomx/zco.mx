#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/torrents.py

"""
import os
import unittest
import urllib2
from applications.zcomx.modules.books import book_name
from applications.zcomx.modules.creators import creator_name
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None
    _book = None

    titles = {
        'download': '<h2>Not authorized</h2>',
        'page_not_found': '<h3>Page not found</h3>',
        'torrent': '30:http://bt.zco.mx:6969/announce',
    }
    url = '/zcomx/torrents'

    @classmethod
    def setUp(cls):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

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
        def get_download_clicks(record_table, record_id, ip_address=None):
            query = (db.download_click.record_table == record_table) & \
                    (db.download_click.record_id == record_id)
            if ip_address is not None:
                query = query & (db.download_click.ip_address == ip_address)
            return db(query).select()

        # Test book torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/download/book/{bid}?no_queue=1'.format(
                url=self.url,
                bid=self._book.id
            ),
            expect
        ))
        download_clicks = get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test creator torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(creator_name(self._creator, use='file'))
        self.assertTrue(web.test(
            '{url}/download/creator/{cid}?no_queue=1'.format(
                url=self.url,
                cid=self._creator.id
            ),
            expect
        ))
        download_clicks = get_download_clicks('creator', self._creator.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        ip_address = download_clicks[0].ip_address

        # Test 'all' torrent.
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/download/all?no_queue=1'.format(url=self.url),
            expect
        ))
        download_clicks = get_download_clicks('all', 0, ip_address=ip_address)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        def test_invalid(url):
            with self.assertRaises(urllib2.HTTPError) as cm:
                web.test(url, None)
            self.assertEqual(cm.exception.code, 404)
            self.assertEqual(cm.exception.msg, 'NOT FOUND')

        # Test: Invalid, no torrent type provided
        test_invalid('{url}/download?no_queue=1'.format(url=self.url))
        # Test: Invalid, invalid torrent type provided
        test_invalid('{url}/download/_fake_?no_queue=1'.format(url=self.url))
        # Test: Invalid, book torrent with no id
        test_invalid('{url}/download/book?no_queue=1'.format(url=self.url))
        # Test: Invalid, creator torrent with no id
        test_invalid('{url}/download/creator?no_queue=1'.format(url=self.url))
        # Test: Invalid, book torrent with invalid id
        test_invalid('{url}/download/book/-1?no_queue=1'.format(url=self.url))
        # Test: Invalid, creator torrent with invalid id
        test_invalid('{url}/download/creator/-1?no_queue=1'.format(
            url=self.url))

        # Cleanup
        db(db.download_click.ip_address == ip_address).delete()
        db.commit()

    def test__route(self):

        def get_download_clicks(record_table, record_id, ip_address=None):
            query = (db.download_click.record_table == record_table) & \
                    (db.download_click.record_id == record_id)
            if ip_address is not None:
                query = query & (db.download_click.ip_address == ip_address)
            return db(query).select()

        # Test creator torrent
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/route?no_queue=1&torrent={tor}'.format(
                url=self.url,
                tor=os.path.basename(self._creator.torrent),
            ),
            expect
        ))
        download_clicks = get_download_clicks('creator', self._creator.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        ip_address = download_clicks[0].ip_address

        # Test book torrent, creator as id
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._book.name)

        self.assertTrue(web.test(
            '{url}/route?no_queue=1&creator={cid:03d}&torrent={tor}'.format(
                url=self.url,
                cid=self._creator.id,
                tor='{n}.torrent'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))
        download_clicks = get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test book torrent, creator as name
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/route?no_queue=1&creator={name}&torrent={tor}'.format(
                url=self.url,
                name=self._creator.name_for_url,
                tor='{n}.torrent'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))
        download_clicks = get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 2)
        self._objects.append(download_clicks[1])

        # Test 'all' torrent
        expect = []
        expect.append(self.titles['torrent'])
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertTrue(web.test(
            '{url}/route?no_queue=1&torrent=zco.mx.torrent'.format(url=self.url),
            expect
        ))
        download_clicks = get_download_clicks('all', 0, ip_address=ip_address)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        web.sessions = {}    # Prevent 'Changed session ID' warnings.

        # page not found: no args
        self.assertTrue(web.test(
            '{url}/route?no_queue=1'.format(url=self.url),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator integer
        self.assertTrue(web.test(
            '{url}/route/{cid:03d}/{tor}?no_queue=1'.format(
                url=self.url,
                cid=-1,
                tor=os.path.basename(self._book.torrent),
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator name
        self.assertTrue(web.test(
            '{url}/route/{name}/{tor}?no_queue=1'.format(
                url=self.url,
                name='_invalid_name_',
                tor=os.path.basename(self._book.torrent),
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid torrent
        self.assertTrue(web.test(
            '{url}/route/{tor}?no_queue=1'.format(
                url=self.url,
                tor='_invalid_.torrent',
            ),
            self.titles['page_not_found']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
