#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/errors.py

"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    def test__handler(self):
        self.assertWebTest('/errors/handler', match_page_key='/errors/index')

    def test__index(self):
        self.assertWebTest('/errors/index')

    def test__page_not_found(self):
        self.assertWebTest('/errors/page_not_found')

    def test__test_exception(self):
        self.assertWebTest(
            '/errors/test_exception', match_page_key='/errors/index')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
