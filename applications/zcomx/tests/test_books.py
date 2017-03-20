#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

Test suite for zcomx/modules/books.py

"""
import datetime
import unittest
import urlparse
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from pydal.objects import Row
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import \
    Book, \
    DEFAULT_BOOK_TYPE, \
    book_name, \
    book_page_for_json, \
    book_pages_as_json, \
    book_pages_years, \
    book_tables, \
    book_types, \
    calc_contributions_remaining, \
    calc_status, \
    cbz_comment, \
    cbz_link, \
    cbz_url, \
    cc_licence_data, \
    complete_link, \
    contribute_link, \
    contributions_remaining_by_creator, \
    contributions_target, \
    cover_image, \
    default_contribute_amount, \
    defaults, \
    download_link, \
    fileshare_link, \
    follow_link, \
    formatted_name, \
    formatted_number, \
    get_page, \
    html_metadata, \
    images, \
    is_completed, \
    is_downloadable, \
    is_followable, \
    magnet_link, \
    magnet_uri, \
    name_fields, \
    names, \
    next_book_in_series, \
    page_url, \
    publication_months, \
    publication_year_range, \
    read_link, \
    rss_url, \
    set_status, \
    short_page_img_url, \
    short_page_url, \
    short_url, \
    show_download_link, \
    social_media_data, \
    torrent_file_name, \
    torrent_link, \
    torrent_url, \
    update_contributions_remaining, \
    update_rating, \
    url
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.events import Contribution
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.mock import DateMock
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import \
    BOOK_STATUSES, \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):

        self._creator = self.add(Creator, dict(
            email='image_test_case@example.com',
        ))

        self._book = self.add(Book, dict(
            name='Image Test Case',
            creator_id=self._creator.id,
        ))

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self._book_page_2 = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        super(WithObjectsTestCase, self).setUp()

    def _set_pages(self, book, num_of_pages):
        set_pages(self, book, num_of_pages)


class TestBook(WithObjectsTestCase):

    def test_parent__init__(self):
        book = Book({'name': '_test_parent__init__'})
        self.assertEqual(book.name, '_test_parent__init__')
        self.assertEqual(book.db_table, 'book')

    def test__page_count(self):
        book = self.add(Book, dict(name='test__pages'))
        self.assertEqual(book.page_count(), 0)
        self.assertEqual(self._book.page_count(), 2)

    def test__pages(self):
        book = self.add(Book, dict(name='test__pages'))
        self.assertEqual(len(book.pages()), 0)

        pages = self._book.pages()
        for p in pages:
            self.assertTrue(isinstance(p, BookPage))
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].page_no, 1)
        self.assertEqual(pages[1].page_no, 2)

        # Test orderby
        orderby = [~db.book_page.page_no]
        pages = self._book.pages(orderby=orderby)
        self.assertEqual(pages[0].page_no, 2)
        self.assertEqual(pages[1].page_no, 1)

        # Test limitby
        pages = self._book.pages(limitby=(0, 1))
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_no, 1)


class TestFunctions(WithObjectsTestCase, ImageTestCase):

    def test__book_name(self):
        book = Book(dict(
            name='My Book',
            book_type_id=BookType.by_name('mini-series').id,
            number=2,
            of_number=19,
            name_for_search='my-search-kw',
            name_for_url='MyUrlName',
        ))

        tests = [
            # (use, expect)
            ('file', 'My Book 02 (of 19)'),
            ('search', 'my-search-kw'),
            ('url', 'MyUrlName'),
        ]

        for t in tests:
            self.assertEqual(book_name(book, use=t[0]), t[1])

    def test__book_page_for_json(self):
        filename = 'file.jpg'
        self._set_image(
            db.book_page.image,
            self._book_page,
            self._prep_image(filename),
            resizer=ResizerQuick
        )

        down_url = '/images/download/{img}'.format(img=self._book_page.image)
        thumb = '/images/download/{img}?size=web'.format(
            img=self._book_page.image)
        fmt = '/login/book_pages_handler/{bid}?book_page_id={pid}'
        delete_url = fmt.format(
            bid=self._book_page.book_id,
            pid=self._book_page.id
        )

        self.assertEqual(
            book_page_for_json(self._book_page),
            {
                'book_id': self._book_page.book_id,
                'book_page_id': self._book_page.id,
                'name': filename,
                'size': 23127,
                'url': down_url,
                'thumbnailUrl': thumb,
                'deleteUrl': delete_url,
                'deleteType': 'DELETE',
            }
        )

    def test__book_pages_as_json(self):
        filename = 'portrait.png'
        self._set_image(
            db.book_page.image,
            self._book_page,
            self._prep_image(filename),
            resizer=ResizerQuick
        )

        filename_2 = 'landscape.png'
        self._set_image(
            db.book_page.image,
            self._book_page_2,
            self._prep_image(filename_2),
            resizer=ResizerQuick
        )

        as_json = book_pages_as_json(self._book)
        data = loads(as_json)
        self.assertTrue('files' in data)
        self.assertEqual(len(data['files']), 2)
        self.assertEqual(sorted(data['files'][0].keys()), [
            'book_id',
            'book_page_id',
            'deleteType',
            'deleteUrl',
            'name',
            'size',
            'thumbnailUrl',
            'url',
        ])
        self.assertEqual(data['files'][0]['name'], 'portrait.png')
        self.assertEqual(data['files'][1]['name'], 'landscape.png')

        # Test book_page_ids param.
        as_json = book_pages_as_json(
            self._book, book_page_ids=[self._book_page.id])
        data = loads(as_json)
        self.assertTrue('files' in data)
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['name'], 'portrait.png')

    def test__book_pages_years(self):
        book = self.add(Book, dict(name='test__book_pages_years'))

        self.assertEqual(book_pages_years(book), [])

        self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
            created_on='2010-12-31 01:01:01',
        ))

        self.assertEqual(book_pages_years(book), [2010])

        self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
            created_on='2011-12-31 01:01:01',
        ))

        self.assertEqual(book_pages_years(book), [2010, 2011])

        self.add(BookPage, dict(
            book_id=book.id,
            page_no=3,
            created_on='2014-12-31 01:01:01',
        ))

        self.assertEqual(book_pages_years(book), [2010, 2011, 2014])

    def test__book_tables(self):
        bookish_fields = ['book_id']
        expect = []
        for table in db.tables:
            for field in db[table].fields:
                if field in bookish_fields:
                    expect.append(table)
                    continue
        self.assertEqual(sorted(book_tables()), sorted(expect))

    def test__book_types(self):
        xml = book_types(db)
        expect = (
            """{"value":"1", "text":"Ongoing (eg 001, 002, 003, etc)"},"""
            """{"value":"2", "text":"Mini-series (eg 01 of 04)"},"""
            """{"value":"3", "text":"One-shot/Graphic Novel"}"""
        )
        self.assertEqual(xml.xml(), expect)

    def test__calc_contributions_remaining(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103

        book = self.add(Book, dict(
            name='test__calc_contributions_remaining',
        ))

        # Book has no pages
        self.assertEqual(calc_contributions_remaining(book), 0.00)

        # Invalid book
        self.assertEqual(calc_contributions_remaining(None), 0.00)

        self._set_pages(book, 10)

        # Book has no contributions
        self.assertEqual(calc_contributions_remaining(book), 100.00)

        # Book has one contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        self.assertEqual(calc_contributions_remaining(book), 85.00)

        # Book has multiple contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        self.assertEqual(calc_contributions_remaining(book), 49.01)

    def test__calc_status(self):
        book = self.add(Book, dict(
            name='test__calc_status',
        ))

        tests = [
            # (pages, disabled, expect)
            (0, False, BOOK_STATUS_DRAFT),
            (0, True, BOOK_STATUS_DISABLED),
            (1, False, BOOK_STATUS_ACTIVE),
            (1, True, BOOK_STATUS_DISABLED),
        ]

        for t in tests:
            pages = book.pages()

            if t[0] and not pages:
                self.add(BookPage, dict(
                    book_id=book.id
                ))
            if not t[0] and pages:
                for page in book.pages():
                    page.delete()
            if t[1]:
                book = Book.from_updated(
                    book, dict(status=BOOK_STATUS_DISABLED))
            else:
                book = Book.from_updated(book, dict(status=''))
            self.assertEqual(calc_status(book), t[2])

    def test__cbz_comment(self):
        cc_by_nd = CCLicence.by_code('CC BY-ND')

        book = Book(dict(
            name='My Book',
            number=2,
            of_number=4,
            creator_id=-1,
            publication_year=1999,
            book_type_id=BookType.by_name('mini-series').id,
            cc_licence_id=cc_by_nd.id,
        ))

        # Creator record not found
        self.assertRaises(LookupError, cbz_comment, book)

        auth_user = self.add(AuthUser, dict(name='Test CBZ Comment'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))
        book.update(creator_id=creator.id)

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        fmt = '1999|Test CBZ Comment|My Book|02 (of 04)|CC BY-ND|http://{cid}.zco.mx'
        self.assertEqual(
            cbz_comment(book),
            fmt.format(cid=creator.id),
        )

    def test__cbz_link(self):
        empty = '<span></span>'

        creator = self.add(Creator, dict(
            email='test__cbz_link@example.com',
            name_for_url='FirstLast',
        ))

        book = Book(dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-02of98'
        ))

        link = cbz_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.cbz')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.cbz',
        )

        # Invalid book
        self.assertEqual(str(cbz_link(None)), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = cbz_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = cbz_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = cbz_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.cbz')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__cbz_url(self):
        creator = self.add(Creator, dict(
            email='test__cbz_url@example.com',
            name_for_url='FirstLast',
        ))

        book = Book(dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(cbz_url(book), '/FirstLast/MyBook-002.cbz')

        book.update(name_for_url='MyBook-03of09')
        self.assertEqual(cbz_url(book), '/FirstLast/MyBook-03of09.cbz')

    def test__cc_licence_data(self):
        test_today = datetime.date(2009, 12, 31)
        with DateMock(test_today):
            self.assertEqual(datetime.date.today(), test_today)

            auth_user = self.add(
                db.auth_user, dict(name='Test CC Licence Data'))
            creator = self.add(Creator, dict(auth_user_id=auth_user.id))

            book = self.add(Book, dict(
                id=-1,
                name='test__cc_licence_data',
                creator_id=creator.id,
                book_type_id=BookType.by_name('one-shot').id,
                name_for_url='TestCcLicenceData',
                cc_licence_place=None,
            ))

            self.add(BookPage, dict(
                book_id=book.id,
                page_no=1,
                created_on='2010-12-31 01:01:01',
            ))

            self.assertEqual(
                cc_licence_data(book),
                {
                    'owner': 'Test CC Licence Data',
                    'owner_url': 'http://{cid}.zco.mx'.format(cid=creator.id),
                    'year': '2010',
                    'place': None,
                    'title': 'test__cc_licence_data',
                    'title_url':
                        'http://{cid}.zco.mx/TestCcLicenceData'.format(
                            cid=creator.id),
                }
            )

            book = Book.from_updated(book, dict(cc_licence_place='Canada'))
            self.assertEqual(
                cc_licence_data(book),
                {
                    'owner': 'Test CC Licence Data',
                    'owner_url': 'http://{cid}.zco.mx'.format(cid=creator.id),
                    'year': '2010',
                    'place': 'Canada',
                    'title': 'test__cc_licence_data',
                    'title_url':
                        'http://{cid}.zco.mx/TestCcLicenceData'.format(
                            cid=creator.id),
                }
            )

            self.assertEqual(cc_licence_data(book)['year'], '2010')
            # Add second book page with different year.
            self.add(BookPage, dict(
                book_id=book.id,
                page_no=2,
                created_on='2014-12-31 01:01:01',
            ))

            self.assertEqual(cc_licence_data(book)['year'], '2010-2014')

    def test__complete_link(self):
        empty = '<span></span>'

        book = Book(dict(
            id=123,
            name='test__complete_link',
            complete_in_progress=False,
        ))

        self.assertEqual(book.complete_in_progress, False)

        link = complete_link(book)
        soup = BeautifulSoup(str(link))
        # <a href="/login/book_complete/2876">
        #   <div class="checkbox_wrapper">
        #     <input type="checkbox" value="off" />
        #   </div>
        # </a>
        anchor = soup.find('a')
        self.assertEqual(
            anchor['href'],
            '/login/book_complete/123'
        )
        div = anchor.find('div')
        self.assertEqual(div['class'], 'checkbox_wrapper')
        checkbox_input = div.find('input')
        self.assertEqual(checkbox_input['type'], 'checkbox')
        self.assertEqual(checkbox_input['value'], 'off')

        # Invalid id
        link = complete_link(None)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = complete_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = complete_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = complete_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        div = anchor.find('div')
        self.assertEqual(div['class'], 'checkbox_wrapper')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__contribute_link(self):
        empty = '<span></span>'

        book = Book(dict(
            id=123,
            name='test__contribute_link',
        ))

        link = contribute_link(book)
        # Eg    <a href="/contributions/modal?book_id=3713" target="_blank">
        #        Contribute
        #       </a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id=123'
        )

        # Invalid id
        link = contribute_link(None)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = contribute_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = contribute_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = contribute_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__contributions_remaining_by_creator(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        creator = self.add(Creator, dict(
            name_for_url='FirstLast',
        ))

        # Creator has no books
        self.assertEqual(contributions_remaining_by_creator(creator), 0.00)

        book = self.add(Book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(book, 10)
        self.assertEqual(contributions_target(book), 100.00)

        # Book has no contributions
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            100.00
        )

        # Book has one contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            85.00
        )

        # Book has multiple contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            49.01
        )

        # Creator has multiple books.
        book_2 = self.add(Book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_DRAFT,
        ))
        self._set_pages(book_2, 5)
        self.assertEqual(contributions_target(book_2), 50.00)

        # status = draft
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            49.01
        )
        book_2 = Book.from_updated(book_2, dict(status=BOOK_STATUS_ACTIVE))
        self.assertAlmostEqual(
            contributions_remaining_by_creator(creator),
            99.01
        )

    def test__contributions_target(self):
        book = self.add(Book, dict(name='test__contributions_target'))

        # Book has no pages
        self.assertEqual(contributions_target(book), 0.00)

        # Invalid book
        self.assertEqual(contributions_target(None), 0.00)

        tests = [
            # (pages, expect)
            (0, 0.00),
            (1, 10.00),
            (19, 190.00),
            (20, 200.00),
            (21, 210.00),
            (39, 390.00),
            (100, 1000.00),
        ]

        for t in tests:
            self._set_pages(book, t[0])
            self.assertEqual(contributions_target(book), t[1])

    def test__cover_image(self):

        placeholder = \
            '<div alt="" class="portrait_placeholder"></div>'

        self.assertEqual(str(cover_image(0)), placeholder)

        book = self.add(Book, dict(name='test__cover_image'))

        # Book has no pages
        self.assertEqual(str(cover_image(book)), placeholder)

        book_images = [
            'book_page.image.page_trees.png',
            'book_page.image.page_flowers.png',
            'book_page.image.page_birds.png',
        ]
        for count, i in enumerate(book_images):
            self.add(BookPage, dict(
                book_id=book.id,
                page_no=(count + 1),
                image=i,
            ))

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        self.assertEqual(
            str(cover_image(book)),
            '<img alt="" src="/images/download/book_page.image.page_trees.png?cache=1&amp;size=original" />'
        )

    def test__default_contribute_amount(self):
        book = self.add(Book, dict(name='test__default_contribute_amount'))

        # Book has no pages
        self.assertEqual(default_contribute_amount(book), 1.00)

        tests = [
            # (pages, expect)
            (0, 1.00),
            (1, 1.00),
            (19, 1.00),
            (20, 1.00),
            (21, 1.00),
            (39, 2.00),
            (40, 2.00),
            (41, 2.00),
            (100, 5.00),
        ]

        # Tests for books with many pages are slow and create many records
        # in the database. Require force to run.
        if self._opts.force:
            tests.append((400, 20.00))
            tests.append((1000, 20.00))

        for t in tests:
            self._set_pages(book, t[0])
            self.assertEqual(default_contribute_amount(book), t[1])

    def test__defaults(self):
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # Test book unique name
        got = defaults('_test__defaults_', self._creator)
        expect = {
            'name': '_test__defaults_',
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'number': 1,
            'of_number': 1,
            'creator_id': self._creator.id,
            'name_for_search': 'test-defaults',
            'name_for_url': 'TestDefaults',
        }
        self.assertEqual(got, expect)

        # Test book name not unique, various number values.
        data = dict(
            book_type_id=types_by_name[DEFAULT_BOOK_TYPE].id,
            number=1,
            of_number=1
        )
        self._book = Book.from_updated(self._book, data)

        got = defaults(self._book.name, self._creator)
        expect = {
            'name': self._book.name,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'number': 2,
            'of_number': 1,
            'creator_id': self._creator.id,
            'name_for_search': 'image-test-case',
            'name_for_url': 'ImageTestCase',
        }
        self.assertEqual(got, expect)

        data = dict(
            number=2,
            of_number=9
        )
        self._book = Book.from_updated(self._book, data)
        got = defaults(self._book.name, self._creator)
        expect = {
            'name': self._book.name,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'number': 3,
            'of_number': 9,
            'creator_id': self._creator.id,
            'name_for_search': 'image-test-case',
            'name_for_url': 'ImageTestCase',
        }
        self.assertEqual(got, expect)

        # Test invalid creator
        data = dict(
            book_type_id=types_by_name[DEFAULT_BOOK_TYPE].id,
            number=1,
            of_number=1
        )
        self._book = Book.from_updated(self._book, data)
        got = defaults(self._book.name, None)
        self.assertEqual(got, {})

    def test__download_link(self):
        empty = '<span></span>'

        book = Book(dict(
            id=123,
            name='test__download_link',
            cbz='_test_cbz_',
            torrent='_test_torrent_',
            status=BOOK_STATUS_ACTIVE,
        ))

        link = download_link(book)
        # Eg  <a href="/downloads/modal/4547">Download</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Download')
        self.assertEqual(
            anchor['href'],
            '/downloads/modal/123'
        )

        # Invalid id
        link = download_link(None)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = download_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = download_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = download_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Download')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large enabled')
        self.assertEqual(anchor['target'], '_blank')

        # Test disabled
        book.cbz = ''
        link = download_link(book)
        soup = BeautifulSoup(str(link))
        self.assertEqual(soup.find('a'), None)
        span = soup.find('span')
        # <span class="disabled"
        #   title="This book has not been released for file sharing."
        # >Download</span>
        self.assertEqual(span.string, 'Download')
        self.assertEqual(span['class'], 'disabled')
        self.assertEqual(
            span['title'],
            'This book has not been released for file sharing.'
        )

    def test__fileshare_link(self):
        empty = '<span></span>'

        book = Book(dict(
            id=123,
            name='test__fileshare_link',
            fileshare_in_progress=False,
        ))

        self.assertEqual(book.fileshare_in_progress, False)

        link = fileshare_link(book)
        soup = BeautifulSoup(str(link))
        # <a href="/login/book_fileshare/2876">
        #   <div class="checkbox_wrapper">
        #     <input type="checkbox" value="off" />
        #   </div>
        # </a>
        anchor = soup.find('a')
        self.assertEqual(
            anchor['href'],
            '/login/book_fileshare/123'
        )
        div = anchor.find('div')
        self.assertEqual(div['class'], 'checkbox_wrapper')
        checkbox_input = div.find('input')
        self.assertEqual(checkbox_input['type'], 'checkbox')
        self.assertEqual(checkbox_input['value'], 'off')

        # Invalid id
        link = fileshare_link(None)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = fileshare_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = fileshare_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = fileshare_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        div = anchor.find('div')
        self.assertEqual(div['class'], 'checkbox_wrapper')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__follow_link(self):
        book = Row(dict(
            name='test__follow_link',
            creator_id=123,
        ))

        link = follow_link(book)
        # Eg  <a href="/rss/modal/4547">Follow</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Follow')
        self.assertEqual(anchor['href'], '/rss/modal/123')

        # Test components param
        components = ['aaa', 'bbb']
        link = follow_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = follow_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = follow_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Follow')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__formatted_name(self):
        book = Book(dict(name='My Book'))

        tests = [
            # (name, pub year, type, number, of_number, expect, expect pub yr),
            ('My Book', 1999, 'one-shot', 1, 999, 'My Book', 'My Book (1999)'),
            (
                'My Book',
                1999,
                'ongoing',
                12,
                999,
                'My Book 012',
                'My Book 012 (1999)'
            ),
            (
                'My Book',
                1999,
                'mini-series',
                2,
                9,
                'My Book 02 (of 09)',
                'My Book 02 (of 09) (1999)'
            ),
        ]
        for t in tests:
            data = dict(
                name=t[0],
                publication_year=t[1],
                book_type_id=BookType.by_name(t[2]).id,
                number=t[3],
                of_number=t[4],
            )
            book.update(data)
            self.assertEqual(
                formatted_name(book, include_publication_year=False),
                t[5]
            )
            self.assertEqual(formatted_name(book), t[6])

    def test__formatted_number(self):
        book = Book(dict(name='My Book'))

        tests = [
            # (type, number, of_number, expect),
            ('one-shot', 1, 999, ''),
            ('ongoing', 12, 999, '012'),
            ('mini-series', 2, 9, '02 (of 09)'),
        ]
        for t in tests:
            data = dict(
                book_type_id=BookType.by_name(t[0]).id,
                number=t[1],
                of_number=t[2],
            )
            book.update(data)
            self.assertEqual(formatted_number(book), t[3])

    def test__get_page(self):
        book = self.add(Book, dict(name='test__get_page'))

        def do_test(page_no, expect):
            kwargs = {}
            if page_no is not None:
                kwargs = {'page_no': page_no}
            if expect is not None:
                book_page = get_page(book, **kwargs)
                self.assertEqual(book_page.id, expect.id)
            else:
                self.assertRaises(LookupError, get_page, book, **kwargs)

        for page_no in ['first', 'last', 'indicia', 1, 2, None]:
            do_test(page_no, None)

        book_page_1 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))

        for page_no in ['first', 'last', 1, None]:
            do_test(page_no, book_page_1)

        do_test(2, None)

        book_page_2 = self.add(BookPage, dict(
            book_id=book.id,
            page_no=2,
        ))

        for page_no in ['first', 1, None]:
            do_test(page_no, book_page_1)
        for page_no in ['last', 2]:
            do_test(page_no, book_page_2)
        do_test(3, None)

        last = get_page(book, page_no='last')
        indicia = get_page(book, page_no='indicia')
        self.assertEqual(indicia.id, None)
        self.assertEqual(indicia.book_id, book.id)
        self.assertEqual(indicia.page_no, last.page_no + 1)
        self.assertEqual(indicia.image, None)

    def test__html_metadata(self):

        self.assertEqual(html_metadata(None), {})

        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(
            auth_user_id=auth_user.id,
            name_for_url='FirstLast',
            twitter='@firstlast',
        ))
        book = self.add(Book, dict(
            name='My Book',
            number=2,
            of_number=1,
            book_type_id=BookType.by_name('ongoing').id,
            publication_year=1998,
            creator_id=creator.id,
            description='This is my book!',
            name_for_url='MyBook',
        ))

        # Book without cover
        expect = {
            'creator_name': 'First Last',
            'creator_twitter': '@firstlast',
            'description': 'This is my book!',
            'image_url': None,
            'name': 'My Book 002 (1998)',
            'type': 'book',
            'url': 'http://127.0.0.1:8000/FirstLast/MyBook'
        }
        self.assertEqual(html_metadata(book), expect)

        # Book with cover
        self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
            image='book_page.image.aaa.000.jpg',
        ))

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        expect['image_url'] = 'http://127.0.0.1:8000/images/download/book_page.image.aaa.000.jpg?size=web'
        self.assertEqual(html_metadata(book), expect)

    def test__images(self):
        book = self.add(Book, dict(name='test_images'))

        book_page_1 = self.add(BookPage, dict(
            book_id=book.id
        ))

        book_page_2 = self.add(BookPage, dict(
            book_id=book.id
        ))

        self.assertEqual(images(book), [])

        book_page_1.update_record(image='a.1.jpg')
        db.commit()
        self.assertEqual(images(book), ['a.1.jpg'])

        book_page_2.update_record(image='b.2.jpg')
        db.commit()
        self.assertEqual(sorted(images(book)), ['a.1.jpg', 'b.2.jpg'])

    def test__is_completed(self):
        now = datetime.datetime.now()
        tests = [
            # (status, complete_in_progress, release_date, expect)
            ('a', False, now, True),
            ('d', False, now, False),
            ('x', False, now, False),
            ('a', True, now, False),
            ('a', False, None, False),
        ]
        for t in tests:
            book = Row(dict(
                name='test_is_completed',
                status=t[0],
                complete_in_progress=t[1],
                release_date=t[2],
            ))
            self.assertEqual(is_completed(book), t[3])

    def test__is_downloadable(self):
        tests = [
            # (status, cbz, torrent, expect)
            ('a', '_cbz_', '_tor_', True),
            ('d', '_cbz_', '_tor_', False),
            ('x', '_cbz_', '_tor_', False),
            ('a', None, '_tor_', False),
            ('a', '_cbz_', None, False),
        ]
        for t in tests:
            book = Row(dict(
                name='test_is_downloadable',
                status=t[0],
                cbz=t[1],
                torrent=t[2],
            ))
            self.assertEqual(is_downloadable(book), t[3])

    def test__is_followable(self):
        now = datetime.datetime.now()
        tests = [
            # (status, complete_in_progress, release_date, expect)
            ('a', False, None, True),
            ('d', False, None, False),
            ('x', False, None, False),
            ('a', True, None, True),
            ('a', True, now, True),
            ('a', False, now, False),
        ]
        for t in tests:
            book = Row(dict(
                name='test_is_followable',
                status=t[0],
                complete_in_progress=t[1],
                release_date=t[2],
            ))
            self.assertEqual(is_followable(book), t[3])

    def test__magnet_link(self):
        # Invalid book
        self.assertEqual(str(magnet_link(None)), str(SPAN('')))

        book = Book(dict(
            id=123,
            name='My Book',
            number=2,
            book_type_id=BookType.by_name('ongoing').id,
            name_for_url='mybook-002',
            cbz=None,
        ))

        # book.cbz not set
        self.assertEqual(str(magnet_link(book)), str(SPAN('')))

        cbz_filename = '/tmp/test.cbz'
        with open(cbz_filename, 'w') as f:
            f.write('Fake cbz file used for testing.')

        book.update(cbz=cbz_filename)

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        def test_href(href):
            parsed = urlparse.urlparse(href)
            self.assertEqual(parsed.scheme, 'magnet')
            self.assertEqual(
                urlparse.parse_qs(parsed.query),
                {
                    'dn': ['test.cbz'],
                    'xl': ['31'],
                    'xt':
                    ['urn:tree:tiger:BOM3RWAED7BCOFOG5EX64QRBECPR4TRYRD7RFTA']
                }
            )

        link = magnet_link(book)
        soup = BeautifulSoup(str(link))
        # Eg <a class="log_download_link"
        #   data-record_id="8999" data-record_table="book"
        #   href="magnet:?xt=urn:tree:tiger:BOM3RWAED7BCOFOG5EX64QRBECPR4TRYRD7RFTA&amp;xl=31&amp;dn=test.cbz">
        #   testbook002.torrent</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-002.magnet')
        test_href(anchor['href'])
        self.assertEqual(anchor['class'], 'log_download_link')
        self.assertEqual(anchor['data-record_table'], 'book')
        self.assertEqual(anchor['data-record_id'], '123')

        # Test components param
        components = ['aaa', 'bbb']
        link = magnet_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = magnet_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = magnet_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-002.magnet')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__magnet_uri(self):
        book = Book(dict(
            id=123,
            name='Test Magnet URI',
            cbz=None,
        ))

        # No book
        self.assertEqual(magnet_uri(None), None)

        # book.cbz not set
        self.assertEqual(magnet_uri(book), None)

        cbz_filename = '/tmp/test.cbz'
        with open(cbz_filename, 'w') as f:
            f.write('Fake cbz file used for testing.')

        book.update(cbz=cbz_filename)

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        got = magnet_uri(book)
        # magnet:?xt=urn:tree:tiger:BOM3RWAED7BCOFOG5EX64QRBECPR4TRYRD7RFTA&xl=31&dn=test.cbz
        parsed = urlparse.urlparse(got)
        self.assertEqual(parsed.scheme, 'magnet')
        self.assertEqual(
            urlparse.parse_qs(parsed.query),
            {
                'dn': ['test.cbz'],
                'xl': ['31'],
                'xt': ['urn:tree:tiger:BOM3RWAED7BCOFOG5EX64QRBECPR4TRYRD7RFTA']
            }
        )

    def test__name_fields(self):
        self.assertEqual(
            name_fields(),
            [
                'name',
                'book_type_id',
                'number',
                'of_number',
            ]
        )

    def test__names(self):
        book = {
            'name': 'My Book',
            'number': 2,
            'of_number': 9,
            'book_type_id': BookType.by_name('mini-series').id,
        }

        # No fields
        self.assertEqual(
            names(book),
            {
                'name_for_file': 'My Book 02 (of 09)',
                'name_for_search': 'my-book-02-of-09',
                'name_for_url': 'MyBook-02of09',
            }
        )

        # db.book fields
        self.assertEqual(
            names(book, fields=db.book.fields),
            {
                'name_for_search': 'my-book-02-of-09',
                'name_for_url': 'MyBook-02of09',
            }
        )

        # custom fields
        fields = ['_fake_1', 'name_for_url', '_fake_2', 'name_for_file']
        self.assertEqual(
            names(book, fields=fields),
            {
                'name_for_file': 'My Book 02 (of 09)',
                'name_for_url': 'MyBook-02of09',
            }
        )

    def test__next_book_in_series(self):
        creator_one = self.add(Creator, dict(
            email='next_book_1@example.com',
        ))
        creator_two = self.add(Creator, dict(
            email='next_book_2@example.com',
        ))

        one_shot_1 = self.add(Book, dict(
            name='one_shot',
            creator_id=creator_one.id,
            number=1,
            book_type_id=BookType.by_name('one-shot').id,
        ))

        one_shot_2 = self.add(Book, dict(
            name='one_shot',
            creator_id=creator_one.id,
            number=2,
            book_type_id=BookType.by_name('one-shot').id,
        ))

        ongoing_1 = self.add(Book, dict(
            name='ongoing',
            creator_id=creator_one.id,
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        ongoing_2 = self.add(Book, dict(
            name='ongoing',
            creator_id=creator_one.id,
            number=2,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        mini_series_1 = self.add(Book, dict(
            name='mini_series',
            creator_id=creator_one.id,
            number=1,
            book_type_id=BookType.by_name('mini-series').id,
        ))

        mini_series_2 = self.add(Book, dict(
            name='mini_series',
            creator_id=creator_one.id,
            number=2,
            book_type_id=BookType.by_name('mini-series').id,
        ))

        tests = [
            # (book, next_book)
            (one_shot_1, None),
            (one_shot_2, None),
            (ongoing_1, ongoing_2),
            (ongoing_2, None),
            (mini_series_1, mini_series_2),
            (mini_series_2, None),
        ]

        for t in tests:
            self.assertEqual(next_book_in_series(t[0]), t[1])

        # Test: book from different creator is ignored
        self.add(Book, dict(
            name='mini_series',
            creator_id=creator_two.id,
            number=3,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), None)

        # Test: book from different name is ignored
        self.add(Book, dict(
            name='mini_series_ZZZ',
            creator_id=creator_one.id,
            number=3,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), None)

        # Test: skipped numbers are okay
        mini_series_3 = self.add(Book, dict(
            name='mini_series',
            creator_id=creator_one.id,
            number=999,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), mini_series_3)

    def test__page_url(self):
        creator = self.add(Creator, dict(
            email='test__page_url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(Book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-01of999',
        ))

        book_page = BookPage(
            book_id=book.id,
            page_no=1,
        )

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        self.assertEqual(
            page_url(book_page),
            '/FirstLast/MyBook-01of999/001'
        )

        self.assertEqual(
            page_url(book_page, reader='slider'),
            '/FirstLast/MyBook-01of999/001?reader=slider'
        )

        book_page.page_no = 99
        db.commit()
        self.assertEqual(
            page_url(book_page),
            '/FirstLast/MyBook-01of999/099'
        )

    def test__publication_months(self):
        self.assertEqual(
            publication_months(),
            [
                {'value': 1, 'text': 'Jan'},
                {'value': 2, 'text': 'Feb'},
                {'value': 3, 'text': 'Mar'},
                {'value': 4, 'text': 'Apr'},
                {'value': 5, 'text': 'May'},
                {'value': 6, 'text': 'Jun'},
                {'value': 7, 'text': 'Jul'},
                {'value': 8, 'text': 'Aug'},
                {'value': 9, 'text': 'Sep'},
                {'value': 10, 'text': 'Oct'},
                {'value': 11, 'text': 'Nov'},
                {'value': 12, 'text': 'Dec'},
            ]
        )

        self.assertEqual(
            publication_months(format_directive='%B'),
            [
                {'value': 1, 'text': 'January'},
                {'value': 2, 'text': 'February'},
                {'value': 3, 'text': 'March'},
                {'value': 4, 'text': 'April'},
                {'value': 5, 'text': 'May'},
                {'value': 6, 'text': 'June'},
                {'value': 7, 'text': 'July'},
                {'value': 8, 'text': 'August'},
                {'value': 9, 'text': 'September'},
                {'value': 10, 'text': 'October'},
                {'value': 11, 'text': 'November'},
                {'value': 12, 'text': 'December'},
            ]
        )

    def test__publication_year_range(self):
        start, end = publication_year_range()
        self.assertEqual(start, 1970)
        self.assertEqual(end, datetime.date.today().year + 5)

    def test__read_link(self):
        empty = '<span></span>'

        creator = self.add(Creator, dict(
            email='test__read_link@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(Book, dict(
            name='test__read_link',
            publication_year=1999,
            creator_id=creator.id,
            reader='slider',
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestReadLink',
        ))

        self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
        ))

        link = read_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/TestReadLink/001'
        )

        # Invalid id
        link = read_link(None)
        self.assertEqual(str(link), empty)

        # Test reader variation
        book.reader = 'awesome_reader'
        link = read_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/TestReadLink/001'
        )

        # Test components param
        components = ['aaa', 'bbb']
        link = read_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = read_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        book.reader = 'slider'
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = read_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__rss_url(self):
        self.assertEqual(rss_url(None), None)

        creator = self.add(Creator, dict(
            email='test__torrent_url@example.com',
            name_for_url='FirstLast',
        ))

        book = Book(dict(
            id=123,
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(rss_url(book), '/FirstLast/MyBook-002.rss')

        book.update(name_for_url='MyBook-03of09')
        self.assertEqual(
            rss_url(book), '/FirstLast/MyBook-03of09.rss')

    def test__set_status(self):
        book = self.add(Book, dict(
            name='test__set_status',
        ))

        self.assertRaises(ValueError, set_status, book, '_fake_')

        for s in BOOK_STATUSES:
            book = set_status(book, s)
            self.assertEqual(book.status, s)

    def test__short_page_img_url(self):
        book = self.add(Book, dict())
        book_page = BookPage(dict(book_id=book.id))
        tests = [
            # (creator_id, book name_for_url, page_no, image,  expect)
            (None, 'MyBook', 1, 'book_page.image.000.aaa.jpg', None),
            (-1, 'MyBook', 1, 'book_page.image.000.aaa.jpg', None),
            (
                98,
                'MyBook',
                1,
                'book_page.image.000.aaa.jpg',
                'http://98.zco.mx/MyBook/001.jpg'
            ),
            (
                101,
                'MyBook',
                2,
                'book_page.image.000.aaa.jpg',
                'http://101.zco.mx/MyBook/002.jpg'
            ),
            (
                101,
                'MyBook',
                2,
                'book_page.image.000.aaa.png',
                'http://101.zco.mx/MyBook/002.png'
            ),
        ]
        for t in tests:
            book.update_record(creator_id=t[0], name_for_url=t[1])
            db.commit()
            book_page.page_no = t[2]
            book_page.image = t[3]
            self.assertEqual(short_page_img_url(book_page), t[4])

    def test__short_page_url(self):
        book = self.add(Book, dict())
        book_page = BookPage(dict(book_id=book.id))
        tests = [
            # (creator_id, book name_for_url, page_no, expect)
            (None, None, 1, None),
            (-1, 'MyBook', 1, None),
            (98, 'MyBook', 1, 'http://98.zco.mx/MyBook/001'),
            (101, 'MyBook', 2, 'http://101.zco.mx/MyBook/002'),
        ]
        for t in tests:
            book.update_record(creator_id=t[0], name_for_url=t[1])
            db.commit()
            book_page.page_no = t[2]
            self.assertEqual(short_page_url(book_page), t[3])

    def test__short_url(self):
        book = Book(dict())
        tests = [
            # (creator_id, book name_for_url, expect)
            (None, None, None),
            (-1, 'MyBook', None),
            (98, 'MyBook', 'http://98.zco.mx/MyBook'),
            (101, 'MyBook-01of99', 'http://101.zco.mx/MyBook-01of99'),
        ]
        for t in tests:
            book.update(creator_id=t[0], name_for_url=t[1])
            self.assertEqual(short_url(book), t[2])

    def test__show_download_link(self):
        now = datetime.datetime.now()
        tests = [
            # (status, complete_in_progress, release_date, expect)
            ('a', False, now, True),
            ('d', False, now, False),
            ('x', False, now, False),
            ('a', True, now, False),
            ('a', False, None, False),
        ]
        for t in tests:
            book = Row(dict(
                name='test_show_download_link',
                status=t[0],
                complete_in_progress=t[1],
                release_date=t[2],
            ))
            self.assertEqual(show_download_link(book), t[3])

    def test__social_media_data(self):

        self.assertEqual(social_media_data(None), {})

        creator = self.add(Creator, dict(
            name_for_url='FirstLast',
        ))

        book = self.add(Book, dict(
            name='My Book',
            number=2,
            of_number=4,
            book_type_id=BookType.by_name('mini-series').id,
            creator_id=creator.id,
            description='This is my book!',
            name_for_url='MyBook',
            name_for_search='my-book-02-of-04',
            publication_year=1999,
        ))

        # Book without cover
        expect = {
            'cover_image_name': None,
            'description': 'This is my book!',
            'download_url': None,
            'formatted_name': 'My Book 02 (of 04) (1999)',
            'formatted_name_no_year': 'My Book 02 (of 04)',
            'formatted_number': '02 (of 04)',
            'name': 'My Book',
            'name_camelcase': 'MyBook',
            'name_for_search': 'my-book-02-of-04',
            'short_url': 'http://{cid}.zco.mx/MyBook'.format(cid=creator.id),
            'url': 'http://zco.mx/FirstLast/MyBook',
        }
        self.assertEqual(social_media_data(book), expect)

        # Book with cover
        self.add(BookPage, dict(
            book_id=book.id,
            page_no=1,
            image='book_page.image.aaa.000.jpg',
        ))

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        expect['download_url'] = 'https://zco.mx/images/download/book_page.image.aaa.000.jpg?size=web'
        expect['cover_image_name'] = 'book_page.image.aaa.000.jpg'
        self.assertEqual(social_media_data(book), expect)

    def test__torrent_file_name(self):
        self.assertEqual(torrent_file_name(None), None)

        creator = Creator(dict(
            id=123,
            email='test__torrent_file_name@example.com',
        ))

        book = Book(dict(
            name='My Book',
            number=2,
            of_number=9,
            creator_id=creator.id,
            publication_year=1999,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        self.assertEqual(
            torrent_file_name(book),
            'My Book 002 (1999) (123.zco.mx).cbz.torrent'
        )

        data = dict(
            number=2,
            of_number=4,
            book_type_id=BookType.by_name('mini-series').id,
        )
        book.update(**data)
        self.assertEqual(
            torrent_file_name(book),
            'My Book 02 (of 04) (1999) (123.zco.mx).cbz.torrent'
        )

    def test__torrent_link(self):
        self.assertEqual(str(torrent_link(None)), str(SPAN('')))

        creator = self.add(Creator, dict(
            email='test__torrent_link@example.com',
            name_for_url='FirstLast',
        ))

        book = Book(dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-02of98'
        ))

        # As Row, book
        link = torrent_link(book)
        soup = BeautifulSoup(str(link))
        # Eg <a class="log_download_link"
        #   data-record_id="8979" data-record_table="book"
        #   href="/First_Last/My_Book_002.torrent">my_book_002.torrent</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.torrent')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.torrent'
        )

        # Test components param
        components = ['aaa', 'bbb']
        link = torrent_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = torrent_link(book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = torrent_link(book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.torrent')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__torrent_url(self):
        self.assertEqual(torrent_url(None), None)

        creator = self.add(Creator, dict(
            email='test__torrent_url@example.com',
            name_for_url='FirstLast',
        ))

        book = Book(dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(torrent_url(book), '/FirstLast/MyBook-002.torrent')

        book.update(name_for_url='MyBook-03of09')
        self.assertEqual(
            torrent_url(book), '/FirstLast/MyBook-03of09.torrent')

    def test__update_contributions_remaining(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        creator = self.add(Creator, dict(
            email='test__update_contributions_remaining@eg.com'
        ))

        creator_contributions = \
            lambda c: Creator.from_id(c.id).contributions_remaining

        # Creator has no books
        self.assertEqual(creator_contributions(creator), 0)

        book = self.add(Book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(book, 10)
        update_contributions_remaining(book)
        self.assertEqual(creator_contributions(creator), 100.00)
        self.assertEqual(calc_contributions_remaining(book), 100.00)

        # Book has one contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        update_contributions_remaining(book)
        self.assertEqual(creator_contributions(creator), 85.00)
        self.assertEqual(calc_contributions_remaining(book), 85.00)

        # Book has multiple contribution
        self.add(Contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        update_contributions_remaining(book)
        self.assertEqual(creator_contributions(creator), 49.01)
        self.assertEqual(calc_contributions_remaining(book), 49.01)

        # Creator has multiple books.
        book_2 = self.add(Book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(book_2, 5)
        update_contributions_remaining(book_2)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)
        self.assertEqual(calc_contributions_remaining(book), 49.01)
        self.assertEqual(calc_contributions_remaining(book_2), 50.00)

        # Creator contributions_remaining should be updated by any of it's
        # books.
        data = dict(contributions_remaining=0)
        creator = Creator.from_updated(creator, data)
        self.assertEqual(creator_contributions(creator), 0)
        update_contributions_remaining(book)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)

    def test__update_rating(self):
        book = self.add(Book, dict(name='test__update_rating'))
        self._set_pages(book, 10)

        def reset(book):
            data = dict(
                contributions=0,
                contributions_remaining=0,
                downloads=0,
                views=0,
                rating=0,
            )
            book = Book.from_updated(book, data)

        def zero(storage):
            for k in storage.keys():
                storage[k] = 0

        def do_test(book, rating, expect):
            update_rating(book, rating=rating)
            query = (db.book.id == book.id)
            r = db(query).select(
                db.book.contributions,
                db.book.contributions_remaining,
                db.book.downloads,
                db.book.views,
                db.book.rating,
            ).first()
            for k, v in expect.items():
                # There may be some rounding foo, so use AlmostEqual
                self.assertAlmostEqual(r[k], v)

        def time_str(days_ago):
            return datetime.datetime.now() - datetime.timedelta(days=days_ago)

        # No rating records, so all values should be 0
        reset(book)
        expect = Storage(dict(
            contributions=0,
            contributions_remaining=100.00,
            downloads=0,
            views=0,
            rating=0,
        ))
        do_test(book, None, expect)

        records = [
            # (table, days_ago, amount)
            (db.contribution, 0, 11.11),
            (db.contribution, 100, 22.22),
            (db.contribution, 500, 44.44),
            (db.download, 0, None),
            (db.download, 100, None),
            (db.download, 500, None),
            (db.rating, 0, 1.1),
            (db.rating, 100, 2.2),
            (db.rating, 500, 4.4),
            (db.book_view, 0, None),
            (db.book_view, 100, None),
            (db.book_view, 500, None),
        ]

        for table, days_ago, amount in records:
            data = dict(book_id=book.id)
            data['time_stamp'] = time_str(days_ago)
            if amount is not None:
                data['amount'] = amount
            self.add(table, data)

        reset(book)
        zero(expect)
        expect.contributions = 77.77
        expect.contributions_remaining = 22.23   # 100.00 - (11.11+22.22+44.44)
        expect.downloads = 3
        expect.rating = 2.56666666                # Avg of 1.1, 2.2, and 4.4
        expect.views = 3
        do_test(book, None, expect)

        # Test rating='contribute'
        rating = 'contribution'
        reset(book)
        zero(expect)
        expect.contributions = 77.77
        expect.contributions_remaining = 22.23   # 100.00 - (11.11+22.22+44.44)
        do_test(book, rating, expect)

        # Test rating='download'
        rating = 'download'
        reset(book)
        zero(expect)
        expect.downloads = 3
        do_test(book, rating, expect)

        # Test rating='rating'
        rating = 'rating'
        reset(book)
        zero(expect)
        expect.rating = 2.56666666           # Avg of 1.1 and 3.3
        do_test(book, rating, expect)

        # Test rating='view'
        rating = 'view'
        reset(book)
        zero(expect)
        expect.views = 3
        do_test(book, rating, expect)

        # Test rating='_invalid_'
        self.assertRaises(
            SyntaxError,
            update_rating,
            book,
            rating='_invalid_'
        )

    def test__url(self):
        self.assertEqual(url(None), None)

        creator = self.add(Creator, dict(
            email='test__url@example.com',
            name_for_url='FirstLast',
        ))

        # Store book so effect of special chars in db is tested.
        book = self.add(Book, dict(name='TestUrl'))

        tests = [
            # (name, name_for_url, expect),
            ('My Book', 'MyBook', '/FirstLast/MyBook'),
            ('My Book', 'MyBook-012', '/FirstLast/MyBook-012'),
            (
                'My Book',
                'MyBook-02of09',
                '/FirstLast/MyBook-02of09'
            ),
            (
                "Hélè d'Eñça",
                "HélèDEñça-02of09",
                '/FirstLast/H%C3%A9l%C3%A8DE%C3%B1%C3%A7a-02of09'
            ),
        ]

        for t in tests:
            data = dict(
                name=t[0],
                name_for_url=t[1],
                creator_id=creator.id,
            )
            book = Book.from_updated(book, data)
            self.assertEqual(url(book), t[2])


def set_pages(obj, book, num_of_pages):
    """Create pages for a book."""
    while book.page_count() < num_of_pages:
        obj.add(BookPage, dict(
            book_id=book.id,
            page_no=(book.page_count() + 1),
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
