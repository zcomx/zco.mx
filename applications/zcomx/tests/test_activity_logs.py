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
    BaseActivityLog, \
    BaseTentativeLogSet, \
    CompletedTentativeLogSet, \
    PageAddedTentativeLogSet, \
    TentativeActivityLog, \
    TentativeLogSet
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestActivityLog(LocalTestCase):
    pass            # See BaseActivityLog


class TestBaseActivityLog(LocalTestCase):

    def test____init__(self):
        log = BaseActivityLog({})
        self.assertTrue(log)

    def test__age(self):
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        record = {'time_stamp': time_stamp}

        as_of = time_stamp + datetime.timedelta(seconds=1)

        log = BaseActivityLog(record)
        got = log.age(as_of=as_of)
        self.assertEqual(got.total_seconds(), 1)

        log = BaseActivityLog({})
        self.assertRaises(SyntaxError, log.age)

    def test__delete(self):
        count = lambda x: db(db.activity_log.id == x).count()

        activity_log_record = self.add(db.activity_log, dict(
            book_id=-1,
            action='_test__delete_',
        ))

        activity_log = BaseActivityLog(activity_log_record.as_dict())
        self.assertEqual(count(activity_log_record.id), 1)

        activity_log.delete()
        self.assertEqual(count(activity_log_record.id), 0)

    def test__save(self):

        activity_log_data = dict(
            book_id=-1,
            action='_test__save_',
        )

        activity_log = BaseActivityLog(activity_log_data)
        record_id = activity_log.save()

        query = (db.activity_log.id == record_id)
        activity_log_record = db(query).select().first()
        self.assertTrue(activity_log_record)
        self._objects.append(activity_log_record)
        self.assertEqual(activity_log_record.book_id, -1)
        self.assertEqual(activity_log_record.action, '_test__save_')


class TestBaseTentativeLogSet(LocalTestCase):

    def test____init__(self):
        log_set = BaseTentativeLogSet([])
        self.assertTrue(log_set)

    def test__as_activity_log(self):
        log_set = BaseTentativeLogSet([])
        self.assertRaises(NotImplementedError, log_set.as_activity_log)

    def test__load(self):
        tentative_activity_log = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='_test__load_',
        ))

        filters = {'book_id': -1}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], tentative_activity_log.id)
        self.assertEqual(
            pre_log.record['book_id'], tentative_activity_log.book_id)
        self.assertEqual(
            pre_log.record['action'], tentative_activity_log.action)

        filters = {'book_id': -1, 'action': '_test__load_'}
        log_set = BaseTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], tentative_activity_log.id)

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
        self.assertEqual(got.record['id'], 2)


class TestCompletedTentativeLogSet(LocalTestCase):

    def test__as_activity_log(self):
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        # Empty set
        log_set = CompletedTentativeLogSet([])
        self.assertEqual(log_set.as_activity_log(), None)

        # Set with single completed record.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = CompletedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], -2)
        self.assertEqual(got.record['action'], 'completed')
        self.assertEqual(got.record['time_stamp'], time_stamp)

        # Set with multiple completed records.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': -3,
                'book_page_id': -4,
                'action': 'completed',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
        ]
        log_set = CompletedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.record['book_id'], -3)
        self.assertEqual(got.record['book_page_id'], -4)
        self.assertEqual(got.record['action'], 'completed')
        self.assertEqual(
            got.record['time_stamp'], time_stamp + datetime.timedelta(days=1))

    def test__load(self):
        completed_log = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = CompletedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], completed_log.id)
        self.assertEqual(pre_log.record['book_id'], completed_log.book_id)
        self.assertEqual(pre_log.record['action'], completed_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'page added'}
        log_set = CompletedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], page_added_log.id)
        self.assertEqual(pre_log.record['book_id'], page_added_log.book_id)
        self.assertEqual(pre_log.record['action'], page_added_log.action)


