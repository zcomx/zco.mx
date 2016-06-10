#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_lists.py

"""
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from applications.zcomx.modules.book_lists import \
    BaseBookList, \
    DisabledBookList, \
    DraftBookList, \
    OngoingBookList, \
    CompletedBookList, \
    class_from_code
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubBookList(BaseBookList):

    @property
    def code(self):
        return 'dubbed'


class TestBaseBookList(LocalTestCase):

    def test____init__(self):
        creator = self.add(Creator, dict(
            email='test__init__@email.com',
        ))
        book_list = BaseBookList(creator)
        self.assertTrue(book_list)

    def test__allow_upload_on_edit(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.allow_upload_on_edit)

    def test__books(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212

        creator = self.add(Creator, dict(
            email='test__books@email.com',
        ))

        book_list = BaseBookList(creator)
        self.assertEqual(book_list.books().as_list(), [])
        self.assertEqual(book_list._books.as_list(), [])

        book_1 = self.add(Book, dict(
            name='My Book 1',
            creator_id=creator.id,
        ))

        book_2 = self.add(Book, dict(
            name='My Book 2',
            creator_id=creator.id,
        ))

        # Accesses cache, so returns none
        self.assertEqual(book_list.books().as_list(), [])

        book_list._books = None     # Clear cache
        books = book_list.books()
        self.assertEqual(len(books), 2)
        self.assertEqual(books[0], book_1)
        self.assertEqual(books[1], book_2)

    def test__code(self):
        book_list = BaseBookList({})
        try:
            book_list.code
        except NotImplementedError:
            pass        # This is expected
        else:
            self.fail('NotImplementedError not raised.')

    def test__display_headers_if_none(self):
        book_list = BaseBookList({})
        self.assertTrue(book_list.display_headers_if_none)

    def test__display_if_none(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.display_if_none)

    def test__filters(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.filters(), [])

    def test__has_complete_in_progress(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        book_list = BaseBookList(Creator())
        book_list._books = []
        self.assertEqual(book_list.has_complete_in_progress, False)

        tests = [
            # (book_1.complete_in_progress, book_2.complete_in_progress, expct)
            (False, False, False),
            (True, False, True),
            (False, True, True),
            (True, True, True),
        ]

        for t in tests:
            book_1 = Book(name='My Book 1', complete_in_progress=t[0])
            book_2 = Book(name='My Book 2', complete_in_progress=t[1])
            book_list = BaseBookList(Creator())
            book_list._books = [book_1, book_2]
            self.assertEqual(book_list.has_complete_in_progress, t[2])

    def test__has_fileshare_in_progress(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        book_list = BaseBookList(Creator())
        book_list._books = []
        self.assertEqual(book_list.has_fileshare_in_progress, False)

        tests = [
            # (book_1.fileshare_in_progress, book_2.fileshare_in_progress, exp)
            (False, False, False),
            (True, False, True),
            (False, True, True),
            (True, True, True),
        ]

        for t in tests:
            book_1 = Book(name='My Book 1', fileshare_in_progress=t[0])
            book_2 = Book(name='My Book 2', fileshare_in_progress=t[1])
            book_list = BaseBookList(Creator())
            book_list._books = [book_1, book_2]
            self.assertEqual(book_list.has_fileshare_in_progress, t[2])

    def test__headers(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.headers(), None)

    def test__include_complete_checkbox(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_complete_checkbox)

    def test__include_fileshare_checkbox(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"%%s*
        # pylint: disable=C0103
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_fileshare_checkbox)

    def test__include_publication_year(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_publication_year)

    def test__include_read(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_read)

    def test__include_upload(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_upload)

    def test__link_to_book_page(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.link_to_book_page)

    def test__no_records_found_msg(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.no_records_found_msg, 'No books found')

    def test__subtitle(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.subtitle, '')

    def test__title(self):
        book_list = DubBookList({})
        self.assertEqual(book_list.title, 'DUBBED')


class TestCompletedBookList(LocalTestCase):

    def test__code(self):
        book_list = CompletedBookList({})
        self.assertEqual(book_list.code, 'completed')

    def test__display_headers_if_none(self):
        book_list = CompletedBookList({})
        self.assertFalse(book_list.display_headers_if_none)

    def test__display_if_none(self):
        book_list = CompletedBookList({})
        self.assertTrue(book_list.display_if_none)

    def test__filters(self):
        book_list = CompletedBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 2)
        self.assertEqual(str(filters[0]), "(book.status = 'a')")
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(filters[1]),
            "((book.release_date IS NOT NULL) OR (book.complete_in_progress = 'T'))"
        )

    def test__headers(self):
        book_list = CompletedBookList({})
        headers = book_list.headers()
        for k, v in headers.iteritems():
            if k == 'fileshare_checkbox':
                continue
            self.assertEqual(v, None)

        soup = BeautifulSoup(str(headers['fileshare_checkbox']))
        # <div class="fileshare_header text-muted">Set as completed</div>
        div = soup.find('div')
        self.assertEqual(div.string, 'Release for filesharing')
        self.assertEqual(div['class'], 'checkbox_header text-muted')

    def test__include_fileshare_checkbox(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"%%s*
        # pylint: disable=C0103
        book_list = CompletedBookList({})
        self.assertTrue(book_list.include_fileshare_checkbox)

    def test__include_publication_year(self):
        book_list = CompletedBookList({})
        self.assertTrue(book_list.include_publication_year)

    def test__include_read(self):
        book_list = CompletedBookList({})
        self.assertTrue(book_list.include_read)

    def test__link_to_book_page(self):
        book_list = CompletedBookList({})
        self.assertTrue(book_list.link_to_book_page)

    def test__no_records_found_msg(self):
        book_list = CompletedBookList({})
        self.assertEqual(book_list.no_records_found_msg, 'No completed books')


class TestDisabledBookList(LocalTestCase):

    def test__code(self):
        book_list = DisabledBookList({})
        self.assertEqual(book_list.code, 'disabled')

    def test__filters(self):
        book_list = DisabledBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 1)
        self.assertEqual(str(filters[0]), "(book.status = 'x')")

    def test__no_records_found_msg(self):
        book_list = DisabledBookList({})
        self.assertEqual(book_list.no_records_found_msg, 'No disabled books')

    def test__subtitle(self):
        book_list = DisabledBookList({})
        self.assertTrue('Books are disabled by' in book_list.subtitle)


class TestDraftBookList(LocalTestCase):

    def test__allow_upload_on_edit(self):
        book_list = DraftBookList({})
        self.assertTrue(book_list.allow_upload_on_edit)

    def test__code(self):
        book_list = DraftBookList({})
        self.assertEqual(book_list.code, 'draft')

    def test__filters(self):
        book_list = DraftBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 1)
        self.assertEqual(str(filters[0]), "(book.status = 'd')")

    def test__include_upload(self):
        book_list = DraftBookList({})
        self.assertTrue(book_list.include_upload)

    def test__no_records_found_msg(self):
        book_list = DraftBookList({})
        self.assertEqual(book_list.no_records_found_msg, 'No draft books')

    def test__subtitle(self):
        book_list = DraftBookList({})
        self.assertTrue('Books remain as a draft' in book_list.subtitle)

    def test__title(self):
        book_list = DraftBookList({})
        self.assertEqual(book_list.title, 'DRAFTS')


class TestOngoingBookList(LocalTestCase):

    def test__allow_upload_on_edit(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.allow_upload_on_edit)

    def test__code(self):
        book_list = OngoingBookList({})
        self.assertEqual(book_list.code, 'ongoing')

    def test__display_headers_if_none(self):
        book_list = OngoingBookList({})
        self.assertFalse(book_list.display_headers_if_none)

    def test__display_if_none(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.display_if_none)

    def test__filters(self):
        book_list = OngoingBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(filters[0]), "(book.status = 'a')")
        self.assertEqual(str(filters[1]), "(book.release_date IS NULL)")
        self.assertEqual(str(filters[2]), "(book.complete_in_progress <> 'T')")

    def test__headers(self):
        book_list = OngoingBookList({})
        headers = book_list.headers()
        for k, v in headers.iteritems():
            if k == 'complete_checkbox':
                continue
            self.assertEqual(v, None)

        soup = BeautifulSoup(str(headers['complete_checkbox']))
        # <div class="checkbox_header text-muted">Set as completed</div>
        div = soup.find('div')
        self.assertEqual(div.string, 'Set as completed')
        self.assertEqual(div['class'], 'checkbox_header text-muted')

    def test__include_complete_checkbox(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.include_complete_checkbox)

    def test__include_read(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.include_read)

    def test__include_upload(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.include_upload)

    def test__link_to_book_page(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.link_to_book_page)

    def test__no_records_found_msg(self):
        book_list = OngoingBookList({})
        self.assertEqual(book_list.no_records_found_msg, 'No ongoing series')


class TestFunctions(LocalTestCase):

    def test__class_from_code(self):
        self.assertEqual(class_from_code('disabled'), DisabledBookList)
        self.assertEqual(class_from_code('draft'), DraftBookList)
        self.assertEqual(class_from_code('ongoing'), OngoingBookList)
        self.assertEqual(class_from_code('completed'), CompletedBookList)
        self.assertRaises(ValueError, class_from_code, None)
        self.assertRaises(ValueError, class_from_code, '')
        self.assertRaises(ValueError, class_from_code, 'fake')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
