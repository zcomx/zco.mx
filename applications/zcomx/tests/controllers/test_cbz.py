#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/cbz.py

"""
import os
import unittest
from applications.zcomx.modules.books import \
    Book, \
    book_name, \
    cbz_comment
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.helpers import \
    WebTestCase, \
    skip_if_quick

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


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
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        cls._creator = Creator.by_email(web.username)
        cls._book = Book.from_key(dict(creator_id=cls._creator.id))
        cls._server_ip = web.server_ip()

    def _get_download_clicks(self, record_table, record_id):
        query = (db.download_click.record_table == record_table) & \
                (db.download_click.record_id == record_id) & \
                (db.download_click.ip_address == self._server_ip)
        return db(query).select()

    @skip_if_quick
    def test__download(self):

        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))
        url_path = '/cbz/download/{bid}?no_queue=1'.format(bid=self._book.id)
        self.assertWebTest(url_path, match_page_key='', match_strings=expect)

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

    @skip_if_quick
    def test__route(self):
        # Test creator as id
        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))

        url_path = '/cbz/route?no_queue=1&creator={cid:03d}&cbz={cbz}'.format(
            cid=self._creator.id,
            cbz='{n}.cbz'.format(n=book_name(self._book, use='url'))
        )
        self.assertWebTest(url_path, match_page_key='', match_strings=expect)

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
        self.assertWebTest(url_path, match_page_key='', match_strings=expect)

        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 2)
        self._objects.append(download_clicks[1])

        # page not found: no args
        url_path = '/cbz/route?no_queue=1'
        self.assertWebTest(url_path, match_page_key='/errors/page_not_found')

        # page not found: invalid creator integer
        url_path = '/cbz/route/{cid:03d}/{cbz}?no_queue=1'.format(
            cid=-1,
            cbz=os.path.basename(self._book.cbz),
        )
        self.assertWebTest(url_path, match_page_key='/errors/page_not_found')

        # page not found: invalid creator name
        url_path = '/cbz/route/{name}/{cbz}?no_queue=1'.format(
            name='_invalid_name_',
            cbz=os.path.basename(self._book.cbz),
        )
        self.assertWebTest(url_path, match_page_key='/errors/page_not_found')

        # page not found: invalid cbz
        url_path = '/cbz/route/{cbz}?no_queue=1'.format(
            cbz='_invalid_.cbz',
        )
        self.assertWebTest(url_path, match_page_key='/errors/page_not_found')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
