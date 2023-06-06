#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/admin.py
"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


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
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
