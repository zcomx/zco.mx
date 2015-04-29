#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_pages.py

"""
import os
import shutil
import unittest
from gluon import *
from applications.zcomx.modules.book_pages import \
    BookPage, \
    delete_pages_not_in_ids, \
    reset_book_page_nos
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import \
    NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/image_for_books'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'
    _test_data_dir = None
    _type_id_by_name = {}
    _uploadfolders = {}

    _objects = []

    @classmethod
    def _store_image(cls, field, image_filename):
        stored_filename = None
        with open(image_filename, 'rb') as f:
            stored_filename = field.store(f)
        return stored_filename

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

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        # Store images in tmp directory
        # Store images in tmp directory
        for field in db.book_page.fields:
            if db.book_page[field].type == 'upload':
                cls._uploadfolders[field] = db.book_page[field].uploadfolder
                db.book_page[field].uploadfolder = cls._image_original

        if not os.path.exists(db.book_page.image.uploadfolder):
            os.makedirs(db.book_page.image.uploadfolder)

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)

        for field in db.book_page.fields:
            if db.book_page[field].type == 'upload':
                db.book_page[field].uploadfolder = cls._uploadfolders[field]


class TestBookPage(ImageTestCase):

    def test____init__(self):
        book_page = self.add(db.book_page, dict(
            image=None
        ))
        page = BookPage(book_page)
        self.assertRaises(NotFoundError, BookPage, -1)
        self.assertEqual(page.min_cbz_width, 1600)
        self.assertEqual(page.min_cbz_height_to_exempt, 2560)

    def test__upload_image(self):
        book_page = self.add(db.book_page, dict(
            image='book_image.aaa.000.jpg'
        ))

        page = BookPage(book_page)
        up_image = page.upload_image()
        self.assertTrue(hasattr(up_image, 'retrieve'))

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212

        # Test cache
        page._upload_image = '_cache_'
        self.assertEqual(page.upload_image(), '_cache_')


class TestFunctions(LocalTestCase):

    def test__delete_pages_not_in_ids(self):

        def get_page_ids(book_id):
            query = (db.book_page.book_id == book_id)
            return sorted([x.id for x in db(query).select()])

        book = self.add(db.book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 11):
            book_page = self.add(db.book_page, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            page_ids,
            get_page_ids(book.id)
        )

        # Keep every other page.
        keep_ids = []
        lose_ids = []
        for count, page_id in enumerate(page_ids):
            if count % 2:
                keep_ids.append(page_id)
            else:
                lose_ids.append(page_id)
        self.assertEqual(len(keep_ids), 5)
        self.assertEqual(len(lose_ids), 5)

        deleted_ids = delete_pages_not_in_ids(book.id, keep_ids)

        self.assertEqual(
            keep_ids,
            get_page_ids(book.id)
        )

        self.assertEqual(
            deleted_ids,
            lose_ids
        )

    def test__reset_book_page_nos(self):

        def get_page_ids_by_page_no(book_id):
            query = (db.book_page.book_id == book_id)
            return [x.id for x in db(query).select(orderby=db.book_page.page_no)]

        book = self.add(db.book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 5):
            book_page = self.add(db.book_page, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            get_page_ids_by_page_no(book.id),
            page_ids
        )

        new_order = [
            page_ids[1],
            page_ids[3],
            page_ids[2],
            page_ids[0],
        ]

        reset_book_page_nos(new_order)

        self.assertEqual(
            get_page_ids_by_page_no(book.id),
            new_order
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
