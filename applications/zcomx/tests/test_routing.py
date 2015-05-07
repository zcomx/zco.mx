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
from applications.zcomx.modules.books import book_name
from applications.zcomx.modules.creators import creator_name
from applications.zcomx.modules.routing import Router
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row
from applications.zcomx.modules.zco import \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT

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
            orderby=[db.creator.name_for_url, db.book_page.page_no],
            limitby=(0, 1),
        ).first()
        first_creator = entity_to_row(db.creator, first['creator'].id)
        first_creator_book = entity_to_row(db.book, first['book'].id)
        first_creator_book_page = entity_to_row(
            db.book_page,
            first['book_page'].id
        )

        first_creator_name = creator_name(first_creator, use='url')
        first_creator_book_name = book_name(first_creator_book, use='url')
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
            name_for_url='FirstLast',
        ))

        cls._creator_2 = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email='test__creator_2@test.com',
            name_for_url='JohnHancock',
        ))

        cls._book = cls.add(db.book, dict(
            name='My Book',
            publication_year=1999,
            book_type_id=cls._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=cls._creator.id,
            reader='slider',
            name_for_url='MyBook',
            status=BOOK_STATUS_ACTIVE,
        ))

        cls._book_2 = cls.add(db.book, dict(
            name='My Second Book',
            publication_year=2002,
            book_type_id=cls._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=cls._creator_2.id,
            reader='slider',
            name_for_url='MySecondBook',
            status=BOOK_STATUS_ACTIVE,
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

        cls._creator_name = creator_name(cls._creator, use='url')
        cls._creator_2_name = creator_name(cls._creator_2, use='url')
        cls._book_name = book_name(cls._book, use='url')
        cls._book_2_name = book_name(cls._book_2, use='url')
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

        router.request.vars.creator = 'FirstLast'
        router.request.vars.book = '_Fake Book_'
        got = router.get_book()
        self.assertEqual(got, None)
        self.assertTrue(router.book_record is None)

        # Test case variations
        tests = [
            'MyBook',
            'mybook',
            'mYbOoK',
        ]
        for t in tests:
            router.request.vars.book = t
            router.book_record = None       # clear cache
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

        # Test case variations
        tests = [
            'FirstLast',
            'firstlast',
            'fIrStLaSt',
        ]
        for t in tests:
            router.request.vars.creator = t
            router.creator_record = None        # clear cache
            got = router.get_creator()
            self.assertEqual(got.email, 'test__creator@test.com')
            self.assertEqual(got.name_for_url, 'FirstLast')
            self.assertTrue(router.creator_record is not None)

        # Subsequent calls get value from cache
        router.request.vars.creator = 'Fake_Creator'
        got = router.get_creator()
        self.assertEqual(got.email, 'test__creator@test.com')
        self.assertEqual(got.name_for_url, 'FirstLast')
        self.assertTrue(router.creator_record is not None)

        # Test by integer.
        router.creator_record = None
        router.request.vars.creator = str(self._creator.id)
        got = router.get_creator()
        self.assertEqual(got.email, 'test__creator@test.com')
        self.assertEqual(got.name_for_url, 'FirstLast')
        self.assertTrue(router.creator_record is not None)

    def test__get_book_page(self):
        router = Router(db, self._request, auth)
        self.assertTrue(router.book_page_record is None)

        # request.vars.page not set
        got = router.get_book_page()
        self.assertEqual(got, None)
        self.assertTrue(router.book_page_record is None)

        router.request.vars.creator = 'FirstLast'
        router.request.vars.book = 'MyBook'
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

        unreadable_statuses = [BOOK_STATUS_DRAFT, BOOK_STATUS_DISABLED]
        readers = ['_reader_', 'slider', 'scroller']
        router.book_record = self._book
        for status in unreadable_statuses:
            self._book.update_record(status=status)
            db.commit()
            for reader in readers:
                router.request.vars.reader = reader
                self.assertEqual(router.get_reader(), 'draft')

        self._book.update_record(status=BOOK_STATUS_ACTIVE)
        db.commit()
        router.book_record = None
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

        def do_test_random(request_vars):
            """Run test."""
            self._request.vars = request_vars
            router = Router(db, self._request, auth)
            router.page_not_found()

            self.assertTrue('urls' in router.view_dict)
            self.assertTrue('suggestions' in router.view_dict['urls'])
            labels = [
                x['label'] for x in router.view_dict['urls']['suggestions']]
            self.assertEqual(
                labels,
                ['Cartoonist page:', 'Book page:', 'Read:']
            )
            self.assertEqual(
                router.view_dict['urls']['invalid'],
                'http://www.domain.com/path/to/page'
            )
            self.assertEqual(router.view, 'errors/page_not_found.html')
            book_url = router.view_dict['urls']['suggestions'][1]['url']
            # http://127.0.0.1:8000/FirstLast/MyBook
            unused_scheme, _, unused_url, creator_for_url, book_for_url = \
                book_url.split('/')

            query = (db.creator.name_for_url == creator_for_url)
            got = db(query).select().first()
            self.assertTrue(got)
            got = db(db.book.name_for_url == book_for_url).select().first()
            self.assertTrue(got)
            self.assertTrue(got.release_date is not None)

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
                        'label': 'Cartoonist page:',
                        'url': 'http://127.0.0.1:8000/FirstLast',
                    },
                    {
                        'label': 'Book page:',
                        'url': 'http://127.0.0.1:8000/FirstLast/MyBook',
                    },
                    {
                        'label': 'Read:',
                        'url': 'http://127.0.0.1:8000/FirstLast/MyBook/001',
                    },
                ],
                'invalid': 'http://www.domain.com/path/to/page',
            },
            'view': 'errors/page_not_found.html',
        })
        crea_url = 'http://127.0.0.1:8000/JohnHancock'
        book_url = 'http://127.0.0.1:8000/JohnHancock/MySecondBook'
        page_url = 'http://127.0.0.1:8000/JohnHancock/MySecondBook/001'
        expect_2 = Storage({
            'view_dict': {
                'suggestions': [
                    {
                        'label': 'Cartoonist page:',
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
            'http://127.0.0.1:8000/FirstLast/MyBook/002'
        do_test(request_vars, expect)

        # If page not indicated, first page of book should be found.
        del request_vars.page
        expect.view_dict['suggestions'][2]['url'] = \
            'http://127.0.0.1:8000/FirstLast/MyBook/001'

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

        # If invalid creator, random released book is used.
        if request_vars.page:
            del request_vars.page
        if request_vars.book:
            del request_vars.book
        request_vars.creator = '_Invalid _Cartoonist'
        do_test_random(request_vars)

        # If no creator, first book of first creator should be found.
        del request_vars.creator
        do_test_random(request_vars)

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

        data = dict(
            shop=None,
            tumblr=None,
        )
        self._creator.update_record(**data)
        db.commit()

        # Creator not set.
        self.assertEqual(router.preset_links(), [])

        # Set creator but still no presets
        router.request.vars.creator = 'FirstLast'
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
        data = dict(
            shop='http://www.shop.com',
            tumblr=None
        )
        self._creator.update_record(**data)
        db.commit()
        router.creator_record = None
        test_presets(router.preset_links(), ['shop'])

        # Set creator.tumblr
        data = dict(
            shop=None,
            tumblr='user.tumblr.com',
        )
        self._creator.update_record(**data)
        db.commit()
        router.creator_record = None
        test_presets(router.preset_links(), ['tumblr'])

        # Set both creator.shop and creator.tumblr
        data = dict(
            shop='http://www.shop.com',
            tumblr='user.tumblr.com',
        )
        self._creator.update_record(**data)
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
                        'label': 'Cartoonist page:',
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
                        'label': 'Cartoonist page:',
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
            'redirect': '/FirstLast',
        })
        do_test(request_vars, expect)

        # Creator as name
        self.assertEqual(len(book_views(self._book.id)), 0)
        request_vars.creator = 'FirstLast'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['creator'],
            'view': 'creators/creator.html',
        })
        do_test(request_vars, expect)

        # Book as name
        self.assertEqual(len(book_views(self._book.id)), 0)
        request_vars.creator = 'FirstLast'
        request_vars.book = 'MyBook'
        expect = Storage({
            'view_dict_keys': self._keys_for_view['book'],
            'view': 'books/book.html',
        })
        do_test(request_vars, expect)

        # Book page: slider
        request_vars.creator = 'FirstLast'
        request_vars.book = 'MyBook'
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
        request_vars.creator = 'FirstLast'
        request_vars.book = 'Some_Invalid_Book'
        do_test(request_vars, expect_not_found)

        # Nonexistent book page
        request_vars.creator = 'FirstLast'
        request_vars.book = 'MyBook'
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
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        router = Router(db, self._request, auth)
        codes = ['opengraph']

        # Has book and creator
        router.book_record = self._book
        router.creator_record = self._creator
        response.meta = Storage()
        router.set_response_meta(codes)
        self.assertEqual(
            response.meta,
            {
                'og:description': {
                    'content': 'By First Last available at zco.mx',
                    'property': 'og:description'
                },
                'og:image': {
                    'content': 'http://127.0.0.1:8000/images/download/book_page.image.000.aaa.png?size=web',
                    'property': 'og:image'
                },
                'og:site_name': {
                    'content': 'zco.mx',
                    'property': 'og:site_name'
                },
                'og:title': {'content': 'My Book (1999)', 'property': 'og:title'},
                'og:type': {'content': 'book', 'property': 'og:type'},
                'og:url': {
                    'content': 'http://127.0.0.1:8000/FirstLast/MyBook',
                    'property': 'og:url'
                }
            }
        )

        # Has creator
        router.book_record = None
        router.creator_record = self._creator
        response.meta = Storage()
        router.set_response_meta(codes)
        self.assertEqual(
            response.meta,
            {
                'og:description': {
                    'content': 'Available at zco.mx',
                    'property': 'og:description'
                },
                'og:image': {
                    'content': '',
                    'property': 'og:image'
                },
                'og:site_name': {
                    'content': 'zco.mx',
                    'property': 'og:site_name'
                },
                'og:title': {'content': 'First Last', 'property': 'og:title'},
                'og:type': {'content': 'profile', 'property': 'og:type'},
                'og:url': {
                    'content': 'http://127.0.0.1:8000/FirstLast',
                    'property': 'og:url'
                }
            }
        )

        # Has neither book nor creator
        router.book_record = None
        router.creator_record = None
        response.meta = Storage()
        router.set_response_meta(codes)
        self.assertEqual(
            response.meta,
            {
                'og:description': {
                    'content': 'zco.mx is a curated not-for-profit comic-sharing website for self-publishing cartoonists and their readers.',
                    'property': 'og:description'
                },
                'og:image': {
                    'content': 'http://127.0.0.1:8000/zcomx/static/images/zco.mx-logo-small.png',
                    'property': 'og:image'
                },
                'og:site_name': {
                    'content': 'zco.mx',
                    'property': 'og:site_name'
                },
                'og:title': {'content': 'zco.mx', 'property': 'og:title'},
                'og:type': {'content': '', 'property': 'og:type'},
                'og:url': {
                    'content': 'http://127.0.0.1:8000/',
                    'property': 'og:url'
                }
            }
        )


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
            ('http://my.domain.com/FirstLast(101.zco.mx).torrent', "/zcomx/torrents/route ?torrent=FirstLast(101.zco.mx).torrent"),
            ('http://my.domain.com/123/My Book 001.torrent', "/zcomx/torrents/route ?creator=123&torrent=My Book 001.torrent"),
            ('http://my.domain.com/FirstLast/My Book 001.torrent', "/zcomx/torrents/route ?creator=FirstLast&torrent=My Book 001.torrent"),

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
            ('http://my.domain.com/aaa/', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/aaa/bbb', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/aaa/bbb/', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/aaa/monies', "/zcomx/creators/index ?creator=aaa&monies=1"),
            ('http://my.domain.com/aaa/monies/', "/zcomx/creators/index ?creator=aaa&monies=1"),
            ('http://my.domain.com/aaa/bbb/ccc', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),
            ('http://my.domain.com/aaa/bbb/ccc/', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),
            ('http://my.domain.com/zcomx/aaa', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/zcomx/aaa/', "/zcomx/creators/index ?creator=aaa"),
            ('http://my.domain.com/zcomx/aaa/bbb', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/zcomx/aaa/bbb/', "/zcomx/creators/index ?creator=aaa&book=bbb"),
            ('http://my.domain.com/zcomx/aaa/monies', "/zcomx/creators/index ?creator=aaa&monies=1"),
            ('http://my.domain.com/zcomx/aaa/monies/', "/zcomx/creators/index ?creator=aaa&monies=1"),
            ('http://my.domain.com/zcomx/aaa/bbb/ccc', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),
            ('http://my.domain.com/zcomx/aaa/bbb/ccc/', "/zcomx/creators/index ?creator=aaa&book=bbb&page=ccc"),

            # Creators
            ('http://my.domain.com/FirstLast', "/zcomx/creators/index ?creator=FirstLast"),
            ('http://my.domain.com/First_M_Last', "/zcomx/creators/index ?creator=First_M_Last"),
            ("http://my.domain.com/First_O'Last", "/zcomx/creators/index ?creator=First_O'Last"),

            # Books
            ('http://my.domain.com/FirstLast/MyBook', '/zcomx/creators/index ?creator=FirstLast&book=MyBook'),
            ('http://my.domain.com/FirstLast/MyBook_(2014)', '/zcomx/creators/index ?creator=FirstLast&book=MyBook_(2014)'),
            ('http://my.domain.com/FirstLast/MyBook_001_(2014)', '/zcomx/creators/index ?creator=FirstLast&book=MyBook_001_(2014)'),
            ('http://my.domain.com/FirstLast/MyBook_01_of_04_(2014)', '/zcomx/creators/index ?creator=FirstLast&book=MyBook_01_of_04_(2014)'),

            # Monies
            ('http://my.domain.com/FirstLast/monies', '/zcomx/creators/index ?creator=FirstLast&monies=1'),
            # if anything after 'monies', assume 'monies' is a book title
            ('http://my.domain.com/zcomx/FirstLast/monies/001', '/zcomx/creators/index ?creator=FirstLast&book=monies&page=001'),

            # Pages
            ('http://my.domain.com/zcomx/FirstLast/MyBook/001', '/zcomx/creators/index ?creator=FirstLast&book=MyBook&page=001'),
            ('http://my.domain.com/zcomx/FirstLast/MyBook/001.jpg', '/zcomx/creators/index ?creator=FirstLast&book=MyBook&page=001.jpg'),

            # Appadmin should be routed like any other url
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
            ('http://my.domain.com/creators/index/FirstLast', '/FirstLast'),
            ('http://my.domain.com/zcomx/creators/index/FirstLast', '/FirstLast'),
            ("http://my.domain.com/zcomx/creators/index/First_O'Last", "/First_O'Last"),

            # Test torrents
            ('http://my.domain.com/zcomx/abc.torrent/index', "/abc.torrent"),
            ('http://my.domain.com/zcomx/zco.mx.torrent/index', "/zco.mx.torrent"),
            ('http://my.domain.com/zcomx/FirstLast(101.zco.mx).torrent/index', "/FirstLast(101.zco.mx).torrent"),
            ('http://my.domain.com/zcomx/FirstLast/My Book 001.torrent', "/FirstLast/My Book 001.torrent"),
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
