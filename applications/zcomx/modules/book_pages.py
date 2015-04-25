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
