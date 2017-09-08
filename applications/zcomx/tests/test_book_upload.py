#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_upload.py

"""
import os
import shutil
import unittest
from gluon.storage import Storage
from applications.zcomx.modules.book_upload import \
    BookPageUploader, \
    FileTypeError, \
    FileTyper, \
    UnpackError, \
    Unpacker, \
    UnpackerRAR, \
    UnpackerZip, \
    UploadedFile, \
    UploadedArchive, \
    UploadedImage, \
    UploadedUnsupported, \
    classify_uploaded_file, \
    create_book_page
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.image.validators import InvalidImageError
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    WithTestDataDirTestCase, \
    skip_if_quick
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestBookPageUploader(ImageTestCase):

    def test____init__(self):
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
        uploader = BookPageUploader(0, [sample_file])
        self.assertTrue(uploader)

    def test__as_json(self):
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
        uploader = BookPageUploader(0, [sample_file])
        self.assertEqual(uploader.as_json(), '{"files": []}')

        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        uploaded = UploadedArchive(filename)
        uploader.uploaded_files = [uploaded]
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            uploader.as_json(),
            """{"files": [{"size": 17105, "thumbnailUrl": "", "name": "sampler.cbr", "book_id": 0, "url": null, "deleteType": "", "book_page_id": 0, "deleteUrl": null}]}"""
        )

    def test__load_file(self):
        pass         # This is tested by test__upload

    @skip_if_quick
    def test__upload(self):
        book = self.add(Book, dict(name='test__load_file'))
        self.assertEqual(book.page_count(), 0)

        sample_file = os.path.join(self._test_data_dir, 'cbz.jpg')
        with open(sample_file, 'r') as f:
            up_file = Storage({
                'file': f,
                'filename': 'cbz.jpg',
            })
            uploader = BookPageUploader(book.id, [up_file])
            uploader.upload()
        pages = book.pages()
        self.assertEqual(len(pages), 1)
        self._objects.append(pages[0])


class TestFileTypeError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise FileTypeError(msg)
        except FileTypeError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('FileTypeError not raised')


class TestFileTyper(WithTestDataDirTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        typer = FileTyper(filename)
        self.assertTrue(typer)

    def test__type(self):

        tests = [
            # (filename, expect)
            ('file.jpg', 'image'),
            ('file.png', 'image'),
            ('sampler.cbr', 'rar'),
            ('sampler.cbz', 'zip'),
        ]
        for t in tests:
            filename = os.path.join(self._test_data_dir, t[0])
            typer = FileTyper(filename)
            self.assertEqual(typer.type(), t[1])

        filename = os.path.join(self._test_data_dir, 'not_exists.txt')
        typer = FileTyper(filename)
        self.assertRaises(FileTypeError, typer.type)


class TestUnpackError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise UnpackError(msg)
        except UnpackError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('UnpackError not raised')


class TestUnpacker(WithTestDataDirTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = Unpacker(filename)
        self.assertEqual(unpacker.filename, filename)
        # W0212 (protected-access): *Access to a protected member %%s
        # pylint: disable=W0212
        self.assertEqual(unpacker._temp_directory, None)

    def test__image_files(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = Unpacker(filename)
        tmp_dir = unpacker.temp_directory()
        files = unpacker.image_files()
        self.assertEqual(files, [])

        img_files = ['file.jpg', 'file.png']
        test_files = list(img_files)
        test_files.append('sampler.cbr')
        for f in test_files:
            src = os.path.join(self._test_data_dir, f)
            dst = os.path.join(tmp_dir, f)
            shutil.copyfile(src, dst)
            self.assertTrue(os.path.exists(dst))
        files = unpacker.image_files()
        expect = [os.path.join(tmp_dir, x) for x in img_files]
        self.assertEqual(files, expect)
        unpacker.cleanup()


class TestUnpackerRAR(WithTestDataDirTestCase):
    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        unpacker = UnpackerRAR(filename)
        self.assertTrue(unpacker)

    def test__extract(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        unpacker = UnpackerRAR(filename)
        images = unpacker.extract()
        img_names = sorted([os.path.basename(x) for x in images])
        expect = [
            'audio.png',
            'default.png',
            'image.png',
            'msword.png',
            'pdf.png',
            'rtf.png',
            'text.png',
            'video.png'
        ]
        self.assertEqual(img_names, expect)
        unpacker.cleanup()


class TestUnpackerZip(WithTestDataDirTestCase):
    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = UnpackerZip(filename)
        self.assertTrue(unpacker)

    def test__extract(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = UnpackerZip(filename)
        images = unpacker.extract()
        img_names = sorted([os.path.basename(x) for x in images])
        self.assertEqual(img_names, ['001.png', '002.png', '003.png'])
        unpacker.cleanup()


class TestUploadedFile(ImageTestCase):
    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedFile(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)
        self.assertEqual(uploaded.image_filenames, [])
        self.assertEqual(uploaded.book_pages, [])
        self.assertEqual(uploaded.unpacker, None)
        self.assertEqual(uploaded.book_page_ids, [])
        self.assertEqual(uploaded.errors, [])

    def test__create_book_pages(self):
        book = self.add(Book, dict(name='test__create_book_pages'))
        self.assertEqual(book.page_count(), 0)

        filename = self._prep_image('file.jpg')
        uploaded = UploadedFile(filename)
        uploaded.image_filenames.append(filename)
        uploaded.create_book_pages(book.id)

        pages = book.pages()
        self.assertEqual(len(pages), 1)
        self._objects.append(pages[0])

    def test__for_json(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedFile(filename)
        self.assertRaises(NotImplementedError, uploaded.for_json)

    @skip_if_quick
    def test__load(self):
        book = self.add(Book, dict(name='test__load'))
        filename = self._prep_image('cbz.jpg')
        # Use UploadedImage as UploadedFile won't have methods implemented
        uploaded = UploadedImage(filename)
        uploaded.load(book.id)

        pages = book.pages()
        self.assertEqual(len(pages), 1)
        self._objects.append(pages[0])

    def test__unpack(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedFile(filename)
        self.assertRaises(NotImplementedError, uploaded.unpack)

    def test__validate_images(self):
        image_dimensions = [
            (1600, 1600),
            (1600, 2000),
            (2650, 1000),
        ]
        filenames = []
        for count, dims in enumerate(image_dimensions):
            filename = self._create_image('file_{c}.jpg'.format(c=count), dims)
            filenames.append(filename)
        uploaded = UploadedFile('fake/path/to/file.jpg')
        uploaded.image_filenames = filenames
        self.assertTrue(uploaded.validate_images())

        invalid_dimensions = [
            (100, 100),
            (100, 1000),
            (1000, 100),
        ]
        valid_filenames = list(filenames)
        for dims in invalid_dimensions:
            filenames = list(valid_filenames)
            filename = self._create_image('file.jpg', dims)
            filenames.append(filename)
            uploaded.image_filenames = filenames
            self.assertRaises(InvalidImageError, uploaded.validate_images)


class TestUploadedArchive(WithTestDataDirTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        uploaded = UploadedArchive(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__for_json(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        uploaded = UploadedArchive(filename)
        json = uploaded.for_json()
        self.assertEqual(json['name'], 'sampler.cbr')
        self.assertEqual(json['size'], 17105)

    def test__unpack(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbr')
        uploaded = UploadedArchive(filename)
        self.assertEqual(len(uploaded.image_filenames), 0)
        uploaded.unpacker = UnpackerRAR(filename)
        uploaded.unpack()
        self.assertEqual(len(uploaded.image_filenames), 8)
        uploaded.unpacker.cleanup()


class TestUploadedImage(ImageTestCase):

    def test____init__(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedImage(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__for_json(self):
        book = self.add(Book, dict(name='test__for_json'))
        filename = self._prep_image('file.jpg')
        uploaded = UploadedImage(filename)
        uploaded.image_filenames.append(filename)
        uploaded.create_book_pages(book.id)
        self.assertEqual(len(uploaded.book_page_ids), 1)
        json = uploaded.for_json()
        self.assertEqual(json['name'], 'file.jpg')
        self.assertEqual(json['size'], 23127)

        pages = book.pages()
        self.assertEqual(len(pages), 1)
        self._objects.append(pages[0])

    def test__unpack(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedImage(filename)
        self.assertEqual(len(uploaded.image_filenames), 0)
        uploaded.unpacker = None
        uploaded.unpack()
        self.assertEqual(len(uploaded.image_filenames), 1)


class TestUploadedUnsupported(ImageTestCase):

    def test____init__(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedUnsupported(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__create_book_pages(self):
        # This is a stub method, prove it's handled gracefully
        filename = self._prep_image('file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.create_book_pages(-1)

    def test__for_json(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedUnsupported(filename)
        json = uploaded.for_json()
        self.assertEqual(json['name'], 'file.jpg')
        self.assertEqual(json['size'], 23127)

    def test__load(self):
        # This is a stub method, prove it's handled gracefully
        filename = self._prep_image('file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.load(-1)

    def test__unpack(self):
        # This is a stub method, prove it's handled gracefully
        filename = self._prep_image('file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.unpack()


class TestFunctions(ImageTestCase):

    def test__classify_uploaded_file(self):
        tests = [
            # (filename, expect, unpacker, errors)
            ('file.jpg', UploadedImage, None, []),
            ('sampler.cbz', UploadedArchive, UnpackerZip, []),
            ('sampler.cbr', UploadedArchive, UnpackerRAR, []),
            (
                'sampler.text',
                UploadedUnsupported,
                None,
                ['Unsupported file type.']
            ),
        ]
        for t in tests:
            sample_file = os.path.join(self._test_data_dir, t[0])
            uploaded = classify_uploaded_file(sample_file)
            self.assertTrue(isinstance(uploaded, t[1]))
            if t[2]:
                self.assertTrue(isinstance(uploaded.unpacker, t[2]))
            else:
                self.assertTrue(uploaded.unpacker is None)
            self.assertEqual(uploaded.errors, t[3])

    @skip_if_quick
    def test__create_book_page(self):
        book = self.add(Book, dict(name='test__add'))
        self.assertEqual(book.page_count(), 0)

        for filename in ['file.jpg', 'file.png']:
            sample_file = self._prep_image(filename)
            book_page_id = create_book_page(db, book.id, sample_file)
            self.assertTrue(book_page_id)

        pages = book.pages()
        self.assertEqual(len(pages), 2)
        for page in pages:
            self._objects.append(page)

        for i, filename in enumerate(['file.jpg', 'file.png']):
            self.assertEqual(pages[i].book_id, book.id)
            self.assertEqual(pages[i].page_no, i + 1)

            original_filename, unused_fullname = db.book_page.image.retrieve(
                pages[i].image,
                nameonly=True,
            )
            self.assertEqual(original_filename, filename)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
