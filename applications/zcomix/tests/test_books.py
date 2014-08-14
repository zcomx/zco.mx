#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/books.py

"""
import datetime
import os
import shutil
import unittest
from BeautifulSoup import BeautifulSoup
from PIL import Image
from gluon import *
from gluon.contrib.simplejson import loads
from applications.zcomix.modules.books import \
    BookEvent, \
    ContributionEvent, \
    RatingEvent, \
    ViewEvent, \
    DEFAULT_BOOK_TYPE, \
    book_page_for_json, \
    book_pages_as_json, \
    cover_image, \
    default_contribute_amount, \
    defaults, \
    is_releasable, \
    publication_year_range, \
    read_link
from applications.zcomix.modules.test_runner import LocalTestCase

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
        cls._book = db(db.book.id == book_id).select().first()
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
        contribution = db(db.contribution.id == event_id).select(
            db.contribution.ALL).first()
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
        rating = db(db.rating.id == event_id).select(db.rating.ALL).first()
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

        view = db(db.book_view.id == event_id).select(db.book_view.ALL).first()
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
        cls._creator = db(db.creator.id == creator_id).select().first()
        cls._objects.append(cls._creator)

        book_id = db.book.insert(
            name='Image Test Case',
            creator_id=cls._creator.id,
        )
        db.commit()
        cls._book = db(db.book.id == book_id).select().first()
        cls._objects.append(cls._book)

        book_page_id = db.book_page.insert(
            book_id=book_id,
            page_no=1,
            image=create_image('file.jpg'),
        )
        db.commit()
        cls._book_page = db(db.book_page.id == book_page_id).select().first()
        cls._objects.append(cls._book_page)

        # Create a second page to test with.
        book_page_id_2 = db.book_page.insert(
            book_id=book_id,
            page_no=2,
            image=create_image('file_2.jpg'),
        )
        db.commit()
        book_page_2 = db(db.book_page.id == book_page_id_2).select().first()
        cls._objects.append(book_page_2)

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

        url = '/images/download/{img}'.format(img=self._book_page.image)
        thumb = '/images/download/{img}?size=thumb'.format(
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
                'url': url,
                'thumbnailUrl': thumb,
                'deleteUrl': delete_url,
                'deleteType': 'DELETE',
            }
        )

    def test__cover_image(self):

        placeholder = \
            '<div class="portrait_placeholder"></div>'

        self.assertEqual(str(cover_image(db, 0)), placeholder)

        book_id = db.book.insert(name='test__cover_image')
        book = db(db.book.id == book_id).select().first()
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
            page = db(db.book_page.id == page_id).select().first()
            self._objects.append(page)

        self.assertEqual(
            str(cover_image(db, book_id)),
            '<img src="/images/download/book_page.image.page_trees.png?size=original" />'
        )

    def test__default_contribute_amount(self):
        book_id = db.book.insert(name='test__default_contribute_amount')
        book = db(db.book.id == book_id).select().first()
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
            (400, 20.00),
            (1000, 20.00),
        ]
        for t in tests:
            page_count = db(db.book_page.book_id == book.id).count()
            while page_count < t[0]:
                page_id = db.book_page.insert(
                    book_id=book_id,
                    page_no=(page_count + 1),
                )
                page = db(db.book_page.id == page_id).select().first()
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

    def test__is_releasable(self):
        book_id = db.book.insert(
            name='test__is_releasable',
        )
        db.commit()
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        book_page_id = db.book_page.insert(
            book_id=book.id,
            page_no=1,
        )
        db.commit()
        book_page = db(db.book_page.id == book_page_id).select().first()
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

    def test__publication_year_range(self):
        start, end = publication_year_range()
        self.assertEqual(start, 1900)
        self.assertEqual(end, datetime.date.today().year + 5)

    def test__read_link(self):
        empty = '<span></span>'
        book_id = db.book.insert(
            name='test__read_link',
            reader='slider',
        )
        book = db(db.book.id == book_id).select().first()
        self._objects.append(book)

        # As integer, book_id
        link = read_link(db, book_id)
        # Eg <a data-w2p_disable_with="default" href="/zcomix/books/slider/57">Read</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/books/slider/{bid}'.format(
            bid=book_id))

        # As Row, book
        link = read_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/books/slider/{bid}'.format(
            bid=book_id))

        # Invalid id
        link = read_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test reader variation
        book.reader = 'awesome_reader'
        link = read_link(db, book)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Read')
        self.assertEqual(anchor['href'], '/books/awesome_reader/{bid}'.format(
            bid=book_id))

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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