class TestPageAddedTentativeLogSet(LocalTestCase):

    def test__as_book_pages(self):
        book_id = -2

        book_page_1 = self.add(db.book_page, dict(
            book_id=book_id,
            page_no=1,
        ))

        book_page_2 = self.add(db.book_page, dict(
            book_id=book_id,
            page_no=1,
        ))

        # Empty set
        log_set = PageAddedTentativeLogSet([])
        self.assertEqual(log_set.as_book_pages(), [])

        tentative_records = [
            TentativeActivityLog({
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
            }),
            TentativeActivityLog({
                'book_id': -1,
                'book_page_id': book_page_2.id,
                'action': 'page added',
            }),
        ]

        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_book_pages()
        self.assertEqual(got, [book_page_1, book_page_2])

    def test__as_activity_log(self):

        book_id = -1
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        book_page_1 = self.add(db.book_page, dict(
            book_id=book_id,
            page_no=3,
        ))

        book_page_2 = self.add(db.book_page, dict(
            book_id=book_id,
            page_no=2,
        ))

        book_page_3 = self.add(db.book_page, dict(
            book_id=book_id,
            page_no=1,
        ))

        # Empty set
        log_set = PageAddedTentativeLogSet([])
        self.assertEqual(log_set.as_activity_log(), None)

        # Set with single page added record.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], book_page_1.id)
        self.assertEqual(got.record['action'], 'page added')
        self.assertEqual(got.record['time_stamp'], time_stamp)

        # Set with multiple page added records.
        tentative_records = [
            TentativeActivityLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': -1,
                'book_page_id': book_page_2.id,
                'action': 'page added',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
            TentativeActivityLog({
                'id': 2,
                'book_id': -1,
                'book_page_id': book_page_3.id,
                'action': 'page added',
                'time_stamp': time_stamp - datetime.timedelta(days=1),
            }),
        ]
        log_set = PageAddedTentativeLogSet(tentative_records)
        got = log_set.as_activity_log()
        self.assertTrue(isinstance(got, ActivityLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], book_page_3.id)
        self.assertEqual(got.record['action'], 'pages added')
        self.assertEqual(
            got.record['time_stamp'], time_stamp + datetime.timedelta(days=1))

    def test__load(self):
        completed_log = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = PageAddedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], page_added_log.id)
        self.assertEqual(pre_log.record['book_id'], page_added_log.book_id)
        self.assertEqual(pre_log.record['action'], page_added_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'completed'}
        log_set = PageAddedTentativeLogSet.load(filters=filters)
        self.assertEqual(len(log_set.tentative_records), 1)
        pre_log = log_set.tentative_records[0]
        self.assertEqual(pre_log.record['id'], completed_log.id)
        self.assertEqual(pre_log.record['book_id'], completed_log.book_id)
        self.assertEqual(pre_log.record['action'], completed_log.action)

    def test__activity_log_action(self):
        log_set = PageAddedTentativeLogSet([])
        self.assertEqual(log_set.activity_log_action(), 'page added')

        log_set = PageAddedTentativeLogSet([{}])
        self.assertEqual(log_set.activity_log_action(), 'page added')

        log_set = PageAddedTentativeLogSet([{}, {}])
        self.assertEqual(log_set.activity_log_action(), 'pages added')


class TestTentativeActivityLog(LocalTestCase):

    def test_delete(self):
        count = lambda x: db(db.tentative_activity_log.id == x).count()

        tentative_record = self.add(db.tentative_activity_log, dict(
            book_id=-1,
            action='_test__delete_',
        ))

        tentative_activity_log = TentativeActivityLog(
            tentative_record.as_dict())
        self.assertEqual(count(tentative_record.id), 1)

        tentative_activity_log.delete()
        self.assertEqual(count(tentative_record.id), 0)

    def test_save(self):

        tentative_activity_log_data = dict(
            book_id=-1,
            action='_test__save_',
        )

        tentative_activity_log = \
            TentativeActivityLog(tentative_activity_log_data)
        record_id = tentative_activity_log.save()

        tentative_record = \
            db(db.tentative_activity_log.id == record_id).select().first()
        self.assertTrue(tentative_record)
        self._objects.append(tentative_record)
        self.assertEqual(tentative_record.book_id, -1)
        self.assertEqual(tentative_record.action, '_test__save_')


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
