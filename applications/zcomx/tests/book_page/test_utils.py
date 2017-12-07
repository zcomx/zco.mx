#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_page/utiles.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.book_page.utils import \
    ActivityLogDeleter, \
    before_delete
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.activity_logs import \
    ActivityLog, \
    TentativeActivityLog
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubActivityLog(ActivityLog):

    def __init__(self, *args, **kwargs):
        """Initializer"""
        ActivityLog.__init__(self, *args, **kwargs)
        self.is_set_deleted = False

    def set_page_deleted(self, book_page):
        self.is_set_deleted = True


class DubTentativeActivityLog(TentativeActivityLog):

    def __init__(self, *args, **kwargs):
        """Initializer"""
        TentativeActivityLog.__init__(self, *args, **kwargs)
        self.is_deleted = False

    def delete(self):
        self.is_deleted = True


class DubActivityLogDeleter(ActivityLogDeleter):
    def __init__(self, book_page):
        super(DubActivityLogDeleter, self).__init__(book_page)
        self.logged_activity_ids = []
        self.logged_tentative_activity_ids = []

    def delete_activity_logs(self):
        for activity_log in self.get_activity_logs(from_cache=True):
            self.logged_activity_ids.append(activity_log.id)

    def delete_tentative_activity_logs(self):
        for tentative_activity_log in \
                self.get_tentative_activity_logs(from_cache=True):
            self.logged_tentative_activity_ids.append(
                tentative_activity_log.id)


class WithObjectsTestCase(LocalTestCase):
    """Class representing a WithObjectsTestCase"""

    _no_logs_book_page = None
    _book_page_1 = None
    _book_page_2 = None
    _book_page_3 = None
    _activity_log_1 = None
    _activity_log_2 = None
    _tentative_activity_log_1 = None
    _tentative_activity_log_2 = None

    def setUp(self):
        self._no_logs_book_page = self.add(BookPage, dict())
        self._book_page_1 = self.add(BookPage, dict())
        self._book_page_2 = self.add(BookPage, dict())
        self._book_page_3 = self.add(BookPage, dict())
        self._activity_log_1 = self.add(ActivityLog, dict(
            book_page_ids=[self._book_page_1.id, self._book_page_2.id],
            deleted_book_page_ids=[],
        ))
        self._activity_log_2 = self.add(ActivityLog, dict(
            book_page_ids=[self._book_page_2.id, self._book_page_3.id],
            deleted_book_page_ids=[],
        ))
        self._tentative_activity_log_1 = self.add(TentativeActivityLog, dict(
            book_page_id=self._book_page_1.id
        ))
        self._tentative_activity_log_2 = self.add(TentativeActivityLog, dict(
            book_page_id=self._book_page_2.id
        ))

        super(WithObjectsTestCase, self).setUp()


