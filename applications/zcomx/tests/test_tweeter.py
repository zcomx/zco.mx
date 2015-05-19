#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/social_media.py

"""
import json
import string
import unittest
import uuid
from twitter import TwitterHTTPError
from applications.zcomx.modules.images import ImageDescriptor, UploadImage
from applications.zcomx.modules.tweeter import \
    Authenticator, \
    POST_IN_PROGRESS, \
    PhotoDataPreparer, \
    Poster, \
    TruncatedTweet, \
    Tweet, \
    formatted_tags
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


class WithMediaTestCase(LocalTestCase):
    """Pre-define an test_image for tweet media."""
    _test_image = None
    _test_image_bytes = 0

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        # Use an existing image to test with.
        email = web.username
        user = db(db.auth_user.email == email).select().first()
        if not user:
            raise SyntaxError('No user with email: {e}'.format(e=email))

        query = db.creator.auth_user_id == user.id
        creator = db(query).select().first()
        if not creator:
            raise SyntaxError('No creator with email: {e}'.format(e=email))

        query = (db.book.release_date != None) & \
                (db.book.creator_id == creator.id) & \
                (db.book_page.page_no == 1)
        rows = db(query).select(
            db.book_page.image,
            left=[
                db.book.on(db.book_page.book_id == db.book.id),
            ],
            limitby=(0, 1),
        )
        if not rows:
            cls.fail('Unable to get image to test with.')
        cls._test_image = rows[0]['image']

        upload_img = UploadImage(db.book_page.image, cls._test_image)
        fullname = upload_img.fullname(size='web')
        cls._test_image_bytes = ImageDescriptor(fullname).size_bytes()


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


class TestPhotoDataPreparer(WithMediaTestCase):

    def test____init__(self):
        preparer = PhotoDataPreparer({})
        self.assertTrue(preparer)

    def test__data(self):
        data = {
            'book': {
                'cover_image_name': self._test_image,
                'formatted_name_no_year': 'My Book 001',
                'short_url': 'http://101.zco.mx/MyBook-001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
            },
            'site': {
                'name': 'zco.mx'
            }
        }

        preparer = PhotoDataPreparer(data)
        got = preparer.data()
        self.assertEqual(sorted(got.keys()), ['media[]', 'status'])
        self.assertEqual(len(got['media[]']), self._test_image_bytes)
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            got['status'],
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx #comics #FirstLast'
        )

    def test__media(self):
        data = {
            'book': {
                'cover_image_name': self._test_image,
            },
        }
        preparer = PhotoDataPreparer(data)
        got = preparer.media()
        self.assertEqual(len(got), self._test_image_bytes)

    def test__status(self):
        data = {
            'book': {
                'formatted_name_no_year': 'My Book 001',
                'short_url': 'http://101.zco.mx/MyBook-001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
                'short_url': 'http://101.zco.mx',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        preparer = PhotoDataPreparer(data)
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
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


class TestTweet(LocalTestCase):

    def test____init__(self):
        tweet = Tweet({})
        self.assertTrue(tweet)
        self.assertEqual(tweet.TWEET_MAX_CHARS, 140)
        self.assertEqual(tweet.SAMPLE_TCO_LINK, 'http://t.co/1234567890')

    def test__creator(self):
        data = {
            'creator': {
                'name': 'First Last',
                'twitter': '@First_Last',
            },
        }

        tweet = Tweet(data)
        self.assertEqual(tweet.creator(), '@First_Last')
        data['creator']['twitter'] = None
        tweet = Tweet(data)
        self.assertEqual(tweet.creator(), 'First Last')

    def test__for_length_calculation(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = {
            'book': {
                'formatted_name_no_year': 'My Book 001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = Tweet(data)
        self.assertEqual(
            tweet.for_length_calculation(),
            'My Book 001 by @First_Last | http://t.co/1234567890 | #zcomx #comics #FirstLast http://t.co/1234567890'
        )

        # No twitter handle
        data['creator']['twitter'] = None
        tweet = Tweet(data)
        self.assertEqual(
            tweet.for_length_calculation(),
            'My Book 001 by First Last | http://t.co/1234567890 | #zcomx #comics #FirstLast http://t.co/1234567890'
        )

    def test__from_data(self):
        data = {
            'book': {
                'formatted_name_no_year': 'My Book 001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = Tweet.from_data(data)
        self.assertTrue(isinstance(tweet, Tweet))
        self.assertEqual(tweet.twitter_data, data)
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

        # Exactly 140 characters
        name = '1234567890123456789012345678901234567890123456789'
        data['book']['formatted_name_no_year'] = name
        tweet = Tweet.from_data(data)
        self.assertTrue(isinstance(tweet, Tweet))
        self.assertEqual(len(tweet.for_length_calculation()), 140)

        # Long name requires truncation
        name = '1234567890123456789012345678901234567890123456789012345678'
        data['book']['formatted_name_no_year'] = name
        tweet = Tweet.from_data(data)
        self.assertTrue(isinstance(tweet, TruncatedTweet))
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

    def test__hash_tag_values(self):
        data = {
            'creator': {
                'name_for_url': 'FirstLast',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = Tweet(data)

        self.assertEqual(
            tweet.hash_tag_values(),
            ['zco.mx', 'comics', 'FirstLast']
        )

    def test__status(self):
        data = {
            'book': {
                'formatted_name_no_year': 'My Book 001',
                'short_url': 'http://101.zco.mx/MyBook-001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
                'short_url': 'http://101.zco.mx',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = Tweet(data)
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            tweet.status(),
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx #comics #FirstLast'
        )


class TestTruncatedTweet(LocalTestCase):

    def test__hash_tag_values(self):
        data = {
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = TruncatedTweet(data)

        self.assertEqual(
            tweet.hash_tag_values(),
            ['zco.mx']
        )

    def test_parent_status(self):
        data = {
            'book': {
                'formatted_name_no_year': 'My Book 001',
                'short_url': 'http://101.zco.mx/MyBook-001',
            },
            'creator': {
                'name': 'First Last',
                'name_for_url': 'FirstLast',
                'twitter': '@First_Last',
                'short_url': 'http://101.zco.mx',
            },
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = TruncatedTweet(data)
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            tweet.status(),
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx'
        )


class TestFunctions(LocalTestCase):

    def test__formatted_tags(self):
        tests = [
            # (tags, expect)
            ([], ''),
            (['val1'], '#val1'),
            (['val1', 'val2', 'val3'], '#val1 #val2 #val3'),
            ([string.punctuation], '#_'),
        ]

        for t in tests:
            self.assertEqual(formatted_tags(t[0]), t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
