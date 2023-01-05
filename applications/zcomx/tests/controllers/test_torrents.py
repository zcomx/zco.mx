#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/torrents.py

"""
import os
import unittest
import urllib.parse
from applications.zcomx.modules.books import \
    Book, \
    book_name
from applications.zcomx.modules.creators import \
    Creator, \
    creator_name
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.helpers import WebTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    _creator = None
    _book = None
    _server_ip = None

    def tearDown(self):
        if self._server_ip:
            for download_click in Records.from_key(
                    DownloadClick, dict(ip_address=self._server_ip)):
                download_click.delete()

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        email = web.username
        query = (db.auth_user.email == email)
        cls._user = db(query).select(limitby=(0, 1)).first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        cls._creator = Creator.from_key(dict(auth_user_id=cls._user.id))
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        query = db.book.creator_id == cls._creator.id
        cls._book = Book.from_query(query)
        if not cls._book:
            raise SyntaxError('No book for creator with email: {e}'.format(
                e=email))

        cls._server_ip = web.server_ip()

    def _get_download_clicks(self, record_table, record_id):
        query = (db.download_click.record_table == record_table) & \
                (db.download_click.record_id == record_id) & \
                (db.download_click.ip_address == self._server_ip)
        return db(query).select()

    def test__download(self):
        # Test book torrent.
        self.assertWebTest(
            '/torrents/download/book/{bid}?no_queue=1'.format(
                bid=self._book.id
            ),
            match_page_key='/torrents/torrent',
            match_strings=[self._book.name],
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test creator torrent.
        self.assertWebTest(
            '/torrents/download/creator/{cid}?no_queue=1'.format(
                cid=self._creator.id
            ),
            match_page_key='/torrents/torrent',
            match_strings=[creator_name(self._creator, use='file')],
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks(
            'creator', self._creator.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test 'all' torrent.
        expect = []
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertWebTest(
            '/torrents/download/all?no_queue=1',
            match_page_key='/torrents/torrent',
            match_strings=expect,
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks('all', 0)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        def test_invalid(url):
            self.assertRaisesHTTPError(
                404, self.assertWebTest, url, match_page_key='')

        # Test: Invalid, no torrent type provided
        test_invalid('/torrents/download?no_queue=1')
        # Test: Invalid, invalid torrent type provided
        test_invalid('/torrents/download/_fake_?no_queue=1')
        # Test: Invalid, book torrent with no id
        test_invalid('/torrents/download/book?no_queue=1')
        # Test: Invalid, creator torrent with no id
        test_invalid('/torrents/download/creator?no_queue=1')
        # Test: Invalid, book torrent with invalid id
        test_invalid('/torrents/download/book/-1?no_queue=1')
        # Test: Invalid, creator torrent with invalid id
        test_invalid('/torrents/download/creator/-1?no_queue=1')

    def test__route(self):

        # Test creator torrent
        expect = []
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertWebTest(
            '/torrents/route?no_queue=1&torrent={tor}'.format(
                tor=urllib.parse.quote_plus(
                    os.path.basename(self._creator.torrent)
                ),
            ),
            match_page_key='/torrents/torrent',
            match_strings=expect,
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks(
            'creator', self._creator.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test book torrent, creator as id
        fmt = '/torrents/route?no_queue=1&creator={cid:03d}&torrent={tor}'
        self.assertWebTest(
            fmt.format(
                cid=self._creator.id,
                tor='{n}.torrent'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/torrents/torrent',
            match_strings=[self._book.name],
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test book torrent, creator as name
        self.assertWebTest(
            '/torrents/route?no_queue=1&creator={name}&torrent={tor}'.format(
                name=self._creator.name_for_url,
                tor='{n}.torrent'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/torrents/torrent',
            match_strings=[self._book.name],
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 2)
        self._objects.append(download_clicks[1])

        # Test 'all' torrent
        expect = []
        expect.append(creator_name(self._creator, use='file'))
        expect.append(self._book.name)
        self.assertWebTest(
            '/torrents/route?no_queue=1&torrent=zco.mx.torrent',
            match_page_key='/torrents/torrent',
            match_strings=expect,
            charset='latin-1',
        )
        download_clicks = self._get_download_clicks('all', 0)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # page not found: no args
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/torrents/route?no_queue=1',
            match_page_key='/errors/page_not_found',
            charset='latin-1',
        )

        # page not found: invalid creator integer
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/torrents/route/{cid:03d}/{tor}?no_queue=1'.format(
                cid=-1,
                tor=urllib.parse.quote_plus(
                    os.path.basename(self._book.torrent)
                ),
            ),
            match_page_key='/errors/page_not_found',
            charset='latin-1',
        )

        # page not found: invalid creator name
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/torrents/route/{name}/{tor}?no_queue=1'.format(
                name='_invalid_name_',
                tor=urllib.parse.quote_plus(
                    os.path.basename(self._book.torrent)
                ),
            ),
            match_page_key='/errors/page_not_found',
            charset='latin-1',
        )

        # page not found: invalid torrent
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/torrents/route/{tor}?no_queue=1'.format(
                tor='_invalid_.torrent',
            ),
            match_page_key='/errors/page_not_found',
            charset='latin-1',
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
