#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_upload.py

"""
import os
import shutil
import unittest
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
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class BaseTestCase(LocalTestCase):
    _test_data_dir = None
    _image_dir = '/tmp/test_book_upload'

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
    def setUp(cls):
        # C0103 (invalid-name): *Invalid name "%%s" for type %%s
        # pylint: disable=C0103
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')
        if not os.path.exists(cls._image_dir):
            os.makedirs(cls._image_dir)

    @classmethod
    def tearDown(cls):
        # C0103 (invalid-name): *Invalid name "%%s" for type %%s
        # pylint: disable=C0103
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestBookPageUploader(BaseTestCase):

    def test____init__(self):
        sample_file = os.path.join(self._test_data_dir, 'file.jpg')
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

        filename = self._prep_image('file.jpg')
        uploaded = UploadedFile(filename)
        uploaded.image_filenames.append(filename)
        uploaded.create_book_pages(book_id)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 1)
        book_page = db(db.book_page.id == pages[0]['id']).select().first()
        self._objects.append(book_page)

    def test__for_json(self):
        filename = self._prep_image('file.jpg')
        uploaded = UploadedFile(filename)
        self.assertRaises(NotImplementedError, uploaded.for_json)

    def test__load(self):
        book_id = db.book.insert(name='test__load')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        filename = self._prep_image('file.jpg')
        # Use UploadedImage as UploadedFile won't have methods implemented
        uploaded = UploadedImage(filename)
        uploaded.load(book_id)

        pages = db(db.book_page.book_id == book_id).select()
        self.assertEqual(len(pages), 1)
        book_page = db(db.book_page.id == pages[0]['id']).select().first()
        self._objects.append(book_page)

    def test__unpack(self):
        filename = self._prep_image('file.jpg')
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
        filename = self._prep_image('file.jpg')
        uploaded = UploadedImage(filename)
        self.assertTrue(uploaded)
        self.assertEqual(uploaded.filename, filename)

    def test__for_json(self):
        book_id = db.book.insert(name='test__for_json')
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        filename = self._prep_image('file.jpg')
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
        filename = self._prep_image('file.jpg')
        uploaded = UploadedImage(filename)
        self.assertEqual(len(uploaded.image_filenames), 0)
        uploaded.unpacker = None
        uploaded.unpack()
        self.assertEqual(len(uploaded.image_filenames), 1)


class TestUploadedUnsupported(BaseTestCase):

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

    def test__create_book_page(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')
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
            sample_file = self._prep_image(filename)
            book_page_id = create_book_page(db, book_id, sample_file)
            self.assertTrue(book_page_id)

        book_pages = pages(book_id)
        self.assertEqual(len(book_pages), 2)
        for book_page in book_pages:
            self._objects.append(book_page)

        for i, filename in enumerate(['file.jpg', 'file.png']):
            self.assertEqual(book_pages[i].book_id, book.id)
            self.assertEqual(book_pages[i].page_no, i + 1)

            original_filename, unused_fullname = db.book_page.image.retrieve(
                book_pages[i].image,
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