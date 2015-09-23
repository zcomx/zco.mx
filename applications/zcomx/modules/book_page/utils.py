#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book page utilities.
"""
import logging
from gluon import *
from applications.zcomx.modules.activity_logs import \
    ActivityLog, \
    TentativeActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.records import Records

LOG = logging.getLogger('app')


class ActivityLogDeleter(object):
    """Class representing a ActivityLogDeleter"""

    def __init__(self, book_page):
        """Initializer

        Args:
            book_page: string, first arg
        """
        self.book_page = book_page
        self._activity_logs = None            # cache
        self._tentative_activity_logs = None           # cache

    def delete_logs(self):
        """Delete logs for the book_page. """
        self.delete_tentative_activity_logs()
        self.delete_activity_logs()

    def delete_activity_logs(self):
        """Delete activity logs for the book_page. """
        for activity_log in self.get_activity_logs(from_cache=True):
            activity_log.set_page_deleted(self.book_page)

    def delete_tentative_activity_logs(self):
        """Delete tentative activity logs for the book_page. """
        for tentative_activity_log in \
                self.get_tentative_activity_logs(from_cache=True):
            tentative_activity_log.delete()

    def get_activity_logs(self, from_cache=False):
        """Get activity logs for the book_page.

        Returns:
            list of ActivityLog instances
        """
        if self._activity_logs is None or not from_cache:
            db = current.app.db
            query = (db.activity_log.book_page_ids.contains(self.book_page.id))
            try:
                self._activity_logs = Records.from_query(
                    ActivityLog,
                    query,
                    orderby=db.activity_log.id
                )
            except LookupError:
                self._activity_logs = []
        return self._activity_logs

    def get_tentative_activity_logs(self, from_cache=False):
        """Get tentative activity logs for the book_page.

        Returns:
            list of TentativeActivityLog instances
        """
        if self._tentative_activity_logs is None or not from_cache:
            db = current.app.db
            query = \
                (db.tentative_activity_log.book_page_id == self.book_page.id)
            try:
                self._tentative_activity_logs = Records.from_query(
                    TentativeActivityLog,
                    query,
                    orderby=db.tentative_activity_log.id
                )
            except LookupError:
                self._tentative_activity_logs = []
        return self._tentative_activity_logs


def before_delete(dal_set):
    """Callback for db.book_page._before_delete.

    Args:
        dal_set: pydal.objects.Set instance

    """
    db = current.app.db
    for book_page_id in [x.id for x in dal_set.select(db.book_page.id)]:
        book_page = BookPage.from_id(book_page_id)
        deleter = ActivityLogDeleter(book_page)
        deleter.delete_logs()
