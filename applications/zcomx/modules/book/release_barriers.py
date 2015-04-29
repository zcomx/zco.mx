#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book release barriers.
"""
import logging
from gluon import *
from applications.zcomx.modules.books import book_pages as b_pages
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.images import ImageDescriptor

LOG = logging.getLogger('app')


class BaseReleaseBarrier(object):
    """Class representing a release barrier"""

    def __init__(self, book):
        """Initializer

        Args:
            book: Row instance representing a book.
        """
        self.book = book

    def applies(self):
        """Test if the barrier is a applicable.

        Returns
            True if the barrier applies and should prevent release.
        """
        raise NotImplementedError

    @property
    def code(self):
        """The release barrier code."""
        raise NotImplementedError

    @property
    def description(self):
        """A description of the barrier."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return ''   # This is optional

    @property
    def fixes(self):
        """A list of instructions to fix the problem."""
        raise NotImplementedError

    @property
    def reason(self):
        """An explanation of why the barrier failed."""
        raise NotImplementedError


class AllRightsReservedBarrier(BaseReleaseBarrier):
    """Class representing a 'licence is all rights reserved' barrier."""

    def applies(self):
        db = current.app.db
        arr = db(db.cc_licence.code == 'All Rights Reserved').select().first()
        return arr and arr.id and self.book.cc_licence_id == arr.id

    @property
    def code(self):
        return 'licence_arr'

    @property
    def description(self):
        return (
            'Books released on zco.mx '
            'are published on public file sharing networks. '
            'This is not permitted if the licence is '
            '"All Rights Reserved".'
        )

    @property
    def fixes(self):
        return [
            'Edit the book and change the licence.',
        ]

    @property
    def reason(self):
        return "The licence on the book is set to 'All Rights Reserved'."


class DupeNameBarrier(BaseReleaseBarrier):
    """Class representing a 'duplicate name' barrier."""

    def applies(self):
        db = current.app.db
        # Note: this barrier requires the book_type_id not match.
        # It is valid to have books with the same name if the book_type_id
        # is the same. This is required for ongoing and mini-series.
        # The DupeNumberBarrier will test those to make sure the
        # name/numbers are unique.
        query = (db.book.creator_id == self.book.creator_id) & \
                (db.book.name == self.book.name) & \
                (db.book.book_type_id != self.book.book_type_id) & \
                (db.book.release_date != None) & \
                (db.book.id != self.book.id)
        return db(query).count() > 0

    @property
    def code(self):
        return 'dupe_name'

    @property
    def description(self):
        return (
            'CBZ and torrent files are named after the book name. '
            'The name of the book must be unique.'
        )

    @property
    def fixes(self):
        return [
            'Modify the name of the book to make it unique.',
            'If this is a duplicate, delete the book.',
        ]

    @property
    def reason(self):
        return 'You already released a book with the same name.'


class DupeNumberBarrier(BaseReleaseBarrier):
    """Class representing a 'duplicate number' barrier."""

    def applies(self):
        db = current.app.db
        query = (db.book.creator_id == self.book.creator_id) & \
                (db.book.name == self.book.name) & \
                (db.book.book_type_id == self.book.book_type_id) & \
                (db.book.number == self.book.number) & \
                (db.book.release_date != None) & \
                (db.book.id != self.book.id)
        return db(query).count() > 0

    @property
    def code(self):
        return 'dupe_number'

    @property
    def description(self):
        return (
            'CBZ and torrent files are named after the book name. '
            'The name/number of the book must be unique.'
        )

    @property
    def fixes(self):
        return [
            (
                'Verify the number of the book is correct. '
                'Possibly it needs to be incremented.'
            ),
            'If this is a duplicate, delete the book.',
        ]

    @property
    def reason(self):
        return 'You already released a book with the same name and number.'


