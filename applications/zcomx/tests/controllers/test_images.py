#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/images.py
"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


class TestFunctions(WebTestCase):

    def test__download(self):
        self.assertRaisesHTTPError(
            404, self.assertWebTest, '/images/download', match_page_key='')

    def test__resize(self):
        pass        # This controller doesn't need testing.


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
