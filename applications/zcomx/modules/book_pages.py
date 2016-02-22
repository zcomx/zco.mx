#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book page classes and functions.
"""
from gluon import *
from applications.zcomx.modules.images import \
    ImageDescriptor, \
    UploadImage
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.utils import abridged_list
from applications.zcomx.modules.zco import SITE_NAME

LOG = current.app.logger


class BookPage(Record):
    """Class representing a book page"""

    db_table = 'book_page'
    min_cbz_width = 1600                # pixels
    min_cbz_height_to_exempt = 2560     # pixels

    def __init__(self, *args, **kwargs):
        """Initializer"""
        Record.__init__(self, *args, **kwargs)
        self._upload_image = None

    def orientation(self):
        """Return the orientation of the book page.

        Returns:
            str: one of 'portrait', 'landscape', 'square'
        """
        if not self.image:
            raise LookupError('Book page has no image, id {i}'.format(
                i=self.id))
        return ImageDescriptor(self.upload_image().fullname()).orientation()

    def upload_image(self):
        """Return an UploadImage instance representing the book page image

        Returns:
            UploadImage instance
        """
        if not self._upload_image:
            db = current.app.db
            self._upload_image = UploadImage(
                db.book_page.image,
                self.image
            )
        return self._upload_image


class BookPageNumber(object):
    """Class representing a set of book page number."""

    def __init__(self, book_page):
        """Constructor

        Args:
            book_page: BookPage instance
        """
        self.book_page = book_page

    def formatted(self):
        """Return the book page number formatted

        Returns:
            string
        """
        return 'p{p:02d}'.format(p=self.book_page.page_no)

    def link(self, url_func):
        """Return the book page number formatted as a link

        Args:
            url_func: function to format url, eg modules/books def page_url

        Returns:
            A instance
        """
        return A(
            self.formatted(),
            _href=url_func(self.book_page, extension=False, host=SITE_NAME)
        )


class BookPageNumbers(object):
    """Class representing a set of book page numbers."""

    def __init__(self, book_pages):
        """Constructor

        Args:
            book_pages: list of BookPage instances
        """
        self.book_pages = book_pages

    def links(self, url_func):
        """Return a list of links

        Args:
            url_func: function used to convert page numbers into links.
        """
        return [BookPageNumber(x).link(url_func) for x in self.book_pages]

    def numbers(self):
        """Return a list of numbers """
        return [BookPageNumber(x).formatted() for x in self.book_pages]


class AbridgedBookPageNumbers(BookPageNumbers):
    """Class representing an abridged set of book page numbers."""

    def links(self, url_func):
        page_links = []
        for item in abridged_list(self.book_pages):
            if item == '...':
                page_links.append(item)
            else:
                page_links.append(BookPageNumber(item).link(url_func))
        return page_links

    def numbers(self):
        """Return a list of numbers """
        page_links = []
        for item in abridged_list(self.book_pages):
            if item == '...':
                page_links.append(item)
            else:
                page_links.append(BookPageNumber(item).formatted())
        return page_links


def delete_pages_not_in_ids(book_id, book_page_ids):
    """Delete book_page record for a book not found in the provided
    list of book_page ids.
    Args:
        book_id: integer id of book
        book_page_ids: list of integers, ids of book_page records
    Returns:
        list of integers, ids of book_page records deleted.
    """
    deleted_ids = []
    db = current.app.db
    query = (db.book_page.book_id == book_id)
    ids = [x.id for x in db(query).select()]
    for page_id in ids:
        if page_id not in book_page_ids:
            page = BookPage.from_id(page_id)
            page.delete()
            deleted_ids.append(page_id)
    return deleted_ids


def pages_sorted_by_page_no(book_pages, reverse=False):
    """Return a list of book_page Row instances sorted by page_no.

    Args:
        list of BookPage instances

    Returns:
        list of BookPage instances, sorted
    """
    return sorted(
        book_pages,
        key=lambda k: k.page_no,
        reverse=reverse,
    )


def reset_book_page_nos(page_ids):
    """Reset the book_page.page_no values according to the
    provided list of book ids.

    Args:
        book_page_ids: list of integers, ids of book_page records
    """
    for count, page_id in enumerate(page_ids):
        page = BookPage.from_id(page_id)
        if page:
            BookPage.from_updated(page, dict(page_no=(count + 1)))
