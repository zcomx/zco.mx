#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/downloaders.py

"""
import os
import unittest
from gluon import *
from gluon.html import DIV, IMG
from gluon.http import HTTP
from gluon.storage import List
from applications.zcomx.modules.archives import TorrentArchive
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.downloaders import \
    CBZDownloader, \
    ImageDownloader, \
    TorrentDownloader
from applications.zcomx.modules.images import \
    UploadImage, \
    filename_for_size
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    skip_if_quick
from applications.zcomx.modules.tests.runner import \
    LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212


class WithObjectsTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _auth_user = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        email = 'up_image@example.com'
        self._auth_user = self.add(AuthUser, dict(
            name='test_downloaders',
            email=email,
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email=email,
        ))
        super(WithObjectsTestCase, self).setUp()

    def tearDown(self):
        if self._creator.image:
            up_image = UploadImage(db.creator.image, self._creator.image)
            up_image.delete_all()
        super(WithObjectsTestCase, self).tearDown()


class TestCBZDownloader(LocalTestCase):

    def test__download(self):
        downloader = CBZDownloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']

        def test_http(args, expect):
            request.args = List(args)
            try:
                downloader.download(request, db)
            except HTTP as http:
                self.assertEqual(http.status, expect['status'])
                if expect['status'] == 200:
                    self.assertEqual(
                        http.headers['Content-Type'],
                        'application/x-cbz'
                    )
                    self.assertEqual(
                        http.headers['Content-Disposition'],
                        'attachment; filename="{f}"'.format(
                            f=expect['filename'])
                    )
                    self.assertEqual(
                        http.headers['Content-Length'],
                        expect['size']
                    )

        # Find a book with a cbz.
        creator = Creator.by_email(web.username)
        query = (db.book.creator_id == creator.id) & \
            (db.book.cbz != None)

        book = Book.from_query(query)
        if not book:
            self.fail('Book by creator {c} with cbz not found.'.format(
                c=creator.email))

        test_http(
            [book.id],
            dict(
                status=200,
                filename=os.path.basename(book.cbz),
                size=os.stat(book.cbz).st_size,
            )
        )

        # Test invalids
        invalid_record_id = -1
        test_http([invalid_record_id], dict(status=404))

        # Find a book without a cbz.
        book = Book.from_key(dict(cbz=None))
        if book:
            test_http([book.id], dict(status=404))


class TestImageDownloader(WithObjectsTestCase, ImageTestCase):

    @skip_if_quick
    def test__download(self):
        downloader = ImageDownloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']

        def set_lengths():
            lengths = {}
            for size in ['original', 'cbz', 'web']:
                unused_name, fullname = db.creator.image.retrieve(
                    self._creator.image, nameonly=True)
                filename = filename_for_size(fullname, size)
                if os.path.exists(filename):
                    lengths[size] = os.stat(filename).st_size
            return lengths

        def test_http(expect_size):
            request.args = List([self._creator.image])
            try:
                downloader.download(request, db)
            except HTTP as http:
                self.assertEqual(http.status, 200)
                self.assertEqual(http.headers['Content-Type'], 'image/jpeg')
                self.assertEqual(
                    http.headers['Content-Disposition'],
                    'attachment; filename="file.jpg"'
                )
                self.assertEqual(
                    http.headers['Content-Length'],
                    lengths[expect_size]
                )

        # web.jpg is small, only the web should be created.
        filename = self._prep_image('web.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        lengths = set_lengths()
        request.vars.size = 'web'
        test_http('web')
        request.vars.size = 'cbz'
        test_http('original')
        request.vars.size = 'original'
        test_http('original')

        filename = self._prep_image('cbz_plus.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        lengths = set_lengths()
        request.vars.size = 'web'
        test_http('web')
        request.vars.size = 'cbz'
        test_http('cbz')
        request.vars.size = 'original'
        test_http('original')

        # Test invalid url          web.jpg?size=web => web.jpg_size=web
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        correct_query = 'book_page.image.ab7ec55b2ce97d6f.626c75655f30302e706e67.png?size=web'
        incorrect_query = correct_query.replace('?', '_')
        request.args = List([incorrect_query])
        self.assertRaises(HTTP, downloader.download, request, db)


class TestTorrentDownloader(LocalTestCase):

    def test__download(self):
        downloader = TorrentDownloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']

        def test_http(args, expect):
            request.args = List(args)
            try:
                downloader.download(request, db)
            except HTTP as http:
                self.assertEqual(http.status, expect['status'])
                if expect['status'] == 200:
                    self.assertEqual(
                        http.headers['Content-Type'],
                        'application/x-bittorrent'
                    )
                    self.assertEqual(
                        http.headers['Content-Disposition'],
                        'attachment; filename="{f}"'.format(
                            f=expect['filename'])
                    )
                    self.assertEqual(
                        http.headers['Content-Length'],
                        expect['size']
                    )

        # Find a book with a torrent.
        creator = Creator.by_email(web.username)
        query = (db.book.creator_id == creator.id) & \
            (db.book.torrent != None)

        book = Book.from_query(query)
        if not book:
            self.fail('Book by creator {c} with torrent not found.'.format(
                c=creator.email))

        test_http(
            ['book', book.id],
            dict(
                status=200,
                filename=os.path.basename(book.torrent),
                size=os.stat(book.torrent).st_size,
            )
        )

        # Find a creator with a torrent.
        creator = Creator.by_email(web.username)
        test_http(
            ['creator', creator.id],
            dict(
                status=200,
                filename=os.path.basename(creator.torrent),
                size=os.stat(creator.torrent).st_size,
            )
        )

        tor_archive = TorrentArchive()
        name = '.'.join([tor_archive.name, 'torrent'])
        all_tor_file = os.path.join(
            tor_archive.base_path,
            tor_archive.category,
            tor_archive.name,
            name
        )

        test_http(
            ['all'],
            dict(
                status=200,
                filename='zco.mx.torrent',
                size=os.stat(all_tor_file).st_size,
            )
        )

        # Test invalids
        invalid_record_id = -1
        test_http(['_fake_tor_type_'], dict(status=404))
        test_http(['book', invalid_record_id], dict(status=404))
        test_http(['creator', invalid_record_id], dict(status=404))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
