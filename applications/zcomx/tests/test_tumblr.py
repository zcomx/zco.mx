#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/tumblr.py
"""
import datetime
import unittest
import uuid
from bs4 import BeautifulSoup
from pydal.objects import Row
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import (
    AuthUser,
    Creator,
)
from applications.zcomx.modules.tumblr import (
    Authenticator,
    BookListingCreator,
    BookListingCreatorWithTumblr,
    OngoingBookListing,
    PhotoDataPreparer,
    Poster,
    TextDataPreparer,
    book_listing_creator,
    postable_activity_log_ids,
)
from applications.zcomx.modules.stickon.dal import RecordGenerator
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class WithObjectsTestCase(LocalTestCase):
    _activity_log_1 = None
    _activity_log_2 = None
    _auth_user = None
    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None

    # pylint: disable=invalid-name
    def setUp(self):

        self._auth_user = self.add(AuthUser, dict(
            name='First Last'
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email='image_test_case@example.com',
            name_for_url='FirstLast',
            tumblr='http://firstlast.tumblr.com',
        ))

        self._book = self.add(Book, dict(
            name='My Book',
            number=1,
            creator_id=self._creator.id,
            book_type_id=BookType.by_name('ongoing').id,
            name_for_url='MyBook-001',
        ))

        page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))
        self._book_page = BookPage.from_id(page.id)

        page_2 = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
        ))
        self._book_page_2 = BookPage.from_id(page_2.id)

        self._activity_log_1 = self.add(ActivityLog, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id],
            action='page added',
            ongoing_post_id=None,
        ))

        self._activity_log_2 = self.add(ActivityLog, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page_2.id],
            action='page added',
            ongoing_post_id=None,
        ))

        super().setUp()


class WithDateTestCase(LocalTestCase):
    _date = None

    # pylint: disable=invalid-name
    def setUp(self):
        self._date = datetime.date.today()
        super().setUp()


class DubClient():
    """Stub pytumblr2 client."""
    def __init__(self):
        self.posts = {}

    def legacy_create_photo(self, username, **kwargs):
        # pylint: disable=unused-argument       # username
        post_id = uuid.uuid4()
        self.posts[post_id] = kwargs
        return post_id

    def legacy_create_text(self, username, **kwargs):
        # pylint: disable=unused-argument       # username
        post_id = uuid.uuid4()
        self.posts[post_id] = kwargs
        return post_id

    def delete_post(self, post_id):
        del self.posts[post_id]


class TestAuthenticator(LocalTestCase):

    def test____init__(self):
        authenticator = Authenticator({})
        self.assertTrue(authenticator)

    def test__authenticate(self):
        credentials = {
            'consumer_key': '',
            'consumer_secret': '',
            'oauth_token': '',
            'oauth_secret': '',
        }
        authenticator = Authenticator(credentials)
        client = authenticator.authenticate()
        info = client.info()
        self.assertTrue(info['meta']['status'], '401')


class TestBookListingCreator(WithObjectsTestCase):

    def test____init__(self):
        listing_creator = BookListingCreator(self._creator)
        self.assertTrue(listing_creator)

    def test__link(self):
        listing_creator = BookListingCreator(self._creator)
        link = listing_creator.link()
        soup = BeautifulSoup(str(link), 'html.parser')
        # <a href="http://123.zco.mx">First Last</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'First Last')
        self.assertEqual(
            anchor['href'],
            'http://{cid}.zco.mx'.format(cid=self._creator.id)
        )


class TestBookListingCreatorWithTumblr(WithObjectsTestCase):

    def test__link(self):
        listing_creator = BookListingCreatorWithTumblr(self._creator)
        link = listing_creator.link()
        soup = BeautifulSoup(str(link), 'html.parser')
        # <a href="http://firstlast.tumblr.com">First Last</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'First Last')
        self.assertEqual(anchor['href'], 'http://firstlast.tumblr.com')


class TestOngoingBookListing(WithObjectsTestCase):

    def test____init__(self):
        listing = OngoingBookListing(
            Row({'name': 'test____init__'}),
            BookPage({'name_for_url': 'FirstLast'}),
            []
        )
        self.assertTrue(listing)

    def test__components(self):
        pages = [self._book_page, self._book_page_2]
        listing = OngoingBookListing(self._book, pages, self._creator)
        got = listing.components()
        self.assertEqual(len(got), 7)
        self.assertEqual(got[1], ' by ')
        self.assertEqual(got[3], ' - ')
        self.assertEqual(got[5], ' ')

        soup = BeautifulSoup(str(got[0]), 'html.parser')
        # <a href="http://zco.mx/FirstLast/MyBook-001">My Book 001</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'My Book 001')
        self.assertEqual(anchor['href'], 'http://zco.mx/FirstLast/MyBook-001')

        soup = BeautifulSoup(str(got[2]), 'html.parser')
        # <a href="http://firstlast.tumblr.com">First Last</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'First Last')
        self.assertEqual(anchor['href'], 'http://firstlast.tumblr.com')

        soup = BeautifulSoup(str(got[4]), 'html.parser')
        # <a href="http://zco.mx/FirstLast/MyBook-001/001">01</a>
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'p01')
        self.assertEqual(
            anchor['href'],
            'http://zco.mx/FirstLast/MyBook-001/001'
        )

        # Test abridged list
        pages = []
        for _ in range(0, 10):
            pages.append(self._book_page)
        listing = OngoingBookListing(self._book, pages, self._creator)
        got = listing.components()
        self.assertEqual(len(got), 11)
        self.assertEqual(got[1], ' by ')
        self.assertEqual(got[3], ' - ')
        self.assertEqual(got[5], ' ')
        self.assertEqual(got[7], ' ')
        self.assertEqual(got[8], '...')
        self.assertEqual(got[9], ' ')

    def test__from_activity_log(self):
        activity_log = Row(dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id, self._book_page_2.id],
        ))
        got = OngoingBookListing.from_activity_log(activity_log)
        self.assertTrue(isinstance(got, OngoingBookListing))
        self.assertEqual(got.book, self._book)
        self.assertEqual(
            got.book_pages[0],
            BookPage.from_id(self._book_page.id)
        )
        self.assertEqual(
            got.book_pages[1],
            BookPage.from_id(self._book_page_2.id)
        )
        self.assertEqual(got.creator, self._creator)


class TestTextDataPreparer(WithObjectsTestCase, WithDateTestCase):

    def test____init__(self):
        generator = RecordGenerator(db.activity_log)
        preparer = TextDataPreparer(self._date, generator)
        self.assertTrue(preparer)

    def test__body(self):

        activity_log = self.add(ActivityLog, dict(
            book_id=self._book.id,
            book_page_ids=[self._book_page.id, self._book_page_2.id],
            action='page added',
            ongoing_post_id=None,
        ))

        log_ids = [activity_log.id, self._activity_log_2.id]
        query = (db.activity_log.id.belongs(log_ids))
        preparer = TextDataPreparer(
            self._date,
            RecordGenerator(query)
        )

        body = preparer.body()
        soup = BeautifulSoup(body, 'html.parser')

        # <ul>
        #  <li>
        #   <i>
        #   <a href="http://zco.mx/FirstLast/MyBook-001">
        #    My Book 001
        #   </a>
        #   </i>
        #   by
        #   <a href="http://firstlast.tumblr.com">
        #    First Last
        #   </a>
        #   -
        #   <a href="http://zco.mx/FirstLast/MyBook-001/002">
        #    02
        #   </a>
        #  </li>
        #  <li>
        #   <span class="hidden"> --- </span>
        #   <i>
        #   <a href="http://zco.mx/FirstLast/MyBook-001">
        #    My Book 001
        #   </a>
        #   </i>
        #   by
        #   <a href="http://firstlast.tumblr.com">
        #    First Last
        #   </a>
        #   -
        #   <a href="http://zco.mx/FirstLast/MyBook-001/001">
        #    01
        #   </a>
        #   ,
        #   <a href="http://zco.mx/FirstLast/MyBook-001/002">
        #    02
        #   </a>
        #  </li>
        # </ul>

        ul = soup.ul
        lis = ul.findAll('li')
        self.assertEqual(len(lis), 2)

        li_1 = lis[0]
        li_1_i = li_1.findAll('i')
        self.assertEqual(len(li_1_i), 1)
        li_1_anchors = li_1.findAll('a')
        self.assertEqual(len(li_1_anchors), 3)
        self.assertEqual(li_1_anchors[0].string, 'My Book 001')
        self.assertEqual(
            li_1_anchors[0]['href'], 'http://zco.mx/FirstLast/MyBook-001')
        self.assertEqual(li_1_anchors[1].string, 'First Last')
        self.assertEqual(
            li_1_anchors[1]['href'], 'http://firstlast.tumblr.com')
        self.assertEqual(li_1_anchors[2].string, 'p02')
        self.assertEqual(
            li_1_anchors[2]['href'],
            'http://zco.mx/FirstLast/MyBook-001/002'
        )
        self.assertEqual(len(li_1.contents), 5)
        self.assertEqual(li_1.contents[1], ' by ')
        self.assertEqual(li_1.contents[3], ' - ')

        li_2 = lis[1]
        li_2_spans = li_2.findAll('span')
        self.assertEqual(len(li_2_spans), 1)
        self.assertEqual(li_2_spans[0].string, ' --- ')
        li_2_i = li_2.findAll('i')
        self.assertEqual(len(li_2_i), 1)
        li_2_anchors = li_2.findAll('a')
        self.assertEqual(len(li_2_anchors), 4)
        self.assertEqual(li_2_anchors[0].string, 'My Book 001')
        self.assertEqual(
            li_2_anchors[0]['href'], 'http://zco.mx/FirstLast/MyBook-001')
        self.assertEqual(li_2_anchors[1].string, 'First Last')
        self.assertEqual(
            li_2_anchors[1]['href'], 'http://firstlast.tumblr.com')
        self.assertEqual(li_2_anchors[2].string, 'p01')
        self.assertEqual(
            li_2_anchors[2]['href'],
            'http://zco.mx/FirstLast/MyBook-001/001'
        )
        self.assertEqual(li_2_anchors[3].string, 'p02')
        self.assertEqual(
            li_2_anchors[3]['href'],
            'http://zco.mx/FirstLast/MyBook-001/002'
        )
        self.assertEqual(len(li_2.contents), 8)
        self.assertEqual(li_2.contents[2], ' by ')
        self.assertEqual(li_2.contents[4], ' - ')
        self.assertEqual(li_2.contents[6], ' ')

    def test__book_listing_generator(self):

        log_ids = [self._activity_log_1.id, self._activity_log_2.id]
        query = (db.activity_log.id.belongs(log_ids))
        preparer = TextDataPreparer(
            self._date,
            RecordGenerator(query)
        )

        generator = preparer.book_listing_generator()

        got = next(generator)
        self.assertTrue(isinstance(got, OngoingBookListing))
        self.assertEqual(got.book, self._book)
        self.assertEqual(got.book_pages, [self._book_page])
        self.assertEqual(got.creator, self._creator)

        got = next(generator)
        self.assertTrue(isinstance(got, OngoingBookListing))
        self.assertEqual(got.book, self._book)
        self.assertEqual(got.book_pages, [self._book_page_2])
        self.assertEqual(got.creator, self._creator)

        self.assertRaises(StopIteration, generator.__next__)

    def test__data(self):
        date = datetime.date(1999, 12, 31)
        log_ids = [self._activity_log_1.id, self._activity_log_2.id]
        query = (db.activity_log.id.belongs(log_ids))
        preparer = TextDataPreparer(
            date,
            RecordGenerator(query)
        )

        # pylint: disable=line-too-long
        self.assertEqual(
            preparer.data(),
            {
                'body': '<ul><li><i><a href="http://zco.mx/FirstLast/MyBook-001">My Book 001</a></i> by <a href="http://firstlast.tumblr.com">First Last</a> - <a href="http://zco.mx/FirstLast/MyBook-001/001">p01</a></li><li><span class="hidden"> --- </span><i><a href="http://zco.mx/FirstLast/MyBook-001">My Book 001</a></i> by <a href="http://firstlast.tumblr.com">First Last</a> - <a href="http://zco.mx/FirstLast/MyBook-001/002">p02</a></li></ul>',
                'format': 'html',
                'slug': 'ongoing-books-update-1999-12-31',
                'state': 'published',
                'tags': ['comics', 'zco.mx'],
                'title': 'Updated Ongoing Books for Fri, Dec 31, 1999'
            }
        )

    def test__slug(self):
        date = datetime.date(1999, 12, 31)
        generator = RecordGenerator(db.activity_log)
        preparer = TextDataPreparer(date, generator)
        self.assertEqual(
            preparer.slug(),
            'ongoing-books-update-1999-12-31'
        )

    def test__tags(self):
        generator = RecordGenerator(db.activity_log)
        preparer = TextDataPreparer(self._date, generator)
        self.assertEqual(
            preparer.tags(),
            ['comics', 'zco.mx']
        )

    def test__title(self):
        # pylint: disable=line-too-long
        date = datetime.date(1999, 12, 31)
        generator = RecordGenerator(db.activity_log)
        preparer = TextDataPreparer(date, generator)
        self.assertEqual(
            preparer.title(),
            'Updated Ongoing Books for Fri, Dec 31, 1999'
        )


class TestPhotoDataPreparer(LocalTestCase):

    def test____init__(self):
        preparer = PhotoDataPreparer({})
        self.assertTrue(preparer)

    def test__caption(self):
        # pylint: disable=line-too-long
        data = {
            'book': {
                'formatted_name': 'My Book 001 (1999)',
                'description': 'This is my book!',
                'url': 'http://zco.mx/FirstLast/MyBook',
            },
            'creator': {
                'social_media': [
                    ('website', 'http://website.com'),
                    ('twitter', 'http://twitter.com'),
                    ('tumblr', 'http://tumblr.com'),
                ],
                'url': 'http://zco.mx/FirstLast',
            },
        }

        expect = """<h3><a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a></h3><p>This is my book!</p><p>by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a> | <a href="http://website.com">website</a> | <a href="http://twitter.com">twitter</a> | <a href="http://tumblr.com">tumblr</a></p>"""
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.caption(), expect)

        # No description, no social media
        data['book']['description'] = None
        data['creator']['social_media'] = []

        expect = """<h3><a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a></h3><p>by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a></p>"""
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.caption(), expect)

    def test__data(self):
        # pylint: disable=line-too-long
        data = {
            'book': {
                'description': None,
                'download_url': 'http://source',
                'formatted_name': 'My Book 001 (1999)',
                'name': 'My Book',
                'name_for_search': 'my-book-001',
                'url': 'http://zco.mx/FirstLast/MyBook',
            },
            'creator': {
                'name_for_search': 'first-last',
                'social_media': [],
                'name_for_url': 'FirstLast',
                'url': 'http://zco.mx/FirstLast',
            },
            'site': {
                'name': 'zco.mx'
            }
        }

        expect = {
            'state': 'published',
            'tags': ['My Book', 'FirstLast', 'comics', 'zco.mx'],
            'tweet': None,
            'slug': 'first-last-my-book-001',
            'format': 'html',
            'source': 'http://source',
            'link': 'http://zco.mx/FirstLast/MyBook',
            'caption': '<h3><a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a></h3><p>by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a></p>',
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.data(), expect)

    def test__slug(self):
        data = {
            'book': {
                'name_for_search': 'my-book-001',
            },
            'creator': {
                'name_for_search': 'first-last',
            },
        }
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.slug(), 'first-last-my-book-001')

    def test__tags(self):
        data = {
            'book': {
                'name': 'My Book',
            },
            'creator': {
                'name_for_url': 'First Last',
            },
            'site': {
                'name': 'zco.mx'
            }
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(
            preparer.tags(),
            ['My Book', 'First Last', 'comics', 'zco.mx']
        )


class TestPoster(LocalTestCase):

    def test____init__(self):
        client = DubClient()
        poster = Poster(client)
        self.assertTrue(poster)

    def test__delete_post(self):
        client = DubClient()
        self.assertEqual(client.posts, {})

        poster = Poster(client)
        post_id = poster.post_photo('username', {})
        self.assertEqual(
            client.posts,
            {post_id: {}}
        )

        poster.delete_post(post_id)
        self.assertEqual(client.posts, {})

    def test__post_photo(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_photo('username', {'aaa': 'bbb'})
        self.assertEqual(
            client.posts,
            {
                post_id: {
                    'aaa': 'bbb',
                }
            }
        )

    def test__post_text(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_text('username', {'aaa': 'bbb'})
        self.assertEqual(
            client.posts,
            {
                post_id: {
                    'aaa': 'bbb',
                }
            }
        )


class TestFunctions(WithObjectsTestCase, WithDateTestCase):

    def test__book_listing_creator(self):
        creator = Row({
            'tumblr': None,
        })

        got = book_listing_creator(creator)
        self.assertTrue(isinstance(got, BookListingCreator))

        creator = Row({
            'tumblr': 'http://user.tumblr.com',
        })
        got = book_listing_creator(creator)
        self.assertTrue(isinstance(got, BookListingCreatorWithTumblr))

    def test__postable_activity_log_ids(self):

        book = self.add(Book, dict(
            name='test__activity_log_ids'
        ))

        activity_log = self.add(ActivityLog, dict(
            book_id=book.id,
        ))

        def reset():
            book.update_record(release_date=None)
            db.commit()
            data = dict(
                book_id=book.id,
                action='page added',
                ongoing_post_id=None,
            )
            activity_log.update_record(**data)
            db.commit()

        reset()
        self.assertTrue(activity_log.id in postable_activity_log_ids())

        # Change book_id
        reset()
        activity_log.update_record(book_id=-1)
        db.commit()
        self.assertTrue(activity_log.id not in postable_activity_log_ids())

        # Released book should be ignored
        reset()
        book.update_record(release_date=self._date)
        db.commit()
        self.assertTrue(activity_log.id not in postable_activity_log_ids())

        # Action != 'page added' should be ignored
        reset()
        activity_log.update_record(action='completed')
        db.commit()
        self.assertTrue(activity_log.id not in postable_activity_log_ids())

        # Already posted should be ignored
        reset()
        activity_log.update_record(ongoing_post_id=-1)
        db.commit()
        self.assertTrue(activity_log.id not in postable_activity_log_ids())


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
