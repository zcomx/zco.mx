#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/social_media.py

"""
import unittest
import uuid
from applications.zcomx.modules.tumblr import \
    Authenticator, \
    POST_IN_PROGRESS, \
    PhotoDataPreparer, \
    Poster
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class DubClient(object):
    """Stub pytumblr client."""
    def __init__(self):
        self.posts = {}

    def create_photo(self, username, **kwargs):
        post_id = uuid.uuid4()
        self.posts[post_id] = kwargs
        return post_id

    def delete_post(self, post_id):
        del self.posts[post_id]


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
        info = client.info()
        self.assertTrue(info['meta']['status'], '401')


class TestPhotoDataPreparer(LocalTestCase):

    def test____init__(self):
        preparer = PhotoDataPreparer({})
        self.assertTrue(preparer)

    def test__caption(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'book': {
                'title': 'My Book 001 (1999)',
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

        expect = """###<a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a>###

This is my book!

by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a> | <a href="http://website.com">website</a> | <a href="http://twitter.com">twitter</a> | <a href="http://tumblr.com">tumblr</a>"""
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.caption(), expect)

        # No description, no social media
        data['book']['description'] = None
        data['creator']['social_media'] = []

        expect = """###<a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a>###

by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a>"""
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.caption(), expect)

    def test__data(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'book': {
                'description': None,
                'slug_name': 'my-book-001',
                'source': 'http://source',
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
            'state': 'published',
            'tags': ['My Book', 'FirstLast', 'zco.mx'],
            'tweet': 'My Book 001|First Last|http://zco.mx/FirstLast/MyBook',
            'slug': 'first-last-my-book-001',
            'format': 'markdown',
            'source': 'http://source',
            'link': 'http://zco.mx/FirstLast/MyBook',
            'caption': """###<a href="http://zco.mx/FirstLast/MyBook">My Book 001 (1999)</a>###

by <a href="http://zco.mx/FirstLast">http://zco.mx/FirstLast</a>"""
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.data(), expect)

    def test__slug(self):
        data = {
            'book': {
                'slug_name': 'my-book-001',
            },
            'creator': {
                'slug_name': 'first-last',
            },
        }
        preparer = PhotoDataPreparer(data)
        self.assertEqual(preparer.slug(), 'first-last-my-book-001')

    def test__tags(self):
        data = {
            'book': {
                'tag_name': 'My Book',
            },
            'creator': {
                'tag_name': 'First Last',
            },
            'site': {
                'name': 'zco.mx'
            }
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(
            preparer.tags(),
            ['My Book', 'First Last', 'zco.mx']
        )

    def test__tweet(self):
        data = {
            'book': {
                'tweet_name': 'My Book 001',
                'url': 'http://zco.mx/FirstLast/MyBook-001',
            },
            'creator': {
                'tweet_name': 'First Last',
            },
        }

        preparer = PhotoDataPreparer(data)
        self.assertEqual(
            preparer.tweet(),
            'My Book 001|First Last|http://zco.mx/FirstLast/MyBook-001'
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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
