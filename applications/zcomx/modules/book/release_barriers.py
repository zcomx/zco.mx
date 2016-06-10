#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book release barriers.
"""
import os
from gluon import *
from applications.zcomx.modules.images import ImageDescriptor
from applications.zcomx.modules.indicias import PublicationMetadata

LOG = current.app.logger


class BaseReleaseBarrier(object):
    """Class representing a complete barrier"""

    def __init__(self, book):
        """Initializer

        Args:
            book: Book instance
        """
        self.book = book

    def applies(self):
        """Test if the barrier is a applicable.

        Returns
            True if the barrier applies and should prevent setting complete.
        """
        raise NotImplementedError

    @property
    def code(self):
        """The complete barrier code."""
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
        query = (db.cc_licence.code == 'All Rights Reserved')
        arr = db(query).select(limitby=(0, 1)).first()
        return arr and arr.id and self.book.cc_licence_id == arr.id

    @property
    def code(self):
        return 'licence_arr'

    @property
    def description(self):
        return (
            'On zco.mx, completed books'
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
    """Class representing a 'duplicate name' barrier.

    CBZ and torrent files are named after the book name so the book name
    must be unique.
    """

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
        return 'You have a completed book with the same name.'


class DupeNumberBarrier(BaseReleaseBarrier):
    """Class representing a 'duplicate number' barrier.

    CBZ and torrent files are named after the book name/number so the book
    name/number must be unique.
    """

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
        return 'You have a completed book with the same name and number.'


class InvalidPageNoBarrier(BaseReleaseBarrier):
    """Class representing a 'invalid page no' barrier."""

    def applies(self):
        pages = self.book.pages()

        # Must have a pages
        if not pages:
            return True

        page_nos = [x.page_no for x in pages]

        # Must have a cover page
        if 1 not in page_nos:
            return True

        # Must have no dupe page_on values.
        if len(page_nos) != len(set(page_nos)):
            return True
        return False

    @property
    def code(self):
        return 'invalid_page_no'

    @property
    def description(self):
        return (
            'Occassionaly during the upload of images, '
            'the page numbers are assigned improperly by our system. '
        )

    @property
    def fixes(self):
        return [
            'Click the Upload button associated with the book.',
            'Check that images are in the correct order and fix as necessary.',
            'Then click the "Post On Web" button.',
        ]

    @property
    def reason(self):
        return 'The page numbers were not set properly.'


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


class NoCBZImageBarrier(BaseReleaseBarrier):
    """Class representing a 'no CBZ size image' barrier."""

    def __init__(self, book):
        """Initializer

        Args:
            book: Row instance representing a book.
        """
        super(NoCBZImageBarrier, self).__init__(book)
        self._no_cbz_images = None

    def applies(self):
        violating_images = self.no_cbz_images()
        return len(violating_images) > 0

    @property
    def code(self):
        return 'no_cbz_images'

    @property
    def description(self):
        return (
            'A minimum width of 2560px is recommended. '
            'The following images should be replaced:'
        )

    @property
    def fixes(self):
        violating_images = self.no_cbz_images()
        return violating_images

    def no_cbz_images(self):
        """Return a list of image names representing images with out a
        'cbz' size.

        Returns:
            list of strings, image names.
        """
        # Images must have a 'cbz' sized version.
        if self._no_cbz_images is None:
            violating_images = []
            for page in self.book.pages():
                upload_img = page.upload_image()
                fullname = upload_img.fullname(size='cbz')
                if not os.path.exists(fullname):
                    # Get width and original name
                    try:
                        dims = ImageDescriptor(fullname).dimensions()
                    except IOError:
                        # The 'cbz' size may not exist.
                        dims = None
                    if not dims:
                        dims = ImageDescriptor(
                            upload_img.fullname(size='original')
                        ).dimensions()
                    width = dims[0]
                    original_name = upload_img.original_name()
                    violating_images.append(
                        '{n} (width: {w} px)'.format(n=original_name, w=width)
                    )
            self._no_cbz_images = violating_images
        return self._no_cbz_images

    @property
    def reason(self):
        return 'Some images are not large enough.'


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
            'On zco.mx, completed books '
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
        return self.book.page_count() == 0

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
        try:
            PublicationMetadata.from_query(query)
        except LookupError:
            return True
        else:
            return False

    @property
    def code(self):
        return 'no_metadata'

    @property
    def description(self):
        return (
            'On zco.mx, completed books include an indicia page. '
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


class NotCompletedBarrier(BaseReleaseBarrier):
    """Class representing a 'not completed' barrier."""

    def applies(self):
        return not self.book.release_date

    @property
    def code(self):
        return 'not_completed'

    @property
    def description(self):
        return (
            'The book cannot be edited '
            'once released for file sharing networks. '
            'It must be set as completed.'
        )

    @property
    def fixes(self):
        return [
            'Click the "Set as completed" checkbox for the book.',
        ]

    @property
    def reason(self):
        return 'The book is not completed.'


COMPLETE_BARRIER_CLASSES = [
    NoBookNameBarrier,
    NoPagesBarrier,
    DupeNameBarrier,
    DupeNumberBarrier,
    NoLicenceBarrier,
    NoPublicationMetadataBarrier,
    InvalidPageNoBarrier,
]

FILESHARING_BARRIER_CLASSES = [
    NotCompletedBarrier,
    AllRightsReservedBarrier,
    NoCBZImageBarrier,
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
            all barriers that prevent the complete of the book.
    """
    barriers = []

    for barrier_class in barrier_classes:
        barrier = barrier_class(book)
        if barrier.applies():
            barriers.append(barrier)
        if fail_fast and barriers:
            break
    return barriers


def complete_barriers(book):
    """Return a list of barriers preventing the book from being set complete.

    Args:
        book: Row instance representing a book record.

    Returns:
        list of BaseReleaseBarrier sub class instances representing
            all barriers that prevent the book from being set complete.
    """
    return barriers_for_book(book, COMPLETE_BARRIER_CLASSES)


def filesharing_barriers(book):
    """Return a list of barriers preventing the book from being released for
    filesharing.

    Args:
        book: Row instance representing a book record.

    Returns:
        list of BaseReleaseBarrier sub class instances representing
            all barriers that prevent the book from being released for
            filesharing.
    """
    return barriers_for_book(book, FILESHARING_BARRIER_CLASSES)


def has_complete_barriers(book):
    """Determine whether a book has barriers preventing it from being set
    complete.

    Args:
        book: Row instance representing a book record.

    Returns:
        True if book has barriers
    """
    return barriers_for_book(book, COMPLETE_BARRIER_CLASSES, fail_fast=True)


def has_filesharing_barriers(book):
    """Determine whether a book has barriers preventing it from being released
    for filesharing.

    Args:
        book: Row instance representing a book record.

    Returns:
        True if book has barriers
    """
    return barriers_for_book(book, FILESHARING_BARRIER_CLASSES, fail_fast=True)
