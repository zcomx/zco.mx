#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/zco.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import \
    BOOK_STATUSES, \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT, \
    NICES, \
    IN_PROGRESS, \
    SITE_NAME, \
    TUMBLR_USERNAME, \
    TWITTER_BOT_HANDLE, \
    Zco, \
    html_metadata

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestZco(LocalTestCase):

    def test____init__(self):
        env = globals()
        session = env['session']
        self.assertTrue('zco' not in session.keys())
        Zco()
        self.assertTrue('zco' in session.keys())

    def test_next_url(self):
        Zco().next_url = 'http://www.aaa.com'
        self.assertEqual(Zco().next_url, 'http://www.aaa.com')
        Zco().next_url = 'http://www.bbb.com'
        self.assertEqual(Zco().next_url, 'http://www.bbb.com')
        del Zco().next_url
        self.assertEqual(Zco().next_url, None)

    def test__get_next_url(self):
        pass        # tested in test_next_url

    def test__set_next_url(self):
        pass        # tested in test_next_url

    def test__del_next_url(self):
        pass        # tested in test_next_url

    def test_paypal_in_progress(self):
        Zco().paypal_in_progress = True
        self.assertEqual(Zco().paypal_in_progress, True)
        Zco().paypal_in_progress = False
        self.assertEqual(Zco().paypal_in_progress, False)
        del Zco().paypal_in_progress
        self.assertEqual(Zco().paypal_in_progress, None)

    def test__get_paypal_in_progress(self):
        pass        # tested in test_paypal_in_progress

    def test__set_paypal_in_progress(self):
        pass        # tested in test_paypal_in_progress

    def test__del_paypal_in_progress(self):
        pass        # tested in test_paypal_in_progress

    def test__all_rss_url(self):
        self.assertEqual(
            Zco().all_rss_url,
            {'c': 'zco.mx.rss', 'f': 'index'}
        )
        self.assertEqual(
            URL(**Zco().all_rss_url),
            '/zco.mx.rss'
        )

    def test__all_torrent_url(self):
        self.assertEqual(
            Zco().all_torrent_url,
            {'c': 'zco.mx.torrent', 'f': 'index'}
        )
        self.assertEqual(
            URL(**Zco().all_torrent_url),
            '/zco.mx.torrent'
        )


class TestConstants(LocalTestCase):
    def test_constants(self):
        self.assertEqual(BOOK_STATUS_ACTIVE, 'a')
        self.assertEqual(BOOK_STATUS_DISABLED, 'x')
        self.assertEqual(BOOK_STATUS_DRAFT, 'd')
        self.assertEqual(
            sorted(BOOK_STATUSES),
            ['a', 'd', 'x']
        )

        self.assertEqual(
            sorted(NICES.keys()),
            [
                'indicia',
                'mktorrent',
                'optimize',
                'resize',
                'zc-p2p',
                'zip',
            ]
        )
        for v in NICES.values():
            self.assertTrue(v <= 19)
            self.assertTrue(v >= 10)

        self.assertEqual(IN_PROGRESS, '__in_progress__')
        self.assertEqual(SITE_NAME, 'zco.mx')
        self.assertEqual(TUMBLR_USERNAME, 'zcomx')
        self.assertEqual(TWITTER_BOT_HANDLE, '@zcomx_bot')


class TestFunctions(LocalTestCase):

    def test__html_metadata(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        expect = {
            'name': 'zco.mx',
            'title': 'zco.mx',
            'description': (
                'zco.mx is a curated not-for-profit comic-sharing website'
                ' for self-publishing cartoonists and their readers.'
            ),
            'icon': 'http://127.0.0.1:8000/zcomx/static/images/zco.mx-logo-small.png',
            'twitter': '@zcomx_bot',
            'type': '',
            'url': 'http://127.0.0.1:8000/',
        }
        self.assertEqual(html_metadata(), expect)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
