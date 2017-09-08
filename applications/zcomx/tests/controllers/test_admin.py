#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/admin.py

"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(WebTestCase):

    def test__index(self):
        # Not logged in, redirects to login page
        web.logout()
        self.assertWebTest(
            '/admin/index',
            match_page_key='/default/user/login',
            login_required=False
        )

        # Logged in, displays admin
        web.login()
        self.assertWebTest('/admin/index')

    def test__job_queuers(self):
        # Not logged in, redirects to login page
        web.logout()
        self.assertWebTest(
            '/admin/job_queuers',
            match_page_key='/default/user/login',
            login_required=False
        )

        # Logged in, displays admin
        web.login()
        self.assertWebTest('/admin/job_queuers')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
