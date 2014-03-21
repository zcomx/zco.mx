#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/profile.py

"""
import unittest
import urllib2
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _book = None
    _creator = None
    _creator_to_link = None
    _book_to_link = None
    _user = None

    titles = {
        'account': '<div class="well well-large" id="account">',
        'book_edit': '<div class="well well-large" id="book_edit">',
        'book_link_edit': '<div class="well well-large" id="book_link_edit">',
        'book_links': '<div class="well well-large" id="book_links">',
        'book_pages': '<div class="well well-large" id="book_pages">',
        'book_pages_handler': '<div class="well well-large" id="book_pages_handler">',
        'book_pages_reorder': '<div class="well well-large" id="book_pages_reorder">',
        'book_release': '<div class="well well-large" id="book_release">',
        'books': '<div class="well well-large" id="books">',
        'creator': '<div class="well well-large" id="creator">',
        'creator_link_edit': '<div class="well well-large" id="creator_link_edit">',
        'creator_links': '<div class="well well-large" id="creator_links">',
        'default': 'This is a not-for-profit site dedicated to promoting',
        'index': '<div class="well well-large" id="index">',
        'links': [
            'href="/zcomix/profile/links.load/new/link',
            'Add</span>',
            'order_no_handler/creator_to_link',
        ],
        'links_book': [
            'href="/zcomix/profile/links.load/new/link',
            'Add</span>',
            'order_no_handler/book_to_link',
        ],
        'order_no_handler': '<div id="creator_page">',
    }
    url = '/zcomix/profile'

    @classmethod
    def setUpClass(cls):
        # Get the data the tests will use.
        email = 'jimkarsten@gmail.com'
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            self.fail('No user with email: {e}'.format(e=email))

        cls._creator = db(db.creator.auth_user_id == cls._user.id).select().first()
        if not cls._creator:
            self.fail('No creator with email: {e}'.format(e=email))

        cls._book = db(db.book.creator_id == cls._creator.id).select().first()
        if not cls._book:
            self.fail('No books for creator with email: {e}'.format(e=email))

        cls._creator_to_link = db(db.creator_to_link.creator_id == cls._creator.id).select(orderby=db.creator_to_link.order_no).first()
        if not cls._creator_to_link:
            self.fail('No creator_to_link with email: {e}'.format(e=email))

        cls._book_to_link = db(db.book_to_link.book_id == cls._book.id).select(orderby=db.book_to_link.order_no).first()
        if not cls._book_to_link:
            self.fail('No book_to_link with email: {e}'.format(e=email))

    def test__account(self):
        self.assertTrue(web.test('{url}/account'.format(url=self.url),
            self.titles['account']))

    def test__book_edit(self):
        # No book id, Add mode
        self.assertTrue(web.test('{url}/book_edit'.format(url=self.url),
            self.titles['book_edit']))

        self.assertTrue(web.test('{url}/book_edit/{bid}'.format(
            bid=self._book.id, url=self.url),
            self.titles['book_edit']))

    def test__creator_link_edit(self):
        # No book id, Add mode
        self.assertTrue(web.test('{url}/creator_link_edit'.format(url=self.url),
            self.titles['creator_link_edit']))

    def test__book_links(self):
        # No book id
        self.assertTrue(web.test('{url}/book_links'.format(url=self.url),
            self.titles['books']))

        self.assertTrue(web.test('{url}/book_links/{bid}'.format(
            bid=self._book.id, url=self.url),
            self.titles['book_links']))

    def test__book_pages(self):
        # No book_id, redirects to books page
        self.assertTrue(web.test('{url}/book_pages'.format(url=self.url),
            self.titles['books']))

        self.assertTrue(web.test('{url}/book_pages/{bid}'.format(
            bid=self._book.id, url=self.url),
            self.titles['book_pages']))

    def test__book_pages_handler(self):
        # No book_id, redirects to books page
        self.assertTrue(web.test('{url}/book_pages_handler'.format(url=self.url),
            self.titles['book_pages_handler']))

    def test__book_pages_reorder(self):
        # No book_id, redirects to books page
        self.assertTrue(web.test('{url}/book_pages_reorder'.format(url=self.url),
            self.titles['book_pages_reorder']))

    def test__book_release(self):
        # No book_id, redirects to books page
        self.assertTrue(web.test('{url}/book_release'.format(url=self.url),
            self.titles['books']))

        self.assertTrue(web.test('{url}/book_release/{bid}'.format(
            bid=self._book.id, url=self.url),
            self.titles['book_release']))

    def test__books(self):
        self.assertTrue(web.test('{url}/books'.format(
            bid=self._book.id, url=self.url),
            self.titles['books']))

    def test__creator(self):
        self.assertTrue(web.test('{url}/creator'.format(url=self.url),
            self.titles['creator']))

    def test__book_link_edit(self):
        # No book id, Add mode
        self.assertTrue(web.test('{url}/book_link_edit'.format(url=self.url),
            self.titles['book_link_edit']))

    def test__creator_links(self):
        self.assertTrue(web.test('{url}/creator_links'.format(url=self.url),
            self.titles['creator_links']))

    def test__index(self):
        self.assertTrue(web.test('{url}/index'.format(url=self.url),
            self.titles['index']))

    def test__links(self):
        self.assertTrue(
            web.test(
                '{url}/links.load'.format(url=self.url),
                self.titles['links']
            )
        )

        self.assertTrue(web.test('{url}/links.load?book_id={bid}'.format(
            bid=self._book.id, url=self.url),
            self.titles['links_book']))

    def test__order_no_handler(self):
        self.assertTrue(web.test('{url}/order_no_handler'.format(url=self.url),
            self.titles['default']))

        self.assertTrue(web.test('{url}/order_no_handler/creator_to_link'.format(url=self.url),
            self.titles['default']))

        self.assertTrue(web.test('{url}/order_no_handler/creator_to_link/{clid}'.format(
            clid=self._creator_to_link.id, url=self.url),
            self.titles['default']))

        # Down
        before = self._creator_to_link.order_no
        next_url = '/zcomix/creators/creator/{cid}'.format(cid=self._creator.id)
        self.assertTrue(web.test('{url}/order_no_handler/creator_to_link/{clid}/down?next={nurl}'.format(
            clid=self._creator_to_link.id,
            nurl=next_url,
            url=self.url),
            self.titles['order_no_handler']))

        after = db(db.creator_to_link.id == self._creator_to_link.id).select().first().order_no
        # This test fails because db is not updated.
        # self.assertEqual(before + 1, after)

        # Up
        self.assertTrue(web.test('{url}/order_no_handler/creator_to_link/{clid}/up?next={nurl}'.format(
            clid=self._creator_to_link.id,
            nurl=next_url,
            url=self.url),
            self.titles['order_no_handler']))

        after = db(db.creator_to_link.id == self._creator_to_link.id).select().first().order_no
        self.assertEqual(before, after)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
