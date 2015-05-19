#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book lists.
"""
import logging
from gluon import *
from applications.zcomx.modules.zco import \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT

LOG = logging.getLogger('app')


class BaseBookList(object):
    """Base class representing a list of books for a creator"""
    # no-self-use (R0201): *Method could be a function*
    # pylint: disable=R0201

    def __init__(self, creator):
        """Constructor

        Args:
            creator: Row instance representing an creator.
        """
        self.creator = creator
        self.db = current.app.db
        self._books = None

    @property
    def allow_upload_on_edit(self):
        """Return whether to allow upload images from edit modal."""
        return False

    def books(self):
        """Return a list of books."""
        if self._books is None:
            db = current.app.db
            queries = []
            queries.append((db.book.creator_id == self.creator.id))
            queries.extend(self.filters())
            if not queries:
                queries.append(db.book)
            query = reduce(lambda x, y: x & y, queries) if queries else None
            self._books = db(query).select(
                db.book.ALL, orderby=[db.book.name, db.book.number])
        return self._books

    @property
    def code(self):
        """Return the code of this book list class."""
        raise NotImplementedError

    @property
    def display_if_none(self):
        """Return whether to display the list if there are no books."""
        return False

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        return []

    def headers(self):
        """Return dict representing column headers.

        Returns:
            dict of column headers. If None, no headers are displayed.
        """
        return

    @property
    def include_complete_checkbox(self):
        """Return whether to include the complete checkbox."""
        return False

    @property
    def include_publication_year(self):
        """Return whether to include the publication year."""
        return False

    @property
    def include_read(self):
        """Return whether to include the read button."""
        return False

    @property
    def include_upload(self):
        """Return whether to include the upload button."""
        return False

    @property
    def link_to_book_page(self):
        """Return whether to display book name as a link to the book page."""
        return False

    @property
    def no_records_found_msg(self):
        """Return the message to display when no records are found.

        Returns:
            str
        """
        return 'No books found'

    @property
    def subtitle(self):
        """Return the subtitle of the book list."""
        return ''

    @property
    def title(self):
        """Return the title of the book list."""
        return self.code.upper()


class CompletedBookList(BaseBookList):
    """Class representing a list of completed books for a creator."""

    @property
    def code(self):
        return 'completed'

    @property
    def display_if_none(self):
        return True

    def filters(self):
        db = self.db
        queries = []
        queries.append((db.book.status == BOOK_STATUS_ACTIVE))
        queries.append((db.book.release_date != None))
        return queries

    @property
    def include_publication_year(self):
        return True

    @property
    def include_read(self):
        return True

    @property
    def link_to_book_page(self):
        return True

    @property
    def no_records_found_msg(self):
        return 'No completed books'


class DisabledBookList(BaseBookList):
    """Class representing a list of disabled books for a creator."""

    @property
    def code(self):
        return 'disabled'

    def filters(self):
        db = self.db
        queries = []
        queries.append((db.book.status == BOOK_STATUS_DISABLED))
        return queries

    @property
    def no_records_found_msg(self):
        return 'No disabled books'

    @property
    def subtitle(self):
        return (
            'Books are disabled by the site admin '
            'if they are under copyright review or deemed inappropriate.'
        )


class DraftBookList(BaseBookList):
    """Class representing a list of draft books for a creator."""

    @property
    def allow_upload_on_edit(self):
        return True

    @property
    def code(self):
        return 'draft'

    def filters(self):
        db = self.db
        queries = []
        queries.append((db.book.status == BOOK_STATUS_DRAFT))
        return queries

    @property
    def include_upload(self):
        return True

    @property
    def no_records_found_msg(self):
        return 'No draft books'

    @property
    def subtitle(self):
        return (
            'Books remain as a draft until pages are added. '
            'Use the Upload button to add page images. '
            'Drafts are not posted online, nor available in search results. '
        )

    @property
    def title(self):
        return 'DRAFTS'


class OngoingBookList(BaseBookList):
    """Class representing a list of ongoing books for a creator."""

    @property
    def allow_upload_on_edit(self):
        return True

    @property
    def code(self):
        return 'ongoing'

    @property
    def display_if_none(self):
        return True

    def filters(self):
        db = self.db
        queries = []
        queries.append((db.book.status == BOOK_STATUS_ACTIVE))
        queries.append((db.book.release_date == None))
        return queries

    def headers(self):
        return {
            'name': None,
            'read': None,
            'upload': None,
            'edit': None,
            'delete': None,
            'complete_checkbox': DIV(
                'Set as completed',
                _class="set_as_completed text-muted",
            ),
        }

    @property
    def include_complete_checkbox(self):
        return True

    @property
    def include_read(self):
        return True

    @property
    def include_upload(self):
        return True

    @property
    def link_to_book_page(self):
        return True

    @property
    def no_records_found_msg(self):
        return 'No ongoing series'


def class_from_code(code):
    """Return a BaseBookList subclass for the given code."""
    lookup = {
        'completed': CompletedBookList,
        'disabled': DisabledBookList,
        'draft': DraftBookList,
        'ongoing': OngoingBookList,
    }

    if code not in lookup:
        raise ValueError('Invalid book list code: {c}'.format(c=code))

    return lookup[code]
