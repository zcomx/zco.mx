#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zco.mx routing.
This tests nginx settings on the live server.
"""
import unittest
import requests
from requests.exceptions import SSLError
from applications.zcomx.modules.tests.helpers import skip_if_quick
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestFunctions(LocalTestCase):

    titles = {
        'creator': [
            '<div id="creator_page">',
            '<h1>Charles Forsman</h1>',
        ],
        'index': '<div id="front_page">',
    }

    # pylint: disable=invalid-name
    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

    @skip_if_quick
    def test_routes(self):
        # JK 2025-05-29 Since implementing cloudflare, some of these tests
        # are no longer reliable. Results change every run of test.
        return

        tests = [
            # (url, verify ssl cert, expect title)
            ('http://zco.mx', False, 'index'),
            ('https://zco.mx', False, 'index'),
            ('http://dev.zco.mx', False, 'index'),
            ('https://dev.zco.mx', False, 'index'),
            ('http://www.zco.mx', False, 'index'),
            ('https://www.zco.mx', False, 'index'),
            ('http://fake.zco.mx', False, 'index'),
            ('https://fake.zco.mx', False, 'index'),
            ('http://101.zco.mx', False, 'creator'),
            ('https://101.zco.mx', False, 'creator'),
            ('https://zco.mx', True, 'index'),
            ('https://dev.zco.mx', True, 'index'),
            ('https://www.zco.mx', True, SSLError),
            ('https://fake.zco.mx', True, SSLError),
            ('https://101.zco.mx', True, 'index'),
        ]

        def is_iterable(obj):
            return isinstance(obj, (list, tuple, str))

        for t in tests:
            url, verify_ssl_cert, expect_title = t
            if expect_title == SSLError:
                self.assertRaises(expect_title, requests.get, url)
            else:
                r = requests.get(url, verify=verify_ssl_cert, timeout=60)
                texts = self.titles[expect_title] \
                    if is_iterable(self.titles[expect_title]) \
                    else [self.titles[expect_title]]
                for text in texts:
                    self.assertTrue(text in r.text)


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
