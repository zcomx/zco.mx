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
    activity_log_as_rss_entry, \
    channel_from_type, \
    entry_class_from_action, \
    rss_serializer_with_image
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    _activity_log = None
    _activity_log_time_stamp = '1999-12-31 12:30:59'
    _auth_user = None
    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None

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

        self._activity_log = self.add(db.activity_log, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id],
            action='completed',
            time_stamp=datetime.datetime.strptime(
                self._activity_log_time_stamp, '%Y-%m-%d %H:%M:%S'),
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
        return WithObjectsTestCase._activity_log_time_stamp

    def description_fmt(self):
        return 'A book {b} by {c}.'

    def guid(self):
        return 'guid-001'

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
        channel._filter_query = (db.activity_log.id < 0)
        self.assertEqual(channel.entries(), [])

        channel._filter_query = (db.activity_log.id == self._activity_log.id)
        got = channel.entries()
        self.assertEqual(len(got), 1)

        entry = got[0]
        self.assertEqual(
            sorted(entry.keys()),
            ['created_on', 'description', 'guid', 'link', 'title']
        )

        self.assertEqual(
            entry['created_on'],
            datetime.datetime.strptime(
                self._activity_log_time_stamp, '%Y-%m-%d %H:%M:%S'
            )
        )

        desc = 'The book My Book 001 by First Last has been set as completed.'
        self.assertEqual(entry['description'], desc)

        self.assertTrue(isinstance(entry['guid'], rss2.Guid))
        self.assertEqual(entry['guid'].guid, str(self._activity_log.id))
        self.assertFalse(entry['guid'].isPermaLink)

        self.assertEqual(
            entry['link'],
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )
        self.assertEqual(entry['title'], 'My Book 001 by First Last')

    def test__feed(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        channel = DubRSSChannel()
        channel._filter_query = (db.activity_log.id == self._activity_log.id)
        got = channel.feed()
        self.assertEqual(
            sorted(got.keys()),
            ['created_on', 'description', 'entries', 'image', 'link', 'title']
        )
        self.assertEqual(got['description'], 'My dub RSS channel.')

        self.assertEqual(len(got['entries']), 1)

        entry = got['entries'][0]
        self.assertEqual(
            sorted(entry.keys()),
            ['created_on', 'description', 'guid', 'link', 'title']
        )

        self.assertEqual(
            entry['created_on'],
            datetime.datetime.strptime(
                self._activity_log_time_stamp, '%Y-%m-%d %H:%M:%S'
            )
        )

        desc = 'The book My Book 001 by First Last has been set as completed.'
        self.assertEqual(entry['description'], desc)

        self.assertTrue(isinstance(entry['guid'], rss2.Guid))
        self.assertEqual(entry['guid'].guid, str(self._activity_log.id))
        self.assertFalse(entry['guid'].isPermaLink)

        self.assertEqual(
            entry['link'],
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )
        self.assertEqual(entry['title'], 'My Book 001 by First Last')

    def test__filter_query(self):
        channel = BaseRSSChannel()
        got = str(channel.filter_query())
        regexp = re.compile(
            r"""
                \(
                activity_log.time_stamp
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
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertTrue(entry)

    def test__created_on(self):
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(entry.created_on(), self._activity_log_time_stamp)

    def test__description(self):
        entry = DubRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description(),
            'A book My Book 001 by First Last.'
        )

    def test__description_fmt(self):
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertRaises(NotImplementedError, entry.description_fmt)

    def test__feed_item(self):
        # The time_stamp and activity_log_id args to DubRSSEntry are irrelevant
        # for this test as the overriden methods determine the feed_item
        # values.
        entry = DubRSSEntry([self._book_page.id], '', 0)
        got = entry.feed_item()
        self.assertEqual(
            sorted(got.keys()),
            ['created_on', 'description', 'guid', 'link', 'title']
        )
        self.assertEqual(
            got,
            {
                'created_on': self._activity_log_time_stamp,
                'description': 'A book My Book 001 by First Last.',
                'guid': 'guid-001',
                'link': '/path/to/entry',
                'title': 'Dub RSS Entry',
            }
        )

    def test__first_of_pages(self):

        book = self.add(db.book, dict(
            name='test__first_of_pages',
            creator_id=self._creator.id,
        ))

        # Test single page
        book_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=999,
        ))

        entry = BaseRSSEntry(
            [book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(entry.first_of_pages(), book_page)

        # Test multiple pages
        book_page_2 = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=666,
        ))

        book_page_3 = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=777,
        ))

        page_ids = [
            book_page.id,
            book_page_2.id,
            book_page_3.id,
        ]
        entry = BaseRSSEntry(
            page_ids,
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(entry.first_of_pages(), book_page_2)

    def test__guid(self):
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            123,
        )
        guid = entry.guid()
        self.assertTrue(isinstance(guid, rss2.Guid))
        self.assertEqual(guid.guid, '123')
        self.assertFalse(guid.isPermaLink)

    def test__link(self):
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/001'
        )

        entry = BaseRSSEntry(
            [self._book_page_2.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.link(),
            'http://127.0.0.1:8000/FirstLast/MyBook-001/002'
        )

    def test__title(self):
        entry = BaseRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
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
        # ((activity_log.time_stamp > '2015-04-22 12:46:06')
        #     AND (activity_log.book_id = 10621))
        regexp = re.compile(
            r"""
                \(
                \(
                activity_log.time_stamp
                \s
                >
                \s
                '(?P<time>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'
                \)
                \s
                AND
                \s
                \(activity_log.book_id\s=\s\d+\)
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
        # ((activity_log.time_stamp > '2015-04-22 12:46:06')
        #     AND (book.creator_id = 12345))
        regexp = re.compile(
            r"""
                \(
                \(
                activity_log.time_stamp
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
        entry = CompletedRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description(),
            'The book My Book 001 by First Last has been set as completed.'
        )

    def test__description_fmt(self):
        entry = CompletedRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description_fmt(),
            'The book {b} by {c} has been set as completed.'
        )


class TestPageAddedRSSEntry(WithObjectsTestCase):

    def test_description(self):

        # Single page
        entry = PageAddedRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description(),
            'A page was added to the book My Book 001 by First Last.'
        )

        # Multiple pages
        entry = PageAddedRSSEntry(
            [self._book_page.id, self._book_page_2.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description(),
            'Several pages were added to the book My Book 001 by First Last.'
        )

    def test__description_fmt(self):
        entry = PageAddedRSSEntry(
            [self._book_page.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description_fmt(),
            'A page was added to the book {b} by {c}.'
        )

        entry = PageAddedRSSEntry(
            [self._book_page.id, self._book_page_2.id],
            self._activity_log_time_stamp,
            self._activity_log.id
        )
        self.assertEqual(
            entry.description_fmt(),
            'Several pages were added to the book {b} by {c}.'
        )


class TestFunctions(WithObjectsTestCase):

    def test__activity_log_as_rss_entry(self):
        self.assertRaises(NotFoundError, activity_log_as_rss_entry, None)
        self.assertRaises(NotFoundError, activity_log_as_rss_entry, -1)

        for action in ['completed', 'page added']:
            self._activity_log.update_record(action=action)
            db.commit()
            got = activity_log_as_rss_entry(self._activity_log)
            self.assertTrue(
                isinstance(got, entry_class_from_action(action))
            )
            self.assertEqual(got.book, self._book)
            self.assertEqual(
                str(got.time_stamp), self._activity_log_time_stamp)
            self.assertEqual(got.activity_log_id, self._activity_log.id)

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
        self.assertRaises(NotFoundError, entry_class_from_action, None)
        self.assertRaises(NotFoundError, entry_class_from_action, '')
        self.assertRaises(NotFoundError, entry_class_from_action, '_fake_')

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
            'entries': [
                {
                    'title': 'My Title',
                    'link': 'http://my_link.com',
                    'description': 'The description',
                    'guid': 'guid-999',
                    'created_on': '1999-12-31 12:30:59',
                }
            ]
        }
        got = rss_serializer_with_image(feed)
        # <?xml version="1.0" encoding="utf-8"?>
        #   <rss version="2.0">
        #     <channel>
        #       <title>test__rss_serializer_with_image</title>
        #       <link>http://www.test.com</link>
        #       <description>My description</description>
        #       <lastBuildDate>Sat, 31 Jan 2015 23:30:59 GMT</lastBuildDate>
        #       <generator>PyRSS2Gen-1.1.0</generator>
        #       <docs>http://blogs.law.harvard.edu/tech/rss</docs>
        #       <image>
        #         <url>http://page.com</url>
        #         <title>My Image</title>
        #         <link>http://image.com</link>
        #       </image>
        #       <item>
        #         <title>My Title</title>
        #         <link>http://my_link.com</link>
        #         <description>The description</description>
        #         <guid>guid-999</guid>
        #         <pubDate>1999-12-31 12:30:59</pubDate>
        #       </item>
        #     </channel>
        #   </rss>

        tag = TAG(got)
        self.assertEqual(
            tag.element('channel').element('title').components[0],
            feed['title']
        )
        # The link is formatted oddly by TAG. No idea why.
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

        image = tag.element('channel').element('image')
        self.assertEqual(
            image.element('url').components[0],
            'http://page.com'
        )
        self.assertEqual(
            image.element('title').components[0],
            'My Image'
        )
        self.assertEqual(
            str(image.element('link')),
            '<link />'
        )

        item = tag.element('channel').element('item')
        self.assertEqual(
            item.element('title').components[0],
            'My Title'
        )
        self.assertEqual(
            str(image.element('link')),
            '<link />'
        )
        self.assertEqual(
            item.element('description').components[0],
            'The description'
        )
        self.assertEqual(
            item.element('guid').components[0],
            'guid-999'
        )
        self.assertEqual(
            item.element('pubdate').components[0],
            '1999-12-31 12:30:59'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
