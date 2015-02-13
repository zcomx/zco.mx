#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/cbz.py

"""
import os
import shutil
import subprocess
import unittest
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.books import DEFAULT_BOOK_TYPE
from applications.zcomx.modules.cbz import \
    CBZCreateError, \
    CBZCreator, \
    archive
from applications.zcomx.modules.images import \
    UploadImage, \
    store
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/test_cbz'
    _image_original = os.path.join(_image_dir, 'original')
    _test_data_dir = None

    _objects = []

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
        if cls._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == cls._user.id
        cls._creator = db(query).select().first()
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        query = (db.book_type.name == DEFAULT_BOOK_TYPE)
        book_type_id = db(query).select().first().id
        cls._book = cls.add(db.book, dict(
            name='Image Test Case',
            creator_id=cls._creator.id,
            book_type_id=book_type_id
        ))

        cls._book_page = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=1,
        ))
        filename = cls._prep_image('cbz_plus.jpg', to_name='file_1.jpg')
        cls._set_image(db.book_page.image, cls._book_page, filename)

        # Create a second page to test with.
        book_page_2 = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=2,
        ))
        filename = cls._prep_image('file.jpg', to_name='file_2.jpg')
        cls._set_image(db.book_page.image, book_page_2, filename)

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestCBZCreateError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise CBZCreateError(msg)
        except CBZCreateError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('CBZCreateError not raised')


class TestCBZCreator(ImageTestCase):

    def test____init__(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        # book as Row instance
        creator = CBZCreator(self._book)
        self.assertTrue(creator)
        self.assertEqual(creator.book.name, self._book.name)

        # book as integer
        creator = CBZCreator(self._book.id)
        self.assertTrue(creator)
        self.assertEqual(creator.book.name, self._book.name)

    def test__cbz_filename(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # One-shot
        book_type_id = types_by_name['one-shot'].id
        tests = [
            # (name, year, creator_id, expect)
            ('My Book', 1999, 1, 'My Book (1999) (1.zco.mx).cbz'),
            ('My Book', 1999, 123, 'My Book (1999) (123.zco.mx).cbz'),
            (
                r'A !@#$%^&*?/\[]{};:" B',
                1999,
                123,
                r'A !@#$^&[]{}; -  B (1999) (123.zco.mx).cbz'
            ),
            ('A B', 1999, 123, 'A B (1999) (123.zco.mx).cbz'),
            ('A  B', 1999, 123, 'A  B (1999) (123.zco.mx).cbz'),
            ('A   B', 1999, 123, 'A   B (1999) (123.zco.mx).cbz'),
            ('A...B', 1999, 123, 'A...B (1999) (123.zco.mx).cbz'),
            ('A---B', 1999, 123, 'A---B (1999) (123.zco.mx).cbz'),
            ('A___B', 1999, 123, 'A___B (1999) (123.zco.mx).cbz'),
            ('A:B', 1999, 123, 'A - B (1999) (123.zco.mx).cbz'),
            ('A: B', 1999, 123, 'A - B (1999) (123.zco.mx).cbz'),
            ('A : B', 1999, 123, 'A - B (1999) (123.zco.mx).cbz'),
            ('A :B', 1999, 123, 'A - B (1999) (123.zco.mx).cbz'),
            ("A'B", 1999, 123, "A'B (1999) (123.zco.mx).cbz"),
            (
                'Berserk Alert!',
                2014,
                6,
                'Berserk Alert! (2014) (6.zco.mx).cbz'
            ),
            (
                'SUPER-ENIGMATIX',
                2014,
                11,
                'SUPER-ENIGMATIX (2014) (11.zco.mx).cbz'
            ),
            (
                'Tarzan Comic #v2#7',
                2014,
                123,
                'Tarzan Comic #v2#7 (2014) (123.zco.mx).cbz'
            ),
            (
                'Hämähäkkimies #11/1986',
                1986,
                123,
                'Hämähäkkimies #111986 (1986) (123.zco.mx).cbz'
            ),
            (
                'Warcraft: Legends',
                2008,
                123,
                'Warcraft - Legends (2008) (123.zco.mx).cbz'
            ),
        ]

        for t in tests:
            self._book.update_record(
                name=t[0],
                book_type_id=book_type_id,
                number=1,
                of_number=1,
                publication_year=t[1],
                creator_id=t[2],
            )
            cbz_creator = CBZCreator(self._book)
            self.assertEqual(cbz_creator.cbz_filename(), t[3])

        # Ongoing
        book_type_id = types_by_name['ongoing'].id
        tests = [
            # (name, number, year, creator_id, expect)
            ('My Book', 1, 1999, 1, 'My Book 001 (1999) (1.zco.mx).cbz'),
            ('My Book', 2, 1999, 1, 'My Book 002 (1999) (1.zco.mx).cbz'),
            ('My Book', 999, 1999, 1, 'My Book 999 (1999) (1.zco.mx).cbz'),
        ]

        for t in tests:
            self._book.update_record(
                name=t[0],
                book_type_id=book_type_id,
                number=t[1],
                of_number=1,
                publication_year=t[2],
                creator_id=t[3],
            )
            cbz_creator = CBZCreator(self._book)
            self.assertEqual(cbz_creator.cbz_filename(), t[4])

        # Mini-series
        book_type_id = types_by_name['mini-series'].id
        tests = [
            # (name, number, of_number, year, creator_id, expect)
            (
                'My Book',
                1,
                4,
                1999,
                1,
                'My Book 01 (of 04) (1999) (1.zco.mx).cbz'
            ),
            (
                'My Book',
                2,
                9,
                1999,
                1,
                'My Book 02 (of 09) (1999) (1.zco.mx).cbz'
            ),
            (
                'My Book',
                99,
                99,
                1999,
                1,
                'My Book 99 (of 99) (1999) (1.zco.mx).cbz'
            ),
        ]

        for t in tests:
            self._book.update_record(
                name=t[0],
                book_type_id=book_type_id,
                number=t[1],
                of_number=t[2],
                publication_year=t[3],
                creator_id=t[4],
            )
            cbz_creator = CBZCreator(self._book)
            self.assertEqual(cbz_creator.cbz_filename(), t[5])

        # Reset the book creator
        self._book.update_record(creator_id=self._creator.id)
        db.commit()

    def test__get_img_filename_fmt(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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

        for t in tests:
            creator._max_page_no = t[0]
            creator._img_filename_fmt = None            # clear cache
            self.assertEqual(creator.get_img_filename_fmt(), t[1])

        # Test cache
        creator._img_filename_fmt = '_cache_'
        self.assertEqual(creator.get_img_filename_fmt(), '_cache_')

        # Test book with no pages.
        book = self.add(db.book, dict(
            name='TestGetMaxPageNo'
        ))
        creator = CBZCreator(book)
        self.assertEqual(creator.get_img_filename_fmt(), '{p:03d}{e}')

    def test__get_max_page_no(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        creator = CBZCreator(self._book)

        def set_page_no(page, page_no):
            """Set the page no for a page"""
            query = (db.book_page.id == page.id)
            db(query).update(page_no=page_no)
            db.commit()

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
        book = self.add(db.book, dict(
            name='TestGetMaxPageNo'
        ))
        creator = CBZCreator(book)
        self.assertRaises(NotFoundError, creator.get_max_page_no)

    def test__image_filename(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212

        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        creator = CBZCreator(self._book)
        zip_file = creator.run()
        self.assertTrue(os.path.exists(zip_file))

        args = ['7z', 't']
        args.append(zip_file)
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_stdout, p_stderr = p.communicate()
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout)
        self.assertEqual(p_stderr, '')

        pages = db(db.book_page.book_id == self._book.id).count()
        files_comment = 'Files: {c}'.format(c=pages + 1)    # +1 for indicia
        self.assertTrue(files_comment in p_stdout)

    def test__zip(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
        creator = CBZCreator(self._book)
        zip_file = creator.zip()
        self.assertTrue(os.path.exists(zip_file))

        args = ['7z', 't']
        args.append(zip_file)
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout)
        self.assertEqual(p_stderr, '')


class TestFunctions(ImageTestCase):
    _base_path = '/tmp/cbz_archive'

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

    def test__archive(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        cbz_filename = archive(self._book, base_path=self._base_path)

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            cbz_filename,
            '/tmp/cbz_archive/cbz/zco.mx/J/Jim Karsten/Image Test Case (2015) ({i}.zco.mx).cbz'.format(i=self._creator.id)
        )

        book = entity_to_row(db.book, self._book.id)
        self.assertEqual(book.cbz, cbz_filename)

        self.assertTrue(os.path.exists(cbz_filename))
        args = ['7z', 't']
        args.append(cbz_filename)
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout)
        self.assertEqual(p_stderr, '')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
