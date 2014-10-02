#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/routing.py

"""
import unittest
from gluon import *
from gluon.http import HTTP
from gluon.rewrite import filter_url
from gluon.storage import \
    List, \
    Storage
from applications.zcomx.modules.routing import route
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _type_id_by_name = {}

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

    def test_routes(self):
        """This tests the ~/routes.py settings."""
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        app_root = '/srv/http/jimk.zsw.ca/web2py/applications'
        in_tests = [
            #(url, URL)
            ('http://my.domain.com', '/zcomx/default/index'),
            ('http://my.domain.com/zcomx', '/zcomx/default/index'),
            ('http://my.domain.com/books', '/zcomx/books/index'),
            ('http://my.domain.com/books/index', '/zcomx/books/index'),
            ('http://my.domain.com/books/book', '/zcomx/books/book'),
            ('http://my.domain.com/zcomx/books', '/zcomx/books/index'),
            ('http://my.domain.com/zcomx/books/index', '/zcomx/books/index'),
            ('http://my.domain.com/zcomx/books/book', '/zcomx/books/book'),
            ('http://my.domain.com/zcomx/books/book/1', "/zcomx/books/book ['1']"),
            # Test: creators controller
            ('http://my.domain.com/creators', '/zcomx/creators/index'),
            ('http://my.domain.com/creators/index', '/zcomx/creators/index'),
            ('http://my.domain.com/zcomx/creators', '/zcomx/creators/index'),
            ('http://my.domain.com/zcomx/creators/index', '/zcomx/creators/index'),
            ('https://my.domain.com/zcomx/search/index', '/zcomx/search/index'),

            # Test: default/user/???
            ('http://my.domain.com/default/user/login', "/zcomx/default/user ['login']"),
            ('http://my.domain.com/default/user/logout', "/zcomx/default/user ['logout']"),

            # Static files
            ('http://my.domain.com/favicon.ico', app_root + '/zcomx/static/images/favicon.ico'),
            ('http://jimk.zsw.ca/robots.txt', app_root + '/zcomx/static/robots.txt'),
            ('http://my.domain.com/zcomx/static/images/loading.gif', app_root + '/zcomx/static/images/loading.gif'),
            ('http://my.domain.com/zcomx/static/css/custom.css', app_root + '/zcomx/static/css/custom.css'),
            ('http://my.domain.com/zcomx/static/js/web2py.js', app_root + '/zcomx/static/js/web2py.js'),

            # Test https
            ('https://my.domain.com', '/zcomx/default/index'),
            ('https://my.domain.com/zcomx', '/zcomx/default/index'),
            ('https://my.domain.com/books', '/zcomx/books/index'),
            ('https://my.domain.com/books/index', '/zcomx/books/index'),

            # Creator variations
            ('http://my.domain.com/aaa', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/aaa/bbb', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/aaa/bbb/ccc', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),
            ('http://my.domain.com/zcomx/aaa', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/zcomx/aaa/bbb', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/zcomx/aaa/bbb/ccc', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),

            # Creators
            ('http://my.domain.com/First_Last', "/zcomx/creators/index ?creator=First_Last"),
            ('http://my.domain.com/First_M_Last', "/zcomx/creators/index ?creator=First_M_Last"),
            ("http://my.domain.com/First_O'Last", "/zcomx/creators/index ?creator=First_O'Last"),

            # Books
            ('http://my.domain.com/First_Last/My_Book', '/zcomx/creators/index ?creator=First_Last&book=My_Book'),
            ('http://my.domain.com/First_Last/My_Book_(2014)', '/zcomx/creators/index ?creator=First_Last&book=My_Book_(2014)'),
            ('http://my.domain.com/First_Last/My_Book_001_(2014)', '/zcomx/creators/index ?creator=First_Last&book=My_Book_001_(2014)'),
            ('http://my.domain.com/First_Last/My_Book_01_of_04_(2014)', '/zcomx/creators/index ?creator=First_Last&book=My_Book_01_of_04_(2014)'),

            # Pages
            ('http://my.domain.com/zcomx/First_Last/My_Book/001', '/zcomx/creators/index ?creator=First_Last&book=My_Book&page=001'),
            ('http://my.domain.com/zcomx/First_Last/My_Book/001.jpg', '/zcomx/creators/index ?creator=First_Last&book=My_Book&page=001.jpg'),

            # Admin/appadmin should be routed like any other url
            ('http://my.domain.com/admin', "/zcomx/creators/index ?creator=admin"),
            ('http://my.domain.com/zcomx/admin', "/zcomx/creators/index ?creator=admin"),
            ('http://my.domain.com/appadmin', "/zcomx/creators/index ?creator=appadmin"),
            ('http://my.domain.com/zcomx/appadmin', "/zcomx/creators/index ?creator=appadmin"),

            # Invalid controller (treated as creator name)
            ('http://my.domain.com/something', "/zcomx/creators/index ?creator=something"),
        ]
        for t in in_tests:
            self.assertEqual(filter_url(t[0]), t[1])

        # in_tests_exceptions = [
        #     'http://my.domain.com/aaa/bbb/a"bc.def',
        # ]
        # for t in in_tests_exceptions:
        #     self.assertRaises(HTTP, filter_url, t)

        out_tests = [
            #(URL, url)
            ('http://my.domain.com/zcomx/books/index', '/books'),
            ('http://my.domain.com/zcomx/books/book/1', '/books/book/1'),
            # Test: creators controller
            ('http://my.domain.com/zcomx/creators/index', '/creators'),
            ('https://my.domain.com/zcomx/search/index', '/search'),

            # Test: default/user/???
            ('http://my.domain.com/zcomx/default/user/login', '/default/user/login'),
            ('http://my.domain.com/zcomx/default/user/logout', '/default/user/logout'),

            # Static files
            ('http://my.domain.com/zcomx/static/images/favicon.ico', '/favicon.ico'),
            ('http://jimk.zsw.ca/zcomx/static/robots.txt', '/robots.txt'),
            ('http://my.domain.com/zcomx/static/images/loading.gif', '/zcomx/static/images/loading.gif'),
            ('http://my.domain.com/zcomx/static/css/custom.css', '/zcomx/static/css/custom.css'),
            ('http://my.domain.com/zcomx/static/js/web2py.js', '/zcomx/static/js/web2py.js'),

            # Test https
            ('https://my.domain.com/zcomx/books/index', '/books'),

            # Creators
            ('http://my.domain.com/creators/index/First_Last', '/First_Last'),
            ('http://my.domain.com/zcomx/creators/index/First_Last', '/First_Last'),
            ("http://my.domain.com/zcomx/creators/index/First_O'Last", "/First_O'Last"),
        ]
        for t in out_tests:
            self.assertEqual(filter_url(t[0], out=True), t[1])

        self.assertEqual(str(URL(a='zcomx', c='default', f='index')), '/')

    def test__route(self):
        auth_user_id = db.auth_user.insert(
            name='First Last',
            email='test__route@test.com',
        )
        db.commit()
        user = entity_to_row(db.auth_user, auth_user_id)
        self._objects.append(user)

        creator_id = db.creator.insert(
            auth_user_id=user.id,
            email='test__route@test.com',
            path_name='First Last',
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

        book_id = db.book.insert(
            name='My Book',
            publication_year=1999,
            book_type_id=self._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=creator.id,
            reader='slider',
        )
        db.commit()
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        page_id = db.book_page.insert(
            book_id=book.id,
            page_no=1,
        )
        db.commit()
        book_page = entity_to_row(db.book_page, page_id)
        self._objects.append(book_page)

        request = Storage()
        request.args = List()
        request.vars = Storage()

        self.assertEqual(route(db, request, auth), (None, None))

        # Creator as integer (creator_id)
        request.vars.creator = creator.id
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            ['auth_user', 'creator', 'links']
        )
        self.assertEqual(view, 'creators/creator.html')

        # Creator as name
        request.vars.creator = 'First_Last'
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            ['auth_user', 'creator', 'links']
        )
        self.assertEqual(view, 'creators/creator.html')

        # Book as name
        request.vars.creator = 'First_Last'
        request.vars.book = 'My_Book_(1999)'
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            [
                'auth_user',
                'book',
                'cover_image',
                'creator',
                'creator_links',
                'links',
                'page_count',
                'read_button'
            ]
        )
        self.assertEqual(view, 'books/book.html')

        # Book page: slider
        request.vars.creator = 'First_Last'
        request.vars.book = 'My_Book_(1999)'
        request.vars.page = '001.jpg'
        book_page_keys = [
            'auth_user',
            'book',
            'creator',
            'links',
            'pages',
            'reader',
            'size',
            'start_page_no',
        ]
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            book_page_keys
        )
        self.assertEqual(view, 'books/slider.html')

        # Book page: scroller
        book.update_record(reader='scroller')
        db.commit()
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            book_page_keys
        )
        self.assertEqual(view, 'books/scroller.html')

        # Book page: page no
        request.vars.page = '001.jpg'
        view_dict, view = route(db, request, auth)
        self.assertEqual(
            sorted(view_dict.keys()),
            book_page_keys
        )
        self.assertEqual(view, 'books/scroller.html')

        # Nonexistent creator
        request.vars.creator = 9999999
        self.assertEqual(route(db, request, auth), (None, None))
        request.vars.creator = '_Invalid_Creator_'
        self.assertEqual(route(db, request, auth), (None, None))

        # Nonexistent book
        request.vars.creator = 'First_Last'
        request.vars.book = 'Invalid_Book_(1900)'
        self.assertEqual(route(db, request, auth), (None, None))

        # Nonexistent book page
        request.vars.creator = 'First_Last'
        request.vars.book = 'My_Book_(1999)'
        request.vars.page = '999.jpg'
        self.assertEqual(route(db, request, auth), (None, None))
        request.vars.page = '999'
        self.assertEqual(route(db, request, auth), (None, None))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()