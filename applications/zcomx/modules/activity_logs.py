#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Classes and functions related to activity logs
"""
import datetime
import logging
from gluon import *
from applications.zcomx.modules.book_pages import \
    pages_sorted_by_page_no
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')

MINIMUM_AGE_TO_LOG_IN_SECONDS = 4 * 60 * 60       # 4 hours


class BaseActivityLog(object):
    """Class representing a BaseActivityLog"""

    db_table = 'activity_log'

    def __init__(self, record):
        """Initializer

        Args:
            record: dict,
                {
                    'id': <id>,
                    'book_id': <book_id>,
                    'book_page_id': <book_page_id>,
                    'action': <action>,
                    'time_stamp': <time_stamp>,
                }
        """
        self.record = record

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
        if not self.record or 'time_stamp' not in self.record:
            raise SyntaxError(
                'Activity log has no timestamp, age indeterminate')
        return as_of - self.record['time_stamp']

    def delete(self):
        """Delete the record from the db"""
        db = current.app.db
        db(db[self.db_table].id == self.record['id']).delete()
        db.commit()

    def save(self):
        """Save the record to the db."""
        db = current.app.db
        record_id = db[self.db_table].insert(**self.record)
        db.commit()
        return record_id


class ActivityLog(BaseActivityLog):
    """Class representing a activity_log record"""
    db_table = 'activity_log'


class TentativeActivityLog(BaseActivityLog):
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
            key=lambda k: k.record['time_stamp'],
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

        record = dict(
            book_id=youngest_log.record['book_id'],
            book_page_id=youngest_log.record['book_page_id'],
            action='completed',
            time_stamp=youngest_log.record['time_stamp'],
        )

        return activity_log_class(record)

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
        """Return a list of Row instances representing book_page records
            associated wiht the set tentative_activity_log records.

        Returns:
            list of Rows representing book_page records.
        """
        book_pages = []
        db = current.app.db
        for tentative_activity_log in self.tentative_records:
            book_page = entity_to_row(
                db.book_page, tentative_activity_log.record['book_page_id'])
            if book_page:
                book_pages.append(book_page)
        return book_pages

    def as_activity_log(self, activity_log_class=ActivityLog):
        youngest_log = self.youngest()
        if not youngest_log:
            return

        book_pages = pages_sorted_by_page_no(self.as_book_pages())
        if not book_pages:
            return

        record = dict(
            book_id=youngest_log.record['book_id'],
            book_page_id=book_pages[0].id,
            action=self.activity_log_action(),
            time_stamp=youngest_log.record['time_stamp'],
        )

        return activity_log_class(record)

    @classmethod
    def load(cls, filters=None, tentative_log_class=TentativeActivityLog):
        super_filters = dict(filters) if filters else {}
        if 'action' not in super_filters:
            super_filters['action'] = 'page added'
        return super(PageAddedTentativeLogSet, cls).load(
            filters=super_filters, tentative_log_class=tentative_log_class)

    def activity_log_action(self):
        """Return the action to be used in the activity_log record.

        Returns:
            string, one of 'page added' or 'pages added'
        """
        if len(self.tentative_records) > 1:
            return 'pages added'
        return 'page added'


class TentativeLogSet(BaseTentativeLogSet):
    """Class representing a set of TentativeActivityLog instances, all
    actions
    """

    def as_activity_log(self, activity_log_class=ActivityLog):
        # This method doesn't apply.
        return
