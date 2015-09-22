#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/cbz.py

"""
import os
import unittest
import urllib2
from applications.zcomx.modules.books import \
    Book, \
    book_name, \
    cbz_comment
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.events import DownloadClick
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None
    _book = None
    _server_ip = None

    titles = {
        'cbz': '30:http://bt.zco.mx:6969/announce',
        'download': '<h2>Not authorized</h2>',
        'page_not_found': '<h3>Page not found</h3>',
    }
    url = '/zcomx/cbz'

    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

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

    def test__download(self):

        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))
        self.assertTrue(web.test(
            '{url}/download/{bid}?no_queue=1'.format(
                url=self.url,
                bid=self._book.id
            ),
            expect
        ))
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        web.sessions = {}    # Prevent 'Changed session ID' warnings.

        def test_invalid(url):
            with self.assertRaises(urllib2.HTTPError) as cm:
                web.test(url, None)
            self.assertEqual(cm.exception.code, 404)
            self.assertEqual(cm.exception.msg, 'NOT FOUND')

        # Test: Invalid, no book id
        test_invalid('{url}/download?no_queue=1'.format(url=self.url))
        # Test: Invalid, invalid book id
        test_invalid('{url}/download/-1?no_queue=1'.format(url=self.url))

    def test__route(self):
        web.sessions = {}    # Prevent 'Changed session ID' warnings.

        # Test creator as id
        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))

        self.assertTrue(web.test(
            '{url}/route?no_queue=1&creator={cid:03d}&cbz={cbz}'.format(
                url=self.url,
                cid=self._creator.id,
                cbz='{n}.cbz'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 1)
        self._objects.append(download_clicks[0])

        # Test book cbz, creator as name
        expect = []
        expect.append(self._book.name)
        expect.append(cbz_comment(self._book))
        self.assertTrue(web.test(
            '{url}/route?no_queue=1&creator={name}&cbz={cbz}'.format(
                url=self.url,
                name=self._creator.name_for_url,
                cbz='{n}.cbz'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))
        download_clicks = self._get_download_clicks('book', self._book.id)
        self.assertEqual(len(download_clicks), 2)
        self._objects.append(download_clicks[1])

        web.sessions = {}    # Prevent 'Changed session ID' warnings.

        # page not found: no args
        self.assertTrue(web.test(
            '{url}/route?no_queue=1'.format(url=self.url),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator integer
        self.assertTrue(web.test(
            '{url}/route/{cid:03d}/{cbz}?no_queue=1'.format(
                url=self.url,
                cid=-1,
                cbz=os.path.basename(self._book.cbz),
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator name
        self.assertTrue(web.test(
            '{url}/route/{name}/{cbz}?no_queue=1'.format(
                url=self.url,
                name='_invalid_name_',
                cbz=os.path.basename(self._book.cbz),
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid cbz
        self.assertTrue(web.test(
            '{url}/route/{cbz}?no_queue=1'.format(
                url=self.url,
                cbz='_invalid_.cbz',
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
