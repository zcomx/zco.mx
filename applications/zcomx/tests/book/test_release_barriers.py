#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book/release_barriers.py

"""
import inspect
import os
import datetime
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.book.release_barriers import \
    AllRightsReservedBarrier, \
    COMPLETE_BARRIER_CLASSES, \
    FILESHARING_BARRIER_CLASSES, \
    BaseReleaseBarrier, \
    DupeNameBarrier, \
    DupeNumberBarrier, \
    InvalidPageNoBarrier, \
    ModalLink, \
    NoBookNameBarrier, \
    NoCBZImageBarrier, \
    NoLicenceBarrier, \
    NoPagesBarrier, \
    NoPublicationMetadataBarrier, \
    NotCompletedBarrier, \
    barriers_for_book, \
    complete_barriers, \
    filesharing_barriers, \
    has_complete_barriers, \
    has_filesharing_barriers
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.indicias import PublicationMetadata
from applications.zcomx.modules.tests.helpers import \
    DubMeta, \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


def _create_cbz(book_page):
    # Quick and dirty method for created a cbz size. Just copy the original
    upload_img = BookPage(book_page.as_dict()).upload_image()
    original = upload_img.fullname(size='original')
    cbz = upload_img.fullname(size='cbz')
    cbz_dirname = os.path.dirname(cbz)
    if not os.path.exists(cbz_dirname):
        os.makedirs(cbz_dirname)
    shutil.copy(original, cbz)


class TestAllRightsReservedBarrier(LocalTestCase):

    def test__applies(self):
        cc_by = CCLicence.by_code('CC BY')
        all_rights = CCLicence.by_code('All Rights Reserved')

        book = Book(dict(
            cc_licence_id=cc_by.id,
        ))
        barrier = AllRightsReservedBarrier(book)
        self.assertFalse(barrier.applies())

        book.update(cc_licence_id=all_rights.id)
        barrier = AllRightsReservedBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = AllRightsReservedBarrier({})
        self.assertEqual(barrier.code, 'licence_arr')

    def test__description(self):
        barrier = AllRightsReservedBarrier({})
        self.assertTrue(
            'you need to grant them permission' in barrier.description)

    def test__fixes(self):
        barrier = AllRightsReservedBarrier(Book(id=123, release_date=None))

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue(
            'change the Copyright Licence' in str(barrier.fixes[0]))

    def test__reason(self):
        barrier = AllRightsReservedBarrier({})
        self.assertTrue('All Rights Reserved' in barrier.reason)


class TestBaseReleaseBarrier(LocalTestCase):

    _dub_modal_link = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        class DubModalLink(ModalLink):
            __metaclass__ = DubMeta
            _dub_methods = [
                'link',
            ]

        def override_link(self):
            return [
                self.book,
                self.text,
                self.modal_btn_class,
                self.controller_func,
            ]
        DubModalLink.dub.link['return'] = override_link
        self._dub_modal_link = DubModalLink

    def test____init__(self):
        barrier = BaseReleaseBarrier({})
        self.assertTrue(barrier)

    def test__applies(self):
        barrier = BaseReleaseBarrier({})
        self.assertRaises(NotImplementedError, barrier.applies)

    def test__code(self):
        barrier = BaseReleaseBarrier({})
        try:
            barrier.code
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')

    def test__complete_link(self):
        barrier = BaseReleaseBarrier(Book(id=123))
        complete_link = barrier.complete_link(
            'Complete Me', modal_class=self._dub_modal_link)
        self.assertTrue(isinstance(complete_link[0], Book))
        self.assertEqual(complete_link[0].id, 123)
        self.assertEqual(
            complete_link[1:],
            [
                'Complete Me',
                'modal-complete-btn',
                'book_complete',
            ]
        )

    def test__delete_link(self):
        barrier = BaseReleaseBarrier(Book(id=123))
        delete_link = barrier.delete_link(
            'Delete Me', modal_class=self._dub_modal_link)
        self.assertTrue(isinstance(delete_link[0], Book))
        self.assertEqual(delete_link[0].id, 123)
        self.assertEqual(
            delete_link[1:],
            [
                'Delete Me',
                'modal-delete-btn',
                'book_delete',
            ]
        )

    def test__description(self):
        barrier = BaseReleaseBarrier({})
        self.assertEqual(barrier.description, '')

    def test__edit_link(self):
        # With no release date
        barrier = BaseReleaseBarrier(Book(id=123, release_date=None))
        edit_link = barrier.edit_link(
            'Edit Me', modal_class=self._dub_modal_link)
        self.assertTrue(isinstance(edit_link[0], Book))
        self.assertEqual(edit_link[0].id, 123)
        self.assertEqual(
            edit_link[1:],
            [
                'Edit Me',
                'modal-edit-ongoing-btn',
                'book_edit',
            ]
        )

        # With release date
        barrier = BaseReleaseBarrier(
            Book(id=123, release_date=datetime.date.today()))
        edit_link = barrier.edit_link(
            'Edit Me', modal_class=self._dub_modal_link)
        self.assertTrue(isinstance(edit_link[0], Book))
        self.assertEqual(edit_link[0].id, 123)
        self.assertEqual(
            edit_link[1:],
            [
                'Edit Me',
                'modal-edit-btn',
                'book_edit',
            ]
        )

    def test__fixes(self):
        barrier = BaseReleaseBarrier({})
        try:
            barrier.fixes
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')

    def test__reason(self):
        barrier = BaseReleaseBarrier({})
        try:
            barrier.reason
        except NotImplementedError:
            pass
        else:
            self.fail('NotImplementedError not raised')

    def test__upload_link(self):
        barrier = BaseReleaseBarrier(Book(id=123))
        upload_link = barrier.upload_link(
            'Upload Me', modal_class=self._dub_modal_link)
        self.assertTrue(isinstance(upload_link[0], Book))
        self.assertEqual(upload_link[0].id, 123)
        self.assertEqual(
            upload_link[1:],
            [
                'Upload Me',
                'modal-upload-btn',
                'book_pages',
            ]
        )


class TestDupeNameBarrier(LocalTestCase):

    def test__applies(self):
        creator = self.add(Creator, dict(email='dupe@example.com'))
        creator_2 = self.add(Creator, dict(email='dupe_2@example.com'))

        book = self.add(Book, dict(
            name='test__applies',
            creator_id=creator.id,
            book_type_id=1,
            release_date=datetime.date(2014, 12, 31),
        ))

        barrier = DupeNameBarrier(book)
        self.assertFalse(barrier.applies())

        dupe_data = dict(
            name=book.name,                                         # same
            creator_id=book.creator_id,                             # same
            book_type_id=book.book_type_id + 1,                     # not same
            release_date=datetime.date(1990, 12, 31),               # not None
        )

        book_2 = self.add(Book, dict(dupe_data))
        self.assertTrue(barrier.applies())

        # Change each field one a time to see test that if changed, the
        # record is no longer a dupe.
        not_dupe_data = dict(
            name=book.name + '_',
            creator_id=creator_2.id,
            book_type_id=book.book_type_id,
            release_date=None
        )

        for k, v in not_dupe_data.items():
            data = dict(dupe_data)
            data[k] = v
            book_2 = Book.from_updated(book_2, data)
            self.assertFalse(barrier.applies())

    def test__code(self):
        barrier = DupeNameBarrier({})
        self.assertEqual(barrier.code, 'dupe_name')

    def test__description(self):
        barrier = DupeNameBarrier({})
        self.assertTrue(
            'name of the book must be unique' in barrier.description)

    def test__fixes(self):
        barrier = DupeNameBarrier(Book(id=123, release_date=None))

        self.assertEqual(len(barrier.fixes), 2)
        self.assertTrue('>Modify</a> the name' in barrier.fixes[0])
        self.assertTrue('>delete</a> the book' in barrier.fixes[1])

    def test__reason(self):
        barrier = DupeNameBarrier({})
        self.assertTrue('book with the same name' in barrier.reason)


class TestDupeNumberBarrier(LocalTestCase):

    def test__applies(self):
        creator = self.add(Creator, dict(name_for_url='test__applies'))
        book = self.add(Book, dict(
            name='test__applies',
            number=2,
            creator_id=creator.id,
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

        book_2 = self.add(Book, dict(dupe_data))
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
        barrier = DupeNumberBarrier(Book(id=123, release_date=None))

        self.assertEqual(len(barrier.fixes), 2)
        self.assertTrue('Verify the number' in barrier.fixes[0])
        self.assertTrue('>delete</a> the book' in barrier.fixes[1])

    def test__reason(self):
        barrier = DupeNumberBarrier({})
        self.assertTrue('book with the same name and number' in barrier.reason)


class TestInvalidPageNoBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(Book, dict(name='test__applies'))

        # Has no pages, alls good (NoPagesBarrier takes care of this)
        barrier = InvalidPageNoBarrier(book)
        self.assertFalse(barrier.applies())

        book_page_1 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))

        self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
        ))

        book_page_3 = self.add(BookPage, dict(
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
        barrier = InvalidPageNoBarrier(Book(id=123))

        self.assertEqual(len(barrier.fixes), 2)
        self.assertTrue('>Check</a> that images are' in barrier.fixes[0])

    def test__reason(self):
        barrier = InvalidPageNoBarrier({})
        self.assertTrue('numbers were not set properly' in barrier.reason)


class TestModalLink(LocalTestCase):

    def test____init__(self):
        modal_link = ModalLink(
            Book(id=123, release_date=None),
            'My Link',
            'modal-action-btn',
            'book_action'
        )
        self.assertTrue(modal_link)

    def test__link(self):
        modal_link = ModalLink(
            Book(id=123, release_date=None),
            'My Link',
            'modal-action-btn',
            'book_action'
        )
        link = modal_link.link()
        soup = BeautifulSoup(str(link))
        # Expect:
        # <a class="modal-action-btn close_current_dialog no_rclick_menu"
        #   data-book_id="123" href="/login/book_action/123">My Link</a>
        anchor = soup.a
        self.assertEqual(anchor.string, 'My Link')
        self.assertEqual(
            anchor['class'],
            'modal-action-btn close_current_dialog no_rclick_menu'
        )
        self.assertEqual(anchor['data-book_id'], '123')
        self.assertEqual(anchor['href'], '/login/book_action/123')


class TestNoBookNameBarrier(LocalTestCase):

    def test__applies(self):
        book = Book(dict(
            name='test__applies',
        ))

        barrier = NoBookNameBarrier(book)
        self.assertFalse(barrier.applies())

        book.update(name='')
        barrier = NoBookNameBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoBookNameBarrier({})
        self.assertEqual(barrier.code, 'no_name')

    def test__description(self):
        barrier = NoBookNameBarrier({})
        self.assertTrue('Without a name' in barrier.description)

    def test__fixes(self):
        barrier = NoBookNameBarrier(Book(id=123, release_date=None))

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('Edit the book' in str(barrier.fixes[0]))

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
        barrier = NoCBZImageBarrier(Book(id=123))
        self.assertTrue('following images should be' in barrier.description)
        self.assertTrue('>replaced</a>' in barrier.description)

    def test__fixes(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        barrier = NoCBZImageBarrier({})

        barrier._no_cbz_images = []
        self.assertEqual(barrier.fixes, [])

        barrier._no_cbz_images = ['file.jpg', 'file2.png']
        self.assertEqual(barrier.fixes, ['file.jpg', 'file2.png'])

    def test__no_cbz_images(self):
        book = self.add(Book, dict(name='test__no_cbz_images'))

        # The images and their sizes are irrelevant other than for identity.
        # The existence of a cbz file will determine whether images violate
        # or not.
        landscape_page = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))
        self._set_image(
            db.book_page.image,
            landscape_page,
            self._create_image('landscape.png', (370, 170)),
            resizer=ResizerQuick
        )

        portrait_page = self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
        ))
        self._set_image(
            db.book_page.image,
            portrait_page,
            self._create_image('portrait.png', (140, 168)),
            resizer=ResizerQuick
        )

        square_page = self.add(BookPage, dict(
            book_id=book.id,
            page_no=3,
        ))
        self._set_image(
            db.book_page.image,
            square_page,
            self._create_image('square.png', (200, 200)),
            resizer=ResizerQuick
        )

        barrier = NoCBZImageBarrier(book)
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        self.assertEqual(barrier._no_cbz_images, None)

        # No images have cbz sizes, all should be in violation
        got = barrier.no_cbz_images()
        self.assertEqual(
            got,
            [
                'landscape.png (landscape, width: 370 px)',
                'portrait.png (portrait, width: 140 px)',
                'square.png (square, width: 200 px)',
            ]
        )

        def has_size(book_page, size):
            upload_img = BookPage(book_page.as_dict()).upload_image()
            fullname = upload_img.fullname(size=size)
            return os.path.exists(fullname)

        # One images has cbz size, others should be in violation
        barrier._no_cbz_images = None       # clear cache
        _create_cbz(landscape_page)
        self.assertTrue(has_size(landscape_page, 'cbz'))
        self.assertFalse(has_size(portrait_page, 'cbz'))
        self.assertFalse(has_size(square_page, 'cbz'))
        got = barrier.no_cbz_images()
        self.assertEqual(
            got,
            [
                'portrait.png (portrait, width: 140 px)',
                'square.png (square, width: 200 px)',
            ]
        )

        # All images have cbz size, none should be in violation
        barrier._no_cbz_images = None       # clear cache
        _create_cbz(portrait_page)
        _create_cbz(square_page)
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
        book = Book(dict(
            cc_licence_id=1,
        ))

        barrier = NoLicenceBarrier(book)
        self.assertFalse(barrier.applies())

        book.update(cc_licence_id=0)
        barrier = NoLicenceBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NoLicenceBarrier({})
        self.assertEqual(barrier.code, 'no_licence')

    def test__description(self):
        barrier = NoLicenceBarrier({})
        self.assertTrue('licence must be set' in barrier.description)

    def test__fixes(self):
        barrier = NoLicenceBarrier(Book(id=123, release_date=None))

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue(
            'change the Copyright Licence' in str(barrier.fixes[0]))

    def test__reason(self):
        barrier = NoLicenceBarrier({})
        self.assertTrue('No licence has been selected' in barrier.reason)


class TestNoPagesBarrier(LocalTestCase):

    def test__applies(self):
        book = self.add(Book, dict(name='test__applies'))
        barrier = NoPagesBarrier(book)
        self.assertTrue(barrier.applies())

        self.add(BookPage, dict(
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
        barrier = NoPagesBarrier(Book(id=123))
        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('>Upload</a> images' in barrier.fixes[0])

    def test__reason(self):
        barrier = NoPagesBarrier({})
        self.assertTrue('book has no pages' in barrier.reason)


class TestNoPublicationMetadataBarrier(LocalTestCase):

    def test__applies(self):
        book = Book(dict(
            id=-1,
            name='test__applies',
        ))

        metadata = self.add(PublicationMetadata, dict(
            book_id=book.id,
        ))

        barrier = NoPublicationMetadataBarrier(book)
        self.assertFalse(barrier.applies())

        metadata.update_record(book_id=-2)
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
        barrier = NoPublicationMetadataBarrier(Book(id=123, release_date=None))
        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue(
            'set the Publication Metadata' in str(barrier.fixes[0]))

    def test__reason(self):
        barrier = NoPublicationMetadataBarrier({})
        self.assertTrue(
            'publication metadata has not been set' in barrier.reason)


class TestNotCompletedBarrier(LocalTestCase):

    def test__applies(self):
        book = Book(dict(
            release_date=datetime.date.today()
        ))

        barrier = NotCompletedBarrier(book)
        self.assertFalse(barrier.applies())

        book.update(release_date=None)
        barrier = NotCompletedBarrier(book)
        self.assertTrue(barrier.applies())

    def test__code(self):
        barrier = NotCompletedBarrier({})
        self.assertEqual(barrier.code, 'not_completed')

    def test__description(self):
        barrier = NotCompletedBarrier({})
        self.assertTrue('It must be set as completed' in barrier.description)

    def test__fixes(self):
        barrier = NotCompletedBarrier(Book(id=123))

        self.assertEqual(len(barrier.fixes), 1)
        self.assertTrue('>Set the book as completed</a>' in barrier.fixes[0])

    def test__reason(self):
        barrier = NotCompletedBarrier({})
        self.assertTrue('book is not completed' in barrier.reason)


class TestConstants(LocalTestCase):
    def test_barrier_classes(self):
        base_class = BaseReleaseBarrier
        base_classes = []

        classes = [x for x in globals().values() if inspect.isclass(x)]
        ignore_classes = [base_class]
        for c in classes:
            if c not in ignore_classes and base_class in inspect.getmro(c):
                base_classes.append(c)
        self.assertEqual(
            sorted(base_classes),
            sorted(COMPLETE_BARRIER_CLASSES + FILESHARING_BARRIER_CLASSES)
        )


class TestFunctions(ImageTestCase):

    _incomplete_book = None
    _complete_book = None
    _sharable_book = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        creator = self.add(Creator, dict(
            email='test__complete_barriers@gmail.com',
        ))

        self._incomplete_book = self.add(Book, dict(
            name='',
            number=0,
            creator_id=creator.id,
            book_type_id=BookType.by_name('ongoing').id,
            cc_licence_id=0,
        ))

        cc_arr = CCLicence.by_code('All Rights Reserved')
        self._complete_book = self.add(Book, dict(
            name='test__complete_barriers',
            number=999,
            creator_id=creator.id,
            book_type_id=BookType.by_name('ongoing').id,
            cc_licence_id=cc_arr.id,
        ))

        complete_book_page = self.add(BookPage, dict(
            book_id=self._complete_book.id,
            page_no=1,
        ))

        self._set_image(
            db.book_page.image,
            complete_book_page,
            self._create_image('file.jpg', (1600, 1600)),
            resizer=ResizerQuick
        )

        self.add(PublicationMetadata, dict(
            book_id=self._complete_book.id,
            republished=False,
        ))

        cc0 = CCLicence.by_code('CC0')

        self._sharable_book = self.add(Book, dict(
            name='test__filesharing_barriers',
            number=999,
            creator_id=creator.id,
            book_type_id=BookType.by_name('ongoing').id,
            cc_licence_id=cc0.id,
            release_date=datetime.date.today(),
        ))

        sharable_book_page = self.add(BookPage, dict(
            book_id=self._sharable_book.id,
            page_no=1,
        ))

        self._set_image(
            db.book_page.image,
            sharable_book_page,
            self._create_image('file.jpg', (1600, 1600)),
            resizer=ResizerQuick
        )

        self.add(PublicationMetadata, dict(
            book_id=self._sharable_book.id,
            republished=False,
        ))

        _create_cbz(sharable_book_page)

    def test__barriers_for_book(self):
        # W0223: *Method ??? is abstract in class
        # pylint: disable=W0223

        class DubAppliesBarrier(BaseReleaseBarrier):
            """Class representing a dub barrier that applies."""
            def applies(self):
                return True

        class DubApplies2Barrier(BaseReleaseBarrier):
            def applies(self):
                return True

        class DubNotAppliesBarrier(BaseReleaseBarrier):
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
        got = complete_barriers(self._incomplete_book)
        self.assertTrue(isinstance(got[0], NoBookNameBarrier))
        self.assertTrue(isinstance(got[1], NoPagesBarrier))
        self.assertTrue(isinstance(got[2], NoLicenceBarrier))
        self.assertTrue(isinstance(got[3], NoPublicationMetadataBarrier))

        self.assertEqual(complete_barriers(self._complete_book), [])

    def test__filesharing_barriers(self):
        got = filesharing_barriers(self._complete_book)
        self.assertTrue(isinstance(got[0], NotCompletedBarrier))
        self.assertTrue(isinstance(got[1], AllRightsReservedBarrier))

        self.assertEqual(filesharing_barriers(self._sharable_book), [])

    def test__has_complete_barriers(self):
        self.assertTrue(has_complete_barriers(self._incomplete_book))
        self.assertFalse(has_complete_barriers(self._complete_book))

    def test__has_filesharing_barriers(self):
        self.assertTrue(has_filesharing_barriers(self._complete_book))
        self.assertFalse(has_filesharing_barriers(self._sharable_book))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
