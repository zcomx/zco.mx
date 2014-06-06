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
from applications.zcomix.modules.cbz import \
    CBZCreateError, \
    CBZCreator
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _image_dir = os.path.join(
        current.request.folder, 'uploads', 'tmp', 'image_for_books'
    )
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'

    _objects = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
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

        # Store images in tmp directory
        db.book_page.image.uploadfolder = cls._image_original
        if not os.path.exists(db.book_page.image.uploadfolder):
            os.makedirs(db.book_page.image.uploadfolder)

        def create_image(image_name):
            image_filename = os.path.join(cls._image_dir, image_name)

            # Create an image to test with.
            im = Image.new('RGB', (1200, 1200))
            with open(image_filename, 'wb') as f:
                im.save(f)

            # Store the image in the uploads/original directory
            stored_filename = None
            with open(image_filename, 'rb') as f:
                stored_filename = db.book_page.image.store(f)
            return stored_filename

        book_id = db.book.insert(
            name='Image Test Case',
            creator_id=cls._creator.id
        )
        db.commit()
        cls._book = db(db.book.id == book_id).select().first()
        cls._objects.append(cls._book)

        book_page_id = db.book_page.insert(
            book_id=book_id,
            page_no=1,
            image=create_image('file.jpg'),
        )
        db.commit()
        cls._book_page = db(db.book_page.id == book_page_id).select().first()
        cls._objects.append(cls._book_page)

        # Create a second page to test with.
        book_page_id_2 = db.book_page.insert(
            book_id=book_id,
            page_no=2,
            image=create_image('file_2.jpg'),
        )
        db.commit()
        book_page_2 = db(db.book_page.id == book_page_id_2).select().first()
        cls._objects.append(book_page_2)

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
        tests = [
            #(name, year, creator_id, expect)
            ('My Book', 1999, 123, 'My Book (1999) (123.zcomix.com).cbz'),
            (r'A !@#$%^&*?/\[]{};:" B', 1999, 123,
                r'A !@#$^&[]{}; -  B (1999) (123.zcomix.com).cbz'),
            ('A B', 1999, 123, 'A B (1999) (123.zcomix.com).cbz'),
            ('A  B', 1999, 123, 'A  B (1999) (123.zcomix.com).cbz'),
            ('A   B', 1999, 123, 'A   B (1999) (123.zcomix.com).cbz'),
            ('A...B', 1999, 123, 'A...B (1999) (123.zcomix.com).cbz'),
            ('A---B', 1999, 123, 'A---B (1999) (123.zcomix.com).cbz'),
            ('A___B', 1999, 123, 'A___B (1999) (123.zcomix.com).cbz'),
            ('A:B', 1999, 123, 'A - B (1999) (123.zcomix.com).cbz'),
            ('A: B', 1999, 123, 'A - B (1999) (123.zcomix.com).cbz'),
            ('A : B', 1999, 123, 'A - B (1999) (123.zcomix.com).cbz'),
            ('A :B', 1999, 123, 'A - B (1999) (123.zcomix.com).cbz'),
            ("A'B", 1999, 123, "A'B (1999) (123.zcomix.com).cbz"),
            ('Berserk Alert!', 2014, 6,
                'Berserk Alert! (2014) (6.zcomix.com).cbz'),
            ('SUPER-ENIGMATIX', 2014, 11,
                'SUPER-ENIGMATIX (2014) (11.zcomix.com).cbz'),
            ('Tarzan Comic #v2#7', 2014, 123,
                'Tarzan Comic #v2#7 (2014) (123.zcomix.com).cbz'),
            ('Hämähäkkimies #11/1986', 1986, 123,
                'Hämähäkkimies #111986 (1986) (123.zcomix.com).cbz'),
            ('Warcraft: Legends', 2008, 123,
                'Warcraft - Legends (2008) (123.zcomix.com).cbz'),
        ]

        for t in tests:
            book = Row(dict(
                name=t[0],
                publication_year=t[1],
                creator_id=t[2],
            ))
            cbz_creator = CBZCreator(book)
            self.assertEqual(cbz_creator.cbz_filename(), t[3])

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

    def test__optimize(self):
        creator = CBZCreator(self._book)
        creator.optimize()
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        self.assertTrue(os.path.exists(creator._working_directory))
        self.assertEqual(
            sorted(os.listdir(creator._working_directory)),
            ['001.jpg', '002.jpg']
        )

        self.assertLess(
            os.stat(
                os.path.join(creator._working_directory, '001.jpg')
            ).st_size,
            os.stat(os.path.join(self._image_dir, 'file.jpg')).st_size
        )
        self.assertLess(
            os.stat(
                os.path.join(creator._working_directory, '002.jpg')
            ).st_size,
            os.stat(os.path.join(self._image_dir, 'file_2.jpg')).st_size
        )

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
