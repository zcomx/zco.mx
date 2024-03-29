#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/events.py
"""
import datetime
import unittest
from gluon import *
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import (
    Book,
    update_rating,
)
from applications.zcomx.modules.creators import AuthUser
from applications.zcomx.modules.events import (
    BaseEvent,
    BookEvent,
    BookView,
    Contribution,
    ContributionEvent,
    Download,
    DownloadClick,
    DownloadEvent,
    Rating,
    RatingEvent,
    ViewEvent,
    ZcoContributionEvent,
    is_loggable,
    log_download_click,
)
from applications.zcomx.modules.user_agents import USER_AGENTS
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring
# pylint: disable=protected-access


class EventTestCase(LocalTestCase):
    """ Base class for Event test cases. Sets up test data."""
    _book = None
    _user = None

    # pylint: disable=invalid-name
    def setUp(self):
        book_row = self.add(Book, dict(name='Event Test Case'))
        self._book = Book.from_id(book_row.id)
        self._user = AuthUser.from_key(dict(email=web.username))

    def _set_pages(self, book, num_of_pages):
        set_pages(self, book, num_of_pages)


class TestBaseEvent(EventTestCase):
    def test____init__(self):
        event = BaseEvent(self._user.id)
        self.assertTrue(event)

    def test_log(self):
        event = BaseEvent(self._user.id)
        self.assertRaises(NotImplementedError, event._log, None)

    def test__log(self):

        class SubBaseEvent(BaseEvent):

            def __init__(self, user_id):
                BaseEvent.__init__(self, user_id)
                self.actions = []

            def _log(self, value=None):
                self.actions.append(value)

            def _post_log(self):
                self.actions.append('post_log')

        event = SubBaseEvent(self._user.id)
        event.log(value='log_me')
        self.assertEqual(event.actions, ['log_me', 'post_log'])

    def test_post_log(self):
        event = BaseEvent(self._user.id)
        self.assertRaises(NotImplementedError, event._post_log)


class TestBookEvent(EventTestCase):
    def test____init__(self):
        event = BookEvent(self._book, self._user.id)
        self.assertTrue(event)
        self.assertEqual(event.book.name, self._book.name)


class TestContributionEvent(EventTestCase):

    def test_log(self):
        self._set_pages(self._book, 10)
        update_rating(self._book)
        event = ContributionEvent(self._book, self._user.id)

        # no value
        event_id = event._log()
        self.assertFalse(event_id)

        event_id = event._log(123.45)
        contribution = Contribution.from_id(event_id)
        self.assertEqual(contribution.id, event_id)
        self.assertEqual(contribution.book_id, self._book.id)
        self.assertAlmostEqual(
            contribution.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self.assertEqual(contribution.amount, 123.45)
        self._objects.append(contribution)

    def test_post_log(self):
        self._set_pages(self._book, 10)
        update_rating(self._book)
        book = Book.from_id(self._book.id)      # Re-load
        self.assertAlmostEqual(book.contributions, 0.00)
        self.assertAlmostEqual(book.contributions_remaining, 100.00)

        event = ContributionEvent(self._book, self._user.id)

        event_id = event._log(123.45)
        contribution = Contribution.from_id(event_id)
        self._objects.append(contribution)

        event._post_log()
        book = Book.from_id(self._book.id)      # Re-load
        self.assertAlmostEqual(book.contributions, 123.45)
        self.assertAlmostEqual(book.contributions_remaining, 0.00)


class TestDownloadEvent(EventTestCase):

    def test_log(self):
        update_rating(self._book)
        book = Book.from_id(self._book.id)      # Re-load

        download_click = self.add(DownloadClick, dict(
            record_table='book',
            record_id=book.id,
        ))

        event = DownloadEvent(self._book, self._user.id)
        event_id = event._log(value=download_click)

        download = Download.from_id(event_id)
        self.assertEqual(download.id, event_id)
        self.assertEqual(download.book_id, self._book.id)
        self.assertEqual(download.download_click_id, download_click.id)
        self.assertAlmostEqual(
            download.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self._objects.append(download)

    def test_post_log(self):
        # This does nothing, test that.
        event = DownloadEvent(self._book, self._user.id)
        event._post_log()


class TestRatingEvent(EventTestCase):

    def test_log(self):
        update_rating(self._book)
        event = RatingEvent(self._book, self._user.id)

        # no value
        event_id = event._log()
        self.assertFalse(event_id)

        event_id = event._log(5)
        rating = Rating.from_id(event_id)
        self.assertEqual(rating.id, event_id)
        self.assertEqual(rating.book_id, self._book.id)
        self.assertAlmostEqual(
            rating.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self.assertEqual(rating.amount, 5)
        self._objects.append(rating)

    def test_post_log(self):
        update_rating(self._book)
        book = Book.from_id(self._book.id)       # Re-load
        self.assertEqual(book.rating, 0)

        event = RatingEvent(self._book, self._user.id)

        event_id = event._log(5)
        rating = Rating.from_id(event_id)
        self._objects.append(rating)

        event._post_log()
        book = Book.from_id(self._book.id)       # Re-load
        self.assertEqual(book.rating, 5)


class TestViewEvent(EventTestCase):

    def test_log(self):
        update_rating(self._book)
        event = ViewEvent(self._book, self._user.id)
        event_id = event._log()

        view = BookView.from_id(event_id)
        self.assertEqual(view.id, event_id)
        self.assertEqual(view.book_id, self._book.id)
        self.assertAlmostEqual(
            view.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self._objects.append(view)

    def test_post_log(self):
        update_rating(self._book)
        book = Book.from_id(self._book.id)       # Re-load
        self.assertEqual(book.views, 0)

        event = ViewEvent(self._book, self._user.id)

        event_id = event._log()
        view = BookView.from_id(event_id)
        self._objects.append(view)

        event._post_log()
        book = Book.from_id(self._book.id)       # Re-load
        self.assertEqual(book.views, 1)


class TestZcoContributionEvent(EventTestCase):

    def test_log(self):
        self._set_pages(self._book, 10)
        update_rating(self._book)
        event = ZcoContributionEvent(self._user.id)

        # no value
        event_id = event._log()
        self.assertFalse(event_id)

        event_id = event._log(123.45)
        contribution = Contribution.from_id(event_id)
        self.assertEqual(contribution.id, event_id)
        self.assertEqual(contribution.book_id, 0)
        self.assertAlmostEqual(
            contribution.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self.assertEqual(contribution.amount, 123.45)
        self._objects.append(contribution)

    def test_post_log(self):
        # This does nothing, test that.
        event = ZcoContributionEvent(self._user.id)
        event._post_log()


class TestFunctions(LocalTestCase):
    def test__is_loggable(self):
        now = request.now

        # Test 'all'
        download_click_all = self.add(DownloadClick, dict(
            ip_address='999.999.999.999',
            auth_user_id=1,
            record_table='all',
            record_id=999,
            is_bot=False,
            loggable=True,
            time_stamp=now,
        ))
        self.assertFalse(is_loggable(download_click_all.id))

        # Test is_bot=True
        download_click_all = self.add(DownloadClick, dict(
            ip_address='999.999.999.999',
            auth_user_id=1,
            record_table='_table_1_',
            record_id=999,
            is_bot=True,
            loggable=True,
            time_stamp=now,
        ))
        self.assertFalse(is_loggable(download_click_all.id))

        # Test non-all
        download_click_1 = self.add(DownloadClick, dict(
            ip_address='111.111.111.111',
            auth_user_id=1,
            record_table='_table_1_',
            record_id=111,
            is_bot=False,
            loggable=True,
            time_stamp=now,
        ))

        # Test: should not match itself.
        self.assertTrue(is_loggable(download_click_1.id))

        # Test: identical record should not be loggable.
        click_2 = dict(
            ip_address='111.111.111.111',
            auth_user_id=1,
            record_table='_table_1_',
            record_id=111,
            is_bot=False,
            loggable=True,
            time_stamp=now,
        )

        download_click_2 = self.add(DownloadClick, dict(click_2))
        self.assertFalse(is_loggable(download_click_2.id))

        # If first record is not loggable, then should be loggable.
        download_click_1 = DownloadClick.from_updated(
            download_click_1, dict(loggable=False))
        self.assertTrue(is_loggable(download_click_2.id))

        # Reset
        download_click_1 = DownloadClick.from_updated(
            download_click_1, dict(loggable=True))
        self.assertFalse(is_loggable(download_click_2.id))

        def test_mismatch(dl_click, change):
            click_2_changed = dict(click_2)
            click_2_changed.update(change)
            dl_click = DownloadClick.from_updated(dl_click, click_2_changed)
            self.assertTrue(is_loggable(dl_click.id))

        # Test mismatching each field in query
        test_mismatch(download_click_2, dict(ip_address='222.222.222.222'))
        test_mismatch(download_click_2, dict(auth_user_id=2))
        test_mismatch(download_click_2, dict(record_table='_table_2_'))
        test_mismatch(download_click_2, dict(record_id=222))

        # Reset
        download_click_2 = DownloadClick.from_updated(
            download_click_2, click_2)
        self.assertFalse(is_loggable(download_click_2.id))

        # Test interval seconds.
        def set_time_stamp(dl_click, increment_seconds):
            click_2_changed = dict(click_2)
            click_2_changed.update(dict(
                time_stamp=(
                    now + datetime.timedelta(seconds=increment_seconds))
            ))
            DownloadClick.from_updated(dl_click, click_2_changed)

        set_time_stamp(download_click_2, 1)
        self.assertFalse(is_loggable(download_click_2.id, interval_seconds=5))

        set_time_stamp(download_click_2, 4)
        self.assertFalse(is_loggable(download_click_2.id, interval_seconds=5))

        set_time_stamp(download_click_2, 5)
        self.assertTrue(is_loggable(download_click_2.id, interval_seconds=5))

        set_time_stamp(download_click_2, 6)
        self.assertTrue(is_loggable(download_click_2.id, interval_seconds=5))

    def test__log_download_click(self):
        test_ip = '000.111.111.333'
        current.session._user_agent = None
        current.request.env.http_user_agent = USER_AGENTS.non_bot
        current.request.client = test_ip

        query = (db.download_click.ip_address == test_ip)
        db(query).delete()
        db.commit()

        click_id = log_download_click('book', 0, queue_log_downloads=False)
        download_click = DownloadClick.from_id(click_id)
        self.assertTrue(download_click)
        self.assertEqual(download_click.ip_address, test_ip)
        self.assertEqual(download_click.loggable, is_loggable(download_click))
        self.assertEqual(download_click.completed, False)
        self._objects.append(download_click)

        click_id_2 = log_download_click('book', 0, queue_log_downloads=False)
        download_click_2 = DownloadClick.from_id(click_id_2)
        self.assertEqual(download_click_2.ip_address, test_ip)
        self.assertEqual(download_click_2.loggable, False)
        self.assertEqual(download_click_2.completed, True)
        self._objects.append(download_click_2)

        # Test invalid record_table.
        got = log_download_click('_invalid_', 0, queue_log_downloads=False)
        self.assertEqual(got, 0)

def set_pages(obj, book, num_of_pages):
    """Create pages for a book."""
    while book.page_count() < num_of_pages:
        obj.add(BookPage, dict(
            book_id=book.id,
            page_no=(book.page_count() + 1),
        ))


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
