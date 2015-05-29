#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/rss.py

"""
import datetime
import re
import unittest
import gluon.contrib.rss2 as rss2
from gluon import *
from applications.zcomx.modules.book_types import by_name as book_type_by_name
from applications.zcomx.modules.rss import \
    AllRSSChannel, \
    BaseRSSChannel, \
    BaseRSSEntry, \
    BaseRSSLog, \
    BaseRSSPreLogSet, \
    BookRSSChannel, \
    CartoonistRSSChannel, \
    CompletedRSSEntry, \
    CompletedRSSPreLogSet, \
    PageAddedRSSEntry, \
    PageAddedRSSPreLogSet, \
    PagesAddedRSSEntry, \
    RSSLog, \
    RSSPreLog, \
    RSSPreLogSet, \
    channel_from_type, \
    entry_class_from_action, \
    rss_log_as_entry, \
    rss_serializer_with_image
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    _auth_user = None
    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None
    _rss_log = None
    _rss_log_time_stamp = '2015-01-31 12:30:59'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):

        self._auth_user = self.add(db.auth_user, dict(
            name='First Last'
        ))

        self._creator = self.add(db.creator, dict(
            auth_user_id=self._auth_user.id,
            email='image_test_case@example.com',
            name_for_url='FirstLast',
        ))

        self._book = self.add(db.book, dict(
            name='My Book',
            number=1,
            creator_id=self._creator.id,
            book_type_id=book_type_by_name('ongoing').id,
            name_for_url='MyBook-001',
        ))

        self._book_page = self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self._book_page_2 = self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        self._rss_log = self.add(db.rss_log, dict(
            book_id=self._book.id,
            book_page_id=self._book_page.id,
            action='completed',
            time_stamp=datetime.datetime.strptime(
                self._rss_log_time_stamp, '%Y-%m-%d %H:%M:%S'),
        ))


class DubRSSChannel(BaseRSSChannel):
    max_entry_age_in_days = 10

    def __init__(self, entity=None):
        super(DubRSSChannel, self).__init__(entity=entity)
        self._filter_query = None

    def description(self):
        return 'My dub RSS channel.'

    def filter_query(self):
        return self._filter_query

    def link(self):
        return '/path/to/channel'

    def title(self):
        return 'Dub RSS Channel'


class DubRSSEntry(BaseRSSEntry):

    def created_on(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        return WithObjectsTestCase._rss_log_time_stamp

    def description(self):
        return 'My dub RSS entry.'

    def link(self):
        return '/path/to/entry'

    def title(self):
        return 'Dub RSS Entry'


class TestAllRSSChannel(LocalTestCase):

    def test__description(self):
        channel = AllRSSChannel()
        self.assertEqual(channel.description(), 'Recent activity on zco.mx.')

    def test__link(self):
        channel = AllRSSChannel()
        self.assertEqual(channel.link(), 'http://127.0.0.1:8000/zco.mx.rss')

    def test__title(self):
        channel = AllRSSChannel()
        self.assertEqual(channel.title(), 'zco.mx')


class TestBaseRSSChannel(WithObjectsTestCase):
    def test____init__(self):
        channel = BaseRSSChannel()
        self.assertTrue(channel)

    def test__description(self):
        channel = BaseRSSChannel()
        self.assertRaises(NotImplementedError, channel.description)

    def test__entries(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        channel = DubRSSChannel()
        channel._filter_query = (db.rss_log.id < 0)
        self.assertEqual(channel.entries(), [])

        channel._filter_query = (db.rss_log.id == self._rss_log.id)
        desc = 'The book My Book 001 by First Last has been set as completed.'
        self.assertEqual(
            channel.entries(),
            [{
                'created_on': datetime.datetime.strptime(
                    self._rss_log_time_stamp, '%Y-%m-%d %H:%M:%S'),
                'description': desc,
                'link': 'http://127.0.0.1:8000/FirstLast/MyBook-001/001',
                'title': 'My Book 001 by First Last',
            }]
        )

    def test__feed(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        channel = DubRSSChannel()
        channel._filter_query = (db.rss_log.id == self._rss_log.id)
        got = channel.feed()
        self.assertEqual(
            sorted(got.keys()),
            ['created_on', 'description', 'entries', 'image', 'link', 'title']
        )
        self.assertEqual(got['description'], 'My dub RSS channel.')
        desc = 'The book My Book 001 by First Last has been set as completed.'
        self.assertEqual(
            got['entries'],
            [{
                'created_on': datetime.datetime.strptime(
                    self._rss_log_time_stamp, '%Y-%m-%d %H:%M:%S'),
                'description': desc,
                'link': 'http://127.0.0.1:8000/FirstLast/MyBook-001/001',
                'title': 'My Book 001 by First Last',
            }]
        )
        self.assertEqual(got['link'], '/path/to/channel')
        self.assertEqual(got['title'], 'Dub RSS Channel')

    def test__filter_query(self):
        channel = BaseRSSChannel()
        got = str(channel.filter_query())
        regexp = re.compile(
            r"""
                \(
                rss_log.time_stamp
                \s
                >
                \s
                '(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'
                \)
            """,
            re.VERBOSE
        )
        self.assertRegexpMatches(got, regexp)
        m = re.match(regexp, got)
        if not m:
            self.fail('Time does not match regexp')
        as_time = datetime.datetime.strptime(
            m.group('time'), '%Y-%m-%d %H:%M:%S')
        expect = datetime.datetime.now() - datetime.timedelta(days=7)
        self.assertAlmostEqual(
            as_time,
            expect,
            delta=datetime.timedelta(minutes=1)
        )

    def test__image(self):
        channel = BaseRSSChannel()
        image = channel.image()
        self.assertTrue(isinstance(image, rss2.Image))
        self.assertEqual(
            image.url,
            'http://127.0.0.1:8000/zcomx/static/images/zco.mx-logo-small.png'
        )
        self.assertEqual(
            image.title,
            'zco.mx'
        )
        self.assertEqual(
            image.link,
            'http://127.0.0.1:8000/'
        )

    def test__link(self):
        channel = BaseRSSChannel()
        self.assertRaises(NotImplementedError, channel.link)

    def test__title(self):
        channel = BaseRSSChannel()
        self.assertRaises(NotImplementedError, channel.title)


class TestBaseRSSEntry(WithObjectsTestCase):
    def test____init__(self):
        entry = BaseRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertTrue(entry)

    def test__created_on(self):
        entry = BaseRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(entry.created_on(), self._rss_log_time_stamp)

    def test__description(self):
        entry = BaseRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'Entry for the book My Book 001 by First Last.'
        )

    def test__feed_item(self):
        entry = DubRSSEntry(self._book_page, datetime.datetime.now())
        got = entry.feed_item()
        self.assertEqual(
            sorted(got.keys()),
            ['created_on', 'description', 'link', 'title']
        )
        self.assertEqual(got['created_on'], self._rss_log_time_stamp)
        self.assertEqual(got['description'], 'My dub RSS entry.')
        self.assertEqual(got['link'], '/path/to/entry')
        self.assertEqual(got['title'], 'Dub RSS Entry')

    def test__link(self):
        entry = BaseRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )

        entry = BaseRSSEntry(self._book_page_2, self._rss_log_time_stamp)
        self.assertEqual(
            entry.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/002'
        )

    def test__title(self):
        entry = BaseRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.title(),
            'My Book 001 by First Last'
        )


class TestBaseRSSLog(LocalTestCase):

    def test____init__(self):
        log = BaseRSSLog({})
        self.assertTrue(log)

    def test__age(self):
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        record = {'time_stamp': time_stamp}

        as_of = time_stamp + datetime.timedelta(seconds=1)

        log = BaseRSSLog(record)
        got = log.age(as_of=as_of)
        self.assertEqual(got.total_seconds(), 1)

        log = BaseRSSLog({})
        self.assertRaises(SyntaxError, log.age)

    def test__delete(self):
        count = lambda x: db(db.rss_log.id == x).count()

        rss_log_record = self.add(db.rss_log, dict(
            book_id=-1,
            action='_test__delete_',
        ))

        rss_log = BaseRSSLog(rss_log_record.as_dict())
        self.assertEqual(count(rss_log_record.id), 1)

        rss_log.delete()
        self.assertEqual(count(rss_log_record.id), 0)

    def test__save(self):

        rss_log_data = dict(
            book_id=-1,
            action='_test__save_',
        )

        rss_log = BaseRSSLog(rss_log_data)
        record_id = rss_log.save()

        rss_log_record = db(db.rss_log.id == record_id).select().first()
        self.assertTrue(rss_log_record)
        self._objects.append(rss_log_record)
        self.assertEqual(rss_log_record.book_id, -1)
        self.assertEqual(rss_log_record.action, '_test__save_')


class TestBaseRSSPreLogSet(LocalTestCase):

    def test____init__(self):
        log_set = BaseRSSPreLogSet([])
        self.assertTrue(log_set)

    def test__as_rss_log(self):
        log_set = BaseRSSPreLogSet([])
        self.assertRaises(NotImplementedError, log_set.as_rss_log)

    def test__load(self):
        rss_pre_log = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='_test__load_',
        ))

        filters = {'book_id': -1}
        log_set = BaseRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], rss_pre_log.id)
        self.assertEqual(pre_log.record['book_id'], rss_pre_log.book_id)
        self.assertEqual(pre_log.record['action'], rss_pre_log.action)

        filters = {'book_id': -1, 'action': '_test__load_'}
        log_set = BaseRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], rss_pre_log.id)

        filters = {'book_id': -2}
        log_set = BaseRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 0)

        filters = {'book_id': -1, 'action': '_fake_'}
        log_set = BaseRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 0)

    def test__youngest(self):
        log_set = BaseRSSPreLogSet([])
        self.assertEqual(log_set.youngest(), None)

        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)
        rss_pre_logs = [
            RSSPreLog({
                'id': 1,
                'book_id': 1,
                'time_stamp': time_stamp,
            }),
            RSSPreLog({
                'id': 2,
                'book_id': 2,
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
            RSSPreLog({
                'id': 3,
                'book_id': 3,
                'time_stamp': time_stamp - datetime.timedelta(days=1),
            }),
        ]
        log_set = BaseRSSPreLogSet(rss_pre_logs)
        got = log_set.youngest()
        self.assertEqual(got.record['id'], 2)


class TestBookRSSChannel(WithObjectsTestCase):

    def test____init__(self):
        channel = BookRSSChannel(self._book)
        self.assertTrue(channel)

    def test__description(self):
        channel = BookRSSChannel(self._book)
        self.assertEqual(
            channel.description(),
            'Recent activity of My Book 001 by First Last on zco.mx.'
        )

    def test__filter_query(self):
        channel = BookRSSChannel(self._book)
        got = str(channel.filter_query())
        # ((rss_log.time_stamp > '2015-04-22 12:46:06')
        #     AND (rss_log.book_id = 10621))
        regexp = re.compile(
            r"""
                \(
                \(
                rss_log.time_stamp
                \s
                >
                \s
                '(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'
                \)
                \s
                AND
                \s
                \(rss_log.book_id\s=\s\d+\)
                \)
            """,
            re.VERBOSE
        )
        self.assertRegexpMatches(got, regexp)
        m = re.match(regexp, got)
        if not m:
            self.fail('Time does not match regexp')
        as_time = datetime.datetime.strptime(
            m.group('time'), '%Y-%m-%d %H:%M:%S')
        expect = datetime.datetime.now() - datetime.timedelta(days=30)
        self.assertAlmostEqual(
            as_time,
            expect,
            delta=datetime.timedelta(minutes=1)
        )

    def test__link(self):
        channel = BookRSSChannel(self._book)
        self.assertEqual(
            channel.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )

    def test__title(self):
        channel = BookRSSChannel(self._book)
        self.assertEqual(
            channel.title(),
            'My Book 001 by First Last on zco.mx'
        )


class TestCartoonistRSSChannel(WithObjectsTestCase):

    def test____init__(self):
        channel = CartoonistRSSChannel(self._creator)
        self.assertTrue(channel)

    def test__description(self):
        channel = CartoonistRSSChannel(self._creator)
        self.assertEqual(
            channel.description(),
            'Recent activity of First Last on zco.mx.'
        )

    def test__filter_query(self):
        channel = CartoonistRSSChannel(self._creator)
        got = str(channel.filter_query())
        # ((rss_log.time_stamp > '2015-04-22 12:46:06')
        #     AND (book.creator_id = 12345))
        regexp = re.compile(
            r"""
                \(
                \(
                rss_log.time_stamp
                \s
                >
                \s
                '(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'
                \)
                \s
                AND
                \s
                \(book.creator_id\s=\s\d+\)
                \)
            """,
            re.VERBOSE
        )
        self.assertRegexpMatches(got, regexp)
        m = re.match(regexp, got)
        if not m:
            self.fail('Time does not match regexp')
        as_time = datetime.datetime.strptime(
            m.group('time'), '%Y-%m-%d %H:%M:%S')
        expect = datetime.datetime.now() - datetime.timedelta(days=30)
        self.assertAlmostEqual(
            as_time,
            expect,
            delta=datetime.timedelta(minutes=1)
        )

    def test__link(self):
        channel = CartoonistRSSChannel(self._creator)
        self.assertEqual(
            channel.link(),
            'http://127.0.0.1:8000/FirstLast'
        )

    def test__title(self):
        channel = CartoonistRSSChannel(self._creator)
        self.assertEqual(
            channel.title(),
            'First Last on zco.mx'
        )


class TestCompletedRSSEntry(WithObjectsTestCase):

    def test_description(self):
        entry = CompletedRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'The book My Book 001 by First Last has been set as completed.'
        )


class TestCompletedRSSPreLogSet(LocalTestCase):

    def test__as_rss_log(self):
        time_stamp = datetime.datetime(2015, 1, 31, 12, 31, 59)

        # Empty set
        log_set = CompletedRSSPreLogSet([])
        self.assertEqual(log_set.as_rss_log(), None)

        # Set with single completed record.
        rss_pre_logs = [
            RSSPreLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = CompletedRSSPreLogSet(rss_pre_logs)
        got = log_set.as_rss_log()
        self.assertTrue(isinstance(got, RSSLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], -2)
        self.assertEqual(got.record['action'], 'completed')
        self.assertEqual(got.record['time_stamp'], time_stamp)

        # Set with multiple completed records.
        rss_pre_logs = [
            RSSPreLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': -2,
                'action': 'completed',
                'time_stamp': time_stamp,
            }),
            RSSPreLog({
                'id': 2,
                'book_id': -3,
                'book_page_id': -4,
                'action': 'completed',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
        ]
        log_set = CompletedRSSPreLogSet(rss_pre_logs)
        got = log_set.as_rss_log()
        self.assertTrue(isinstance(got, RSSLog))
        self.assertEqual(got.record['book_id'], -3)
        self.assertEqual(got.record['book_page_id'], -4)
        self.assertEqual(got.record['action'], 'completed')
        self.assertEqual(
            got.record['time_stamp'], time_stamp + datetime.timedelta(days=1))

    def test__load(self):
        completed_log = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = CompletedRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], completed_log.id)
        self.assertEqual(pre_log.record['book_id'], completed_log.book_id)
        self.assertEqual(pre_log.record['action'], completed_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'page added'}
        log_set = CompletedRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], page_added_log.id)
        self.assertEqual(pre_log.record['book_id'], page_added_log.book_id)
        self.assertEqual(pre_log.record['action'], page_added_log.action)


class TestPageAddedRSSEntry(WithObjectsTestCase):

    def test_description(self):
        entry = PageAddedRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'A page was added to the book My Book 001 by First Last.'
        )


class TestPageAddedRSSPreLogSet(LocalTestCase):

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
        log_set = PageAddedRSSPreLogSet([])
        self.assertEqual(log_set.as_book_pages(), [])

        rss_pre_logs = [
            RSSPreLog({
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
            }),
            RSSPreLog({
                'book_id': -1,
                'book_page_id': book_page_2.id,
                'action': 'page added',
            }),
        ]

        log_set = PageAddedRSSPreLogSet(rss_pre_logs)
        got = log_set.as_book_pages()
        self.assertEqual(got, [book_page_1, book_page_2])

    def test__as_rss_log(self):

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
        log_set = PageAddedRSSPreLogSet([])
        self.assertEqual(log_set.as_rss_log(), None)

        # Set with single page added record.
        rss_pre_logs = [
            RSSPreLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
        ]
        log_set = PageAddedRSSPreLogSet(rss_pre_logs)
        got = log_set.as_rss_log()
        self.assertTrue(isinstance(got, RSSLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], book_page_1.id)
        self.assertEqual(got.record['action'], 'page added')
        self.assertEqual(got.record['time_stamp'], time_stamp)

        # Set with multiple page added records.
        rss_pre_logs = [
            RSSPreLog({
                'id': 1,
                'book_id': -1,
                'book_page_id': book_page_1.id,
                'action': 'page added',
                'time_stamp': time_stamp,
            }),
            RSSPreLog({
                'id': 2,
                'book_id': -1,
                'book_page_id': book_page_2.id,
                'action': 'page added',
                'time_stamp': time_stamp + datetime.timedelta(days=1),
            }),
            RSSPreLog({
                'id': 2,
                'book_id': -1,
                'book_page_id': book_page_3.id,
                'action': 'page added',
                'time_stamp': time_stamp - datetime.timedelta(days=1),
            }),
        ]
        log_set = PageAddedRSSPreLogSet(rss_pre_logs)
        got = log_set.as_rss_log()
        self.assertTrue(isinstance(got, RSSLog))
        self.assertEqual(got.record['book_id'], -1)
        self.assertEqual(got.record['book_page_id'], book_page_3.id)
        self.assertEqual(got.record['action'], 'pages added')
        self.assertEqual(
            got.record['time_stamp'], time_stamp + datetime.timedelta(days=1))

    def test__load(self):
        completed_log = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='completed',
        ))

        page_added_log = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='page added',
        ))

        filters = {'book_id': -1}
        log_set = PageAddedRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], page_added_log.id)
        self.assertEqual(pre_log.record['book_id'], page_added_log.book_id)
        self.assertEqual(pre_log.record['action'], page_added_log.action)

        # Test: override action filter
        filters = {'book_id': -1, 'action': 'completed'}
        log_set = PageAddedRSSPreLogSet.load(filters=filters)
        self.assertEqual(len(log_set.rss_pre_logs), 1)
        pre_log = log_set.rss_pre_logs[0]
        self.assertEqual(pre_log.record['id'], completed_log.id)
        self.assertEqual(pre_log.record['book_id'], completed_log.book_id)
        self.assertEqual(pre_log.record['action'], completed_log.action)

    def test__rss_log_action(self):
        log_set = PageAddedRSSPreLogSet([])
        self.assertEqual(log_set.rss_log_action(), 'page added')

        log_set = PageAddedRSSPreLogSet([{}])
        self.assertEqual(log_set.rss_log_action(), 'page added')

        log_set = PageAddedRSSPreLogSet([{}, {}])
        self.assertEqual(log_set.rss_log_action(), 'pages added')


class TestPagesAddedRSSEntry(WithObjectsTestCase):

    def test_description(self):
        entry = PagesAddedRSSEntry(self._book_page, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'Several pages were added to the book My Book 001 by First Last.'
        )


class TestRSSLog(LocalTestCase):
    pass            # See BaseRSSLog


class TestRSSPreLog(LocalTestCase):

    def test_delete(self):
        count = lambda x: db(db.rss_pre_log.id == x).count()

        rss_pre_log_record = self.add(db.rss_pre_log, dict(
            book_id=-1,
            action='_test__delete_',
        ))

        rss_pre_log = RSSPreLog(rss_pre_log_record.as_dict())
        self.assertEqual(count(rss_pre_log_record.id), 1)

        rss_pre_log.delete()
        self.assertEqual(count(rss_pre_log_record.id), 0)

    def test_save(self):

        rss_pre_log_data = dict(
            book_id=-1,
            action='_test__save_',
        )

        rss_pre_log = RSSPreLog(rss_pre_log_data)
        record_id = rss_pre_log.save()

        rss_pre_log_record = \
            db(db.rss_pre_log.id == record_id).select().first()
        self.assertTrue(rss_pre_log_record)
        self._objects.append(rss_pre_log_record)
        self.assertEqual(rss_pre_log_record.book_id, -1)
        self.assertEqual(rss_pre_log_record.action, '_test__save_')


class TestRSSPreLogSet(LocalTestCase):

    def test__as_rss_log(self):
        log_set = RSSPreLogSet([])
        self.assertEqual(log_set.as_rss_log(), None)


class TestFunctions(WithObjectsTestCase):

    def test__channel_from_type(self):
        # Invalid channel
        self.assertRaises(SyntaxError, channel_from_type, '_fake_')

        # No record_id provided
        self.assertRaises(NotFoundError, channel_from_type, 'creator')
        self.assertRaises(NotFoundError, channel_from_type, 'book')

        got = channel_from_type('all')
        self.assertTrue(isinstance(got, AllRSSChannel))
        self.assertEqual(got.entity, None)

        got = channel_from_type('book', self._book.id)
        self.assertTrue(isinstance(got, BookRSSChannel))
        self.assertEqual(got.entity, self._book.id)

        got = channel_from_type('creator', self._creator.id)
        self.assertTrue(isinstance(got, CartoonistRSSChannel))
        self.assertEqual(got.entity, self._creator.id)

    def test__entry_class_from_action(self):
        self.assertEqual(
            entry_class_from_action('completed'), CompletedRSSEntry)
        self.assertEqual(
            entry_class_from_action('page added'), PageAddedRSSEntry)
        self.assertEqual(
            entry_class_from_action('pages added'), PagesAddedRSSEntry)
        self.assertRaises(NotFoundError, entry_class_from_action, None)
        self.assertRaises(NotFoundError, entry_class_from_action, '')
        self.assertRaises(NotFoundError, entry_class_from_action, '_fake_')

    def test__rss_log_as_entry(self):
        self.assertRaises(NotFoundError, rss_log_as_entry, None)
        self.assertRaises(NotFoundError, rss_log_as_entry, -1)

        for action in ['completed', 'page added', 'pages added']:
            self._rss_log.update_record(action=action)
            db.commit()
            got = rss_log_as_entry(self._rss_log)
            self.assertTrue(
                isinstance(got, entry_class_from_action(action))
            )
            self.assertEqual(got.book, self._book)
            self.assertEqual(str(got.time_stamp), self._rss_log_time_stamp)

    def test__rss_serializer_with_image(self):
        created_on = datetime.datetime(2015, 1, 31, 23, 30, 59)
        image = rss2.Image(
            'http://page.com',
            'My Image',
            'http://image.com',
        )
        feed = {
            'title': 'test__rss_serializer_with_image',
            'link': 'http://www.test.com',
            'description': 'My description',
            'image': image,
            'created_on': created_on,
            'entries': []
        }
        got = rss_serializer_with_image(feed)
        tag = TAG(got)
        self.assertEqual(
            tag.element('channel').element('title').components[0],
            feed['title']
        )
        # The link is formatted oddly. No idea why.
        # Should be
        #     <link>http://www.test.com</link>
        # Have
        #     <link />http://www.test.com
        self.assertEqual(
            str(tag.element('channel').element('link')),
            '<link />'
        )
        self.assertEqual(
            tag.element('channel').element('description').components[0],
            feed['description']
        )
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        self.assertEqual(
            tag.element('channel').element('lastbuilddate').components[0],
            rss2._format_date(created_on)
        )
        self.assertEqual(
            tag.element('channel')
            .element('image').element('url').components[0],
            'http://page.com'
        )
        self.assertEqual(
            tag.element('channel')
            .element('image').element('title').components[0],
            'My Image'
        )
        self.assertEqual(
            str(tag.element('channel').element('image').element('link')),
            '<link />'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
