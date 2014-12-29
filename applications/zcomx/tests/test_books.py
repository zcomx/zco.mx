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
from gluon.storage import Storage
from applications.zcomx.modules.books import \
    BookEvent, \
    ContributionEvent, \
    RatingEvent, \
    ViewEvent, \
    DEFAULT_BOOK_TYPE, \
    book_page_for_json, \
    book_pages_as_json, \
    book_pages_years, \
    book_types, \
    by_attributes, \
    calc_contributions_remaining, \
    cc_licence_data, \
    contribute_link, \
    contributions_remaining_by_creator, \
    contributions_target, \
    cover_image, \
    default_contribute_amount, \
    defaults, \
    formatted_name, \
    get_page, \
    is_releasable, \
    numbers_for_book_type, \
    orientation, \
    page_url, \
    parse_url_name, \
    publication_year_range, \
    publication_years, \
    read_link, \
    update_contributions_remaining, \
    update_rating, \
    url, \
    url_name
from applications.zcomx.modules.images import store
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

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
        cls._book = cls.add(db.book, dict(name='Event Test Case'))
        email = web.username
        cls._user = db(db.auth_user.email == email).select().first()
        if not cls._user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

    def _set_pages(self, db, book_id, num_of_pages):
        set_pages(self, db, book_id, num_of_pages)


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
        self._set_pages(db, self._book.id, 10)
        update_rating(db, self._book)
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.contributions, 0)
        self.assertAlmostEqual(book.contributions_remaining, 100.00)

        event = ContributionEvent(self._book, self._user.id)

        # no value
        event_id = event.log()
        self.assertFalse(event_id)
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.contributions, 0)
        self.assertAlmostEqual(book.contributions_remaining, 100.00)

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
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.contributions, 123.45)
        self.assertAlmostEqual(book.contributions_remaining, 0.00)


class TestRatingEvent(EventTestCase):
    def test____init__(self):
        event = RatingEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        update_rating(db, self._book)
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.rating, 0)

        event = RatingEvent(self._book, self._user.id)

        # no value
        event_id = event.log()
        self.assertFalse(event_id)
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.rating, 0)

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
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.rating, 5)


class TestViewEvent(EventTestCase):
    def test____init__(self):
        event = ViewEvent(self._book, self._user.id)
        self.assertTrue(event)

    def test__log(self):
        update_rating(db, self._book)
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.views, 0)

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
        book = entity_to_row(db.book, self._book.id)  # Use id to force re-read
        self.assertAlmostEqual(book.views, 1)


