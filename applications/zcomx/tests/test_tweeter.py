#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/social_media.py

"""
import json
import unittest
import uuid
from twitter import TwitterHTTPError
from applications.zcomx.modules.tweeter import \
    Authenticator, \
    POST_IN_PROGRESS, \
    PhotoDataPreparer, \
    Poster
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubStatuses(object):
    """Stub Twitter statuses."""
    def __init__(self):
        self.posts = {}

    def destroy(self, post_id):
        del self.posts[post_id]

    def update_with_media(self, **kwargs):
        post_id = uuid.uuid4()
        self.posts[post_id] = kwargs
        return post_id


class DubClient(object):
    """Stub Twitter client."""
    def __init__(self):
        self.statuses = DubStatuses()


class TestConstants(LocalTestCase):
    def test_constants(self):
        self.assertEqual(POST_IN_PROGRESS, '__in_progress__')


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
        try:
            client.statuses.home_timeline()
        except TwitterHTTPError as err:
            response_data = json.loads(err.response_data)
            errors = response_data['errors']
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]['message'], 'Bad Authentication data.')
            self.assertEqual(errors[0]['code'], 215)
        else:
            self.fail('TwitterHTTPError not raised.')


class TestPhotoDataPreparer(LocalTestCase):

    def test____init__(self):
        preparer = PhotoDataPreparer({})
        self.assertTrue(preparer)

    def test__data(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'book': {
                'description': None,
                'slug_name': 'my-book-001',
                'image_name': 'http://source',
                'title': 'My Book 001 (1999)',
                'tag_name': 'My Book',
                'tweet_name': 'My Book 001',
                'url': 'http://zco.mx/FirstLast/MyBook',
            },
            'creator': {
                'slug_name': 'first-last',
                'social_media': [],
                'tag_name': 'FirstLast',
                'tweet_name': 'First Last',
                'url': 'http://zco.mx/FirstLast',
            },
            'site': {
                'name': 'zco.mx'
            }
        }

        expect = {
            'media[]': 'FIXME',
            'status': 'FIXME',
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.data(), expect)

    def test__media(self):
        self.fail('FIXME')
        data = {
            'book': {
                'source': '/tmp/fixem',
            },
        }
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.media(), 'first-last-my-book-001')

    def test__status(self):
        data = {
            'book': {
                'tweet_name': 'My Book 001',
                'short_url': 'http://101.zco.mx/MyBook-001',
            },
            'creator': {
                'twitter_username': '@First_Last',
                'tag_name': 'FirstLast',
                'name': 'First Last',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        preparer = PhotoDataPreparer(data)
        self.assertEqual(
            preparer.status(),
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx #comics #FirstLast'
        )


class TestPoster(LocalTestCase):

    def test____init__(self):
        client = DubClient()
        poster = Poster(client)
        self.assertTrue(poster)

    def test__delete_post(self):
        client = DubClient()
        self.assertEqual(client.statuses.posts, {})

        poster = Poster(client)
        post_id = poster.post_photo({})
        self.assertEqual(
            client.statuses.posts,
            {post_id: {}}
        )

        poster.delete_post(post_id)
        self.assertEqual(client.statuses.posts, {})

    def test__post_photo(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_photo({'aaa': 'bbb'})
        self.assertEqual(
            client.statuses.posts,
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
