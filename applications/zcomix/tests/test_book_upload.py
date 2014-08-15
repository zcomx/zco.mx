#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/book_upload.py

"""
import os
import shutil
import unittest
from applications.zcomix.modules.book_upload import \
    BookPageFile, \
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
    classify_uploaded_file
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
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise FileTypeError(msg)
        except FileTypeError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('FileTypeError not raised')


class TestFileTyper(BaseTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        typer = FileTyper(filename)
        self.assertTrue(typer)

    def test__type(self):

        tests = [
            #(filename, expect)
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


class TestUnpacker(BaseTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = Unpacker(filename)
        self.assertEqual(unpacker.filename, filename)
        self.assertEqual(unpacker._temp_directory, None)

    def test__cleanup(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = Unpacker(filename)
        tmp_dir = unpacker.temp_directory()
        self.assertTrue(os.path.exists(tmp_dir))
        unpacker.cleanup()
        self.assertFalse(os.path.exists(tmp_dir))

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

    def test__temp_directory(self):
        filename = os.path.join(self._test_data_dir, 'sampler.cbz')
        unpacker = Unpacker(filename)
        tmp_dir = unpacker.temp_directory()
        expect = os.path.join(request.folder, 'uploads', 'tmp')
        self.assertEqual(
            os.path.realpath(os.path.dirname(tmp_dir)),
            os.path.realpath(expect)
        )
        self.assertEqual(unpacker._temp_directory, tmp_dir)

        unpacker.cleanup()


class TestUnpackerRAR(BaseTestCase):
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


class TestUnpackerZip(BaseTestCase):
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


class TestUploadedFile(BaseTestCase):
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
        book_id = db.book.insert(name='test__create_book_pages')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 0)

        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedFile(filename)
        uploaded.image_filenames.append(filename)
        uploaded.create_book_pages(book_id)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 1)
        book_page = db(db.book_page.id == pages[0]['id']).select().first()
        self._objects.append(book_page)

    def test__for_json(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedFile(filename)
        self.assertRaises(NotImplementedError, uploaded.for_json)

    def test__load(self):
        book_id = db.book.insert(name='test__load')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        filename = os.path.join(self._test_data_dir, 'file.jpg')
        # Use UploadedImage as UploadedFile won't have methods implemented
        uploaded = UploadedImage(filename)
        uploaded.load(book_id)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 1)
        book_page = db(db.book_page.id == pages[0]['id']).select().first()
        self._objects.append(book_page)

    def test__unpack(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedFile(filename)
        self.assertRaises(NotImplementedError, uploaded.unpack)


class TestUploadedArchive(BaseTestCase):

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


class TestUploadedImage(BaseTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedImage(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__for_json(self):
        book_id = db.book.insert(name='test__for_json')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedImage(filename)
        uploaded.image_filenames.append(filename)
        uploaded.create_book_pages(book_id)
        self.assertEqual(len(uploaded.book_page_ids), 1)
        json = uploaded.for_json()
        self.assertEqual(json['name'], 'file.jpg')
        self.assertEqual(json['size'], 23127)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 1)
        book_page = db(db.book_page.id == pages[0]['id']).select().first()
        self._objects.append(book_page)

    def test__unpack(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedImage(filename)
        self.assertEqual(len(uploaded.image_filenames), 0)
        uploaded.unpacker = None
        uploaded.unpack()
        self.assertEqual(len(uploaded.image_filenames), 1)


class TestUploadedUnsupported(BaseTestCase):

    def test____init__(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedUnsupported(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__create_book_pages(self):
        # This is a stub method, prove it's handled gracefully
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.create_book_pages(-1)

    def test__for_json(self):
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedUnsupported(filename)
        json = uploaded.for_json()
        self.assertEqual(json['name'], 'file.jpg')
        self.assertEqual(json['size'], 23127)

    def test__load(self):
        # This is a stub method, prove it's handled gracefully
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.load(-1)

    def test__unpack(self):
        # This is a stub method, prove it's handled gracefully
        filename = os.path.join(self._test_data_dir, 'file.jpg')
        uploaded = UploadedUnsupported(filename)
        uploaded.unpack()


class TestFunctions(BaseTestCase):

    def test__classify_uploaded_file(self):
        tests = [
            #(filename, expect, unpacker, errors)
            ('file.jpg', UploadedImage, None, []),
            ('sampler.cbz', UploadedArchive, UnpackerZip, []),
            ('sampler.cbr', UploadedArchive, UnpackerRAR, []),
            ('sampler.text', UploadedUnsupported, None,
                ['Unsupported file type.']),
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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
