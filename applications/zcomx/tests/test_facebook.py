#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/facebook.py

"""
import datetime
import re
import unittest
import uuid
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.facebook import \
    Authenticator, \
    FacebookAPIAuthenticator, \
    FacebookAPIClient, \
    PhotoDataPreparer, \
    Poster, \
    TextDataPreparer
from applications.zcomx.modules.social_media import FacebookPoster
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    _activity_log_1 = None
    _activity_log_2 = None
    _auth_user = None
    _book = None
    _book_page = None
    _book_page_2 = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
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

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        self._book_page_2 = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
        ))

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

        super(WithObjectsTestCase, self).setUp()


class WithDateTestCase(LocalTestCase):
    _date = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        self._date = datetime.date.today()
        super(WithDateTestCase, self).setUp()


class DubGraphAPI(object):

    def __init__(self):
        self.oauth_token = '_stub_access_token_'
        self.args = None
        self.kwargs = None

    def get(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return 'get called'

    def delete(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return 'delete called'

    def post(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return 'post called'

    def reset(self):
        self.args = None
        self.kwargs = None


class DubClient(object):
    """Stub pytumblr client."""
    def __init__(self):
        self.user_id = '1234567890'
        self.posts = {}

    def delete_post(self, post_id):
        del self.posts[post_id]

    def page_feed_post(self, args):
        post_id = uuid.uuid4()
        self.posts[post_id] = args
        return post_id


class TestAuthenticator(LocalTestCase):

    def test____init__(self):
        authenticator = Authenticator({})
        self.assertTrue(authenticator)

    def test__authenticate(self):
        return      # Facebook is over
        credentials = FacebookPoster().credentials()
        authenticator = Authenticator(credentials)
        client = authenticator.authenticate()
        self.assertTrue(isinstance(client, FacebookAPIClient))
        self.assertTrue(
            re.match(r'^[\d]{15}$', str(client.user_id)) is not None)


class TestFacebookAPIAuthenticator(LocalTestCase):

    api_authenticator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):
        credentials = FacebookPoster().credentials()
        self. api_authenticator = FacebookAPIAuthenticator(
            credentials['email'],
            credentials['password'],
            credentials['client_id'],
            credentials['redirect_uri'],
            credentials['page_name'],
        )

    def test____init__(self):
        self.assertTrue(self.api_authenticator)

    def test__authenticate(self):
        return      # Facebook is over
        client = self.api_authenticator.authenticate()
        self.assertTrue(isinstance(client, FacebookAPIClient))
        self.assertTrue(
            re.match(r'^[\d]{15}$', str(client.user_id)) is not None)

    def test__get_token(self):
        return      # Facebook is over
        self.assertTrue(self.api_authenticator.login())
        token = self.api_authenticator.get_token()
        self.assertTrue(len(token) > 170)
        self.assertTrue(len(token) < 300)
        self.assertTrue(re.match(r'^[\w]+$', token) is not None)

    def test__login(self):
        return      # Facebook is over
        self.assertTrue(self.api_authenticator.login())


class TestFacebookAPIClient(LocalTestCase):

    def test____init__(self):
        graph = DubGraphAPI()
        api_client = FacebookAPIClient(graph)
        self.assertTrue(api_client)
        self.assertEqual(api_client.access_token, '_stub_access_token_')
        self.assertEqual(api_client.user_id, 'me')

        api_client = FacebookAPIClient(graph, user_id='1234567890')
        self.assertEqual(api_client.user_id, '1234567890')

    def test__accounts(self):
        graph = DubGraphAPI()
        api_client = FacebookAPIClient(graph, user_id='1234567890')
        got = api_client.accounts()
        self.assertEqual(got, 'get called')
        self.assertEqual(graph.args, ('1234567890/accounts',))
        self.assertEqual(graph.kwargs, {})

    def test__delete_post(self):
        graph = DubGraphAPI()
        api_client = FacebookAPIClient(graph, user_id='1234567890')
        got = api_client.delete_post('post_id_123')
        self.assertEqual(got, 'delete called')
        self.assertEqual(graph.args, ('post_id_123',))
        self.assertEqual(graph.kwargs, {})

    def test__page_feed_post(self):
        graph = DubGraphAPI()
        api_client = FacebookAPIClient(graph, user_id='1234567890')
        post_data = {
            'aaa': 111,
            'bbb': 222,
        }
        got = api_client.page_feed_post(post_data)
        self.assertEqual(got, 'post called')
        self.assertEqual(graph.args, ())
        self.assertEqual(
            graph.kwargs,
            {
                'path': '1234567890/feed',
                'access_token': '_stub_access_token_',
                'debug': 'all',
                'aaa': 111,
                'bbb': 222,
            }
        )

    def test__post(self):
        graph = DubGraphAPI()
        api_client = FacebookAPIClient(graph, user_id='1234567890')
        path = 'some/test/path'
        post_data = {
            'aaa': 111,
            'bbb': 222,
        }
        got = api_client.post(path, post_data)
        self.assertEqual(got, 'post called')
        self.assertEqual(graph.args, ())
        self.assertEqual(
            graph.kwargs,
            {
                'path': 'some/test/path',
                'access_token': '_stub_access_token_',
                'debug': 'all',
                'aaa': 111,
                'bbb': 222,
            }
        )


class TestTextDataPreparer(WithObjectsTestCase, WithDateTestCase):
    facebook_data = {'tumblr_post_id': '123456789012'}
    picture_url = 'https://zco.mx/zcomx/static/images/white_280x280.png'

    def test____init__(self):
        preparer = TextDataPreparer({})
        self.assertTrue(preparer)

    def test__data(self):
        preparer = TextDataPreparer(self.facebook_data)
        self.assertEqual(
            preparer.data(),
            {
                'link': 'http://zcomx.tumblr.com/post/123456789012',
                'picture': self.picture_url,
            }
        )

    def test__link(self):
        preparer = TextDataPreparer(self.facebook_data)
        self.assertEqual(
            preparer.link(),
            'http://zcomx.tumblr.com/post/123456789012'
        )


class TestPhotoDataPreparer(LocalTestCase):

    def test____init__(self):
        preparer = PhotoDataPreparer({})
        self.assertTrue(preparer)

    def test__caption(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'creator': {'name': 'First Last'}
        }
        expect = 'by First Last'
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.caption(), expect)

    def test__data(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'book': {
                'description': 'This is my book',
                'download_url': 'http://source',
                'formatted_name': 'My Book 001 (1999)',
                'url': 'http://zco.mx/FirstLast/MyBook',
            },
            'creator': {
                'name': 'First Last',
            },
        }

        expect = {
            'caption': 'by First Last',
            'description': 'This is my book',
            'link': 'http://zco.mx/FirstLast/MyBook',
            'name': 'My Book 001 (1999)',
            'picture': 'http://source',
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.data(), expect)


class TestPoster(LocalTestCase):

    def test____init__(self):
        client = DubClient()
        poster = Poster(client)
        self.assertTrue(poster)

    def test__delete_post(self):
        client = DubClient()
        self.assertEqual(client.posts, {})

        poster = Poster(client)
        post_id = poster.post_photo({})
        self.assertEqual(
            client.posts,
            {post_id: {}}
        )

        poster.delete_post(post_id)
        self.assertEqual(client.posts, {})

    def test__post_photo(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_photo({'aaa': 'bbb'})
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
        post_id = poster.post_text({'aaa': 'bbb'})
        self.assertEqual(
            client.posts,
            {
                post_id: {
                    'aaa': 'bbb',
                }
            }
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
