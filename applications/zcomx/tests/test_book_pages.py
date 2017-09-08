#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_pages.py

"""
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from applications.zcomx.modules.book_pages import \
    AbridgedBookPageNumbers, \
    BookPage, \
    BookPageNumber, \
    BookPageNumbers, \
    delete_pages_not_in_ids, \
    pages_sorted_by_page_no, \
    reset_book_page_nos
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.images import store
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


def url_func(book_page, extension=False, host=None):
    # W0613: *Unused argument %%r*
    # pylint: disable=W0613
    return 'http://page/{p:03d}'.format(p=book_page.page_no)


class WithPagesTestCase(LocalTestCase):
    """Class representing a WithPagesTestCase"""

    _book_pages = None

    def setUp(self):
        book_page_1 = BookPage({
            'page_no': 1,
        })
        book_page_2 = BookPage({
            'page_no': 2,
        })
        book_page_3 = BookPage({
            'page_no': 3,
        })
        book_page_4 = BookPage({
            'page_no': 4,
        })
        book_page_5 = BookPage({
            'page_no': 5,
        })

        self._book_pages = [
            book_page_1,
            book_page_2,
            book_page_3,
            book_page_4,
            book_page_5,
        ]

        super(WithPagesTestCase, self).setUp()


class TestAbridgedBookPageNumbers(WithPagesTestCase):

    def test__links(self):
        # Four pages, not abridged
        numbers = AbridgedBookPageNumbers(self._book_pages[:4])
        got = numbers.links(url_func)
        self.assertEqual(len(got), 4)
        for link in got:
            self.assertTrue(isinstance(link, A))

        # Five pages, abridged
        numbers = AbridgedBookPageNumbers(self._book_pages[:5])
        got = numbers.links(url_func)
        self.assertEqual(len(got), 4)
        for count, link in enumerate(got):
            if count == 2:
                self.assertEqual(link, '...')
            else:
                self.assertTrue(isinstance(link, A))

    def test__numbers(self):
        # Four pages, not abridged
        numbers = AbridgedBookPageNumbers(self._book_pages[:4])
        self.assertEqual(numbers.numbers(), ['p01', 'p02', 'p03', 'p04'])

        # Five pages, abridged
        numbers = AbridgedBookPageNumbers(self._book_pages[:5])
        self.assertEqual(numbers.numbers(), ['p01', 'p02', '...', 'p05'])


class TestBookPage(ImageTestCase):

    def test____init__(self):
        page = BookPage({})
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        self.assertEqual(page._upload_image, None)

    def test__orientation(self):
        # Test book without an image.
        book_page = BookPage(dict(id=-1, image=None))
        self.assertRaises(LookupError, book_page.orientation)

        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            stored_filename = store(
                db.book_page.image, filename, resizer=ResizerQuick)

            book_page_row = self.add(BookPage, dict(
                image=stored_filename,
            ))
            book_page = BookPage.from_id(book_page_row.id)
            self.assertEqual(book_page.orientation(), t)

    def test__upload_image(self):
        book_page = BookPage(dict(image='book_image.aaa.000.jpg'))

        up_image = book_page.upload_image()
        self.assertTrue(hasattr(up_image, 'retrieve'))

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212

        # Test cache
        book_page._upload_image = '_cache_'
        self.assertEqual(book_page.upload_image(), '_cache_')


class TestBookPageNumber(WithPagesTestCase):

    def test____init__(self):
        number = BookPageNumber(BookPage({}))
        self.assertTrue(number)

    def test__formatted(self):
        number = BookPageNumber(self._book_pages[2])
        self.assertEqual(number.formatted(), 'p03')

    def test__link(self):
        number = BookPageNumber(self._book_pages[2])
        got = number.link(url_func)
        soup = BeautifulSoup(str(got))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'p03')
        self.assertEqual(anchor['href'], 'http://page/003')


class TestBookPageNumbers(WithPagesTestCase):

    def test____init__(self):
        numbers = BookPageNumbers([])
        self.assertTrue(numbers)

    def test__links(self):
        numbers = BookPageNumbers(self._book_pages[:3])
        got = numbers.links(url_func)
        self.assertEqual(len(got), 3)

        soup = BeautifulSoup(str(got[0]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'p01')
        self.assertEqual(anchor['href'], 'http://page/001')

        soup = BeautifulSoup(str(got[1]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'p02')
        self.assertEqual(anchor['href'], 'http://page/002')

        soup = BeautifulSoup(str(got[2]))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'p03')
        self.assertEqual(anchor['href'], 'http://page/003')

    def test__numbers(self):
        numbers = BookPageNumbers(self._book_pages[:3])
        self.assertEqual(numbers.numbers(), ['p01', 'p02', 'p03'])


class TestFunctions(LocalTestCase):

    def test__delete_pages_not_in_ids(self):

        def get_page_ids(book):
            return [x.id for x in book.pages()]

        book = self.add(Book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 11):
            book_page = self.add(BookPage, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            page_ids,
            get_page_ids(book)
        )

        # Keep every other page.
        keep_ids = []
        lose_ids = []
        for count, page_id in enumerate(page_ids):
            if count % 2:
                keep_ids.append(page_id)
            else:
                lose_ids.append(page_id)
        self.assertEqual(len(keep_ids), 5)
        self.assertEqual(len(lose_ids), 5)

        deleted_ids = delete_pages_not_in_ids(book.id, keep_ids)

        self.assertEqual(
            keep_ids,
            get_page_ids(book)
        )

        self.assertEqual(
            deleted_ids,
            lose_ids
        )

    def test__pages_sorted_by_page_no(self):
        book_page_1 = BookPage({
            'page_no': 3,
        })
        book_page_2 = BookPage({
            'page_no': 1,
        })
        book_page_3 = BookPage({
            'page_no': 2,
        })
        self.assertEqual(
            pages_sorted_by_page_no([book_page_1, book_page_2, book_page_3]),
            [book_page_2, book_page_3, book_page_1]
        )
        self.assertEqual(
            pages_sorted_by_page_no(
                [book_page_1, book_page_2, book_page_3], reverse=True),
            [book_page_1, book_page_3, book_page_2]
        )

    def test__reset_book_page_nos(self):

        def get_page_ids_by_page_no(book):
            return [x.id for x in book.pages()]

        book = self.add(Book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 5):
            book_page = self.add(BookPage, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            get_page_ids_by_page_no(book),
            page_ids
        )

        new_order = [
            page_ids[1],
            page_ids[3],
            page_ids[2],
            page_ids[0],
        ]

        reset_book_page_nos(new_order)

        self.assertEqual(
            get_page_ids_by_page_no(book),
            new_order
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