class ImagesTooNarrowBarrier(BaseReleaseBarrier):
    """Class representing a 'no publication metadata' barrier."""

    def __init__(self, book):
        """Initializer

        Args:
            book: Row instance representing a book.
        """
        super(ImagesTooNarrowBarrier, self).__init__(book)
        self._narrow_images = None

    def applies(self):
        small_images = self.narrow_images()
        return len(small_images) > 0

    @property
    def code(self):
        return 'images_too_narrow'

    @property
    def description(self):
        return (
            'Released books are packaged for CBZ viewers. '
            'In order for images to display clearly '
            'a minimum resolution of {w}px is required. '
            'The following images need to be replaced:'
        )

    @property
    def fixes(self):
        small_images = self.narrow_images()
        return small_images

    def narrow_images(self):
        """Return a list of image names representing images too narrow
        for release.

        Returns:
            list of strings, image names.
        """
        # Images must be a min_cbz_width unless the height is a
        # minimum (min_cbz_height_to_exempt)
        if self._narrow_images is None:
            pages = b_pages(self.book)
            small_images = []
            min_width = BookPage.min_cbz_width
            min_height = BookPage.min_cbz_height_to_exempt
            for page in pages:
                try:
                    dims = ImageDescriptor(
                        page.upload_image().fullname(size='cbz')
                    ).dimensions()
                except IOError:
                    # The 'cbz' size may not exist.
                    dims = None
                if not dims:
                    dims = ImageDescriptor(
                        page.upload_image().fullname(size='original')
                    ).dimensions()
                width = dims[0]
                height = dims[1]
                if width < min_width and height < min_height:
                    original_name = page.upload_image().original_name()
                    small_images.append(
                        '{n} (width: {w} px)'.format(n=original_name, w=width)
                    )
            self._narrow_images = small_images
        return self._narrow_images

    @property
    def reason(self):
        return 'Some images are not large enough.'


class NoBookNameBarrier(BaseReleaseBarrier):
    """Class representing a 'no book name' barrier."""

    def applies(self):
        return not self.book.name

    @property
    def code(self):
        return 'no_name'

    @property
    def description(self):
        return (
            'CBZ and torrent files are named after the book name. '
            'Without a name these files cannot be created.'
        )

    @property
    def fixes(self):
        return [
            'Edit the book and set the name.',
        ]

    @property
    def reason(self):
        return 'The book has no name.'


class NoLicenceBarrier(BaseReleaseBarrier):
    """Class representing a 'no licence' barrier."""

    def applies(self):
        return not self.book.cc_licence_id

    @property
    def code(self):
        return 'no_licence'

    @property
    def description(self):
        return (
            'Books released on zco.mx '
            'are published on public file sharing networks. '
            'A licence must be set indicating permission to do this.'
        )

    @property
    def fixes(self):
        return [
            'Edit the book and set the licence.',
        ]

    @property
    def reason(self):
        return 'No licence has been selected for the book.'


class NoPagesBarrier(BaseReleaseBarrier):
    """Class representing a 'no pages' barrier."""

    def applies(self):
        pages = b_pages(self.book)
        return len(pages) == 0

    @property
    def code(self):
        return 'no_pages'

    @property
    def fixes(self):
        return [
            'Upload images to create pages for the book.',
        ]

    @property
    def reason(self):
        return 'The book has no pages.'


class NoPublicationMetadataBarrier(BaseReleaseBarrier):
    """Class representing a 'no publication metadata' barrier."""

    def applies(self):
        db = current.app.db
        query = (db.publication_metadata.book_id == self.book.id)
        metadata = db(query).select().first()
        return not metadata

    @property
    def code(self):
        return 'no_metadata'

    @property
    def description(self):
        return (
            'Books released on zco.mx include an indicia page. '
            'The page has a paragraph outlining '
            'the publication history of the book.'
            'The publication metadata has to be set '
            'to create this paragraph.'
        )

    @property
    def fixes(self):
        return [
            'Edit the book and set the publication metadata.',
        ]

    @property
    def reason(self):
        return 'The publication metadata has not been set for the book.'


BARRIER_CLASSES = [
    NoBookNameBarrier,
    NoPagesBarrier,
    DupeNameBarrier,
    DupeNumberBarrier,
    NoLicenceBarrier,
    AllRightsReservedBarrier,
    NoPublicationMetadataBarrier,
    ImagesTooNarrowBarrier,
]


def barriers_for_book(book, barrier_classes, fail_fast=False):
    """Return ReleaseBarrier instances for a book.

    Args:
        book: Row instance representing a book.
        barrier_classes: list of BaseReleaseBarrier subclasses
        fail_fast: If True, return the first barrier that applies.
            This can be used to test if a book has any barriers.

    Returns:
        list of BaseReleaseBarrier sub class instances representing
            all barriers that prevent the release of the book.
    """
    barriers = []

    for barrier_class in barrier_classes:
        barrier = barrier_class(book)
        if barrier.applies():
            barriers.append(barrier)
        if fail_fast and barriers:
            break
    return barriers


def has_release_barriers(book):
    """Determine whether a book has barriers preventing release.

    Args:
        book: Row instance representing a book record.

    Returns:
        True if book has release barriers
    """
    return barriers_for_book(book, BARRIER_CLASSES, fail_fast=True)


def release_barriers(book):
    """Return a list of barriers preventing the release of a book.

    Args:
        book: Row instance representing a book record.

    Returns:
        list of BaseReleaseBarrier sub class instances representing
            all barriers that prevent the release of the book.
    """
    return barriers_for_book(book, BARRIER_CLASSES)
