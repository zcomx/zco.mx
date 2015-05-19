#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/controllers/default.py

"""
import unittest
import urllib2
from applications.zcomx.modules.tests.runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    titles = {
        '404': 'Page not found',
        'about': '<h1>About</h1>',
        'cartoonists': '<div id="front_page">',
        'completed': '<div id="front_page">',
        'contribute': '<form id="paypal_form"',
        'copyright_claim':
            '<h3>Notice and Procedure for Making Claims of Copyright',
        'data': '<h2>Not authorized</h2>',
        'expenses': '<h1>Expenses</h1>',
        'faq': '<h1>FAQ</h1>',
        'faqc': [
            '<h1>FAQ</h1>',
            '<div class="faq_options_container">',
        ],
        'files': '<div id="files_page">',
        'index': '<div id="front_page">',
        'login': '<h2>Cartoonist Login</h2>',
        'logos': '<h1>Logos</h1>',
        'modal_error': 'An error occurred. Please try again.',
        'ongoing': '<div id="front_page">',
        'overview': '<h1>Overview</h1>',
        'page_not_found': '<h3>Page not found</h3>',
        'search': '<div id="front_page">',
        'terms': '<h1>Terms and Conditions</h1>',
        'todo': '<h1>TODO</h1>',
        'top': '<h2>Top</h2>',
        'user': [
            'web2py_user_form',
            'web2py_user_form_container',
            'forgot_password_container',
            'register_container'
        ],
    }
    url = '/zcomx/z'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        # Prevent 'Changed session ID' warnings.
        web.sessions = {}

    def test__about(self):
        self.assertTrue(web.test(
            '{url}/about'.format(url=self.url),
            self.titles['about']
        ))

    def test__cartoonists(self):
        self.assertTrue(web.test(
            '{url}/cartoonists'.format(url=self.url),
            self.titles['cartoonists']
        ))

    def test__completed(self):
        self.assertTrue(web.test(
            '{url}/completed'.format(url=self.url),
            self.titles['completed']
        ))

    def test__contribute(self):
        self.assertTrue(web.test(
            '{url}/contribute'.format(url=self.url),
            self.titles['contribute']
        ))

    def test__copyright_claim(self):
        self.assertTrue(web.test(
            '{url}/copyright_claim'.format(url=self.url),
            self.titles['copyright_claim']
        ))

    def test__expenses(self):
        self.assertTrue(web.test(
            '{url}/expenses'.format(url=self.url),
            self.titles['expenses']
        ))

    def test__faq(self):
        self.assertTrue(web.test(
            '{url}/faq'.format(url=self.url),
            self.titles['faq']
        ))

    def test__faqc(self):
        self.assertTrue(web.test(
            '{url}/faqc'.format(url=self.url),
            self.titles['faqc']
        ))

    def test__files(self):
        self.assertTrue(web.test(
            '{url}/files'.format(url=self.url),
            self.titles['files']
        ))

    def test__index(self):
        self.assertTrue(web.test(
            '{url}/index'.format(url=self.url),
            self.titles['index']
        ))

    def test__logos(self):
        self.assertTrue(web.test(
            '{url}/logos'.format(url=self.url),
            self.titles['logos']
        ))

    def test__modal_error(self):
        self.assertTrue(
            web.test(
                '{url}/modal_error'.format(url=self.url),
                self.titles['modal_error']
            )
        )

    def test__monies(self):
        self.assertTrue(web.test(
            '{url}/monies'.format(url=self.url),
            self.titles['index']
        ))

    def test__ongoing(self):
        self.assertTrue(web.test(
            '{url}/ongoing'.format(url=self.url),
            self.titles['ongoing']
        ))

    def test__overview(self):
        self.assertTrue(web.test(
            '{url}/overview'.format(url=self.url),
            self.titles['overview']
        ))

    def test__search(self):
        self.assertTrue(web.test(
            '{url}/search'.format(url=self.url),
            self.titles['search']
        ))

    def test__terms(self):
        self.assertTrue(web.test(
            '{url}/terms'.format(url=self.url),
            self.titles['terms']
        ))

    def test__todo(self):
        self.assertTrue(web.test(
            '{url}/todo'.format(url=self.url),
            self.titles['todo']
        ))

    def test__top(self):
        self.assertTrue(web.test(
            '{url}/top'.format(url=self.url),
            self.titles['top']
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
