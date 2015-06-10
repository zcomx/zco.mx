#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book_pages.py

"""
import unittest
from gluon import *
from pydal.objects import Row
from applications.zcomx.modules.book_pages import \
    BookPage, \
    delete_pages_not_in_ids, \
    pages_sorted_by_page_no, \
    reset_book_page_nos
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import \
    NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestBookPage(LocalTestCase):

    def test____init__(self):
        book_page = self.add(db.book_page, dict(
            image=None
        ))
        page = BookPage(book_page)
        self.assertRaises(NotFoundError, BookPage, -1)
        self.assertEqual(page.min_cbz_width, 1600)
        self.assertEqual(page.min_cbz_height_to_exempt, 2560)

    def test__upload_image(self):
        book_page = self.add(db.book_page, dict(
            image='book_image.aaa.000.jpg'
        ))

        page = BookPage(book_page)
        up_image = page.upload_image()
        self.assertTrue(hasattr(up_image, 'retrieve'))

        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212

        # Test cache
        page._upload_image = '_cache_'
        self.assertEqual(page.upload_image(), '_cache_')


class TestFunctions(LocalTestCase):

    def test__delete_pages_not_in_ids(self):

        def get_page_ids(book_id):
            query = (db.book_page.book_id == book_id)
            return sorted([x.id for x in db(query).select()])

        book = self.add(db.book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 11):
            book_page = self.add(db.book_page, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            page_ids,
            get_page_ids(book.id)
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
            get_page_ids(book.id)
        )

        self.assertEqual(
            deleted_ids,
            lose_ids
        )

    def test__pages_sorted_by_page_no(self):
        book_page_1 = Row({
            'page_no': 3,
        })
        book_page_2 = Row({
            'page_no': 1,
        })
        book_page_3 = Row({
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

        def get_page_ids_by_page_no(book_id):
            query = (db.book_page.book_id == book_id)
            return [
                x.id
                for x in db(query).select(orderby=db.book_page.page_no)
            ]

        book = self.add(db.book, dict(
            name='test__delete_pages_not_in_ids',
        ))

        page_ids = []
        for page_no in range(1, 5):
            book_page = self.add(db.book_page, dict(
                book_id=book.id,
                page_no=page_no,
            ))
            page_ids.append(book_page.id)

        self.assertEqual(
            get_page_ids_by_page_no(book.id),
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
            get_page_ids_by_page_no(book.id),
            new_order
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
