#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book page classes and functions.
"""
import logging
from gluon import *
from applications.zcomx.modules.images import UploadImage
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

LOG = logging.getLogger('app')


class BookPage(object):
    """Class representing a book page"""

    min_cbz_width = 1600                # pixels
    min_cbz_height_to_exempt = 2560     # pixels

    def __init__(self, book_page_entity):
        """Constructor

        Args:
            book_page_entity: Row instance or integer representing a book_page
                record.
        """
        db = current.app.db
        self.book_page_entity = book_page_entity
        self.book_page = entity_to_row(db.book_page, book_page_entity)
        if not self.book_page:
            raise NotFoundError('Book page not found, {e}'.format(
                e=book_page_entity))
        self._upload_image = None

    def upload_image(self):
        """Return an UploadImage instance representing the book page image

        Returns:
            UploadImage instance
        """
        db = current.app.db
        if not self._upload_image:
            self._upload_image = UploadImage(
                db.book_page.image,
                self.book_page.image
            )
        return self._upload_image


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
            db(db.book_page.id == page_id).delete()
            db.commit()
            deleted_ids.append(page_id)
    return deleted_ids


def pages_sorted_by_page_no(book_pages, reverse=False):
    """Return a list of book_page Row instances sorted by page_no.

    Args:
        list of Row instances representing book_page records.

    Returns:
        list of Row instances representing book_page records, sorted
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
    db = current.app.db
    for count, page_id in enumerate(page_ids):
        page_record = entity_to_row(db.book_page, page_id)
        if page_record:
            page_record.update_record(page_no=(count + 1))
            db.commit()
