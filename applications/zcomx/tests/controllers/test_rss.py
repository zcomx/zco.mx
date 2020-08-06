#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/rss.py

"""
import datetime
import os
import unittest
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import \
    Book, \
    book_name
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.helpers import WebTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase, ImageTestCase):

    _creator = None
    _book = None
    _book_page = None
    _activity_log_time_stamp = datetime.datetime.now()
    _activity_log_time_stamp_str = datetime.datetime.strftime(
        _activity_log_time_stamp, '%b %d, %Y')

    def setUp(self):
        self._auth_user = self.add(AuthUser, dict(
            name='First Last',
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email='test_rss@example.com',
            name_for_url='FirstLast',
        ))

        self._book = self.add(Book, dict(
            name='Test RSS',
            creator_id=self._creator.id,
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestRss',
        ))

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        self.add(ActivityLog, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id],
            action='page added',
            time_stamp=self._activity_log_time_stamp,
        ))

        super(TestFunctions, self).setUp()

    def test__modal(self):
        self.assertWebTest('/rss/modal')

    def test__route(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        filename = 'file.jpg'
        self._set_image(
            db.book_page.image,
            self._book_page,
            self._prep_image(filename),
            resizer=ResizerQuick
        )

        # Test cartoonist rss
        expect = []
        expect.append('<title>zco.mx: First Last</title>')
        expect.append('<description>Recent activity of First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertWebTest(
            '/rss/route?&rss={rss}'.format(
                rss=os.path.basename(self._creator.name_for_url),
            ),
            match_page_key='/rss/rss',
            match_strings=expect,
        )

        # Test book rss, creator as id
        expect = []
        expect.append(self._book.name)
        expect.append('<title>zco.mx: Test RSS by First Last</title>')
        expect.append('<description>Recent activity of Test RSS by First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertWebTest(
            '/rss/route?&creator={cid:03d}&rss={rss}'.format(
                cid=self._creator.id,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/rss/rss',
            match_strings=expect,
        )

        # Test book rss, creator as name
        expect = []
        expect.append(self._book.name)
        expect.append('<title>zco.mx: Test RSS by First Last</title>')
        expect.append('<description>Recent activity of Test RSS by First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertWebTest(
            '/rss/route?&creator={name}&rss={rss}'.format(
                name=self._creator.name_for_url,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/rss/rss',
            match_strings=expect,
        )

        # Test 'all' rss
        expect = []
        expect.append('<title>zco.mx</title>')
        expect.append('<description>Recent activity on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertWebTest(
            '/rss/route?&rss=zco.mx.rss',
            match_page_key='/rss/rss',
            match_strings=expect,
        )

        # page not found: no args
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/rss/route',
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid creator integer
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/rss/route/{cid:03d}/{rss}?'.format(
                cid=-1,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid creator name
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/rss/route/{name}/{rss}?'.format(
                name='_invalid_name_',
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            match_page_key='/errors/page_not_found',
        )

        # page not found: invalid rss
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/rss/route/_invalid_.rss',
            match_page_key='/errors/page_not_found',
        )

    def test__widget(self):
        self.assertWebTest('/rss/widget.load')

        # With creator
        self.assertWebTest(
            '/rss/widget.load/{cid}'.format(
                cid=self._creator.id,
            ),
            match_page_key='/rss/widget.load',
            match_strings=['Follow all works by First Last'],
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
