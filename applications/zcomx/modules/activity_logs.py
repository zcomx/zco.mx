#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classes and functions related to activity logs
"""
import datetime
from gluon import *
from applications.zcomx.modules.book_pages import \
    BookPage, \
    pages_sorted_by_page_no
from applications.zcomx.modules.books import \
    Book, \
    get_page
from applications.zcomx.modules.records import Record

LOG = current.app.logger

MINIMUM_AGE_TO_LOG_IN_SECONDS = 4 * 60 * 60       # 4 hours


class ActivityLogMixin(object):
    """Mixin class for activity log classes."""

    def age(self, as_of=None):
        """Return the age of the record in seconds.

        Args:
            as_of: datetime.datetime instance, the time to determine the age
                 of. Default: datetime.datetime.now()

        Returns:
            datetime.timedelta instance representing the age.
        """
        if as_of is None:
            as_of = datetime.datetime.now()
        if 'time_stamp' not in self.keys() or not self.time_stamp:
            raise SyntaxError(
                'Activity log has no timestamp, age indeterminate')
        return as_of - self.time_stamp

    def verified_book_page_ids(self):
        """Return a list of verified book page ids.

        Pages of books can be deleted after the activity log record is
        created. This method filters out the ids of deleted pages and
        returns only those that exist.
        """
        verified = []
        db = current.app.db
        if self.book_page_ids:
            for book_page_id in self.book_page_ids:
                query = (db.book_page.id == book_page_id)
                if db(query).select(db.book_page.id).first():
                    verified.append(book_page_id)
        return verified


class ActivityLog(Record, ActivityLogMixin):
    """Class representing a activity_log record"""
    db_table = 'activity_log'

    def set_page_deleted(self, book_page):
        """Set a page in the activity log as deleted.

        Args:
            book_page: BookPage instance representing page to delete

        Return:
            ActivityLog instance updated.
        """
        data = {}
        if self.book_page_ids:
            if book_page.id in self.book_page_ids:
                data['book_page_ids'] = \
                    [x for x in self.book_page_ids if x != book_page.id]

        data['deleted_book_page_ids'] = \
            sorted(self.deleted_book_page_ids + [book_page.id])
        return ActivityLog.from_updated(self, data)


class TentativeActivityLog(Record, ActivityLogMixin):
    """Class representing a tentative_activity_log record"""
    db_table = 'tentative_activity_log'


class BaseTentativeLogSet(object):
    """Base class representing a set of TentativeActivityLog instances"""

    def __init__(self, tentative_records):
        """Initializer

        Args:
            tentative_records: list of TentativeActivityLog instances
        """
        self.tentative_records = tentative_records

    def as_activity_log(self, activity_log_class=ActivityLog):
        """Return an ActivityLog instance representing the
        tentative_activity_log records.

        Args:
            activity_log_class: class used to create instance returned.

        Returns:
            RssLog instance
        """
        raise NotImplementedError()

    @classmethod
    def load(cls, filters=None, tentative_log_class=TentativeActivityLog):
        """Load tentative_activity_log records into set.

        Args:
            filters: dict of tentative_activity_log fields and values to filter
                on. Example {'book_id': 123, 'action': 'page added'}
            tentative_log_class: class used to create log instances stored in
                    self.tentative_records
        Returns:
            BaseRssPreLogSet (or subclass) instance
        """
        db = current.app.db
        tentative_records = []
        queries = []
        if filters:
            for field, value in filters.iteritems():
                if field not in db.tentative_activity_log.fields:
                    continue
                queries.append((db.tentative_activity_log[field] == value))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        rows = db(query).select()
        for r in rows:
            tentative_records.append(tentative_log_class(r.as_dict()))
        return cls(tentative_records)

    def youngest(self):
        """Return the youngest tentative_activity_log record in the set.

        Returns:
            TentativeActivityLog instance representing the youngest.
        """
        if not self.tentative_records:
            return

        by_age = sorted(
            self.tentative_records,
            key=lambda k: k.time_stamp,
            reverse=True
        )
        return by_age[0]


class CompletedTentativeLogSet(BaseTentativeLogSet):
    """Class representing a set of TentativeActivityLog instances,
    action=completed
    """
    def as_activity_log(self, activity_log_class=ActivityLog):

        youngest_log = self.youngest()
        if not youngest_log:
            return
        try:
            youngest_book = Book.from_id(youngest_log.book_id)
            first_page = get_page(youngest_book, page_no='first')
        except LookupError:
            first_page = None

        book_page_ids = [first_page.id] \
            if first_page else \
            [youngest_log.book_page_id]

        record = dict(
            book_id=youngest_log.book_id,
            book_page_ids=book_page_ids,
            action='completed',
            time_stamp=youngest_log.time_stamp,
            deleted_book_page_ids=[],
        )

        return activity_log_class(**record)

    @classmethod
    def load(cls, filters=None, tentative_log_class=TentativeActivityLog):
        super_filters = dict(filters) if filters else {}
        if 'action' not in super_filters:
            super_filters['action'] = 'completed'
        return super(CompletedTentativeLogSet, cls).load(
            filters=super_filters, tentative_log_class=tentative_log_class)


class PageAddedTentativeLogSet(BaseTentativeLogSet):
    """Class representing a set of TentativeActivityLog instances,
    action=page added
    """

    def as_book_pages(self):
        """Return a list of book pages associated with the set
        tentative_activity_log records.

        Returns:
            list of BookPage instances
        """
        book_pages = []
        for tentative_activity_log in self.tentative_records:
            try:
                book_page = BookPage.from_id(
                    tentative_activity_log.book_page_id)
            except LookupError:
                pass        # This will happen if the book is deleted.
            else:
                book_pages.append(book_page)
        return book_pages

    def as_activity_log(self, activity_log_class=ActivityLog):
        youngest_log = self.youngest()
        if not youngest_log:
            return

        book_pages = pages_sorted_by_page_no(self.as_book_pages())
        if not book_pages:
            return
        book_page_ids = [x.id for x in book_pages]

        record = dict(
            book_id=youngest_log.book_id,
            book_page_ids=book_page_ids,
            action='page added',
            time_stamp=youngest_log.time_stamp,
            deleted_book_page_ids=[],
        )

        return activity_log_class(**record)

    @classmethod
    def load(cls, filters=None, tentative_log_class=TentativeActivityLog):
        super_filters = dict(filters) if filters else {}
        if 'action' not in super_filters:
            super_filters['action'] = 'page added'
        return super(PageAddedTentativeLogSet, cls).load(
            filters=super_filters, tentative_log_class=tentative_log_class)


class TentativeLogSet(BaseTentativeLogSet):
    """Class representing a set of TentativeActivityLog instances, all
    actions
    """

    def as_activity_log(self, activity_log_class=ActivityLog):
        # This method doesn't apply.
        return
