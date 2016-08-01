#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zco.mx routing.
This tests nginx settings on the live server.

"""
import requests
import unittest
from requests.exceptions import SSLError
from applications.zcomx.modules.tests.helpers import skip_if_quick
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'creator': [
            '<div id="creator_page">',
            '<h1>Charles Forsman</h1>',
        ],
        'index': '<div id="front_page">',
    }

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

    @skip_if_quick
    def test_routes(self):
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
            ('https://dev.zco.mx', True, SSLError),
            ('https://www.zco.mx', True, SSLError),
            ('https://fake.zco.mx', True, SSLError),
            ('https://101.zco.mx', True, 'index'),
        ]

        is_iterable = lambda obj: isinstance(obj, basestring) \
            or getattr(obj, '__iter__', False)

        for t in tests:
            if t[2] == SSLError:
                self.assertRaises(t[2], requests.get, t[0])
            else:
                r = requests.get(t[0], verify=t[1])
                texts = self.titles[t[2]] if is_iterable(self.titles[t[2]]) \
                    else [self.titles[t[2]]]
                for text in texts:
                    self.assertTrue(text in r.text)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
