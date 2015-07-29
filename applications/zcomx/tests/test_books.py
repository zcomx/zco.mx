#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

Test suite for zcomx/modules/books.py

"""
import ast
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
    book_pages, \
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
    follow_link, \
    formatted_name, \
    formatted_number, \
    get_page, \
    html_metadata, \
    images, \
    is_downloadable, \
    is_followable, \
    is_released, \
    magnet_link, \
    magnet_uri, \
    name_fields, \
    names, \
    next_book_in_series, \
    page_url, \
    publication_year_range, \
    publication_years, \
    read_link, \
    rss_url, \
    set_status, \
    short_page_img_url, \
    short_page_url, \
    short_url, \
    social_media_data, \
    torrent_file_name, \
    torrent_link, \
    torrent_url, \
    update_contributions_remaining, \
    update_rating, \
    url
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.tests.helpers import \
    ImageTestCase, \
    ResizerQuick
from applications.zcomx.modules.tests.runner import \
    LocalTestCase, \
    _mock_date as mock_date
from applications.zcomx.modules.utils import \
    entity_to_row
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

        creator = self.add(db.creator, dict(
            email='image_test_case@example.com',
        ))
        self._creator = Creator.from_id(creator.id)

        self._book = self.add(db.book, dict(
            name='Image Test Case',
            creator_id=self._creator.id,
        ))

        self._book_page = self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self._book_page_2 = self.add(db.book_page, dict(
            book_id=self._book.id,
            page_no=2,
        ))

        super(WithObjectsTestCase, self).setUp()

    def _set_pages(self, db, book_id, num_of_pages):
        set_pages(self, db, book_id, num_of_pages)


class TestBook(LocalTestCase):

    def test_parent__init__(self):
        book = Book({'name': '_test_parent__init__'})
        self.assertEqual(book.name, '_test_parent__init__')
        self.assertEqual(book.db_table, 'book')


class TestFunctions(WithObjectsTestCase, ImageTestCase):

    def test__book_name(self):
        book = self.add(db.book, dict(
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
            book_page_for_json(db, self._book_page.id),
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

    def test__book_pages(self):
        pages = book_pages(self._book)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].page_no, 1)
        self.assertEqual(pages[1].page_no, 2)

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

        as_json = book_pages_as_json(db, self._book.id)
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
            db, self._book.id, book_page_ids=[self._book_page.id])
        data = loads(as_json)
        self.assertTrue('files' in data)
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['name'], 'portrait.png')

    def test__book_pages_years(self):
        book = self.add(db.book, dict(name='test__book_pages_years'))

        self.assertEqual(book_pages_years(book), [])

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            created_on='2010-12-31 01:01:01',
        ))

        self.assertEqual(book_pages_years(book), [2010])

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=2,
            created_on='2011-12-31 01:01:01',
        ))

        self.assertEqual(book_pages_years(book), [2010, 2011])

        self.add(db.book_page, dict(
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

        book = self.add(db.book, dict(
            name='test__calc_contributions_remaining',
        ))

        # Book has no pages
        self.assertEqual(calc_contributions_remaining(db, book), 0.00)

        # Invalid book
        self.assertEqual(calc_contributions_remaining(db, -1), 0.00)

        self._set_pages(db, book.id, 10)
        self.assertEqual(contributions_target(db, book.id), 100.00)

        # Book has no contributions
        self.assertEqual(calc_contributions_remaining(db, book), 100.00)

        # Book has one contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        self.assertEqual(calc_contributions_remaining(db, book), 85.00)

        # Book has multiple contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        self.assertEqual(calc_contributions_remaining(db, book), 49.01)

    def test__calc_status(self):
        book = self.add(db.book, dict(
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
            pages = book_pages(book)

            if t[0] and not pages:
                self.add(db.book_page, dict(
                    book_id=book.id
                ))
            if not t[0] and pages:
                db(db.book_page.book_id == book.id).delete()
                db.commit()
            if t[1]:
                book.update_record(status=BOOK_STATUS_DISABLED)
                db.commit()
            else:
                book.update_record(status='')
                db.commit()
            self.assertEqual(calc_status(book), t[2])

    def test__cbz_comment(self):

        self.assertRaises(LookupError, cbz_comment, -1)

        cc_by_nd = CCLicence.by_code('CC BY-ND')

        book = self.add(db.book, dict(
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

        auth_user = self.add(db.auth_user, dict(name='Test CBZ Comment'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))
        book.update_record(creator_id=creator.id)
        db.commit()

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        fmt = '1999|Test CBZ Comment|My Book|02 (of 04)|CC BY-ND|http://{cid}.zco.mx'
        self.assertEqual(
            cbz_comment(book),
            fmt.format(cid=creator.id),
        )

    def test__cbz_link(self):
        creator = self.add(db.creator, dict(
            email='test__cbz_link@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-02of98'
        ))

        # As integer, book.id
        link = cbz_link(book.id)
        # Eg <a class="log_download_link"
        #   data-record_id="8979" data-record_table="book"
        #   href="/First_Last/My_Book_002.cbz">my_book_002.cbz</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.cbz')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.cbz'.format(i=book.id)
        )

        # As Row, book
        link = cbz_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.cbz')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.cbz'.format(i=book.id)
        )

        # Invalid id
        self.assertRaises(LookupError, cbz_link, -1)

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
        self.assertRaises(LookupError, cbz_url, -1)

        creator = self.add(db.creator, dict(
            email='test__cbz_url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(cbz_url(book), '/FirstLast/MyBook-002.cbz')

        book.update_record(name_for_url='MyBook-03of09')
        db.commit()
        self.assertEqual(
            cbz_url(book), '/FirstLast/MyBook-03of09.cbz')

    def test__cc_licence_data(self):
        str_to_date = lambda x: datetime.datetime.strptime(
            x, "%Y-%m-%d").date()
        datetime.date = mock_date(self, today_value=str_to_date('2014-12-31'))
        # date.today overridden
        self.assertEqual(datetime.date.today(), str_to_date('2014-12-31'))

        self.assertRaises(LookupError, cc_licence_data, -1)

        book = self.add(db.book, dict(
            name='test__cc_licence_data',
            creator_id=-1,
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestCcLicenceData',
        ))

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            created_on='2010-12-31 01:01:01',
        ))

        # no creator
        self.assertRaises(LookupError, cc_licence_data, book)

        auth_user = self.add(db.auth_user, dict(name='Test CC Licence Data'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))

        book.update_record(creator_id=creator.id)
        db.commit()
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

        book.update_record(cc_licence_place='Canada')
        db.commit()
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
        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=2,
            created_on='2014-12-31 01:01:01',
        ))

        self.assertEqual(cc_licence_data(book)['year'], '2010-2014')

    def test__complete_link(self):
        empty = '<span></span>'

        book = self.add(db.book, dict(
            name='test__complete_link',
        ))

        self.assertEqual(book.releasing, False)

        # As integer, book_id
        link = complete_link(book.id)
        # <a href="/login/book_release/2876">
        #   <div class="completed_checkbox_wrapper">
        #     <input type="checkbox" value="off" />
        #   </div>
        # </a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(
            anchor['href'],
            '/login/book_release/{i}'.format(i=book.id)
        )
        div = anchor.find('div')
        self.assertEqual(div['class'], 'completed_checkbox_wrapper')
        checkbox_input = div.find('input')
        self.assertEqual(checkbox_input['type'], 'checkbox')
        self.assertEqual(checkbox_input['value'], 'off')

        # As Row, book
        link = complete_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(
            anchor['href'],
            '/login/book_release/{i}'.format(i=book.id)
        )
        div = anchor.find('div')
        self.assertEqual(div['class'], 'completed_checkbox_wrapper')
        checkbox_input = div.find('input')
        self.assertEqual(checkbox_input['type'], 'checkbox')
        self.assertEqual(checkbox_input['value'], 'off')

        # Invalid id
        link = complete_link(-1)
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
        self.assertEqual(div['class'], 'completed_checkbox_wrapper')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__contribute_link(self):
        empty = '<span></span>'

        book = self.add(db.book, dict(
            name='test__contribute_link',
        ))

        # As integer, book_id
        link = contribute_link(db, book.id)
        # Eg    <a href="/contributions/modal?book_id=3713" target="_blank">
        #        Contribute
        #       </a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id={i}'.format(i=book.id)
        )

        # As Row, book
        link = contribute_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id={i}'.format(i=book.id)
        )

        # Invalid id
        link = contribute_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = contribute_link(db, book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = contribute_link(db, book, components=components)
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
        link = contribute_link(db, book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__contributions_remaining_by_creator(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        creator = Creator({'id': -1})

        # Creator has no books
        self.assertEqual(contributions_remaining_by_creator(creator), 0.00)

        book = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(db, book.id, 10)
        self.assertEqual(contributions_target(db, book.id), 100.00)

        # Book has no contributions
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            100.00
        )

        # Book has one contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            85.00
        )

        # Book has multiple contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            49.01
        )

        # Creator has multiple books.
        book_2 = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_DRAFT,
        ))
        self._set_pages(db, book_2.id, 5)
        self.assertEqual(contributions_target(db, book_2.id), 50.00)

        # status = draft
        self.assertEqual(
            contributions_remaining_by_creator(creator),
            49.01
        )
        book_2.update_record(status=BOOK_STATUS_ACTIVE)
        db.commit()
        self.assertAlmostEqual(
            contributions_remaining_by_creator(creator),
            99.01
        )

    def test__contributions_target(self):
        book = self.add(db.book, dict(name='test__contributions_target'))

        # Book has no pages
        self.assertEqual(contributions_target(db, book), 0.00)

        # Invalid book
        self.assertEqual(contributions_target(db, -1), 0.00)

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
            self._set_pages(db, book.id, t[0])
            self.assertEqual(contributions_target(db, book), t[1])

    def test__cover_image(self):

        placeholder = \
            '<div alt="" class="portrait_placeholder"></div>'

        self.assertEqual(str(cover_image(db, 0)), placeholder)

        book = self.add(db.book, dict(name='test__cover_image'))

        # Book has no pages
        for book_entity in [book, book.id]:
            self.assertEqual(str(cover_image(db, book_entity)), placeholder)

        book_images = [
            'book_page.image.page_trees.png',
            'book_page.image.page_flowers.png',
            'book_page.image.page_birds.png',
        ]
        for count, i in enumerate(book_images):
            self.add(db.book_page, dict(
                book_id=book.id,
                page_no=(count + 1),
                image=i,
            ))

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        for book_entity in [book, book.id]:
            self.assertEqual(
                str(cover_image(db, book_entity)),
                '<img alt="" src="/images/download/book_page.image.page_trees.png?cache=1&amp;size=original" />'
            )

    def test__default_contribute_amount(self):
        book = self.add(db.book, dict(name='test__default_contribute_amount'))

        # Book has no pages
        self.assertEqual(default_contribute_amount(db, book), 1.00)

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
            self._set_pages(db, book.id, t[0])
            self.assertEqual(default_contribute_amount(db, book), t[1])

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
        self._book.update_record(**data)
        db.commit()

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
        self._book.update_record(**data)
        db.commit()
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
        self._book.update_record(**data)
        db.commit()

        got = defaults(self._book.name, None)
        self.assertEqual(got, {})

    def test__download_link(self):
        empty = '<span></span>'

        book = self.add(db.book, dict(
            name='test__download_link',
            cbz='_test_cbz_',
            torrent='_test_torrent_',
        ))

        # As integer, book_id
        link = download_link(db, book.id)
        # Eg  <a href="/downloads/modal/4547">Download</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Download')
        self.assertEqual(
            anchor['href'],
            '/downloads/modal/{i}'.format(i=book.id)
        )

        # As Row, book
        link = download_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Download')
        self.assertEqual(
            anchor['href'],
            '/downloads/modal/{i}'.format(i=book.id)
        )

        # Invalid id
        link = download_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = download_link(db, book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = download_link(db, book, components=components)
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
        link = download_link(db, book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Download')
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
        book = self.add(db.book, dict(name='My Book'))

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
            book.update_record(**data)
            db.commit()
            self.assertEqual(
                formatted_name(db, book, include_publication_year=False),
                t[5]
            )
            self.assertEqual(
                formatted_name(db, book.id, include_publication_year=False),
                t[5]
            )
            self.assertEqual(formatted_name(db, book), t[6])
            self.assertEqual(formatted_name(db, book.id), t[6])

    def test__formatted_number(self):
        book = self.add(db.book, dict(name='My Book'))

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
            book.update_record(**data)
            db.commit()
            self.assertEqual(formatted_number(book), t[3])
            self.assertEqual(formatted_number(book.id), t[3])

    def test__get_page(self):
        book = self.add(db.book, dict(name='test__get_page'))

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

        book_page_1 = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
        ))

        for page_no in ['first', 'last', 1, None]:
            do_test(page_no, book_page_1)

        do_test(2, None)

        book_page_2 = self.add(db.book_page, dict(
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

        auth_user = self.add(db.auth_user, dict(name='First Last'))
        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            name_for_url='FirstLast',
            twitter='@firstlast',
        ))
        book = self.add(db.book, dict(
            name='My Book',
            number=2,
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
        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image='book_page.image.aaa.000.jpg',
        ))

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        expect['image_url'] = 'http://127.0.0.1:8000/images/download/book_page.image.aaa.000.jpg?size=web'
        self.assertEqual(html_metadata(book), expect)

    def test__images(self):
        book = self.add(db.book, dict(
            name='test_images'
        ))

        book_page_1 = self.add(db.book_page, dict(
            book_id=book.id
        ))

        book_page_2 = self.add(db.book_page, dict(
            book_id=book.id
        ))

        self.assertEqual(images(book), [])

        book_page_1.update_record(image='a.1.jpg')
        db.commit()
        self.assertEqual(images(book), ['a.1.jpg'])

        book_page_2.update_record(image='b.2.jpg')
        db.commit()
        self.assertEqual(sorted(images(book)), ['a.1.jpg', 'b.2.jpg'])

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
            # (status, releasing, release_date, expect)
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
                releasing=t[1],
                release_date=t[2],
            ))
            self.assertEqual(is_followable(book), t[3])

    def test__is_released(self):
        now = datetime.datetime.now()
        tests = [
            # (status, releasing, release_date, expect)
            ('a', False, now, True),
            ('d', False, now, False),
            ('x', False, now, False),
            ('a', True, now, False),
            ('a', False, None, False),
        ]
        for t in tests:
            book = Row(dict(
                name='test_is_released',
                status=t[0],
                releasing=t[1],
                release_date=t[2],
            ))
            self.assertEqual(is_released(book), t[3])

    def test__magnet_link(self):
        book = self.add(db.book, dict(
            name='My Book',
            number=2,
            book_type_id=BookType.by_name('ongoing').id,
            name_for_url='mybook-002',
        ))

        # book.cbz not set
        self.assertEqual(str(magnet_link(book)), str(SPAN('')))

        cbz_filename = '/tmp/test.cbz'
        with open(cbz_filename, 'w') as f:
            f.write('Fake cbz file used for testing.')

        book.update_record(cbz=cbz_filename)
        db.commit()

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

        # As integer, book.id
        link = magnet_link(book.id)
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
        self.assertEqual(anchor['data-record_id'], str(book.id))

        # As Row, book
        link = magnet_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-002.magnet')
        test_href(anchor['href'])
        self.assertEqual(anchor['class'], 'log_download_link')
        self.assertEqual(anchor['data-record_table'], 'book')
        self.assertEqual(anchor['data-record_id'], str(book.id))

        # Invalid id
        self.assertRaises(LookupError, magnet_link, -1)

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
        book = self.add(db.book, dict(
            name='Test Magnet URI'
        ))

        # No book
        self.assertEqual(magnet_uri(None), None)

        # book.cbz not set
        self.assertEqual(magnet_uri(book), None)

        cbz_filename = '/tmp/test.cbz'
        with open(cbz_filename, 'w') as f:
            f.write('Fake cbz file used for testing.')

        book.update_record(cbz=cbz_filename)
        db.commit()

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
        creator_one = -1
        creator_two = -2

        one_shot_1 = self.add(db.book, dict(
            name='one_shot',
            creator_id=creator_one,
            number=1,
            book_type_id=BookType.by_name('one-shot').id,
        ))

        one_shot_2 = self.add(db.book, dict(
            name='one_shot',
            creator_id=creator_one,
            number=2,
            book_type_id=BookType.by_name('one-shot').id,
        ))

        ongoing_1 = self.add(db.book, dict(
            name='ongoing',
            creator_id=creator_one,
            number=1,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        ongoing_2 = self.add(db.book, dict(
            name='ongoing',
            creator_id=creator_one,
            number=2,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        mini_series_1 = self.add(db.book, dict(
            name='mini_series',
            creator_id=creator_one,
            number=1,
            book_type_id=BookType.by_name('mini-series').id,
        ))

        mini_series_2 = self.add(db.book, dict(
            name='mini_series',
            creator_id=creator_one,
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
        self.add(db.book, dict(
            name='mini_series',
            creator_id=creator_two,
            number=3,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), None)

        # Test: book from different name is ignored
        self.add(db.book, dict(
            name='mini_series_ZZZ',
            creator_id=creator_one,
            number=3,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), None)

        # Test: skipped numbers are okay
        mini_series_3 = self.add(db.book, dict(
            name='mini_series',
            creator_id=creator_one,
            number=999,
            book_type_id=BookType.by_name('mini-series').id,
        ))
        self.assertEqual(next_book_in_series(mini_series_2), mini_series_3)

    def test__page_url(self):
        creator = self.add(db.creator, dict(
            email='test__page_url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
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

    def test__publication_year_range(self):
        start, end = publication_year_range()
        self.assertEqual(start, 1970)
        self.assertEqual(end, datetime.date.today().year + 5)

    def test__publication_years(self):
        xml = publication_years()
        got = ast.literal_eval(xml.xml())
        self.assertEqual(got[0], {'value':'1970', 'text':'1970'})
        self.assertEqual(got[1], {'value':'1971', 'text':'1971'})
        self.assertEqual(got[30], {'value':'2000', 'text':'2000'})
        final_year = datetime.date.today().year + 5 - 1
        self.assertEqual(
            got[-1],
            {'value':str(final_year), 'text':str(final_year)}
        )

    def test__read_link(self):
        empty = '<span></span>'

        creator = self.add(db.creator, dict(
            email='test__read_link@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='test__read_link',
            publication_year=1999,
            creator_id=creator.id,
            reader='slider',
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestReadLink',
        ))

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
        ))

        # As integer, book_id
        link = read_link(db, book.id)
        # Eg <a data-w2p_disable_with="default"
        #       href="/zcomx/books/slider/57">Read</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/TestReadLink/001'
        )

        # As Row, book
        link = read_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/TestReadLink/001'
        )

        # Invalid id
        link = read_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test reader variation
        book.reader = 'awesome_reader'
        link = read_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/TestReadLink/001'
        )

        # Test components param
        components = ['aaa', 'bbb']
        link = read_link(db, book, components=components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = read_link(db, book, components=components)
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
        link = read_link(db, book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__rss_url(self):
        self.assertRaises(LookupError, rss_url, -1)

        creator = self.add(db.creator, dict(
            email='test__torrent_url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(rss_url(book), '/FirstLast/MyBook-002.rss')

        book.update_record(name_for_url='MyBook-03of09')
        db.commit()
        self.assertEqual(
            rss_url(book), '/FirstLast/MyBook-03of09.rss')

    def test__set_status(self):
        book = self.add(db.book, dict(
            name='test__set_status',
        ))

        self.assertRaises(LookupError, set_status, -1, BOOK_STATUS_ACTIVE)
        self.assertRaises(ValueError, set_status, book, '_fake_')

        for s in BOOK_STATUSES:
            set_status(book, s)
            book_1 = db(db.book.id == book.id).select(limitby=(0, 1)).first()   # Reload
            self.assertEqual(book_1.status, s)

    def test__short_page_img_url(self):
        book = self.add(db.book, dict())
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
        book = self.add(db.book, dict())
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
        book = self.add(db.book, dict())
        tests = [
            # (creator_id, book name_for_url, expect)
            (None, None, None),
            (-1, 'MyBook', None),
            (98, 'MyBook', 'http://98.zco.mx/MyBook'),
            (101, 'MyBook-01of99', 'http://101.zco.mx/MyBook-01of99'),
        ]
        for t in tests:
            book.update_record(creator_id=t[0], name_for_url=t[1])
            db.commit()
            self.assertEqual(short_url(book), t[2])

    def test__social_media_data(self):

        self.assertEqual(social_media_data(None), {})

        creator = self.add(db.creator, dict(
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
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
        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            image='book_page.image.aaa.000.jpg',
        ))

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        expect['download_url'] = 'http://zco.mx/images/download/book_page.image.aaa.000.jpg?size=web'
        expect['cover_image_name'] = 'book_page.image.aaa.000.jpg'
        self.assertEqual(social_media_data(book), expect)

    def test__torrent_file_name(self):
        self.assertRaises(LookupError, torrent_file_name, -1)

        creator = self.add(db.creator, dict(
            email='test__torrent_file_name@example.com',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            number=2,
            creator_id=creator.id,
            publication_year=1999,
            book_type_id=BookType.by_name('ongoing').id,
        ))

        self.assertEqual(
            torrent_file_name(book),
            'My Book 002 (1999) ({i}.zco.mx).cbz.torrent'.format(i=creator.id)
        )

        data = dict(
            number=2,
            of_number=4,
            book_type_id=BookType.by_name('mini-series').id,
        )
        book.update_record(**data)
        db.commit()
        self.assertEqual(
            torrent_file_name(book),
            'My Book 02 (of 04) (1999) ({i}.zco.mx).cbz.torrent'.format(
                i=creator.id)
        )

    def test__torrent_link(self):
        creator = self.add(db.creator, dict(
            email='test__torrent_link@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-02of98'
        ))

        # As integer, book.id
        link = torrent_link(book.id)
        # Eg <a class="log_download_link"
        #   data-record_id="8979" data-record_table="book"
        #   href="/First_Last/My_Book_002.torrent">my_book_002.torrent</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.torrent')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.torrent'.format(i=book.id)
        )

        # As Row, book
        link = torrent_link(book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'mybook-02of98.torrent')
        self.assertEqual(
            anchor['href'],
            '/FirstLast/MyBook-02of98.torrent'.format(i=book.id)
        )

        # Invalid id
        self.assertRaises(LookupError, torrent_link, -1)

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
        self.assertRaises(LookupError, torrent_url, -1)

        creator = self.add(db.creator, dict(
            email='test__torrent_url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            creator_id=creator.id,
            name_for_url='MyBook-002',
        ))

        self.assertEqual(torrent_url(book), '/FirstLast/MyBook-002.torrent')

        book.update_record(name_for_url='MyBook-03of09')
        db.commit()
        self.assertEqual(
            torrent_url(book), '/FirstLast/MyBook-03of09.torrent')

    def test__update_contributions_remaining(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        creator_row = self.add(db.creator, dict(
            email='test__update_contributions_remaining@eg.com'
        ))
        creator = Creator.from_id(creator_row.id)

        book_contributions = lambda b: calc_contributions_remaining(db, b)
        creator_contributions = \
            lambda c: Creator.from_id(c.id).contributions_remaining

        # Creator has no books
        self.assertEqual(creator_contributions(creator), 0)

        book = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(db, book.id, 10)
        update_contributions_remaining(db, book)
        self.assertEqual(creator_contributions(creator), 100.00)
        self.assertEqual(book_contributions(book), 100.00)

        # Book has one contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        update_contributions_remaining(db, book)
        self.assertEqual(creator_contributions(creator), 85.00)
        self.assertEqual(book_contributions(book), 85.00)

        # Book has multiple contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        update_contributions_remaining(db, book)
        self.assertEqual(creator_contributions(creator), 49.01)
        self.assertEqual(book_contributions(book), 49.01)

        # Creator has multiple books.
        book_2 = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
            status=BOOK_STATUS_ACTIVE,
        ))
        self._set_pages(db, book_2.id, 5)
        update_contributions_remaining(db, book_2)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)
        self.assertEqual(book_contributions(book), 49.01)
        self.assertEqual(book_contributions(book_2), 50.00)

        # Creator contributions_remaining should be updated by any of it's
        # books.
        data = dict(contributions_remaining=0)
        db(db.creator.id == creator.id).update(**data)
        db.commit()
        creator.update(**data)
        self.assertEqual(creator_contributions(creator), 0)
        update_contributions_remaining(db, book)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)

    def test__update_rating(self):
        book_record = self.add(db.book, dict(name='test__update_rating'))
        book = Book.from_id(book_record.id)
        self._set_pages(db, book.id, 10)

        def reset(book):
            data = dict(
                contributions=0,
                contributions_remaining=0,
                downloads=0,
                views=0,
                rating=0,
            )
            db(db.book.id == book.id).update(**data)
            db.commit()

        def zero(storage):
            for k in storage.keys():
                storage[k] = 0

        def do_test(book, rating, expect):
            update_rating(db, book, rating=rating)
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
            db,
            book,
            rating='_invalid_'
        )

    def test__url(self):
        creator = self.add(db.creator, dict(
            email='test__url@example.com',
            name_for_url='FirstLast',
        ))

        book = self.add(db.book, dict(name=''))

        tests = [
            # (name, name_for_url, expect),
            (None, None, None),
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
            book.update_record(**data)
            db.commit()
            self.assertEqual(url(book), t[2])


def set_pages(obj, db, book_id, num_of_pages):
    """Create pages for a book."""
    # protected-access (W0212): *Access to a protected member
    # pylint: disable=W0212
    def page_count():
        return db(db.book_page.book_id == book_id).count()
    while page_count() < num_of_pages:
        obj.add(db.book_page, dict(
            book_id=book_id,
            page_no=(page_count() + 1),
        ))


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
