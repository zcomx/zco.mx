#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/cbz.py
"""
import os
import unittest
import urllib.parse
from applications.zcomx.modules.books import (
    Book,
    book_name,
    cbz_comment,
)
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


class TestFunctions(WebTestCase):

    _creator = None
    _book = None
    _server_ip = None

    def tearDown(self):
        for download_click in Records.from_key(
                DownloadClick, dict(ip_address=web.server_ip())):
            download_click.delete()

    @classmethod
    def setUpClass(cls):
        # pylint: disable=invalid-name
        # Get the data the tests will use.
        cls._creator = Creator.by_email(web.username)
        query = (db.book.creator_id == cls._creator.id) & \
            (db.book.name == 'Test Do Not Delete')
        cls._book = Book.from_query(query)

        cls._server_ip = web.server_ip()

    def _get_download_clicks(self, record_table, record_id):
        query = (db.download_click.record_table == record_table) & \
                (db.download_click.record_id == record_id) & \
                (db.download_click.ip_address == self._server_ip)
        return db(query).select()

    def test__download(self):

        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))
        url_path = '/cbz/download/{bid}?no_queue=1'.format(bid=self._book.id)
        self.assertWebTest(
            url_path,
            match_page_key='',
            match_strings=expect,
            charset='latin-1'
        )

        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/download?no_queue=1',
            match_page_key=''
        )

        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/download/-1?no_queue=1',
            match_page_key=''
        )

    def test__route(self):
        # Test creator as id
        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))

        url_path = '/cbz/route?no_queue=1&creator={cid:03d}&cbz={cbz}'.format(
            cid=self._creator.id,
            cbz='{n}.cbz'.format(n=book_name(self._book, use='url'))
        )
        self.assertWebTest(
            url_path,
            match_page_key='',
            match_strings=expect,
            charset='latin-1'
        )

        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test book cbz, creator as name
        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))
        url_path = '/cbz/route?no_queue=1&creator={name}&cbz={cbz}'.format(
            name=self._creator.name_for_url,
            cbz='{n}.cbz'.format(n=book_name(self._book, use='url'))
        )
        self.assertWebTest(
            url_path,
            match_page_key='',
            match_strings=expect,
            charset='latin-1'
        )

        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 2)
        self._objects.append(download_clicks[1])

        # page not found: no args
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/route?no_queue=1',
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid creator integer
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/route/{cid:03d}/{cbz}?no_queue=1'.format(
                cid=-1,
                cbz=urllib.parse.quote_plus(
                    os.path.basename(self._book.cbz)
                ),
            ),
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid creator name
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/route/{name}/{cbz}?no_queue=1'.format(
                name='_invalid_name_',
                cbz=urllib.parse.quote_plus(
                    os.path.basename(self._book.cbz)
                ),
            ),
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid cbz
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/cbz/route/{cbz}?no_queue=1'.format(
                cbz='_invalid_.cbz',
            ),
            match_page_key='/errors/page_not_found',
        )


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
