#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/admin.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _creator = None

    titles = {
        'default': '<div id="front_page">',
    }
    url = '/zcomx/admin'


    def test__index(self):
        current.request.client = '123.123.123.123'
        self.assertTrue(web.test(
            '{url}/index'.format(
                url=self.url,
            ),
            self.titles['default']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
