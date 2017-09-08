#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/errors.py

"""
import os
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
        errors_path = os.path.join(request.folder, 'errors')
        errors_before = os.listdir(errors_path)
        self.assertWebTest(
            '/errors/test_exception', match_page_key='/errors/index')
        errors_after = os.listdir(errors_path)
        self.assertEqual(len(errors_after), len(errors_before) + 1)

        # Cleanup
        new_files = set(errors_after).difference(set(errors_before))
        for new_file in new_files:
            filename = os.path.join(errors_path, new_file)
            if os.path.exists(filename):
                os.unlink(filename)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
