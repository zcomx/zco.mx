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
    BookRSSChannel, \
    CartoonistRSSChannel, \
    CompletedRSSEntry, \
    PageAddedRSSEntry, \
    PagesAddedRSSEntry, \
    channel_from_args, \
    entry_class_from_action, \
    rss_log_as_entry
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    _auth_user = None
    _book = None
    _book_page = None
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

        self._rss_log = self.add(db.rss_log, dict(
            book_id=self._book.id,
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
        entry = BaseRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertTrue(entry)

    def test__created_on(self):
        entry = BaseRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(entry.created_on(), self._rss_log_time_stamp)

    def test__description(self):
        entry = BaseRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'Entry for the book My Book 001 by First Last.'
        )

    def test__feed_item(self):
        entry = DubRSSEntry(self._book, datetime.datetime.now())
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
        entry = BaseRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )

    def test__title(self):
        entry = BaseRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.title(),
            'My Book 001 by First Last'
        )


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
        entry = CompletedRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'The book My Book 001 by First Last has been set as completed.'
        )


class TestPageAddedRSSEntry(WithObjectsTestCase):

    def test_description(self):
        entry = PageAddedRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'A page was added to the book My Book 001 by First Last.'
        )


class TestPagesAddedRSSEntry(WithObjectsTestCase):

    def test_description(self):
        entry = PagesAddedRSSEntry(self._book, self._rss_log_time_stamp)
        self.assertEqual(
            entry.description(),
            'Several pages were added to the book My Book 001 by First Last.'
        )


class TestFunctions(WithObjectsTestCase):

    def test__channel_from_args(self):
        # Invalid channel
        self.assertRaises(SyntaxError, channel_from_args, '_fake_')

        # No record_id provided
        self.assertRaises(NotFoundError, channel_from_args, 'creator')
        self.assertRaises(NotFoundError, channel_from_args, 'book')

        got = channel_from_args('all')
        self.assertTrue(isinstance(got, AllRSSChannel))
        self.assertEqual(got.entity, None)

        got = channel_from_args('book', self._book.id)
        self.assertTrue(isinstance(got, BookRSSChannel))
        self.assertEqual(got.entity, self._book.id)

        got = channel_from_args('creator', self._creator.id)
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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
