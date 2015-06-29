#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/rss.py

"""
import datetime
import os
import unittest
from applications.zcomx.modules.book_types import by_name as book_type_by_name
from applications.zcomx.modules.books import book_name
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None
    _book = None
    _book_page = None
    _activity_log_time_stamp = datetime.datetime.now()
    _activity_log_time_stamp_str = datetime.datetime.strftime(
        _activity_log_time_stamp, '%b %d, %Y')

    titles = {
        'modal': '<div id="rss_modal">',
        'page_not_found': '<h3>Page not found</h3>',
        'rss': [
            '<?xml version="1.0"',
            '<rss version="2.0">',
        ],
        'widget': '<div class="rss_widget_body">',
    }
    url = '/zcomx/rss'

    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

        self._auth_user = self.add(db.auth_user, dict(
            name='First Last',
        ))

        self._creator = self.add(db.creator, dict(
            auth_user_id=self._auth_user.id,
            email='test_rss@example.com',
            name_for_url='FirstLast',
        ))

        self._book = self.add(db.book, dict(
            name='Test RSS',
            creator_id=self._creator.id,
            book_type_id=book_type_by_name('one-shot').id,
            name_for_url='TestRss',
        ))

        self._book_page = self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        self.add(db.activity_log, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id],
            action='page added',
            time_stamp=self._activity_log_time_stamp,
        ))

    def test__modal(self):
        self.assertTrue(
            web.test(
                '{url}/modal'.format(url=self.url),
                self.titles['modal']
            )
        )

    def test__route(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        # Test cartoonist rss
        expect = []
        expect.extend(self.titles['rss'])
        expect.append('<title>zco.mx: First Last</title>')
        expect.append('<description>Recent activity of First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertTrue(web.test(
            '{url}/route?&rss={rss}'.format(
                url=self.url,
                rss=os.path.basename(self._creator.name_for_url),
            ),
            expect
        ))

        # Test book rss, creator as id
        expect = []
        expect.extend(self.titles['rss'])
        expect.append(self._book.name)
        expect.append('<title>zco.mx: Test RSS by First Last</title>')
        expect.append('<description>Recent activity of Test RSS by First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertTrue(web.test(
            '{url}/route?&creator={cid:03d}&rss={rss}'.format(
                url=self.url,
                cid=self._creator.id,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))

        # Test book rss, creator as name
        expect = []
        expect.extend(self.titles['rss'])
        expect.append(self._book.name)
        expect.append('<title>zco.mx: Test RSS by First Last</title>')
        expect.append('<description>Recent activity of Test RSS by First Last on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertTrue(web.test(
            '{url}/route?&creator={name}&rss={rss}'.format(
                url=self.url,
                name=self._creator.name_for_url,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            expect
        ))

        # Test 'all' rss
        expect = []
        expect.extend(self.titles['rss'])
        expect.append('<title>zco.mx</title>')
        expect.append('<description>Recent activity on zco.mx.</description>')
        expect.append("<title>'Test RSS' p01 by First Last</title>")
        expect.append("<description>Posted: {d} - A page was added to the book 'Test RSS' by First Last.</description>".format(
            d=self._activity_log_time_stamp_str))
        self.assertTrue(web.test(
            '{url}/route?&rss=zco.mx.rss'.format(
                url=self.url),
            expect
        ))

        web.sessions = {}    # Prevent 'Changed session ID' warnings.

        # page not found: no args
        self.assertTrue(web.test(
            '{url}/route?'.format(url=self.url),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator integer
        self.assertTrue(web.test(
            '{url}/route/{cid:03d}/{rss}?'.format(
                url=self.url,
                cid=-1,
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid creator name
        self.assertTrue(web.test(
            '{url}/route/{name}/{rss}?'.format(
                url=self.url,
                name='_invalid_name_',
                rss='{n}.rss'.format(n=book_name(self._book, use='url'))
            ),
            self.titles['page_not_found']
        ))

        # page not found: invalid rss
        self.assertTrue(web.test(
            '{url}/route/{rss}?'.format(
                url=self.url,
                rss='_invalid_.rss',
            ),
            self.titles['page_not_found']
        ))

    def test__widget(self):
        self.assertTrue(
            web.test(
                '{url}/widget.load'.format(url=self.url),
                self.titles['widget']
            )
        )

        # With creator
        expect = []
        expect.extend(self.titles['widget'])
        expect.append('Follow all works by First Last')
        self.assertTrue(
            web.test(
                '{url}/widget.load/{cid}'.format(
                    url=self.url,
                    cid=self._creator.id,
                ),
                expect,
            )
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
