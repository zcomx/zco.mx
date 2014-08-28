#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/books.py

"""
import os
import shutil
import subprocess
import unittest
from PIL import Image
from gluon import *
from gluon.dal import Row
from applications.zcomix.modules.books import DEFAULT_BOOK_TYPE
from applications.zcomix.modules.cbz import \
    CBZCreateError, \
    CBZCreator
from applications.zcomix.modules.images import \
    UploadImage, \
    store
from applications.zcomix.modules.test_runner import LocalTestCase

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
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'
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

        book_type_id = db(db.book_type.name == DEFAULT_BOOK_TYPE).select().first().id
        book_id = db.book.insert(
            name='Image Test Case',
            creator_id=cls._creator.id,
            book_type_id=book_type_id
        )
        db.commit()
        cls._book = db(db.book.id == book_id).select().first()
        cls._objects.append(cls._book)


        book_page_id = db.book_page.insert(
            book_id=book_id,
            page_no=1,
        )
        db.commit()
        cls._book_page = db(db.book_page.id == book_page_id).select().first()
        cls._objects.append(cls._book_page)

        filename = cls._prep_image('cbz_plus.jpg', to_name='file_1.jpg')
        cls._set_image(db.book_page.image, cls._book_page, filename)

        # Create a second page to test with.
        book_page_id_2 = db.book_page.insert(
            book_id=book_id,
            page_no=2,
        )
        db.commit()
        book_page_2 = db(db.book_page.id == book_page_id_2).select().first()
        cls._objects.append(book_page_2)
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
        # book as Row instance
        creator = CBZCreator(self._book)
        self.assertTrue(creator)
        self.assertEqual(creator.book.name, self._book.name)

        # book as integer
        creator = CBZCreator(self._book.id)
        self.assertTrue(creator)
        self.assertEqual(creator.book.name, self._book.name)

    def test__cbz_filename(self):
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # One-shot
        book_type_id = types_by_name['one-shot'].id
        tests = [
            #(name, year, creator_id, expect)
            ('My Book', 1999, 1, 'My Book (1999) (1.zco.mx).cbz'),
            ('My Book', 1999, 123, 'My Book (1999) (123.zco.mx).cbz'),
            (r'A !@#$%^&*?/\[]{};:" B', 1999, 123,
                r'A !@#$^&[]{}; -  B (1999) (123.zco.mx).cbz'),
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
            ('Berserk Alert!', 2014, 6,
                'Berserk Alert! (2014) (6.zco.mx).cbz'),
            ('SUPER-ENIGMATIX', 2014, 11,
                'SUPER-ENIGMATIX (2014) (11.zco.mx).cbz'),
            ('Tarzan Comic #v2#7', 2014, 123,
                'Tarzan Comic #v2#7 (2014) (123.zco.mx).cbz'),
            ('Hämähäkkimies #11/1986', 1986, 123,
                'Hämähäkkimies #111986 (1986) (123.zco.mx).cbz'),
            ('Warcraft: Legends', 2008, 123,
                'Warcraft - Legends (2008) (123.zco.mx).cbz'),
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
            #(name, number, year, creator_id, expect)
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
            #(name, number, of_number, year, creator_id, expect)
            ('My Book', 1, 4, 1999, 1, 'My Book 01 (of 04) (1999) (1.zco.mx).cbz'),
            ('My Book', 2, 9, 1999, 1, 'My Book 02 (of 09) (1999) (1.zco.mx).cbz'),
            ('My Book', 99, 99, 1999, 1, 'My Book 99 (of 99) (1999) (1.zco.mx).cbz'),
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

    def test__image_filename(self):
        creator = CBZCreator(self._book)

        def set_page_no(page, page_no):
            """Set the page no for a page"""
            query = (db.book_page.id == page.id)
            db(query).update(page_no=page_no)
            db.commit()

        tests = [
            #(pages, image name, page_no, expect)
            (1, 'file.jpg', 1, '001.jpg'),
            (10, 'file.jpg', 1, '001.jpg'),
            (100, 'file.jpg', 1, '001.jpg'),
            (999, 'file.jpg', 1, '001.jpg'),
            (1000, 'file.jpg', 1, '0001.jpg'),
            (9999, 'file.jpg', 1, '0001.jpg'),
            (10000, 'file.jpg', 1, '00001.jpg'),
            (99999, 'file.jpg', 1, '00001.jpg'),
            (100000, 'file.jpg', 1, '000001.jpg'),
            (10, 'file.png', 1, '001.png'),
            (10, 'file.jpg', 2, '002.jpg'),
            (999, 'file.jpg', 999, '999.jpg'),
        ]

        for t in tests:
            set_page_no(self._book_page, t[0])
            book_page = Row(dict(
                image=t[1],
                page_no=t[2]
            ))
            self.assertEqual(creator.image_filename(book_page), t[3])

    def test__run(self):
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
        files_comment = 'Files: {c}'.format(c=pages)
        self.assertTrue(files_comment in p_stdout)

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
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*
        # pylint: disable=E1101
        self.assertFalse(p.returncode)
        self.assertTrue('Everything is Ok' in p_stdout)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
