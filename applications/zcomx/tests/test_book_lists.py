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
        creator = self.add(db.creator, dict(
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

        creator = self.add(db.creator, dict(
            email='test__books@email.com',
        ))

        book_list = BaseBookList(creator)
        self.assertEqual(book_list.books().as_list(), [])
        self.assertEqual(book_list._books.as_list(), [])

        book_1 = self.add(db.book, dict(
            name='My Book 1',
            creator_id=creator.id,
        ))

        book_2 = self.add(db.book, dict(
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

    def test__display_if_none(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.display_if_none)

    def test__filters(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.filters(), [])

    def test__headers(self):
        book_list = BaseBookList({})
        self.assertEqual(book_list.headers(), None)

    def test__include_complete_checkbox(self):
        book_list = BaseBookList({})
        self.assertFalse(book_list.include_complete_checkbox)

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

    def test__display_if_none(self):
        book_list = CompletedBookList({})
        self.assertTrue(book_list.display_if_none)

    def test__filters(self):
        book_list = CompletedBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 2)
        self.assertEqual(str(filters[0]), "(book.status = 'a')")
        self.assertEqual(str(filters[1]), "(book.release_date IS NOT NULL)")

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

    def test__display_if_none(self):
        book_list = OngoingBookList({})
        self.assertTrue(book_list.display_if_none)

    def test__filters(self):
        book_list = OngoingBookList({})
        filters = book_list.filters()
        self.assertEqual(len(filters), 2)
        self.assertEqual(str(filters[0]), "(book.status = 'a')")
        self.assertEqual(str(filters[1]), "(book.release_date IS NULL)")

    def test__headers(self):
        book_list = OngoingBookList({})
        headers = book_list.headers()
        for k, v in headers.iteritems():
            if k == 'complete_checkbox':
                continue
            self.assertEqual(v, None)

        soup = BeautifulSoup(str(headers['complete_checkbox']))
        # <div class="set_as_completed text-muted">Set as completed</div>
        div = soup.find('div')
        self.assertEqual(div.string, 'Set as completed')
        self.assertEqual(div['class'], 'set_as_completed text-muted')

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
