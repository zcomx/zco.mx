#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/book_upload.py

"""
import os
import unittest
from applications.zcomix.modules.book_upload import \
    BookPageFile, \
    BookPageUploader, \
    FileTypeError, \
    FileTyper, \
    TemporaryDirectory, \
    UnpackError, \
    Unpacker, \
    UnpackerRAR, \
    UnpackerZip, \
    UploadError, \
    UploadedFile, \
    UploadedArchive, \
    UploadedImage, \
    UploadedUnsupported, \
    classify_uploaded_file, \
    temp_directory
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class BaseTestCase(LocalTestCase):
    _test_data_dir = None

    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')


class TestBookPageFile(BaseTestCase):

    def test____init__(self):
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
        with open(sample_file, 'rb') as f:
            page_file = BookPageFile(f)
            self.assertTrue(page_file)

    def test__add(self):
        book_id = db.book.insert(name='test__add')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        def pages(book_id):
            """Get pages of book"""
            return db(db.book_page.book_id == book_id).select(
                orderby=[db.book_page.page_no, db.book_page.id]
            )

        self.assertEqual(len(pages(book_id)), 0)

        for filename in ['file.jpg', 'file.png']:
            sample_file = os.path.join(self._test_data_dir, filename)
            with open(sample_file, 'rb') as f:
                page_file = BookPageFile(f)
                self.assertTrue(page_file)
                book_page_id = page_file.add(book_id)
                self.assertTrue(book_page_id)

        book_pages = pages(book_id)
        self.assertEqual(len(book_pages), 2)

        for i, filename in enumerate(['file.jpg', 'file.png']):
            self.assertEqual(book_pages[i].book_id, book.id)
            self.assertEqual(book_pages[i].page_no, i + 1)

            original_filename, unused_fullname = db.book_page.image.retrieve(
                book_pages[i].image,
                nameonly=True,
            )
            self.assertEqual(original_filename, filename)


class TestBookPageUploader(BaseTestCase):

    def test____init__(self):
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
        with open(sample_file, 'rb') as f:
            uploader = BookPageUploader(0, [sample_file])
            self.assertTrue(uploader)

    def test__as_json(self):
        pass            # FIXME

    def test__load_file(self):
        pass            # FIXME

    def test__upload(self):
        pass            # FIXME


class TestFileTypeError(LocalTestCase):
    def test____init__(self):
        msg = 'This is an error message.'
        try:
            raise FileTypeError(msg)
        except FileTypeError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('FileTypeError not raised')


class TestFileTyper(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestTemporaryDirectory(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUnpackError(LocalTestCase):
    def test____init__(self):
        msg = 'This is an error message.'
        try:
            raise UnpackError(msg)
        except UnpackError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('UnpackError not raised')


class TestUnpacker(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUnpackerRAR(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUnpackerZip(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUploadError(LocalTestCase):
    def test____init__(self):
        msg = 'This is an error message.'
        try:
            raise UploadError(msg)
        except UploadError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('UploadError not raised')


class TestUploadedFile(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUploadedArchive(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUploadedImage(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestUploadedUnsupported(BaseTestCase):
    def test____init__(self):
        pass        # FIXME


class TestFunctions(BaseTestCase):

    def test__classify_uploaded_file(self):
        pass        # FIXME

    def test__temp_directory(self):
        pass        # FIXME


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
