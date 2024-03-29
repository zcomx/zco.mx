#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/controllers/default.py
"""
import unittest
from applications.zcomx.modules.tests.helpers import WebTestCase
# pylint: disable=missing-docstring


class TestFunctions(WebTestCase):

    def test__about(self):
        self.assertWebTest('/z/about')

    def test__cartoonists(self):
        self.assertWebTest('/z/cartoonists')

    def test__completed(self):
        self.assertWebTest('/z/completed')

    def test__contribute(self):
        self.assertWebTest('/z/contribute')

    def test__copyright_claim(self):
        self.assertWebTest('/z/copyright_claim')

    def test__expenses(self):
        self.assertWebTest('/z/expenses')

    def test__faq(self):
        self.assertWebTest('/z/faq')

    def test__faqc(self):
        self.assertWebTest('/z/faqc')

    def test__files(self):
        self.assertWebTest('/z/files')

    def test__index(self):
        self.assertWebTest('/z/index')

    def test__logos(self):
        self.assertWebTest('/z/logos')

    def test__modal_error(self):
        self.assertWebTest('/z/modal_error')

    def test__monies(self):
        self.assertWebTest('/z/monies', match_page_key='/default/index')

    def test__ongoing(self):
        self.assertWebTest('/z/ongoing')

    def test__overview(self):
        self.assertWebTest('/z/overview')

    def test__rss(self):
        self.assertWebTest('/z/rss')

    def test__search(self):
        self.assertWebTest('/z/search')

    def test__terms(self):
        self.assertWebTest('/z/terms')

    def test__todo(self):
        self.assertWebTest('/z/todo')

    def test__top(self):
        self.assertWebTest('/z/top')


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    WebTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
