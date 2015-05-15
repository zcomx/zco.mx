#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book/complete_barriers.py

"""
import inspect
import os
import datetime
import shutil
import unittest
from PIL import Image
from gluon import *
from applications.zcomx.modules.book.complete_barriers import \
    AllRightsReservedBarrier, \
    BARRIER_CLASSES, \
    BaseCompleteBarrier, \
    DupeNameBarrier, \
    DupeNumberBarrier, \
    InvalidPageNoBarrier, \
    NoBookNameBarrier, \
    NoCBZImageBarrier, \
    NoLicenceBarrier, \
    NoPagesBarrier, \
    NoPublicationMetadataBarrier, \
    barriers_for_book, \
    complete_barriers, \
    has_complete_barriers
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.indicias import cc_licence_by_code
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _image_dir = '/tmp/image_for_books'
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'
    _image_original = os.path.join(_image_dir, 'original')
    _test_data_dir = None
    _type_id_by_name = {}

    _objects = []

    @classmethod
    def _create_cbz(cls, book_page):
        # Quick and dirty method for created a cbz size. Just copy the original
        upload_img = BookPage(book_page).upload_image()
        original = upload_img.fullname(size='original')
        cbz = upload_img.fullname(size='cbz')
        shutil.copy(original, cbz)

    @classmethod
    def _create_image(cls, image_name, dimensions=None):
        image_filename = os.path.join(cls._image_dir, image_name)
        if not dimensions:
            dimensions = (1200, 1200)

        # Create an image to test with.
        im = Image.new('RGB', dimensions)
        with open(image_filename, 'wb') as f:
            im.save(f)
        return image_filename

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

        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestAllRightsReservedBarrier(LocalTestCase):

    def test__applies(self):
        cc_by_id = cc_licence_by_code('CC BY', want='id')
        arr_id = cc_licence_by_code('All Rights Reserved', want='id')

        book = self.add(db.book, dict(
            cc_licence_id=cc_by_id,
        ))
        barrier = AllRightsReservedBarrier(book)
        self.assertFalse(barrier.applies())

        book.update_record(cc_licence_id=arr_id)
        db.commit()
        barrier = AllRightsReservedBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = AllRightsReservedBarrier({})
        self.assertEqual(barrier.code, 'licence_arr')

    def test__description(self):
        barrier = AllRightsReservedBarrier({})
        self.assertTrue('published on public file' in barrier.description)

    def test__fixes(self):
        barrier = AllRightsReservedBarrier({})

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('change the licence' in barrier.fixes[0])

    def test__reason(self):
        barrier = AllRightsReservedBarrier({})
        self.assertTrue('All Rights Reserved' in barrier.reason)


class TestBaseCompleteBarrier(LocalTestCase):

    def test____init__(self):
        barrier = BaseCompleteBarrier({})
        self.assertTrue(barrier)

    def test__applies(self):
        barrier = BaseCompleteBarrier({})
        self.assertRaises(NotImplementedError, barrier.applies)

    def test__code(self):
        barrier = BaseCompleteBarrier({})
        try:
            barrier.code
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')

    def test__description(self):
        barrier = BaseCompleteBarrier({})
        self.assertEqual(barrier.description, '')

    def test__fixes(self):
        barrier = BaseCompleteBarrier({})
        try:
            barrier.fixes
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')

    def test__reason(self):
        barrier = BaseCompleteBarrier({})
        try:
            barrier.reason
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')


class TestDupeNameBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
            creator_id=-1,
            book_type_id=1,
            release_date=datetime.date(2014, 12, 31),
        ))

        barrier = DupeNameBarrier(book)
        self.assertFalse(barrier.applies())

        dupe_data = dict(
            name=book.name,                                         # same
            creator_id=book.creator_id,                             # same
            book_type_id=book.book_type_id + 1,                     # not same
            release_date=datetime.date.today()                      # not None
        )

        book_2 = self.add(db.book, dict(dupe_data))
        self.assertTrue(barrier.applies())

        # Change each field one a time to see test that if changed, the
        # record is no longer a dupe.
        not_dupe_data = dict(
            name=book.name + '_',
            creator_id=book.creator_id - 1,
            book_type_id=book.book_type_id,
            release_date=None
        )

        for k, v in not_dupe_data.items():
            data = dict(dupe_data)
            data[k] = v
            book_2.update_record(**data)
            db.commit()
            self.assertFalse(barrier.applies())

    def test__code(self):
        barrier = DupeNameBarrier({})
        self.assertEqual(barrier.code, 'dupe_name')

    def test__description(self):
        barrier = DupeNameBarrier({})
        self.assertTrue(
            'name of the book must be unique' in barrier.description)

    def test__fixes(self):
        barrier = DupeNameBarrier({})

        self.assertEqual(len(barrier.fixes), 2)
        self.assertTrue('Modify the name' in barrier.fixes[0])
        self.assertTrue('delete the book' in barrier.fixes[1])

    def test__reason(self):
        barrier = DupeNameBarrier({})
        self.assertTrue('book with the same name' in barrier.reason)


class TestDupeNumberBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
            number=2,
            creator_id=-1,
            book_type_id=1,
            release_date=datetime.date(2014, 12, 31),
        ))

        barrier = DupeNumberBarrier(book)
        self.assertFalse(barrier.applies())

        dupe_data = dict(
            name=book.name,                                         # same
            number=book.number,                                     # same
            creator_id=book.creator_id,                             # same
            book_type_id=book.book_type_id,                         # same
            release_date=datetime.date.today()                      # not None
        )

        book_2 = self.add(db.book, dict(dupe_data))
        self.assertTrue(barrier.applies())

        # Change each field one a time to see test that if changed, the
        # record is no longer a dupe.
        not_dupe_data = dict(
            name=book.name + '_',
            number=book.number + 1,
            creator_id=book.creator_id - 1,
            book_type_id=book.book_type_id + 1,
            release_date=None
        )

        for k, v in not_dupe_data.items():
            data = dict(dupe_data)
            data[k] = v
            book_2.update_record(**data)
            db.commit()
            self.assertFalse(barrier.applies())

    def test__code(self):
        barrier = DupeNumberBarrier({})
        self.assertEqual(barrier.code, 'dupe_number')

    def test__description(self):
        barrier = DupeNumberBarrier({})
        self.assertTrue(
            'name/number of the book must be unique' in barrier.description)

    def test__fixes(self):
        barrier = DupeNumberBarrier({})

        self.assertEqual(len(barrier.fixes), 2)
        self.assertTrue('Verify the number' in barrier.fixes[0])
        self.assertTrue('delete the book' in barrier.fixes[1])

    def test__reason(self):
        barrier = DupeNumberBarrier({})
        self.assertTrue('book with the same name and number' in barrier.reason)


class TestInvalidPageNoBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
        ))

        book_page_1 = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
        ))

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=2,
        ))

        book_page_3 = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=3,
        ))

        # Has a cover page and no dupes, alls good
        barrier = InvalidPageNoBarrier(book)
        self.assertFalse(barrier.applies())

        # Has no cover
        book_page_1.update_record(page_no=4)
        db.commit()
        barrier = InvalidPageNoBarrier(book)
        self.assertTrue(barrier.applies())

        # Has dupe page no
        book_page_1.update_record(page_no=1)
        db.commit()
        book_page_3.update_record(page_no=2)
        db.commit()
        barrier = InvalidPageNoBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = InvalidPageNoBarrier({})
        self.assertEqual(barrier.code, 'invalid_page_no')

    def test__description(self):
        barrier = InvalidPageNoBarrier({})
        self.assertTrue(
            'numbers are assigned improperly' in barrier.description)

    def test__fixes(self):
        barrier = InvalidPageNoBarrier({})

        self.assertEqual(len(barrier.fixes), 3)
        self.assertTrue('Click the Upload' in barrier.fixes[0])

    def test__reason(self):
        barrier = InvalidPageNoBarrier({})
        self.assertTrue('numbers were not set properly' in barrier.reason)


class TestNoBookNameBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
        ))

        barrier = NoBookNameBarrier(book)
        self.assertFalse(barrier.applies())

        book.update_record(name='')
        db.commit()

        barrier = NoBookNameBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoBookNameBarrier({})
        self.assertEqual(barrier.code, 'no_name')

    def test__description(self):
        barrier = NoBookNameBarrier({})
        self.assertTrue('Without a name' in barrier.description)

    def test__fixes(self):
        barrier = NoBookNameBarrier({})

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('Edit the book' in barrier.fixes[0])

    def test__reason(self):
        barrier = NoBookNameBarrier({})
        self.assertTrue('book has no name' in barrier.reason)


class TestNoCBZImageBarrier(ImageTestCase):

    def test____init__(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        barrier = NoCBZImageBarrier({})
        self.assertTrue(barrier)
        self.assertEqual(barrier._no_cbz_images, None)

    def test__applies(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        barrier = NoCBZImageBarrier({})

        barrier._no_cbz_images = []
        self.assertFalse(barrier.applies())

        barrier._no_cbz_images = ['file.jpg']
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoCBZImageBarrier({})
        self.assertEqual(barrier.code, 'no_cbz_images')

    def test__description(self):
        barrier = NoCBZImageBarrier({})
        self.assertTrue('images should be replaced' in barrier.description)

    def test__fixes(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        barrier = NoCBZImageBarrier({})

        barrier._no_cbz_images = []
        self.assertEqual(barrier.fixes, [])

        barrier._no_cbz_images = ['file.jpg', 'file2.png']
        self.assertEqual(barrier.fixes, ['file.jpg', 'file2.png'])

    def test__no_cbz_images(self):
        book = self.add(db.book, dict(
            name='test__no_cbz_images'
        ))

        # The images and their sizes are irrelevant other than for identity.
        # The existence of a cbz file will determine whether images violate
        # or not.
        landscape_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image=self._store_image(
                db.book_page.image,
                self._create_image('landscape.png', (370, 170)),
            )
        ))

        portrait_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image=self._store_image(
                db.book_page.image,
                self._create_image('portrait.png', (140, 168)),
            )
        ))

        square_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image=self._store_image(
                db.book_page.image,
                self._create_image('square.png', (200, 200)),
            )
        ))

        barrier = NoCBZImageBarrier(book)
        self.assertEqual(barrier._no_cbz_images, None)

        # No images have cbz sizes, all should be in violation
        got = barrier.no_cbz_images()
        self.assertEqual(
            got,
            [
                'landscape.png (width: 370 px)',
                'portrait.png (width: 140 px)',
                'square.png (width: 200 px)',
            ]
        )

        def has_size(book_page, size):
            upload_img = BookPage(book_page).upload_image()
            fullname = upload_img.fullname(size=size)
            return os.path.exists(fullname)

        # One images has cbz size, others should be in violation
        barrier._no_cbz_images = None       # clear cache
        self._create_cbz(landscape_page)
        self.assertTrue(has_size(landscape_page, 'cbz'))
        self.assertFalse(has_size(portrait_page, 'cbz'))
        self.assertFalse(has_size(square_page, 'cbz'))
        got = barrier.no_cbz_images()
        self.assertEqual(
            got,
            [
                'portrait.png (width: 140 px)',
                'square.png (width: 200 px)',
            ]
        )

        # All images have cbz size, none should be in violation
        barrier._no_cbz_images = None       # clear cache
        self._create_cbz(portrait_page)
        self._create_cbz(square_page)
        self.assertTrue(has_size(landscape_page, 'cbz'))
        self.assertTrue(has_size(portrait_page, 'cbz'))
        self.assertTrue(has_size(square_page, 'cbz'))
        got = barrier.no_cbz_images()
        self.assertEqual(got, [])

    def test__reason(self):
        barrier = NoCBZImageBarrier({})
        self.assertTrue('images are not large enough' in barrier.reason)


class TestNoLicenceBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            cc_licence_id=1,
        ))

        barrier = NoLicenceBarrier(book)
        self.assertFalse(barrier.applies())

        book.update_record(cc_licence_id=0)
        db.commit()

        barrier = NoLicenceBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoLicenceBarrier({})
        self.assertEqual(barrier.code, 'no_licence')

    def test__description(self):
        barrier = NoLicenceBarrier({})
        self.assertTrue('licence must be set' in barrier.description)

    def test__fixes(self):
        barrier = NoLicenceBarrier({})

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('set the licence' in barrier.fixes[0])

    def test__reason(self):
        barrier = NoLicenceBarrier({})
        self.assertTrue('No licence has been selected' in barrier.reason)


class TestNoPagesBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
        ))

        barrier = NoPagesBarrier(book)
        self.assertTrue(barrier.applies())

        self.add(db.book_page, dict(
            book_id=book.id
        ))

        barrier = NoPagesBarrier(book)
        self.assertFalse(barrier.applies())

    def test__code(self):
        barrier = NoPagesBarrier({})
        self.assertEqual(barrier.code, 'no_pages')

    def test_description(self):
        barrier = NoPagesBarrier({})
        self.assertEqual(barrier.description, '')

    def test__fixes(self):
        barrier = NoPagesBarrier({})
        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('Upload images' in barrier.fixes[0])

    def test__reason(self):
        barrier = NoPagesBarrier({})
        self.assertTrue('book has no pages' in barrier.reason)


class TestNoPublicationMetadataBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(db.book, dict(
            name='test__applies',
        ))

        metadata = self.add(db.publication_metadata, dict(
            book_id=book.id,
        ))

        barrier = NoPublicationMetadataBarrier(book)
        self.assertFalse(barrier.applies())

        metadata.update_record(book_id=-1)
        db.commit()
        barrier = NoPublicationMetadataBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoPublicationMetadataBarrier({})
        self.assertEqual(barrier.code, 'no_metadata')

    def test__description(self):
        barrier = NoPublicationMetadataBarrier({})
        self.assertTrue('metadata has to be set' in barrier.description)

    def test__fixes(self):
        barrier = NoPublicationMetadataBarrier({})
        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('set the publication metadata' in barrier.fixes[0])

    def test__reason(self):
        barrier = NoPublicationMetadataBarrier({})
        self.assertTrue(
            'publication metadata has not been set' in barrier.reason)


class TestConstants(LocalTestCase):
    def test_barrier_classes(self):
        base_class = BaseCompleteBarrier
        base_classes = []

        classes = [x for x in globals().values() if inspect.isclass(x)]
        ignore_classes = [base_class]
        for c in classes:
            if c not in ignore_classes and base_class in inspect.getmro(c):
                base_classes.append(c)
        self.assertEqual(
            sorted(base_classes),
            sorted(BARRIER_CLASSES)
        )


class TestFunctions(ImageTestCase):

    def test__barriers_for_book(self):
        # W0223: *Method ??? is abstract in class
        # pylint: disable=W0223

        class DubAppliesBarrier(BaseCompleteBarrier):
            """Class representing a dub barrier that applies."""
            def applies(self):
                return True

        class DubApplies2Barrier(BaseCompleteBarrier):
            def applies(self):
                return True

        class DubNotAppliesBarrier(BaseCompleteBarrier):
            """Class representing a dub barrier that does not apply"""
            def applies(self):
                return False

        classes = [
            DubAppliesBarrier,
            DubApplies2Barrier,
            DubNotAppliesBarrier,
        ]

        barriers = barriers_for_book({}, classes)
        self.assertEqual(len(barriers), 2)
        self.assertTrue(isinstance(barriers[0], DubAppliesBarrier))
        self.assertTrue(isinstance(barriers[1], DubApplies2Barrier))

        # Test fail_fast
        barriers = barriers_for_book({}, classes, fail_fast=True)
        self.assertEqual(len(barriers), 1)
        self.assertTrue(isinstance(barriers[0], DubAppliesBarrier))

    def test__complete_barriers(self):
        creator = self.add(db.creator, dict(
            email='test__complete_barriers@gmail.com',
        ))

        cc0_id = cc_licence_by_code('CC0', want='id')

        book = self.add(db.book, dict(
            name='test__complete_barriers',
            number=999,
            creator_id=creator.id,
            book_type_id=self._type_id_by_name['ongoing'],
            cc_licence_id=cc0_id,
        ))

        book_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image=self._store_image(
                db.book_page.image,
                self._create_image('file.jpg', (1600, 1600)),
            ),
        ))

        self._create_cbz(book_page)

        self.add(db.publication_metadata, dict(
            book_id=book.id,
            republished=False,
        ))

        # Has all criteria
        self.assertEqual(complete_barriers(book), [])

    def test__has_complete_barriers(self):
        creator = self.add(db.creator, dict(
            email='test__complete_barriers@gmail.com',
        ))

        cc0_id = cc_licence_by_code('CC0', want='id')

        book = self.add(db.book, dict(
            name='test__complete_barriers',
            number=999,
            creator_id=creator.id,
            book_type_id=self._type_id_by_name['ongoing'],
            cc_licence_id=cc0_id,
        ))

        book_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image=self._store_image(
                db.book_page.image,
                self._create_image('file.jpg', (1600, 1600)),
            ),
        ))

        self._create_cbz(book_page)

        self.add(db.publication_metadata, dict(
            book_id=book.id,
            republished=False,
        ))

        self.assertFalse(has_complete_barriers(book))
        book.update_record(name='')
        db.commit()
        self.assertTrue(has_complete_barriers(book))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