class ImageTestCase(LocalTestCase):
    """ Base class for Image test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _image_dir = '/tmp/image_for_books'
    _image_original = os.path.join(_image_dir, 'original')
    _image_name = 'file.jpg'
    _image_name_2 = 'file_2.jpg'
    _test_data_dir = None
    _type_id_by_name = {}

    _objects = []

    @classmethod
    def _prep_image(cls, img, working_directory=None, to_name=None):
        """Prepare an image for testing.
        Copy an image from private/test/data to a working directory.

        Args:
            img: string, name of source image, eg file.jpg
                must be in cls._test_data_dir
            working_directory: string, path of working directory to copy to.
                If None, uses cls._image_dir
            to_name: string, optional, name of image to copy file to.
                If None, img is used.
        """
        src_filename = os.path.join(
            os.path.abspath(cls._test_data_dir),
            img
        )

        if working_directory is None:
            working_directory = os.path.abspath(cls._image_dir)

        if to_name is None:
            to_name = img

        filename = os.path.join(working_directory, to_name)
        shutil.copy(src_filename, filename)
        return filename

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

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

        cls._creator = cls.add(db.creator, dict(
            email='image_test_case@example.com',
        ))

        cls._book = cls.add(db.book, dict(
            name='Image Test Case',
            creator_id=cls._creator.id,
        ))

        cls._book_page = cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=1,
            image=create_image('file.jpg'),
        ))

        # Create a second page to test with.
        cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=2,
            image=create_image('file_2.jpg'),
        ))

        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls._image_dir):
            shutil.rmtree(cls._image_dir)

    def _set_pages(self, db, book_id, num_of_pages):
        set_pages(self, db, book_id, num_of_pages)


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

    def test__book_types(self):
        xml = book_types(db)
        expect = (
            """{"value":"1", "text":"Ongoing (eg 001, 002, 003, etc)"},"""
            """{"value":"2", "text":"Mini-series (eg 01 of 04)"},"""
            """{"value":"3", "text":"One-shot/Graphic Novel"}"""
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
            book = self.add(db.book, dict(**data))
            ids_by_name[key] = book.id

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

    def test__cc_licence_data(self):
        self.assertRaises(NotFoundError, cc_licence_data, -1)

        book = self.add(db.book, dict(
            name='test__cc_licence_data',
            creator_id=-1,
        ))

        # no creator
        self.assertRaises(NotFoundError, cc_licence_data, book)

        auth_user = self.add(db.auth_user, dict(name='Test CC Licence Data'))
        creator = self.add(db.creator, dict(auth_user_id=auth_user.id))

        book.update_record(creator_id=creator.id)
        self.assertEqual(
            cc_licence_data(book),
            {
                'owner': 'Test CC Licence Data',
                'year': '2014',
                'place': None,
                'title': 'test__cc_licence_data'
            }
        )

        book.update_record(cc_licence_place='Canada')
        self.assertEqual(
            cc_licence_data(book),
            {
                'owner': 'Test CC Licence Data',
                'year': '2014',
                'place': 'Canada',
                'title': 'test__cc_licence_data'
            }
        )

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
            created_on='2010-12-31 01:01:01',
        ))

        self.assertEqual(
            cc_licence_data(book),
            {
                'owner': 'Test CC Licence Data',
                'year': '2010',
                'place': 'Canada',
                'title': 'test__cc_licence_data'
            }
        )

        self.add(db.book_page, dict(
            book_id=book.id,
            page_no=2,
            created_on='2014-12-31 01:01:01',
        ))

        self.assertEqual(
            cc_licence_data(book),
            {
                'owner': 'Test CC Licence Data',
                'year': '2010-2014',
                'place': 'Canada',
                'title': 'test__cc_licence_data'
            }
        )

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
        link = contribute_link(db, book, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = contribute_link(db, book, components)
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
        creator = self.add(db.creator, dict(
            email='test__contributions_remaining_by_creator@eg.com'
        ))

        # Creator has no books
        self.assertEqual(contributions_remaining_by_creator(db, creator), 0.00)

        book = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
        ))
        self._set_pages(db, book.id, 10)
        self.assertEqual(contributions_target(db, book.id), 100.00)

        # Book has no contributions
        self.assertEqual(
            contributions_remaining_by_creator(db, creator),
            100.00
        )

        # Book has one contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=15.00,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(db, creator),
            85.00
        )

        # Book has multiple contribution
        self.add(db.contribution, dict(
            book_id=book.id,
            amount=35.99,
        ))
        self.assertEqual(
            contributions_remaining_by_creator(db, creator),
            49.01
        )

        # Creator has multiple books.
        book_2 = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
        ))
        self._set_pages(db, book_2.id, 5)
        self.assertEqual(contributions_target(db, book_2.id), 50.00)
        self.assertAlmostEqual(
            contributions_remaining_by_creator(db, creator),
            99.01
        )

    def test__contributions_target(self):
        book = self.add(db.book, dict(name='test__contributions_target'))

        # Book has no pages
        self.assertEqual(contributions_target(db, book), 0.00)

        # Invalid book
        self.assertEqual(contributions_target(db, -1), 0.00)

        tests = [
            #(pages, expect)
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

        images = [
            'book_page.image.page_trees.png',
            'book_page.image.page_flowers.png',
            'book_page.image.page_birds.png',
        ]
        for count, i in enumerate(images):
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
                '<img alt="" src="/images/download/book_page.image.page_trees.png?size=original" />'
            )

    def test__default_contribute_amount(self):
        book = self.add(db.book, dict(name='test__default_contribute_amount'))

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
            self._set_pages(db, book.id, t[0])
            self.assertEqual(default_contribute_amount(db, book), t[1])

    def test__defaults(self):
        types_by_name = {}
        for row in db(db.book_type).select(db.book_type.ALL):
            types_by_name[row.name] = row

        # Test book unique name
        got = defaults(db, '_test__defaults_', self._creator)
        expect = {
            'creator_id': self._creator.id,
            'book_type_id': types_by_name[DEFAULT_BOOK_TYPE].id,
            'urlify_name': 'test-defaults',
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
            'urlify_name': 'image-test-case',
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
            'urlify_name': 'image-test-case',
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
                'urlify_name': 'image-test-case',
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

    def test__formatted_name(self):
        book = self.add(db.book, dict(name='My Book'))

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
                self.assertRaises(NotFoundError, get_page, book, **kwargs)

        for page_no in ['first', 'last', 1, 2, None]:
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

    def test__is_releasable(self):
        book = self.add(db.book, dict(name='test__is_releasable'))
        book_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
        ))

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

    def test__orientation(self):
        if self._opts.quick:
            raise unittest.SkipTest('Remove --quick option to run test.')

        # Test invalid book entity
        self.assertRaises(NotFoundError, orientation, -1)

        # Test booke without an image.
        book_page = self.add(db.book_page, dict(
            image=None,
        ))
        self.assertRaises(NotFoundError, orientation, book_page)

        for t in ['portrait', 'landscape', 'square']:
            img = '{n}.png'.format(n=t)
            filename = self._prep_image(img)
            stored_filename = store(db.book_page.image, filename)

            book_page = self.add(db.book_page, dict(
                image=stored_filename,
            ))
            self.assertEqual(orientation(book_page), t)

    def test__page_url(self):
        creator = self.add(db.creator, dict(
            email='test__page_url@example.com',
            path_name='First Last',
        ))

        book = self.add(db.book, dict(
            name='My Book',
            publication_year=1999,
            book_type_id=self._type_id_by_name['one-shot'],
            number=1,
            of_number=999,
            creator_id=creator.id,
        ))

        book_page = self.add(db.book_page, dict(
            book_id=book.id,
            page_no=1,
        ))

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301

        self.assertEqual(
            page_url(book_page),
            '/First_Last/My_Book/001'
        )

        # By id
        self.assertEqual(
            page_url(book_page.id),
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

        creator = self.add(db.creator, dict(
            email='test__read_linke@example.com',
            path_name='First Last',
        ))

        book = self.add(db.book, dict(
            name='test__read_link',
            publication_year=1999,
            creator_id=creator.id,
            reader='slider',
            book_type_id=self._type_id_by_name['one-shot'],
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

        components = [IMG(_src='http://www.img.com', _alt='')]
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
            _target='_blank',
        )
        link = read_link(db, book, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__update_contributions_remaining(self):
        # invalid-name (C0103): *Invalid %%s name "%%s"*
        # pylint: disable=C0103
        creator = self.add(db.creator, dict(
            email='test__update_contributions_remaining@eg.com'
        ))

        book_contributions = lambda b: calc_contributions_remaining(db, b)
        creator_contributions = \
            lambda c: entity_to_row(db.creator, c.id).contributions_remaining

        # Creator has no books
        self.assertEqual(creator_contributions(creator), 0)

        book = self.add(db.book, dict(
            name='test__contributions_remaining_by_creator',
            creator_id=creator.id,
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
        ))
        self._set_pages(db, book_2.id, 5)
        update_contributions_remaining(db, book_2)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)
        self.assertEqual(book_contributions(book), 49.01)
        self.assertEqual(book_contributions(book_2), 50.00)

        # Creator contributions_remaining should be updated by any of it's
        # books.
        creator.update_record(contributions_remaining=0)
        db.commit()
        self.assertEqual(creator_contributions(creator), 0)
        update_contributions_remaining(db, book)
        self.assertAlmostEqual(creator_contributions(creator), 99.01)

    def test__update_rating(self):
        book = self.add(db.book, dict(name='test__update_rating'))
        self._set_pages(db, book.id, 10)

        def reset(book_record):
            book_record.update_record(
                contributions=0,
                contributions_remaining=0,
                views=0,
                rating=0,
            )
            db.commit()

        def zero(storage):
            for k in storage.keys():
                storage[k] = 0

        def do_test(book_record, rating, expect):
            update_rating(db, book_record, rating=rating)
            query = (db.book.id == book_record.id)
            r = db(query).select(
                db.book.contributions,
                db.book.contributions_remaining,
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
            views=0,
            rating=0,
        ))
        do_test(book, None, expect)

        records = [
            #(table, days_ago, amount)
            (db.contribution, 0, 11.11),
            (db.contribution, 100, 22.22),
            (db.contribution, 500, 44.44),
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
            path_name='First Last',
        ))

        book = self.add(db.book, dict(name=''))

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
                creator_id=creator.id,
            )
            db.commit()
            self.assertEqual(url(book), t[5])

    def test__url_name(self):
        book = self.add(db.book, dict(name=''))

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
