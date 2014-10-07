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
from applications.zcomx.modules.routing import Router
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):
    _type_id_by_name = {}
    _request = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id
        cls._request = Storage()
        cls._request.env = Storage()
        cls._request.env.wsgi_url_scheme = 'http'
        cls._request.env.http_host = 'www.domain.com'
        cls._request.env.web2py_original_uri = '/path/to/page'
        cls._request.env.request_uri = '/request/uri/path'
        cls._request.args = List()
        cls._request.vars = Storage()

    def test_routes(self):
        """This tests the ~/routes.py settings."""
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        app_root = '/srv/http/jimk.zsw.ca/web2py/applications'
        in_tests = [
            #(url, URL)
            ('http://my.domain.com/', '/zcomx/search/index'),
            ('http://my.domain.com/zcomx', '/zcomx/search/index'),

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

            # Test default functions
            ('http://my.domain.com/contribute', '/zcomx/default/contribute'),
            ('http://my.domain.com/faq', '/zcomx/default/faq'),
            ('http://my.domain.com/faqc', '/zcomx/default/faqc'),
            ('http://my.domain.com/files', '/zcomx/default/files'),
            ('http://my.domain.com/goodwill', '/zcomx/default/goodwill'),
            ('http://my.domain.com/logos', '/zcomx/default/logos'),
            ('http://my.domain.com/overview', '/zcomx/default/overview'),
            ('http://my.domain.com/todo', '/zcomx/default/todo'),

            # Test: default/user/???
            ('http://my.domain.com/login', "/zcomx/default/user ['login']"),
            ('http://my.domain.com/default/user/login', "/zcomx/default/user ['login']"),
            ('http://my.domain.com/default/user/logout', "/zcomx/default/user ['logout']"),

            # Static files
            ('http://my.domain.com/favicon.ico', app_root + '/zcomx/static/images/favicon.ico'),
            ('http://jimk.zsw.ca/robots.txt', app_root + '/zcomx/static/robots.txt'),
            ('http://my.domain.com/zcomx/static/images/loading.gif', app_root + '/zcomx/static/images/loading.gif'),
            ('http://my.domain.com/zcomx/static/css/custom.css', app_root + '/zcomx/static/css/custom.css'),
            ('http://my.domain.com/zcomx/static/js/web2py.js', app_root + '/zcomx/static/js/web2py.js'),

            # Test https
            ('https://my.domain.com/', '/zcomx/search/index'),
            ('https://my.domain.com/zcomx', '/zcomx/search/index'),
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

            # Special characters
            ('http://my.domain.com/zcomx/a%26b', "/zcomx/creators/index ?creator=a%26b"),
            ('http://my.domain.com/zcomx/a+b', "/zcomx/creators/index ?creator=a%2Bb"),

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
            ('http://my.domain.com/zcomx/search/index', '/'),

            ('http://my.domain.com/zcomx/books/index', '/books'),
            ('http://my.domain.com/zcomx/books/book/1', '/books/book/1'),
            # Test: creators controller
            ('http://my.domain.com/zcomx/creators/index', '/creators'),

            # Test default functions
            ('http://my.domain.com/zcomx/default/contribute', '/contribute'),
            ('http://my.domain.com/zcomx/default/faq', '/faq'),
            ('http://my.domain.com/zcomx/default/faqc', '/faqc'),
            ('http://my.domain.com/zcomx/default/files', '/files'),
            ('http://my.domain.com/zcomx/default/goodwill', '/goodwill'),
            ('http://my.domain.com/zcomx/default/logos', '/logos'),
            ('http://my.domain.com/zcomx/default/overview', '/overview'),
            ('http://my.domain.com/zcomx/default/todo', '/todo'),

            # Test: default/user/???
            ('http://my.domain.com/zcomx/default/user/login', '/login'),
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
        return  #FIXME
        route = Router().route

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

        request = self._request

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

        def not_found(result):
            view_dict, view = result
            self.assertTrue('urls' in view_dict)
            self.assertEqual(
                view_dict['message'],
                'The requested page was not found on this server.'
            )
            self.assertEqual(view, 'default/page_not_found.html')

        # Nonexistent creator
        request.vars.creator = 9999999
        not_found(route(db, request, auth))
        request.vars.creator = '_Invalid_Creator_'
        not_found(route(db, request, auth))

        # Nonexistent book
        request.vars.creator = 'First_Last'
        request.vars.book = 'Invalid_Book_(1900)'
        not_found(route(db, request, auth))

        # Nonexistent book page
        request.vars.creator = 'First_Last'
        request.vars.book = 'My_Book_(1999)'
        request.vars.page = '999.jpg'
        not_found(route(db, request, auth))
        request.vars.page = '999'
        not_found(route(db, request, auth))

    def test__page_not_found(self):
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

        page_2_id = db.book_page.insert(
            book_id=book.id,
            page_no=2,
        )
        db.commit()
        book_page_2 = entity_to_row(db.book_page, page_2_id)
        self._objects.append(book_page_2)

        request = self._request

        view_dict, view = page_not_found(
            db, request, creator.id, book.id, book_page.id)
        self.assertTrue('urls' in view_dict)
        expect = {
            'creator': 'http://127.0.0.1:8000/First_Last',
            'book': 'http://127.0.0.1:8000/First_Last/My_Book',
            'page': 'http://127.0.0.1:8000/First_Last/My_Book/001',
            'invalid': 'http://www.domain.com/path/to/page',
        }
        self.assertEqual(dict(view_dict['urls']), expect)
        self.assertEqual(view, 'default/page_not_found.html')

        expect_2 = dict(expect)
        expect_2['page'] = \
            'http://127.0.0.1:8000/First_Last/My_Book/002'

        # Second page should be found if indicated.
        view_dict, view = page_not_found(
            db, request, creator.id, book.id, book_page_2.id)
        self.assertEqual(dict(view_dict['urls']), expect_2)

        # Book and creator should be found even if not indicated.
        view_dict, view = page_not_found(
            db, request, None, None, book_page.id)
        self.assertEqual(dict(view_dict['urls']), expect)

        # First page should be found if no page indicated.
        view_dict, view = page_not_found(
            db, request, creator.id, book.id, None)
        self.assertEqual(dict(view_dict['urls']), expect)

        # If book is indicated, first page should be found.
        view_dict, view = page_not_found(
            db, request, None, book.id, None)
        self.assertEqual(dict(view_dict['urls']), expect)

        # Creators first book should be found if nothing else specified.
        view_dict, view = page_not_found(db, request, creator.id, None, None)
        self.assertEqual(dict(view_dict['urls']), expect)

        # If nothing specified, it should work but will return the first
        # creator on file.
        view_dict, view = page_not_found(db, request, None, None, None)
        self.assertTrue('urls' in view_dict)
        self.assertEqual(
            sorted(view_dict['urls'].keys()),
            [
                'book',
                'creator',
                'invalid',
                'page',
            ]
        )
        self.assertEqual(view, 'default/page_not_found.html')

        # self.assertEqual(dict(view_dict['urls']), expect)

        # Test missing web2py_original_uri
        request.env.web2py_original_uri = None
        view_dict, view = page_not_found(
            db, request, creator.id, book.id, book_page.id)
        self.assertEqual(
            view_dict['urls'].invalid,
            'http://www.domain.com/request/uri/path'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
