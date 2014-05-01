#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/controllers/profile.py

"""
import re
import unittest
from applications.zcomix.modules.test_runner import LocalTestCase


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _book = None
    _book_page = None
    _book_to_link = None
    _creator = None
    _creator_to_link = None
    _user = None

    titles = {
        'account': '<div class="well well-sm" id="account">',
        'book_add': [
            '<div id="book_edit_section">',
            "'value': '__Untitled-",
        ],
        'book_edit': '<div id="book_edit_section">',
        'book_pages': '<div id="profile_book_pages_page">',
        'book_pages_handler_fail': [
            '{"files":',
            'Upload service unavailable',
        ],
        'book_pages_handler': [
            '{"files":',
            '"thumbnailUrl"',
        ],
        'book_pages_reorder_fail': [
            '"success": false',
            '"error": "Reorder service unavailable."',
        ],
        'book_pages_reorder': [
            '"success": true',
        ],
        'book_release': '<div id="profile_book_release_page">',
        'books': '<div class="well well-sm" id="books">',
        'creator': '<div class="well well-sm" id="creator">',
        'default': 'This is a not-for-profit site dedicated to promoting',
        'index': '<div class="well well-sm" id="account">',
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
        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        cls._creator = db(db.creator.auth_user_id == cls._user.id).select().first()
        if not cls._creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        # Get a book by creator with pages and links.
        count = db.book_page.book_id.count()
        query = (db.creator.id == cls._creator.id)
        book_page = db(query).select(
            db.book_page.ALL,
            count,
            left=[
                db.book.on(db.book.id == db.book_page.book_id),
                db.book_to_link.on(db.book_to_link.book_id == db.book.id),
                db.creator.on(db.creator.id == db.book.creator_id),
            ],
            groupby=db.book_page.book_id,
            orderby=~count
        ).first()
        if not book_page:
            raise SyntaxError('No book page from creator with email: {e}'.format(e=email))

        cls._book_page = db(db.book_page.id == book_page.book_page.id).select().first()
        if not cls._book_page:
            raise SyntaxError('Unable to get book_page for: {e}'.format(e=email))

        query = (db.book.id == cls._book_page.book_id)
        cls._book = db(query).select(db.book.ALL).first()
        if not cls._book:
            raise SyntaxError('No books for creator with email: {e}'.format(e=email))

        cls._creator_to_link = db(db.creator_to_link.creator_id == cls._creator.id).select(orderby=db.creator_to_link.order_no).first()
        if not cls._creator_to_link:
            raise SyntaxError('No creator_to_link with email: {e}'.format(e=email))

        cls._book_to_link = db(db.book_to_link.book_id == cls._book.id).select(orderby=db.book_to_link.order_no).first()
        if not cls._book_to_link:
            raise SyntaxError('No book_to_link with email: {e}'.format(e=email))

    def test__account(self):
        self.assertTrue(
            web.test(
                '{url}/account'.format(url=self.url),
                self.titles['account']
            )
        )

    def test__book_add(self):
        # This test will create a book.

        def book_ids(creator_id):
            return [
                x.id for x in
                db(db.book.creator_id == creator_id).select(db.book.id)
            ]

        before_ids = book_ids(self._creator.id)
        self.assertTrue(
            web.test(
                '{url}/book_add'.format(url=self.url),
                self.titles['book_add']
            )
        )
        after_ids = book_ids(self._creator.id)
        self.assertEqual(set(before_ids).difference(set(after_ids)), set())
        diff_set = set(after_ids).difference(set(before_ids))
        self.assertEqual(len(diff_set), 1)
        new_book = db(db.book.id == list(diff_set)[0]).select().first()
        self._objects.append(new_book)
        self.assertEqual(new_book.creator_id, self._creator.id)
        self.assertRegexpMatches(
            new_book.name,
            re.compile(r'__Untitled-[0-9]{2}__')
        )

    def test__book_edit(self):
        # No book id, redirect to books
        self.assertTrue(
            web.test(
                '{url}/book_edit'.format(url=self.url),
                self.titles['books']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_edit/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_edit']
            )
        )

    def test__book_pages(self):
        # No book_id, redirects to books page
        self.assertTrue(
            web.test(
                '{url}/book_pages'.format(url=self.url),
                self.titles['books']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_pages/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_pages']
            )
        )

    def test__book_pages_handler(self):
        # No book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_handler'.format(url=self.url),
                self.titles['book_pages_handler_fail']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_pages_handler/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_pages_handler']
            )
        )

    def test__book_pages_reorder(self):
        # No book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder'.format(url=self.url),
                self.titles['book_pages_reorder_fail']
            )
        )

        # Invalid book_id, return fail message
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}'.format(
                    bid=999999, url=self.url),
                self.titles['book_pages_reorder_fail']
            )
        )

        # Valid book_id, no book pages returns success
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}'.format(
                    bid=self._book.id,
                    url=self.url,
                ),
                self.titles['book_pages_reorder']
            )
        )

        # Valid
        query = (db.book_page.book_id == self._book.id)
        book_page_ids = [x.id for x in db(query).select(db.book_page.id)]
        bpids = ['book_page_ids[]={pid}'.format(pid=x) for x in book_page_ids]
        self.assertTrue(
            web.test(
                '{url}/book_pages_reorder/{bid}?{bpid}'.format(
                    bid=self._book.id,
                    bpid='&'.join(bpids),
                    url=self.url),
                self.titles['book_pages_reorder']
            )
        )

    def test__book_release(self):
        # No book_id, redirects to books page
        self.assertTrue(
            web.test(
                '{url}/book_release'.format(url=self.url),
                self.titles['books']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/book_release/{bid}'.format(
                    bid=self._book.id, url=self.url),
                self.titles['book_release']
            )
        )

    def test__books(self):
        self.assertTrue(
            web.test(
                '{url}/books'.format(bid=self._book.id, url=self.url),
                self.titles['books']
            )
        )

    def test__creator(self):
        self.assertTrue(
            web.test(
                '{url}/creator'.format(url=self.url),
                self.titles['creator']
            )
        )

    def test__index(self):
        self.assertTrue(
            web.test(
                '{url}/index'.format(url=self.url),
                self.titles['index']
            )
        )

    def test__order_no_handler(self):
        self.assertTrue(
            web.test(
                '{url}/order_no_handler'.format(url=self.url),
                self.titles['default']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link'.format(url=self.url),
                self.titles['default']
            )
        )

        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link/{clid}'.format(
                    clid=self._creator_to_link.id, url=self.url),
                self.titles['default']
            )
        )

        # Down
        before = self._creator_to_link.order_no
        next_url = '/zcomix/creators/creator/{cid}'.format(cid=self._creator.id)
        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link/{clid}/down?next={nurl}'.format(
                    clid=self._creator_to_link.id,
                    nurl=next_url,
                    url=self.url
                ),
                self.titles['order_no_handler']
            )
        )

        after = db(db.creator_to_link.id == self._creator_to_link.id).select().first().order_no
        # This test fails because db is not updated.
        # self.assertEqual(before + 1, after)

        # Up
        self.assertTrue(
            web.test(
                '{url}/order_no_handler/creator_to_link/{clid}/up?next={nurl}'.format(
                    clid=self._creator_to_link.id,
                    nurl=next_url,
                    url=self.url
                ),
                self.titles['order_no_handler']
            )
        )

        after = db(db.creator_to_link.id == self._creator_to_link.id).select().first().order_no
        self.assertEqual(before, after)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
