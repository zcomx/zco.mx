#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/cbz.py
"""
import datetime
import os
import shutil
import subprocess
import unittest
import zipfile
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import \
    Book, \
    DEFAULT_BOOK_TYPE
from applications.zcomx.modules.cbz import \
    CBZCreateError, \
    CBZCreator, \
    archive
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class WithObjectsTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None

    def _set_images(self):
        """Set image fields on records.

        This step is slow and used be called directly only by the
        tests that need it.
        """
        filename = self._prep_image('file.jpg', to_name='file_1.jpg')
        self._set_image(
            db.book_page.image,
            self._book_page,
            filename,
            resizer=ResizerQuick
        )

        filename = self._prep_image('file.jpg', to_name='file_2.jpg')
        self._set_image(
            db.book_page.image,
            self._book_page_2,
            filename,
            resizer=ResizerQuick
        )

        filename = self._prep_image('cbz.jpg')
        self._set_image(
            db.creator.indicia_image,
            self._creator,
            filename,
            resizer=ResizerQuick
        )

    # pylint: disable=invalid-name
    def setUp(self):
        email = web.username
        self._user = db(
            db.auth_user.email == email).select(limitby=(0, 1)).first()
        if not self._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == self._user.id
        self._creator = db(query).select(limitby=(0, 1)).first()
        if not self._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        query = (db.book_type.name == DEFAULT_BOOK_TYPE)
        book_type_id = db(query).select(limitby=(0, 1)).first().id
        cc_by_nd = CCLicence.by_code('CC BY-ND')
        self._book = self.add(Book, dict(
            name='My CBZ Test',
            creator_id=self._creator.id,
            book_type_id=book_type_id,
            cc_licence_id=cc_by_nd.id,

        ))

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        # Create a second page to test with.
        self._book_page_2 = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        super().setUp()


class TestCBZCreateError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise CBZCreateError(msg)
        except CBZCreateError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('CBZCreateError not raised')


class TestCBZCreator(WithObjectsTestCase, ImageTestCase):

    def test____init__(self):
        # book as Row instance
        creator = CBZCreator(self._book)
        self.assertTrue(creator)
        self.assertEqual(creator.book.name, self._book.name)

    def test__cbz_filename(self):
        data = dict(
            name='My Book',
            publication_year=1998,
            creator_id=123,
        )
        self._book.update(**data)

        cbz_creator = CBZCreator(self._book)
        self.assertEqual(
            cbz_creator.cbz_filename(),
            'My Book (1998) (123.zco.mx).cbz'
        )

    def test__get_img_filename_fmt(self):
        creator = CBZCreator(self._book)

        tests = [
            # (pages (excluding indicia page), expect)
            (1, '{p:03d}{e}'),
            (10, '{p:03d}{e}'),
            (100, '{p:03d}{e}'),
            (998, '{p:03d}{e}'),
            (999, '{p:04d}{e}'),
            (1000, '{p:04d}{e}'),
            (9998, '{p:04d}{e}'),
            (9999, '{p:05d}{e}'),
            (10000, '{p:05d}{e}'),
            (99998, '{p:05d}{e}'),
            (99999, '{p:06d}{e}'),
            (100000, '{p:06d}{e}'),
        ]

        # pylint: disable=protected-access
        for t in tests:
            creator._max_page_no = t[0]
            creator._img_filename_fmt = None            # clear cache
            self.assertEqual(creator.get_img_filename_fmt(), t[1])

        # Test cache
        creator._img_filename_fmt = '_cache_'
        self.assertEqual(creator.get_img_filename_fmt(), '_cache_')

        # Test book with no pages.
        book = self.add(Book, dict(
            name='TestGetMaxPageNo'
        ))
        creator = CBZCreator(book)
        self.assertEqual(creator.get_img_filename_fmt(), '{p:03d}{e}')

    def test__get_max_page_no(self):
        creator = CBZCreator(self._book)

        def set_page_no(page, page_no):
            """Set the page no for a page"""
            query = (db.book_page.id == page.id)
            db(query).update(page_no=page_no)
            db.commit()

        # pylint: disable=protected-access
        tests = [1, 10, 100, 1000]
        for t in tests:
            set_page_no(self._book_page, t)
            creator._max_page_no = None            # clear cache
            self.assertEqual(
                creator.get_max_page_no(),
                max(t, 2)                   # self._book page 2 has page_no=2
            )

        # Test cache
        creator._max_page_no = -1
        self.assertEqual(creator.get_max_page_no(), -1)

        # Test book with no pages.
        book = self.add(Book, dict(
            name='TestGetMaxPageNo'
        ))
        creator = CBZCreator(book)
        self.assertRaises(LookupError, creator.get_max_page_no)

    def test__image_filename(self):
        creator = CBZCreator(self._book)

        tests = [
            # (image name, page_no, fmt, extension, expect)
            ('file.jpg', 1, '{p}{e}', None, '1.jpg'),
            ('file.jpg', 1, '{p:03d}{e}', None, '001.jpg'),
            ('file.jpg', 9, '{p:03d}{e}', None, '009.jpg'),
            ('file.jpg', 1, '{p:03d}{e}', '.png', '001.png'),
            ('file.png', 1, '{p:03d}{e}', '.jpg', '001.jpg'),
        ]

        for t in tests:
            book_page = Storage(dict(
                image=t[0],
                page_no=t[1],
            ))
            self.assertEqual(
                creator.image_filename(book_page, t[2], extension=t[3]),
                t[4]
            )

    def test__run(self):
        self._set_images()
        creator = CBZCreator(self._book)
        zip_file = creator.run()
        self.assertTrue(os.path.exists(zip_file))

        args = ['7z', 't']
        args.append(zip_file)
        with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE) as p:
            p_stdout, p_stderr = p.communicate()
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout.decode('utf-8'))
        self.assertEqual(p_stderr, b'')

        page_count = self._book.page_count() + 1       # +1 for indicia
        files_comment = 'Files: {c}'.format(c=page_count)
        self.assertTrue(files_comment in p_stdout.decode('utf-8'))

        this_year = datetime.date.today().year
        fmt = '{y}|Jim Karsten|My CBZ Test||CC BY-ND|http://{cid}.zco.mx'
        with zipfile.ZipFile(zip_file) as f:
            self.assertEqual(
                f.comment,
                fmt.format(y=this_year, cid=self._creator.id).encode('utf-8')
            )

    def test__working_directory(self):
        creator = CBZCreator(self._book)
        work_dir = creator.working_directory()
        self.assertTrue(os.path.exists(work_dir))
        self.assertEqual(os.path.basename(work_dir), self._book.name)

    def test__zip(self):
        creator = CBZCreator(self._book)
        zip_file = creator.zip()
        self.assertTrue(os.path.exists(zip_file))

        args = ['7z', 't']
        args.append(zip_file)
        with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE) as p:
            p_stdout, p_stderr = p.communicate()
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout.decode('utf-8'))
        self.assertEqual(p_stderr, b'')


class TestFunctions(WithObjectsTestCase, ImageTestCase):
    _base_path = '/tmp/cbz_archive'

    # pylint: disable=invalid-name
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls._base_path):
            os.makedirs(cls._base_path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._base_path):
            shutil.rmtree(cls._base_path)
        super().tearDownClass()

    def test__archive(self):
        self._set_images()

        cbz_filename = archive(self._book, base_path=self._base_path)

        # pylint: disable=line-too-long
        this_year = datetime.date.today().year
        self.assertEqual(
            cbz_filename,
            '/tmp/cbz_archive/cbz/zco.mx/J/JimKarsten/My CBZ Test ({y}) ({i}.zco.mx).cbz'.format(
                y=this_year, i=self._creator.id)
        )

        book = Book.from_id(self._book.id)
        self.assertEqual(book.cbz, cbz_filename)

        self.assertTrue(os.path.exists(cbz_filename))
        args = ['7z', 't']
        args.append(cbz_filename)
        with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE) as p:
            p_stdout, p_stderr = p.communicate()
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout.decode('utf-8'))
        self.assertEqual(p_stderr, b'')


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
