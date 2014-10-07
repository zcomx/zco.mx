#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/books.py

"""
import ast
import copy
import datetime
import os
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.contrib.simplejson import loads
from applications.zcomx.modules.books import \
    BookEvent, \
    ContributionEvent, \
    RatingEvent, \
    ViewEvent, \
    DEFAULT_BOOK_TYPE, \
    book_page_for_json, \
    book_pages_as_json, \
    book_types, \
    by_attributes, \
    cover_image, \
    default_contribute_amount, \
    defaults, \
    first_page, \
    formatted_name, \
    is_releasable, \
    numbers_for_book_type, \
    page_url, \
    parse_url_name, \
    publication_year_range, \
    publication_years, \
    read_link, \
    url, \
    url_name
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class EventTestCase(LocalTestCase):
    """ Base class for Event test cases. Sets up test data."""
    _book = None
    _user = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        book_id = db.book.insert(
            name='Event Test Case',
        )
        db.commit()
        cls._book = entity_to_row(db.book, book_id)
        cls._objects.append(cls._book)

        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))


class TestBookEvent(EventTestCase):
    def test____init__(self):
        event = BookEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        event = BookEvent(self._book, self._user.id)
        self.assertRaises(NotImplementedError, event.log, None)


class TestContributionEvent(EventTestCase):
    def test____init__(self):
        event = ContributionEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        event = ContributionEvent(self._book, self._user.id)

        # no value
        event_id = event.log()
        self.assertFalse(event_id)

        event_id = event.log(123.45)
        contribution = entity_to_row(db.contribution, event_id)
        self.assertEqual(contribution.id, event_id)
        self.assertAlmostEqual(
            contribution.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self.assertEqual(contribution.amount, 123.45)
        self._objects.append(contribution)


class TestRatingEvent(EventTestCase):
    def test____init__(self):
        event = RatingEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        event = RatingEvent(self._book, self._user.id)

        # no value
        event_id = event.log()
        self.assertFalse(event_id)

        event_id = event.log(5)
        rating = entity_to_row(db.rating, event_id)
        self.assertEqual(rating.id, event_id)
        self.assertAlmostEqual(
            rating.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self.assertEqual(rating.amount, 5)
        self._objects.append(rating)


class TestViewEvent(EventTestCase):
    def test____init__(self):
        event = ViewEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        event = ViewEvent(self._book, self._user.id)
        event_id = event.log()

        view = entity_to_row(db.book_view, event_id)
        self.assertEqual(view.id, event_id)
        self.assertAlmostEqual(
            view.time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )
        self._objects.append(view)


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/image_for_books'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'
    _type_id_by_name = {}

    _objects = []

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        if not os.path.exists(cls._image_original):
            os.makedirs(cls._image_original)

        # Store images in tmp directory
        db.book_page.image.uploadfolder = cls._image_original
        if not os.path.exists(db.book_page.image.uploadfolder):
            os.makedirs(db.book_page.image.uploadfolder)

        def create_image(image_name):
            image_filename = os.path.join(cls._image_dir, image_name)

            # Create an image to test with.
            im = Image.new('RGB', (1200, 1200))
            with open(image_filename, 'wb') as f:
                im.save(f)

            # Store the image in the uploads/original directory
            stored_filename = None
            with open(image_filename, 'rb') as f:
                stored_filename = db.book_page.image.store(f)
            return stored_filename

        creator_id = db.creator.insert(email='image_test_case@example.com')
        db.commit()
        cls._creator = entity_to_row(db.creator, creator_id)
        cls._objects.append(cls._creator)

        book_id = db.book.insert(
            name='Image Test Case',
            creator_id=cls._creator.id,
        )
        db.commit()
        cls._book = entity_to_row(db.book, book_id)
        cls._objects.append(cls._book)

        book_page_id = db.book_page.insert(
            book_id=book_id,
            page_no=1,
            image=create_image('file.jpg'),
        )
        db.commit()
        cls._book_page = entity_to_row(db.book_page, book_page_id)
        cls._objects.append(cls._book_page)

        # Create a second page to test with.
        book_page_id_2 = db.book_page.insert(
            book_id=book_id,
            page_no=2,
            image=create_image('file_2.jpg'),
        )
        db.commit()
        book_page_2 = entity_to_row(db.book_page, book_page_id_2)
        cls._objects.append(book_page_2)

        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)


class TestFunctions(ImageTestCase):

    def test__book_pages_as_json(self):
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
        self.assertEqual(data['files'][0]['name'], 'file.jpg')
        self.assertEqual(data['files'][1]['name'], 'file_2.jpg')

        # Test book_page_ids param.
        as_json = book_pages_as_json(
            db, self._book.id, book_page_ids=[self._book_page.id])
        data = loads(as_json)
        self.assertTrue('files' in data)
        self.assertEqual(len(data['files']), 1)
        self.assertEqual(data['files'][0]['name'], 'file.jpg')

    def test__book_page_for_json(self):

        filename, unused_original_fullname = db.book_page.image.retrieve(
            self._book_page.image,
            nameonly=True,
        )

        down_url = '/images/download/{img}'.format(img=self._book_page.image)
        thumb = '/images/download/{img}?size=tbn'.format(
            img=self._book_page.image)
        fmt = '/profile/book_pages_handler/{bid}?book_page_id={pid}'
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

    def test__book_types(self):
        xml = book_types(db)
        expect = (
            """{'value':'1', 'text':'Ongoing (eg 001, 002, 003, etc)'},"""
            """{'value':'2', 'text':'Mini-series (eg 01 of 04)'},"""
            """{'value':'3', 'text':'One-shot/Graphic Novel'}"""
        )
        self.assertEqual(xml.xml(), expect)

    def test__by_attributes(self):
        ids_by_name = {}
        books = {
            'a': {
                'name': 'My Book',
                'publication_year': 1999,
                'number': 1,
                'of_number': 1,
                'book_type_id': self._type_id_by_name['one-shot'],
            },
            'b': {
                'name': 'Some Title',
                'publication_year': 2000,
                'number': 2,
                'of_number': 1,
                'book_type_id': self._type_id_by_name['ongoing'],
            },
            'c': {
                'name': 'Another Book',
                'publication_year': 2001,
                'number': 2,
                'of_number': 9,
                'book_type_id': self._type_id_by_name['mini-series'],
            },
        }
        for key, data in books.items():
            book_id = db.book.insert(**data)
            book = entity_to_row(db.book, book_id)
            self._objects.append(book)
            ids_by_name[key] = book_id

        default_attrs = {
            'name': None,
            'publication_year': None,
            'number': None,
            'of_number': None,
            'book_type_id': None,
        }

        self.assertEqual(by_attributes({}), None)
        self.assertEqual(by_attributes(default_attrs), None)

        def do_test(attrs, expect):
            got = by_attributes(attrs)
            if expect is not None:
                self.assertEqual(got.id, ids_by_name[expect])
            else:
                self.assertEqual(got, None)

        for key, data in books.items():
            do_test(data, key)

        # Vary each field on it's own. Should return none.
        attrs = copy.copy(books['c'])
        attrs['name'] = '_Fake Name_'
        do_test(attrs, None)

        attrs = copy.copy(books['c'])
        attrs['publication_year'] = 1901
        do_test(attrs, None)

        attrs = copy.copy(books['c'])
        attrs['number'] = 99
        do_test(attrs, None)

        attrs = copy.copy(books['c'])
        attrs['of_number'] = 999
        do_test(attrs, None)

        attrs = copy.copy(books['c'])
        attrs['book_type_id'] = self._type_id_by_name['ongoing']
        do_test(attrs, None)

    def test__cover_image(self):

        placeholder = \
            '<div class="portrait_placeholder"></div>'

        self.assertEqual(str(cover_image(db, 0)), placeholder)

        book_id = db.book.insert(name='test__cover_image')
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        # Book has no pages
        self.assertEqual(str(cover_image(db, book_id)), placeholder)

        images = [
            'book_page.image.page_trees.png',
            'book_page.image.page_flowers.png',
            'book_page.image.page_birds.png',
        ]
        for count, i in enumerate(images):
            page_id = db.book_page.insert(
                book_id=book_id,
                page_no=(count + 1),
                image=i,
            )
            page = entity_to_row(db.book_page, page_id)
            self._objects.append(page)

        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(cover_image(db, book_id)),
            '<img src="/images/download/book_page.image.page_trees.png?size=original" />'
        )

    def test__default_contribute_amount(self):
        book_id = db.book.insert(name='test__default_contribute_amount')
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        # Book has no pages
        self.assertEqual(default_contribute_amount(db, book), 1.00)

        tests = [
            #(pages, expect)
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
            page_count = db(db.book_page.book_id == book.id).count()
            while page_count < t[0]:
                page_id = db.book_page.insert(
                    book_id=book_id,
                    page_no=(page_count + 1),
                )
                page = entity_to_row(db.book_page, page_id)
                self._objects.append(page)
                page_count = db(db.book_page.book_id == book.id).count()
            self.assertEqual(default_contribute_amount(db, book), t[1])

    def test__defaults(self):
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # Test book unique name
        got = defaults(db, '_test__defaults_', self._creator)
        expect = {
            'creator_id': self._creator.id,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id
        }
        self.assertEqual(got, expect)

        # Test book name not unique, various number values.
        self._book.update_record(
            book_type_id=types_by_name[DEFAULT_BOOK_TYPE].id,
            number=1,
            of_number=1
        )
        db.commit()

        got = defaults(db, self._book.name, self._creator)
        expect = {
            'creator_id': self._creator.id,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'number': 2,
            'of_number': 1,
        }
        self.assertEqual(got, expect)

        self._book.update_record(
            number=2,
            of_number=9
        )
        db.commit()
        got = defaults(db, self._book.name, self._creator)
        expect = {
            'creator_id': self._creator.id,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'number': 3,
            'of_number': 9,
        }
        self.assertEqual(got, expect)

        # Test: various book_types
        for book_type in ['one-shot', 'ongoing', 'mini-series']:
            self._book.update_record(
                book_type_id=types_by_name[book_type].id,
                number=1,
                of_number=1
            )
            db.commit()

            got = defaults(db, self._book.name, self._creator)
            expect = {
                'creator_id': self._creator.id,
                'book_type_id': types_by_name[book_type].id,
                'number': 2,
                'of_number': 1,
            }
            self.assertEqual(got, expect)

        # Test invalid creator
        self._book.update_record(
            book_type_id=types_by_name[DEFAULT_BOOK_TYPE].id,
            number=1,
            of_number=1
        )
        db.commit()

        got = defaults(db, self._book.name, -1)
        self.assertEqual(got, {})

    def test__first_page(self):
        book_id = db.book.insert(name='test__first_page')
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        # Book has no pages
        self.assertEqual(first_page(db, book_id), None)

        for count in range(0, 3):
            page_id = db.book_page.insert(
                book_id=book_id,
                page_no=(count + 1),
            )
            page = entity_to_row(db.book_page, page_id)
            self._objects.append(page)

        tests = [
            #(order_by, expect page_no)
            (None, 1),
            (db.book_page.page_no, 1),
            (~db.book_page.page_no, 3),
        ]
        for t in tests:
            page = first_page(db, book_id, orderby=t[0])
            for f in db.book_page.fields:
                self.assertTrue(f in page.keys())
            self.assertEqual(page.page_no, t[1])

    def test__formatted_name(self):
        book_id = db.book.insert(name='My Book')
        db.commit()
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        tests = [
            #(name, pub year, type, number, of_number, expect, expect pub yr),
            ('My Book', 1999, 'one-shot', 1, 999,
                'My Book', 'My Book (1999)'),
            ('My Book', 1999, 'ongoing', 12, 999,
                'My Book 012', 'My Book 012 (1999)'),
            ('My Book', 1999, 'mini-series', 2, 9,
                'My Book 02 (of 09)', 'My Book 02 (of 09) (1999)'),
        ]
        for t in tests:
            book.update_record(
                name=t[0],
                publication_year=t[1],
                book_type_id=self._type_id_by_name[t[2]],
                number=t[3],
                of_number=t[4],
            )
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

    def test__is_releasable(self):
        book_id = db.book.insert(
            name='test__is_releasable',
        )
        db.commit()
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        book_page_id = db.book_page.insert(
            book_id=book.id,
            page_no=1,
        )
        db.commit()
        book_page = entity_to_row(db.book_page, book_page_id)
        self._objects.append(book_page)

        # Has name and pages.
        self.assertTrue(is_releasable(db, book))

        # As id
        self.assertTrue(is_releasable(db, book.id))

        # No name
        book.name = ''
        self.assertFalse(is_releasable(db, book))
        book.name = 'test__is_releasable'
        self.assertTrue(is_releasable(db, book))

        # No pages
        db(db.book_page.id == book_page.id).update(book_id=-1)
        db.commit()
        self.assertFalse(is_releasable(db, book))

    def test__numbers_for_book_type(self):
        type_id_by_name = {}
        for t in db(db.book_type).select():
            type_id_by_name[t.name] = t.id

        tests = [
            #(name, expect)
            ('ongoing', {'of_number': False, 'number': True}),
            ('mini-series', {'of_number': True, 'number': True}),
            ('one-shot', {'of_number': False, 'number': False}),
        ]

        for t in tests:
            self.assertEqual(
                numbers_for_book_type(db, type_id_by_name[t[0]]),
                t[1]
            )
        self.assertEqual(
            numbers_for_book_type(db, -1),
            {'of_number': False, 'number': False}
        )

    def test__page_url(self):
        creator_id = db.creator.insert(
            email='test__page_url@example.com',
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

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        self.assertEqual(
            page_url(book_page),
            '/First_Last/My_Book/001'
        )

        self.assertEqual(
            page_url(book_page, reader='slider'),
            '/First_Last/My_Book/001?reader=slider'
        )

        book_page.update_record(page_no=99)
        db.commit()
        self.assertEqual(
            page_url(book_page),
            '/First_Last/My_Book/099'
        )

    def test__parse_url_name(self):

        tests = [
            #(url_name, expect),
            (None, None),
            ('My_Book', {
                'name': 'My Book',
                'book_type_id': self._type_id_by_name['one-shot'],
                'number': None,
                'of_number': None,
            }),
            ('My_Book_012', {
                'name': 'My Book',
                'book_type_id': self._type_id_by_name['ongoing'],
                'number': 12,
                'of_number': None,
            }),
            ('My_Book_02_(of_09)', {
                'name': 'My Book',
                'book_type_id': self._type_id_by_name['mini-series'],
                'number': 2,
                'of_number': 9,
            }),
            # Tricky stuff
            ("Hélè d'Eñça_02_(of_09)", {
                'name': "Hélè d'Eñça",
                'book_type_id': self._type_id_by_name['mini-series'],
                'number': 2,
                'of_number': 9,
            }),
            ('Bond_007_012', {
                'name': 'Bond 007',
                'book_type_id': self._type_id_by_name['ongoing'],
                'number': 12,
                'of_number': None,
            }),
            ('Agent_05_of_99_02_(of_09)', {
                'name': 'Agent 05 of 99',
                'book_type_id': self._type_id_by_name['mini-series'],
                'number': 2,
                'of_number': 9,
            }),
            ('My_Book', {
                'name': 'My Book',
                'book_type_id': self._type_id_by_name['one-shot'],
                'number': None,
                'of_number': None,
            }),
        ]

        for t in tests:
            self.assertEqual(parse_url_name(t[0]), t[1])

    def test__publication_year_range(self):
        start, end = publication_year_range()
        self.assertEqual(start, 1900)
        self.assertEqual(end, datetime.date.today().year + 5)

    def test__publication_years(self):
        xml = publication_years()
        got = ast.literal_eval(xml.xml())
        self.assertEqual(got[0], {'value':'1900', 'text':'1900'})
        self.assertEqual(got[1], {'value':'1901', 'text':'1901'})
        self.assertEqual(got[100], {'value':'2000', 'text':'2000'})
        final_year = datetime.date.today().year + 5 - 1
        self.assertEqual(
            got[-1],
            {'value':str(final_year), 'text':str(final_year)}
        )

    def test__read_link(self):
        empty = '<span></span>'

        creator_id = db.creator.insert(
            email='test__read_link@example.com',
            path_name='First Last',
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

        book_id = db.book.insert(
            name='test__read_link',
            publication_year=1999,
            creator_id=creator.id,
            reader='slider',
            book_type_id=self._type_id_by_name['one-shot'],
        )
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        book_page_id = db.book_page.insert(
            book_id=book.id,
            page_no=1,
        )
        db.commit()
        book_page = entity_to_row(db.book_page, book_page_id)
        self._objects.append(book_page)

        # As integer, book_id
        link = read_link(db, book_id)
        # Eg <a data-w2p_disable_with="default"
        #       href="/zcomx/books/slider/57">Read</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/First_Last/test__read_link/001'
        )

        # As Row, book
        link = read_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(
            anchor['href'],
            '/First_Last/test__read_link/001'
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
            '/First_Last/test__read_link/001'
        )

        # Test components param
        components = ['aaa', 'bbb']
        link = read_link(db, book, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src="http://www.img.com")]
        link = read_link(db, book, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        book.reader = 'slider'
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _type='button',
            _target='_blank',
        )
        link = read_link(db, book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['type'], 'button')
        self.assertEqual(anchor['target'], '_blank')

    def test__url(self):
        creator_id = db.creator.insert(
            email='test__url@example.com',
            path_name='First Last',
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

        book_id = db.book.insert(
            name='',
        )
        db.commit()
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        # Note: The publication year was removed from the url.

        tests = [
            #(name, pub year, type, number, of_number, expect),
            (None, None, 'one-shot', None, None, None),
            ('My Book', 1999, 'one-shot', 1, 999,
                '/First_Last/My_Book'),
            ('My Book', 1999, 'ongoing', 12, 999,
                '/First_Last/My_Book_012'),
            ('My Book', 1999, 'mini-series', 2, 9,
                '/First_Last/My_Book_02_%28of_09%29'),
            ("Hélè d'Eñça", 1999, 'mini-series', 2, 9,
                '/First_Last/H%C3%A9l%C3%A8_d%27E%C3%B1%C3%A7a_02_%28of_09%29'),
        ]

        for t in tests:
            book.update_record(
                name=t[0],
                publication_year=t[1],
                book_type_id=self._type_id_by_name[t[2]],
                number=t[3],
                of_number=t[4],
                creator_id=creator_id,
            )
            db.commit()
            self.assertEqual(url(book), t[5])

    def test__url_name(self):
        book_id = db.book.insert(
            name='',
        )
        db.commit()
        book = entity_to_row(db.book, book_id)
        self._objects.append(book)

        # Note: The publication year was removed from the url.
        tests = [
            #(name, pub year, type, number, of_number, expect),
            (None, None, 'one-shot', None, None, None),
            ('My Book', 1999, 'one-shot', 1, 999,
                'My_Book'),
            ('My Book', 1999, 'ongoing', 12, 999,
                'My_Book_012'),
            ('My Book', 1999, 'mini-series', 2, 9,
                'My_Book_02_(of_09)'),
            ("Hélè d'Eñça", 1999, 'mini-series', 2, 9,
                "H\xc3\xa9l\xc3\xa8_d'E\xc3\xb1\xc3\xa7a_02_(of_09)"),
        ]

        for t in tests:
            book.update_record(
                name=t[0],
                publication_year=t[1],
                book_type_id=self._type_id_by_name[t[2]],
                number=t[3],
                of_number=t[4],
            )
            db.commit()
            self.assertEqual(url_name(book), t[5])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
