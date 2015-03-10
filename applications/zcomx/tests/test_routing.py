#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/routing.py

"""
import urllib
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.http import HTTP
from gluon.rewrite import filter_url
from gluon.storage import \
    List, \
    Storage
from applications.zcomx.modules.books import url_name as book_url_name
from applications.zcomx.modules.creators import url_name as creator_url_name
from applications.zcomx.modules.routing import Router
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestRouter(LocalTestCase):
    _auth_user = None
    _book = None
    _book_2 = None
    _book_2_name = None
    _book_2_page = None
    _book_2_page_2 = None
    _book_2_page_name = None
    _book_2page_2_name = None
    _book_name = None
    _book_page = None
    _book_page_2 = None
    _creator = None
    _creator_2 = None
    _creator_2_name = None
    _creator_name = None
    _first_creator_links = {}
    _keys_for_view = {}
    _page_2_name = None
    _page_name = None
    _request = None
    _type_id_by_name = {}

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

        first = db().select(
            db.book_page.id,
            db.book.id,
            db.creator.id,
            left=[
                db.book.on(db.book_page.book_id == db.book.id),
                db.creator.on(db.book.creator_id == db.creator.id),
                db.auth_user.on(db.creator.auth_user_id == db.auth_user.id),
            ],
            orderby=[db.creator.path_name, db.book_page.page_no],
            limitby=(0, 1),
        ).first()
        first_creator = entity_to_row(db.creator, first['creator'].id)
        first_creator_book = entity_to_row(db.book, first['book'].id)
        first_creator_book_page = entity_to_row(
            db.book_page,
            first['book_page'].id
        )

        first_creator_name = creator_url_name(first_creator)
        first_creator_book_name = book_url_name(first_creator_book)
        first_creator_page_name = '{p:03d}'.format(
            p=first_creator_book_page.page_no)

        cls._first_creator_links = Storage({
            'creator': 'http://127.0.0.1:8000/{c}'.format(
                c=urllib.quote(first_creator_name)
            ),
            'book': 'http://127.0.0.1:8000/{c}/{b}'.format(
                c=urllib.quote(first_creator_name),
                b=urllib.quote(first_creator_book_name)
            ),
            'page': 'http://127.0.0.1:8000/{c}/{b}/{p}'.format(
                c=urllib.quote(first_creator_name),
                b=urllib.quote(first_creator_book_name),
                p=urllib.quote(first_creator_page_name)
            ),
        })

        cls._auth_user = cls.add(db.auth_user, dict(
            name='First Last',
            email='test__auth_user@test.com',
        ))

        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email='test__creator@test.com',
            path_name='First Last',
        ))

        cls._creator_2 = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email='test__creator_2@test.com',
            path_name='John Hancock',
        ))

        cls._book = cls.add(db.book, dict(
            name='My Book',
            publication_year=1999,
            book_type_id=cls._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=cls._creator.id,
            reader='slider',
        ))

        cls._book_2 = cls.add(db.book, dict(
            name='My Second Book',
            publication_year=2002,
            book_type_id=cls._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=cls._creator_2.id,
            reader='slider',
        ))

        cls._book_page = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            image='book_page.image.000.aaa.png',
            page_no=1,
        ))

        cls._book_page_2 = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=2,
        ))

        cls._book_2_page = cls.add(db.book_page, dict(
            book_id=cls._book_2.id,
            page_no=1,
        ))

        cls._book_2_page_2 = cls.add(db.book_page, dict(
            book_id=cls._book_2.id,
            page_no=2,
        ))

        cls._creator_name = creator_url_name(cls._creator)
        cls._creator_2_name = creator_url_name(cls._creator_2)
        cls._book_name = book_url_name(cls._book)
        cls._book_2_name = book_url_name(cls._book_2)
        cls._page_name = '{p:03d}'.format(p=cls._book_page.page_no)
        cls._page_2_name = '{p:03d}'.format(p=cls._book_page_2.page_no)
        cls._book_2_page_name = '{p:03d}'.format(p=cls._book_2_page.page_no)
        cls._book_2page_2_name = '{p:03d}'.format(p=cls._book_2_page_2.page_no)

        cls._keys_for_view = {
            'creator': [
                'creator',
                'grid',
                'links',
                'ongoing_grid',
                'released_grid',
            ],
            'creator_monies': [
                'creator',
                'grid',
            ],
            'book': [
                'book',
                'cover_image',
                'creator',
                'creator_links',
                'links',
                'page_count',
            ],
            'page_image': [
                'image',
                'size',
            ],
            'page_not_found': [
                'message',
                'urls',
            ],
            'reader': [
                'book',
                'creator',
                'links',
                'pages',
                'reader',
                'size',
                'start_page_no',
            ]
        }

    def test____init__(self):
        router = Router(db, self._request, auth)
        self.assertTrue(router)

    def test__get_book(self):
        router = Router(db, self._request, auth)
        self.assertTrue(router.book_record is None)

        # request.vars.book not set
        got = router.get_book()
        self.assertEqual(got, None)
        self.assertTrue(router.book_record is None)

        router.request.vars.creator = 'First Last'
        router.request.vars.book = '_Fake Book_'
        got = router.get_book()
        self.assertEqual(got, None)
        self.assertTrue(router.book_record is None)

        router.request.vars.book = 'My Book'
        got = router.get_book()
        self.assertEqual(got.name, 'My Book')
        self.assertEqual(got.creator_id, self._creator.id)
        self.assertTrue(router.book_record is not None)

        # Subsequent calls get value from cache
        router.request.vars.book = '_Fake Book_'
        got = router.get_book()
        self.assertEqual(got.name, 'My Book')
        self.assertEqual(got.creator_id, self._creator.id)
        self.assertTrue(router.book_record is not None)

    def test__get_creator(self):
        router = Router(db, self._request, auth)
        self.assertTrue(router.creator_record is None)

        # request.vars.creator not set
        got = router.get_creator()
        self.assertEqual(got, None)
        self.assertTrue(router.creator_record is None)

        router.request.vars.creator = 'Fake_Creator'
        got = router.get_creator()
        self.assertEqual(got, None)
        self.assertTrue(router.creator_record is None)

        router.request.vars.creator = str(99999999)
        got = router.get_creator()
        self.assertEqual(got, None)
        self.assertTrue(router.creator_record is None)

        router.request.vars.creator = 'First_Last'
        got = router.get_creator()
        self.assertEqual(got.email, 'test__creator@test.com')
        self.assertEqual(got.path_name, 'First Last')
        self.assertTrue(router.creator_record is not None)

        # Subsequent calls get value from cache
        router.request.vars.creator = 'Fake_Creator'
        got = router.get_creator()
        self.assertEqual(got.email, 'test__creator@test.com')
        self.assertEqual(got.path_name, 'First Last')
        self.assertTrue(router.creator_record is not None)

        # Test by integer.
        router.creator_record = None
        router.request.vars.creator = str(self._creator.id)
        got = router.get_creator()
        self.assertEqual(got.email, 'test__creator@test.com')
        self.assertEqual(got.path_name, 'First Last')
        self.assertTrue(router.creator_record is not None)

    def test__get_book_page(self):
        router = Router(db, self._request, auth)
        self.assertTrue(router.book_page_record is None)

        # request.vars.page not set
        got = router.get_book_page()
        self.assertEqual(got, None)
        self.assertTrue(router.book_page_record is None)

        router.request.vars.creator = 'First Last'
        router.request.vars.book = 'My Book'
        router.request.vars.page = '999.jpg'
        got = router.get_book_page()
        self.assertEqual(got, None)
        self.assertTrue(router.book_page_record is None)

        router.request.vars.page = '001.jpg'
        got = router.get_book_page()
        self.assertEqual(got.book_id, self._book.id)
        self.assertEqual(got.page_no, 1)
        self.assertTrue(router.book_page_record is not None)

        # Subsequent calls get value from cache
        router.request.vars.page = '999.jpg'
        got = router.get_book_page()
        self.assertEqual(got.book_id, self._book.id)
        self.assertEqual(got.page_no, 1)
        self.assertTrue(router.book_page_record is not None)

        # Test as page no.
        router.book_page_record = None
        router.request.vars.page = '001'
        got = router.get_book_page()
        self.assertEqual(got.book_id, self._book.id)
        self.assertEqual(got.page_no, 1)
        self.assertTrue(router.book_page_record is not None)

        router.book_page_record = None
        router.request.vars.page = '002'
        got = router.get_book_page()
        self.assertEqual(got.book_id, self._book.id)
        self.assertEqual(got.page_no, 2)
        self.assertTrue(router.book_page_record is not None)

        # Test indicia page
        router.book_page_record = None
        router.request.vars.page = '003'
        got = router.get_book_page()
        self.assertEqual(got.id, None)    # The indicia has no book_page record
        self.assertEqual(got.book_id, self._book.id)
        self.assertEqual(got.page_no, 3)
        self.assertTrue(router.book_page_record is not None)

        # Test request of non-existent page
        router.book_page_record = None
        router.request.vars.page = '004'
        got = router.get_book_page()
        self.assertEqual(got, None)
        self.assertTrue(router.book_page_record is None)

        # Handle non-page value
        router.book_page_record = None
        router.request.vars.page = 'not_a_page'
        got = router.get_book_page()
        self.assertEqual(got, None)
        self.assertTrue(router.book_page_record is None)

    def test__get_reader(self):
        router = Router(db, self._request, auth)

        # No request.vars.reader, no book_record
        self.assertEqual(router.get_reader(), None)

        router.request.vars.reader = '_reader_'
        self.assertEqual(router.get_reader(), '_reader_')

        router.book_record = self._book
        self.assertEqual(router.get_reader(), '_reader_')

        del router.request.vars.reader
        self.assertEqual(router.get_reader(), 'slider')

        self._book.update_record(reader='scroller')
        db.commit()
        self.assertEqual(router.get_reader(), 'scroller')
        self._book.update_record(reader='slider')
        db.commit()

    def test__page_not_found(self):

        def do_test(request_vars, expect):
            """Run test."""
            self._request.vars = request_vars
            router = Router(db, self._request, auth)
            router.page_not_found()
            self.assertTrue('urls' in router.view_dict)
            self.assertEqual(dict(router.view_dict['urls']), expect.view_dict)
            self.assertEqual(router.view, expect.view)

        # Test first page, all parameters
        request_vars = Storage(dict(
            creator=self._creator_name,
            book=self._book_name,
            page=self._page_name,
        ))
        expect = Storage({
            'view_dict': {
                'suggestions': [
                    {
                        'label': 'Creator page:',
                        'url': 'http://127.0.0.1:8000/First_Last',
                    },
                    {
                        'label': 'Book page:',
                        'url': 'http://127.0.0.1:8000/First_Last/My_Book',
                    },
                    {
                        'label': 'Read:',
                        'url': 'http://127.0.0.1:8000/First_Last/My_Book/001',
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
            'view': 'errors/page_not_found.html',
        })
        crea_url = 'http://127.0.0.1:8000/John_Hancock'
        book_url = 'http://127.0.0.1:8000/John_Hancock/My_Second_Book'
        page_url = 'http://127.0.0.1:8000/John_Hancock/My_Second_Book/001'
        expect_2 = Storage({
            'view_dict': {
                'suggestions': [
                    {
                        'label': 'Creator page:',
                        'url': crea_url,
                    },
                    {
                        'label': 'Book page:',
                        'url': book_url,
                    },
                    {
                        'label': 'Read:',
                        'url': page_url,
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
            'view': 'errors/page_not_found.html',
        })

        do_test(request_vars, expect)

        # Second page should be found if indicated.
        request_vars.page = self._page_2_name
        expect.view_dict['suggestions'][2]['url'] = \
            'http://127.0.0.1:8000/First_Last/My_Book/002'
        do_test(request_vars, expect)

        # If page not indicated, first page of book should be found.
        del request_vars.page
        expect.view_dict['suggestions'][2]['url'] = \
            'http://127.0.0.1:8000/First_Last/My_Book/001'

        # If page doesn't exist, first page of book should be found.
        request_vars.page = '999'
        do_test(request_vars, expect)

        # If book doesn't match creator, first book of creator should be found
        request_vars = Storage(dict(
            creator=self._creator_name,
            book=self._book_2_name,
            page=self._book_2_page_name,
        ))
        do_test(request_vars, expect)

        request_vars = Storage(dict(
            creator=self._creator_2_name,
            book=self._book_name,
            page=self._page_name,
        ))
        do_test(request_vars, expect_2)

        # If book not indicated, first book of creator should be found.
        del request_vars.page
        del request_vars.book
        request_vars.creator = self._creator_name
        do_test(request_vars, expect)

        request_vars.creator = self._creator_2_name
        do_test(request_vars, expect_2)

        # If book doesn't exist, first book of creator should be found.
        request_vars.book = '_Fake_Book_'
        request_vars.creator = self._creator_name
        do_test(request_vars, expect)

        request_vars.creator = self._creator_2_name
        do_test(request_vars, expect_2)

        # If creator not indicated, first book of first creator should be
        # found.
        expect_first = Storage({
            'view_dict': {
                'suggestions': [
                    {
                        'label': 'Creator page:',
                        'url': self._first_creator_links.creator,
                    },
                    {
                        'label': 'Book page:',
                        'url': self._first_creator_links.book,
                    },
                    {
                        'label': 'Read:',
                        'url': self._first_creator_links.page,
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
            'view': 'errors/page_not_found.html',
        })

        # If invalid creator, first book of first creator should be found.
        if request_vars.page:
            del request_vars.page
        if request_vars.book:
            del request_vars.book
        request_vars.creator = '_Hannah _Montana'
        do_test(request_vars, expect_first)

        # If no creator, first book of first creator should be found.
        del request_vars.creator
        do_test(request_vars, expect_first)

        # Test missing web2py_original_uri
        self._request.env.web2py_original_uri = None
        request_vars.creator = self._creator_name
        request_vars.book = self._book_name
        request_vars.page = self._page_name
        router = Router(db, self._request, auth)
        router.page_not_found()
        self.assertTrue('urls' in router.view_dict)
        self.assertEqual(
            router.view_dict['urls'].invalid,
            'http://www.domain.com/request/uri/path'
        )
        self.assertEqual(router.view, expect.view)

    def test__preset_links(self):
        router = Router(db, self._request, auth)

        self._creator.update_record(
            shop=None,
            tumblr=None,
        )
        db.commit()

        # Creator not set.
        self.assertEqual(router.preset_links(), [])

        # Set creator but still no presets
        router.request.vars.creator = 'First_Last'
        self.assertEqual(router.preset_links(), [])

        def test_presets(links, expect):
            soups = [BeautifulSoup(str(x)) for x in links]
            anchors = [x.find('a') for x in soups]
            self.assertEqual(
                [x.string for x in anchors],
                expect
            )
            for anchor in anchors:
                if anchor.string == 'shop':
                    self.assertEqual(anchor['href'], 'http://www.shop.com')
                elif anchor.string == 'tumblr':
                    self.assertEqual(anchor['href'], 'user.tumblr.com')
                self.assertEqual(anchor['target'], '_blank')

        # Set creator.shop
        self._creator.update_record(
            shop='http://www.shop.com',
            tumblr=None
        )
        db.commit()
        router.creator_record = None
        test_presets(router.preset_links(), ['shop'])

        # Set creator.tumblr
        self._creator.update_record(
            shop=None,
            tumblr='user.tumblr.com',
        )
        db.commit()
        router.creator_record = None
        test_presets(router.preset_links(), ['tumblr'])

        # Set both creator.shop and creator.tumblr
        self._creator.update_record(
            shop='http://www.shop.com',
            tumblr='user.tumblr.com',
        )
        db.commit()
        router.creator_record = None
        test_presets(router.preset_links(), ['shop', 'tumblr'])

    def test__route(self):
        router = Router(db, self._request, auth)

        def book_views(book_id):
            return db(db.book_view.book_id == book_id).select()

        self.assertEqual(len(book_views(self._book.id)), 0)

        def do_test(request_vars, expect):
            """Run test."""
            self._request.vars = request_vars
            router = Router(db, self._request, auth)
            router.route()
            if 'redirect' in expect:
                self.assertEqual(router.redirect, expect.redirect)
            if 'view_dict' in expect:
                self.assertEqual(
                    dict(router.view_dict['urls']),
                    expect.view_dict
                )
            if 'view_dict_keys' in expect:
                self.assertEqual(
                    sorted(router.view_dict.keys()),
                    expect.view_dict_keys
                )
            self.assertEqual(router.view, expect.view)

        # No creator, should route to page_not_found with first creator.
        request_vars = Storage(dict())

        first_expect = Storage({
            'view_dict': {
                'suggestions': [
                    {
                        'label': 'Creator page:',
                        'url': self._first_creator_links.creator,
                    },
                    {
                        'label': 'Book page:',
                        'url': self._first_creator_links.book,
                    },
                    {
                        'label': 'Read:',
                        'url': self._first_creator_links.page,
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
            'view': 'errors/page_not_found.html',
        })
        do_test(request_vars, first_expect)
        self.assertEqual(len(book_views(self._book.id)), 0)

        router.route()
        self.assertEqual(
            router.view_dict['urls'],
            {
                'suggestions': [
                    {
                        'label': 'Creator page:',
                        'url': self._first_creator_links.creator,
                    },
                    {
                        'label': 'Book page:',
                        'url': self._first_creator_links.book,
                    },
                    {
                        'label': 'Read:',
                        'url': self._first_creator_links.page,
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
        )

        # Creator as integer (creator_id) should redirect.
        self.assertEqual(len(book_views(self._book.id)), 0)
        request_vars.creator = str(self._creator.id)
        expect = Storage({
            'redirect': '/First_Last',
        })
        do_test(request_vars, expect)

        # Creator as name
        self.assertEqual(len(book_views(self._book.id)), 0)
        request_vars.creator = 'First_Last'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['creator'],
            'view': 'creators/creator.html',
        })
        do_test(request_vars, expect)

        # Book as name
        self.assertEqual(len(book_views(self._book.id)), 0)
        request_vars.creator = 'First_Last'
        request_vars.book = 'My_Book'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['book'],
            'view': 'books/book.html',
        })
        do_test(request_vars, expect)

        # Book page: slider
        request_vars.creator = 'First_Last'
        request_vars.book = 'My_Book'
        request_vars.page = '001'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['reader'],
            'view': 'books/slider.html',
        })

        self.assertEqual(len(book_views(self._book.id)), 0)
        do_test(request_vars, expect)
        views = book_views(self._book.id)
        self.assertEqual(len(views), 1)
        for obj in views:
            self._objects.append(obj)

        # Book page: scroller
        self._book.update_record(reader='scroller')
        db.commit()
        expect = Storage({
            'view_dict_keys': self._keys_for_view['reader'],
            'view': 'books/scroller.html',
        })
        do_test(request_vars, expect)
        views = book_views(self._book.id)
        self.assertEqual(len(views), 2)
        for obj in views:
            self._objects.append(obj)

        self._book.update_record(reader='slider')
        db.commit()

        # Book page image
        request_vars.page = '001.jpg'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['page_image'],
            'view': 'books/page_image.html'
        })
        do_test(request_vars, expect)

        # Nonexistent creator
        request_vars.creator = str(9999999)
        expect_not_found = Storage({
            'view_dict_keys': self._keys_for_view['page_not_found'],
            'view': 'errors/page_not_found.html',
        })
        do_test(request_vars, expect_not_found)

        request_vars.creator = '_Invalid_Creator_'
        do_test(request_vars, expect_not_found)

        # Nonexistent book
        request_vars.creator = 'First_Last'
        request_vars.book = 'Some_Invalid_Book'
        do_test(request_vars, expect_not_found)

        # Nonexistent book page
        request_vars.creator = 'First_Last'
        request_vars.book = 'My_Book'
        request_vars.page = '999.jpg'
        do_test(request_vars, expect_not_found)

        request_vars.page = '999'
        do_test(request_vars, expect_not_found)

    def test__set_book_view(self):
        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        router.book_record = self._book
        router.set_book_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['book'],
        )
        self.assertEqual(
            router.view,
            'books/book.html',
        )
        self.assertEqual(router.redirect, None)

    def test__set_creator_monies_view(self):
        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        router.set_creator_monies_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['creator_monies'],
        )
        self.assertEqual(
            router.view,
            'creators/monies.html',
        )
        self.assertEqual(router.redirect, None)

    def test__set_creator_view(self):
        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        router.set_creator_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['creator'],
        )
        self.assertEqual(
            router.view,
            'creators/creator.html',
        )
        self.assertEqual(router.redirect, None)

    def test__set_page_image_view(self):
        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        router.book_record = self._book
        router.book_page_record = self._book_page
        router.set_page_image_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['page_image'],
        )
        self.assertEqual(
            router.view,
            'books/page_image.html',
        )
        self.assertEqual(router.redirect, None)

    def test__set_reader_view(self):
        def book_views(book_id):
            return db(db.book_view.book_id == book_id).select()

        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        router.book_record = self._book
        router.book_page_record = self._book_page
        self.assertEqual(len(book_views(self._book.id)), 0)
        router.set_reader_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['reader'],
        )
        self.assertEqual(
            router.view,
            'books/slider.html',
        )
        self.assertEqual(router.redirect, None)
        views = book_views(self._book.id)
        self.assertEqual(len(views), 1)
        for obj in views:
            self._objects.append(obj)

        router.book_record.update_record(reader='scroller')
        db.commit()
        db(db.book_view.book_id == self._book.id).delete()
        db.commit()
        self.assertEqual(len(book_views(self._book.id)), 0)
        router.set_reader_view()
        self.assertEqual(
            sorted(router.view_dict.keys()),
            self._keys_for_view['reader'],
        )
        self.assertEqual(
            router.view,
            'books/scroller.html',
        )
        views = book_views(self._book.id)
        self.assertEqual(len(views), 1)
        for obj in views:
            self._objects.append(obj)
        router.book_record.update_record(reader='slider')
        db.commit()

    def test__set_response_meta(self):
        router = Router(db, self._request, auth)
        router.creator_record = self._creator
        response.meta = Storage()

        def test_it(expect):
            meta = dict(response.meta)
            self.assertEqual(sorted(meta.keys()), sorted(expect.keys()))
            for k, v in expect.items():
                self.assertEqual(
                    meta[k],
                    {'content': v, 'property': k}
                )

        test_it({})

        # Router has no book, expect creator data.
        expect = {
            'og:description': 'Available at zco.mx',
            'og:image': '',
            'og:site_name': 'zco.mx',
            'og:title': 'First Last',
            'og:type': 'profile',
            'og:url': 'http://127.0.0.1:8000/First_Last'
        }
        router.set_response_meta()
        test_it(expect)

        bio = 'Creator of creations at zco.mx'
        router.creator_record.bio = bio
        expect['og:description'] = bio
        router.set_response_meta()
        test_it(expect)

        # Router has book, expect book data.
        router.book_record = self._book

        expect = {
            'og:description': 'By First Last available at zco.mx',
            'og:image': 'http://{cid}.zco.mx/My_Book/001.png'.format(
                cid=self._creator.id),
            'og:site_name': 'zco.mx',
            'og:title': 'My Book',
            'og:type': 'book',
            'og:url': 'http://127.0.0.1:8000/First_Last/My_Book'
        }

        router.set_response_meta()
        test_it(expect)

        descr = 'One of many fine books at zco.mx'
        router.book_record.description = descr
        expect['og:description'] = descr
        router.set_response_meta()
        test_it(expect)


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
            # (url, URL)
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
            ('http://my.domain.com/about', '/zcomx/default/about'),
            ('http://my.domain.com/contribute', '/zcomx/default/contribute'),
            ('http://my.domain.com/expenses', '/zcomx/default/expenses'),
            ('http://my.domain.com/faq', '/zcomx/default/faq'),
            ('http://my.domain.com/faqc', '/zcomx/default/faqc'),
            ('http://my.domain.com/files', '/zcomx/default/files'),
            ('http://my.domain.com/logos', '/zcomx/default/logos'),
            ('http://my.domain.com/overview', '/zcomx/default/overview'),
            ('http://my.domain.com/todo', '/zcomx/default/todo'),

            # Test: default/user/???
            ('http://my.domain.com/login', "/zcomx/default/user ['login']"),
            ('http://my.domain.com/default/user/login', "/zcomx/default/user ['login']"),
            ('http://my.domain.com/default/user/logout', "/zcomx/default/user ['logout']"),

            # Test torrents
            ('http://my.domain.com/abc.torrent', "/zcomx/torrents/route ?torrent=abc.torrent"),
            ('http://my.domain.com/zcomx/abc.torrent', "/zcomx/torrents/route ?torrent=abc.torrent"),
            ('http://my.domain.com/zco.mx.torrent', "/zcomx/torrents/route ?torrent=zco.mx.torrent"),
            ('http://my.domain.com/First_Last_(101.zco.mx).torrent', "/zcomx/torrents/route ?torrent=First_Last_(101.zco.mx).torrent"),
            ('http://my.domain.com/123/My Book 001.torrent', "/zcomx/torrents/route ?creator=123&torrent=My Book 001.torrent"),
            ('http://my.domain.com/First_Last/My Book 001.torrent', "/zcomx/torrents/route ?creator=First_Last&torrent=My Book 001.torrent"),

            # Static files
            ('http://my.domain.com/favicon.ico', app_root + '/zcomx/static/images/favicon.ico'),
            ('http://jimk.zsw.ca/robots.txt', app_root + '/zcomx/static/robots.txt'),
            ('http://my.domain.com/zcomx/static/images/loading/16x16.gif', app_root + '/zcomx/static/images/loading/16x16.gif'),
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
            ('http://my.domain.com/aaa/monies', "/zcomx/creators/index ?creator=aaa&monies=1"),
            ('http://my.domain.com/aaa/bbb/ccc', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),
            ('http://my.domain.com/zcomx/aaa', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/zcomx/aaa/bbb', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/zcomx/aaa/monies', "/zcomx/creators/index ?creator=aaa&monies=1"),
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

            # Monies
            ('http://my.domain.com/First_Last/monies', '/zcomx/creators/index ?creator=First_Last&monies=1'),
            # if anything after 'monies', assume 'monies' is a book title
            ('http://my.domain.com/zcomx/First_Last/monies/001', '/zcomx/creators/index ?creator=First_Last&book=monies&page=001'),

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
            # (URL, url)
            ('http://my.domain.com/zcomx/search/index', '/'),

            ('http://my.domain.com/zcomx/books/index', '/books'),
            ('http://my.domain.com/zcomx/books/book/1', '/books/book/1'),
            # Test: creators controller
            ('http://my.domain.com/zcomx/creators/index', '/creators'),

            # Test default functions
            ('http://my.domain.com/zcomx/default/about', '/about'),
            ('http://my.domain.com/zcomx/default/contribute', '/contribute'),
            ('http://my.domain.com/zcomx/default/expenses', '/expenses'),
            ('http://my.domain.com/zcomx/default/faq', '/faq'),
            ('http://my.domain.com/zcomx/default/faqc', '/faqc'),
            ('http://my.domain.com/zcomx/default/files', '/files'),
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

            # Test torrents
            ('http://my.domain.com/zcomx/abc.torrent/index', "/abc.torrent"),
            ('http://my.domain.com/zcomx/zco.mx.torrent/index', "/zco.mx.torrent"),
            ('http://my.domain.com/zcomx/First_Last_(101.zco.mx).torrent/index', "/First_Last_(101.zco.mx).torrent"),
            ('http://my.domain.com/zcomx/First_Last/My Book 001.torrent', "/First_Last/My Book 001.torrent"),
        ]
        for t in out_tests:
            self.assertEqual(filter_url(t[0], out=True), t[1])

        self.assertEqual(str(URL(a='zcomx', c='default', f='index')), '/')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
