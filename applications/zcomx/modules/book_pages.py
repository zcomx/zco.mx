#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Book page classes and functions.
"""
import os
import shutil
from gluon import *
from applications.zcomx.modules.images import (
    ImageDescriptor,
    SIZES,
    UploadImage,
    rename,
)
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.shell_utils import set_owner
from applications.zcomx.modules.utils import abridged_list
from applications.zcomx.modules.zco import SITE_NAME

LOG = current.app.logger


class BookPage(Record):
    """Class representing a book page"""

    db_table = 'book_page'

    def __init__(self, *args, **kwargs):
        """Initializer"""
        Record.__init__(self, *args, **kwargs)
        self._upload_image = None

    def copy_images(self, to_table):
        """Copy images of all sizes to another table, to_table."""
        for size in SIZES:
            fullname = self.upload_image().fullname(size=size)
            new_fullname = fullname.replace(
                '{t}.image'.format(t=self.db_table),
                '{t}.image'.format(t=to_table)
            )
            dirname = os.path.dirname(new_fullname)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
                set_owner(dirname)
            shutil.copy(fullname, new_fullname)
            set_owner(new_fullname)

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
                db[self.db_table].image,
                self.image
            )
        return self._upload_image


class BookPageTmp(BookPage):
    """Class representing a book_page_tmp record."""

    db_table = 'book_page_tmp'

    def rename_image(self, new_filename):
        """Rename the original name of the book page image

        Args:
            new_filename: str, new original name for image file, eg myfile.jpg

        Returns:
            BookPageTmp instance with new image name.
        """
        db = current.app.db
        upload_image = self.upload_image()
        old_fullname = upload_image.fullname()
        stored_filenames = rename(
            old_fullname,
            db[self.db_table].image, new_filename
        )
        new_image = os.path.basename(stored_filenames['original'])
        return BookPageTmp.from_updated(self, {'image': new_image})


class BookPageNumber():
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


class BookPageNumbers():
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


def delete_pages_not_in_ids(book_id, book_page_ids, book_page_tbl=None):
    """Delete book_page record for a book not found in the provided
    list of book_page ids.
    Args:
        book_id: integer id of book
        book_page_ids: list of integers, ids of book_page records
        book_page_tbl: Table instance, db.book_page or db.book_page_tmp
            default db.book_page
    Returns:
        list of integers, ids of book_page records deleted.
    """
    db = current.app.db

    if book_page_tbl is None:
        book_page_tbl = db.book_page

    if book_page_tbl == db.book_page:
        book_page_class = BookPage
    elif book_page_tbl == db.book_page_tmp:
        book_page_class = BookPageTmp
    else:
        raise LookupError(
            'Invalid book_page_tbl: {t}'.format(t=str(book_page_tbl)))

    deleted_ids = []
    query = (book_page_tbl.book_id == book_id)
    ids = [x.id for x in db(query).select()]
    for page_id in ids:
        if page_id not in book_page_ids:
            page = book_page_class.from_id(page_id)
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


def reset_book_page_nos(page_ids, book_page_tbl=None):
    """Reset the book_page.page_no values according to the
    provided list of book ids.

    Args:
        page_ids: list of integers, ids of book_page records
        book_page_tbl: Table instance, db.book_page or db.book_page_tmp
            default db.book_page
    """
    db = current.app.db
    if book_page_tbl is None:
        book_page_tbl = db.book_page

    if book_page_tbl == db.book_page:
        book_page_class = BookPage
    elif book_page_tbl == db.book_page_tmp:
        book_page_class = BookPageTmp
    else:
        raise LookupError(
            'Invalid book_page_tbl: {t}'.format(t=str(book_page_tbl)))

    for count, page_id in enumerate(page_ids):
        page = book_page_class.from_id(page_id)
        if page:
            book_page_class.from_updated(page, dict(page_no=(count + 1)))