class TestActivityLogDeleter(WithObjectsTestCase):

    def test____init__(self):
        log_deleter = DubActivityLogDeleter(self._book_page_1)
        self.assertTrue(log_deleter)
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        self.assertEqual(log_deleter._activity_logs, None)
        self.assertEqual(log_deleter._tentative_activity_logs, None)

    def test__delete_logs(self):
        log_deleter = DubActivityLogDeleter(self._book_page_1)
        self.assertEqual(log_deleter.logged_tentative_activity_ids, [])
        self.assertEqual(log_deleter.logged_activity_ids, [])
        log_deleter.delete_logs()
        self.assertEqual(
            log_deleter.logged_tentative_activity_ids,
            [self._tentative_activity_log_1.id]
        )
        self.assertEqual(
            log_deleter.logged_activity_ids,
            [self._activity_log_1.id]
        )

        log_deleter = DubActivityLogDeleter(self._book_page_2)
        self.assertEqual(log_deleter.logged_tentative_activity_ids, [])
        self.assertEqual(log_deleter.logged_activity_ids, [])
        log_deleter.delete_logs()
        self.assertEqual(
            log_deleter.logged_tentative_activity_ids,
            [self._tentative_activity_log_2.id]
        )
        self.assertEqual(
            log_deleter.logged_activity_ids,
            [self._activity_log_1.id, self._activity_log_2.id]
        )

    def test__delete_activity_logs(self):
        activity_log_1 = DubActivityLog(self._activity_log_1.as_dict())
        activity_log_2 = DubActivityLog(self._activity_log_2.as_dict())
        logs = [activity_log_1, activity_log_2]

        log_deleter = ActivityLogDeleter(BookPage())
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        log_deleter._activity_logs = logs
        for log in logs:
            self.assertEqual(log.is_set_deleted, False)

        log_deleter.delete_activity_logs()

        for log in logs:
            self.assertEqual(log.is_set_deleted, True)

    def test__delete_tentative_activity_logs(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"%%s*
        # pylint: disable=C0103
        tentative_activity_log_1 = DubTentativeActivityLog(
            self._tentative_activity_log_1.as_dict())
        tentative_activity_log_2 = DubTentativeActivityLog(
            self._tentative_activity_log_2.as_dict())
        logs = [tentative_activity_log_1, tentative_activity_log_2]

        log_deleter = ActivityLogDeleter(BookPage())
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        log_deleter._tentative_activity_logs = logs
        for log in logs:
            self.assertEqual(log.is_deleted, False)

        log_deleter.delete_tentative_activity_logs()

        for log in logs:
            self.assertEqual(log.is_deleted, True)

    def test__get_activity_logs(self):
        log_deleter = ActivityLogDeleter(self._no_logs_book_page)
        self.assertEqual(log_deleter.get_activity_logs().records, [])

        log_deleter = ActivityLogDeleter(self._book_page_1)
        got = log_deleter.get_activity_logs()
        self.assertEqual(
            got.records,
            [self._activity_log_1],
        )

        log_deleter = ActivityLogDeleter(self._book_page_2)
        got = log_deleter.get_activity_logs()
        self.assertEqual(
            got.records,
            [self._activity_log_1, self._activity_log_2]
        )

        # Test cache.
        log_deleter = ActivityLogDeleter(self._book_page_2)
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        log_deleter._activity_logs = ['_dummy_']
        self.assertEqual(
            log_deleter.get_activity_logs(from_cache=True),
            ['_dummy_']
        )
        got = log_deleter.get_activity_logs(from_cache=False)
        self.assertEqual(
            got.records,
            [self._activity_log_1, self._activity_log_2]
        )

    def test__get_tentative_activity_logs(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"%%s*
        # pylint: disable=C0103
        log_deleter = ActivityLogDeleter(self._no_logs_book_page)
        self.assertEqual(log_deleter.get_tentative_activity_logs().records, [])

        log_deleter = ActivityLogDeleter(self._book_page_1)
        got = log_deleter.get_tentative_activity_logs()
        self.assertEqual(
            got.records,
            [self._tentative_activity_log_1],
        )

        log_deleter = ActivityLogDeleter(self._book_page_2)
        got = log_deleter.get_tentative_activity_logs()
        self.assertEqual(
            got.records,
            [self._tentative_activity_log_2],
        )

        # Test cache.
        log_deleter = ActivityLogDeleter(self._book_page_2)
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        log_deleter._tentative_activity_logs = ['_tent_dummy_']
        self.assertEqual(
            log_deleter.get_tentative_activity_logs(from_cache=True),
            ['_tent_dummy_']
        )
        got = log_deleter.get_tentative_activity_logs(from_cache=False)
        self.assertEqual(
            got.records,
            [self._tentative_activity_log_2],
        )


class TestFunctions(LocalTestCase):

    def test__before_delete(self):
        book = self.add(Book, dict(name='test__before_delete'))
        book_page = self.add(BookPage, dict(
            book_id=book.id
        ))

        activity_log = self.add(ActivityLog, dict(
            book_id=book.id,
            book_page_ids=[book_page.id],
            deleted_book_page_ids=[],
        ))

        dal_set = db(db.book_page.book_id == book.id)

        before_delete(dal_set)

        after_activity_log = ActivityLog.from_id(activity_log.id)
        self.assertEqual(after_activity_log.id, activity_log.id)
        self.assertEqual(after_activity_log.book_page_ids, None)
        self.assertEqual(
            after_activity_log.deleted_book_page_ids, [book_page.id])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
