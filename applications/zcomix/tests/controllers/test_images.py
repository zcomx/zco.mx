#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/default.py

"""
import unittest
import urllib2
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        'download': '<h2>Not authorized</h2>',
    }
    url = '/zcomix/images'

    def test__download(self):
        with self.assertRaises(urllib2.HTTPError) as cm:
            web.test('{url}/download'.format(url=self.url), None)
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, 'NOT FOUND')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
