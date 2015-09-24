#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/activity_logs.py

"""
import datetime
import unittest
from gluon import *
from applications.zcomx.modules.activity_logs import \
    ActivityLog, \
    ActivityLogMixin, \
    BaseTentativeLogSet, \
    CompletedTentativeLogSet, \
    PageAddedTentativeLogSet, \
    TentativeActivityLog, \
    TentativeLogSet
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubActivityLog(Record, ActivityLogMixin):
    db_table = 'activity_log'


class TestActivityLog(LocalTestCase):

    def test__set_page_deleted(self):
        book_page = BookPage(id=999999)

        activity_log = self.add(ActivityLog, dict(
            book_page_ids=[],
            deleted_book_page_ids=[],
        ))

        got = activity_log.set_page_deleted(book_page)
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_page_ids, [])
        self.assertEqual(got.deleted_book_page_ids, [book_page.id])

        activity_log = self.add(ActivityLog, dict(
            book_page_ids=[-1, -2, book_page.id],
            deleted_book_page_ids=[-3, -4],
        ))

        got = activity_log.set_page_deleted(book_page)
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_page_ids, [-1, -2])
        self.assertEqual(got.deleted_book_page_ids, [-4, -3, book_page.id])


class TestActivityLogMixin(LocalTestCase):

    time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

    def test__age(self):
        record = {'time_stamp': self.time_stamp}

        as_of = self.time_stamp + datetime.timedelta(seconds=1)

        log = DubActivityLog(**record)
        got = log.age(as_of=as_of)
        self.assertEqual(got.total_seconds(), 1)

        log = DubActivityLog({})
        self.assertRaises(SyntaxError, log.age)

    def test__verified_book_page_ids(self):
        book = self.add(Book, dict(name='test__verified_book_page_ids'))

        book_page_1 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))

        book_page_2 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
        ))

        original_ids = [book_page_1.id, book_page_2.id]
        reversed_ids = [book_page_2.id, book_page_1.id]
        tarnished_ids = [book_page_1.id, -3, book_page_2.id]

        tests = [
            # (book_page_ids, expect)
            (original_ids, original_ids),
            (reversed_ids, reversed_ids),
            (tarnished_ids, original_ids),
        ]

        for t in tests:
            record = {'book_page_ids': t[0]}
            log = DubActivityLog(**record)
            self.assertEqual(
                log.verified_book_page_ids(),
                t[1]
            )


class TestBaseTentativeLogSet(LocalTestCase):

    def test____init__(self):
        log_set = BaseTentativeLogSet([])
        self.assertTrue(log_set)

    def test__as_activity_log(self):
        log_set = BaseTentativeLogSet([])
        self.assertRaises(NotImplementedError, log_set.as_activity_log)

    def test__load(self):
        tentative_activity_log = self.add(TentativeActivityLog, dict(
            book_id=-1,
            action='_test__load_',
        ))

        filters = {'book_id': -1}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, tentative_activity_log.id)
        self.assertEqual(
            pre_log.book_id, tentative_activity_log.book_id)
        self.assertEqual(
            pre_log.action, tentative_activity_log.action)

        filters = {'book_id': -1, 'action': '_test__load_'}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, tentative_activity_log.id)

        filters = {'book_id': -2}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 0)

        filters = {'book_id': -1, 'action': '_fake_'}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 0)

    def test__youngest(self):
        log_set = BaseTentativeLogSet([])
        self.assertEqual(log_set.youngest(), None)

        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': 1,
                'time_stamp': time_stamp,
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': 2,
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
            TentativeActivityLog({
                'id': 3,
                'book_id': 3,
                'time_stamp': time_stamp - datetime.timedelta(days=1),
            }),
        ]
        log_set = BaseTentativeLogSet(tentative_records)
        got = log_set.youngest()
        self.assertEqual(got.id, 2)


class TestCompletedTentativeLogSet(LocalTestCase):

    def test__as_activity_log(self):
        book = self.add(Book, dict(name='test__as_activity_log'))
        book_2 = self.add(Book, dict(name='test__as_activity_log_2'))
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        # Empty set
        log_set = CompletedTentativeLogSet([])
        self.assertEqual(log_set.as_activity_log(), None)

        # Set with single completed record.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': book.id,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = CompletedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_id, book.id)
        self.assertEqual(got.book_page_ids, [-2])
        self.assertEqual(got.action, 'completed')
        self.assertEqual(got.time_stamp, time_stamp)
        self.assertEqual(got.deleted_book_page_ids, [])

        # Set with multiple completed records.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': book.id,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': book_2.id,
                'book_page_id': -4,
                'action': 'completed',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
        ]
        log_set = CompletedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_id, book_2.id)
        self.assertEqual(got.book_page_ids, [-4])
        self.assertEqual(got.action, 'completed')
        self.assertEqual(
            got.time_stamp, time_stamp + datetime.timedelta(days=1))
        self.assertEqual(got.deleted_book_page_ids, [])

    def test__load(self):
        completed_log = self.add(TentativeActivityLog, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(TentativeActivityLog, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = CompletedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, completed_log.id)
        self.assertEqual(pre_log.book_id, completed_log.book_id)
        self.assertEqual(pre_log.action, completed_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'page added'}
        log_set = CompletedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, page_added_log.id)
        self.assertEqual(pre_log.book_id, page_added_log.book_id)
        self.assertEqual(pre_log.action, page_added_log.action)


class TestPageAddedTentativeLogSet(LocalTestCase):

    def test__as_book_pages(self):
        book = self.add(Book, dict(name='test__as_book_pages'))

        page_1 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))
        book_page_1 = BookPage.from_id(page_1)

        page_2 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))
        book_page_2 = BookPage.from_id(page_2)

        # Empty set
        log_set = PageAddedTentativeLogSet([])
        self.assertEqual(log_set.as_book_pages(), [])

        tentative_records = [
            TentativeActivityLog({
                'book_id': book.id,
                'book_page_id': book_page_1.id,
                'action': 'page added',
            }),
            TentativeActivityLog({
                'book_id': book.id,
                'book_page_id': book_page_2.id,
                'action': 'page added',
            }),
        ]

        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_book_pages()
        self.assertEqual(got, [book_page_1, book_page_2])

    def test__as_activity_log(self):
        book = self.add(Book, dict(name='test__as_activity_log'))
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        book_page_1 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=3,
        ))

        book_page_2 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
        ))

        book_page_3 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))

        # Empty set
        log_set = PageAddedTentativeLogSet([])
        self.assertEqual(log_set.as_activity_log(), None)

        # Set with single page added record.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': book.id,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_id, book.id)
        self.assertEqual(got.book_page_ids, [book_page_1.id])
        self.assertEqual(got.action, 'page added')
        self.assertEqual(got.time_stamp, time_stamp)
        self.assertEqual(got.deleted_book_page_ids, [])

        # Set with multiple page added records.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': book.id,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': book.id,
                'book_page_id': book_page_2.id,
                'action': 'page added',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
            TentativeActivityLog({
                'id': 3,
                'book_id': book.id,
                'book_page_id': book_page_3.id,
                'action': 'page added',
                'time_stamp': time_stamp - datetime.timedelta(days=1),
            }),
        ]
        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.book_id, book.id)
        self.assertEqual(
            got.book_page_ids,
            [book_page_3.id, book_page_2.id, book_page_1.id]
        )
        self.assertEqual(got.action, 'page added')
        self.assertEqual(
            got.time_stamp, time_stamp + datetime.timedelta(days=1))
        self.assertEqual(got.deleted_book_page_ids, [])

    def test__load(self):
        completed_log = self.add(TentativeActivityLog, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(TentativeActivityLog, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = PageAddedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, page_added_log.id)
        self.assertEqual(pre_log.book_id, page_added_log.book_id)
        self.assertEqual(pre_log.action, page_added_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'completed'}
        log_set = PageAddedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.id, completed_log.id)
        self.assertEqual(pre_log.book_id, completed_log.book_id)
        self.assertEqual(pre_log.action, completed_log.action)


class TestTentativeActivityLog(LocalTestCase):
    pass            # Record subclass


class TestTentativeLogSet(LocalTestCase):

    def test__as_activity_log(self):
        log_set = TentativeLogSet([])
        self.assertEqual(log_set.as_activity_log(), None)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
