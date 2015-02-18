#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/downloaders.py

"""
import os
import shutil
import unittest
from gluon import *
from gluon.html import DIV, IMG
from gluon.http import HTTP
from gluon.storage import List
from applications.zcomx.modules.archives import TorrentArchive
from applications.zcomx.modules.downloaders import \
    ImageDownloader, \
    TorrentDownloader
from applications.zcomx.modules.images import \
    UploadImage, \
    filename_for_size, \
    store
from applications.zcomx.modules.tests.runner import \
    LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _auth_user = None
    _creator = None
    _image_dir = '/tmp/image_resizer'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _test_data_dir = None

    @classmethod
    def _prep_image(cls, img, working_directory=None, to_name=None):
        """Prepare an image for testing.
        Copy an image from private/test/data to a working directory.

        Args:
            img: string, name of source image, eg file.jpg
                must be in cls._test_data_dir
            working_directory: string, path of working directory to copy to.
                If None, uses cls._image_dir
            to_name: string, optional, name of image to copy file to.
                If None, img is used.
        """
        src_filename = os.path.join(
            os.path.abspath(cls._test_data_dir),
            img
        )

        if working_directory is None:
            working_directory = os.path.abspath(cls._image_dir)

        if to_name is None:
            to_name = img

        filename = os.path.join(working_directory, to_name)
        shutil.copy(src_filename, filename)
        return filename

    @classmethod
    def _set_image(cls, field, record, img):
        """Set the image for a record field.

        Args:
            field: gluon.dal.Field instance
            record: Row instance.
            img: string, path/to/name of image.
        """
        # Delete images if record field is set.
        if record[field.name]:
            up_image = UploadImage(field, record[field.name])
            up_image.delete_all()
        stored_filename = store(field, img)
        data = {field.name: stored_filename}
        record.update_record(**data)
        db.commit()

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        src_filename = os.path.join(cls._test_data_dir, 'tbn_plus.jpg')
        image_filename = os.path.join(cls._image_dir, cls._image_name)
        shutil.copy(src_filename, image_filename)

        # Store the image in the uploads/original directory
        stored_filename = store(db.creator.image, image_filename)

        # Create a creator and set the image
        email = 'up_image@example.com'
        cls._auth_user = cls.add(db.auth_user, dict(
            name='Image UploadImage',
            email=email,
        ))

        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email=email,
            image=stored_filename,
        ))

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)
        if cls._creator.image:
            up_image = UploadImage(db.creator.image, cls._creator.image)
            up_image.delete_all()


class TestImageDownloader(ImageTestCase):

    def test__download(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        downloader = ImageDownloader()
        self.assertTrue(downloader)
        env = globals()
        request = env['request']

        def set_lengths():
            lengths = {}
            for size in ['original', 'cbz', 'web', 'tbn']:
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

        # tbn.jpg is tiny, only the thumbnail should be created.
        filename = self._prep_image('tbn.jpg', to_name='file.jpg')
        self._set_image(db.creator.image, self._creator, filename)
        lengths = set_lengths()
        request.vars.size = 'web'
        test_http('original')
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


class TestTorrentDownloader(LocalTestCase):
    _base_path = '/tmp/torrent_downloader'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls._base_path):
            os.makedirs(cls._base_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._base_path):
            shutil.rmtree(cls._base_path)

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
        book = db(db.book.torrent != None).select().first()
        test_http(
            ['book', book.id],
            dict(
                status=200,
                filename=os.path.basename(book.torrent),
                size=os.stat(book.torrent).st_size,
            )
        )

        # Find a creator with a torrent.
        creator = db(db.creator.torrent != None).select().first()
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
