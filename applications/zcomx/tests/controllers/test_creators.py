#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/creators.py

"""
import unittest
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    _creator = None

    @classmethod
    def setUpClass(cls):
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        # Get the data the tests will use.
        cls._creator = Creator.by_email(web.username)

    def test__creator(self):
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/creators/creator',
            match_page_key='',
        )

    def test__index(self):
        # Test: no creator
        self.assertWebTest(
            '/creators/index', match_page_key='/errors/page_not_found')

        # Test: creator as integer
        url_path = '/creators/index?creator={cid}'.format(cid=self._creator.id)
        self.assertWebTest(url_path, match_page_key='/creators/creator')

        # Test: creator as name
        url_path = '/creators/index?creator={name}'.format(
            name=self._creator.name_for_url)
        self.assertWebTest(url_path, match_page_key='/creators/creator')

    def test__monies(self):
        self.assertRaisesHTTPError(
            404,
            self.assertWebTest,
            '/creators/monies',
            match_page_key='',
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
