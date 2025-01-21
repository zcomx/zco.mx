#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/tweeter.py
"""
import copy
import datetime
import json
import string
import unittest
import uuid
from twitter import TwitterHTTPError
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images import ImageDescriptor, UploadImage
from applications.zcomx.modules.social_media import OngoingPost
from applications.zcomx.modules.tweeter import (
    Authenticator,
    BaseTweet,
    CompletedBookTweet,
    ManyCreatorsOngoingUpdateTweet,
    OngoingUpdateTweet,
    PhotoDataPreparer,
    Poster,
    TextDataPreparer,
    TruncatedCompletedBookTweet,
    TruncatedOngoingUpdateTweet,
    creators_in_ongoing_post,
    formatted_tags,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class DubStatuses():
    """Stub Twitter statuses."""
    def __init__(self):
        self.posts = {}

    def destroy(self, post_id):
        if 'destroy' not in self.posts:
            self.posts['destroy'] = {}
        self.posts['destroy'][post_id] = 'destroyed'
        return post_id

    def update(self, **kwargs):
        if 'update' not in self.posts:
            self.posts['update'] = {}
        post_id = uuid.uuid4()
        self.posts['update'][post_id] = kwargs
        return post_id

    def update_with_media(self, **kwargs):
        if 'update_with_media' not in self.posts:
            self.posts['update_with_media'] = {}
        post_id = uuid.uuid4()
        self.posts['update_with_media'][post_id] = kwargs
        return post_id


class DubClient():
    """Stub Twitter client."""
    def __init__(self):
        self.statuses = DubStatuses()


class WithMediaTestCase(LocalTestCase):
    """Pre-define an test_image for tweet media."""
    _test_image = None
    _test_image_bytes = 0

    # pylint: disable=invalid-name
    @classmethod
    def setUpClass(cls):
        # Use an existing image to test with.
        creator = Creator.by_email(web.username)
        book_name = 'Test Do Not Delete'
        query = (db.book.name == book_name)
        rows = db(query).select(db.book.id)
        if not rows:
            cls.fail('Book not found, name: {n}'.format(n=book_name))

        book_id = rows[0].id

        query = (db.book_page.book_id == book_id) & \
            (db.book_page.page_no == 1)
        rows = db(query).select(
            db.book_page.image,
            limitby=(0, 1),
        )
        if not rows:
            cls.fail('Unable to get image to test with.')
        cls._test_image = rows[0]['image']

        upload_img = UploadImage(db.book_page.image, cls._test_image)
        fullname = upload_img.fullname(size='web')
        cls._test_image_bytes = ImageDescriptor(fullname).size_bytes()


class WithOngoingPostTestCase(LocalTestCase):

    _expect_status = None
    _twitter_data = None

    def setUp(self):
        self._twitter_data = {
            'ongoing_post': {
                'creators': [
                    {'name': 'Joe Smoe', 'twitter': '@joesmoe'},
                    {'name': 'My Name', 'twitter': '@myname'},
                ],
                'tumblr_post_id': '123456789012',
            },
            'site': {
                'name': 'zco.mx',
            },
        }

        # pylint: disable=line-too-long
        self._expect_status = 'New pages added by @joesmoe, @myname on zco.mx | http://zcomx.tumblr.com/post/123456789012 | #zcomx #comics'

        super().setUp()


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
            if isinstance(err.response_data, dict):
                json_data = str(err.response_data).replace("'", '"')
            else:
                json_data = err.response_data
            response_data = json.loads(json_data)
            errors = response_data['errors']
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]['message'], 'Bad Authentication data.')
            self.assertEqual(errors[0]['code'], 215)
        else:
            self.fail('TwitterHTTPError not raised.')


class TestBaseTweet(LocalTestCase):

    def test____init__(self):
        tweet = BaseTweet({})
        self.assertTrue(tweet)
        self.assertEqual(tweet.TWEET_MAX_CHARS, 140)
        self.assertEqual(tweet.SAMPLE_TCO_LINK, 'http://t.co/1234567890')


class TestCompletedBookTweet(LocalTestCase):

    def test__creator(self):
        data = {
            'creator': {
                'name': 'First Last',
                'twitter': '@First_Last',
            },
        }

        tweet = CompletedBookTweet(data)
        self.assertEqual(tweet.creator(), '@First_Last')
        data['creator']['twitter'] = None
        tweet = CompletedBookTweet(data)
        self.assertEqual(tweet.creator(), 'First Last')

    def test__for_length_calculation(self):
        # pylint: disable=line-too-long
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
        tweet = CompletedBookTweet(data)
        self.assertEqual(
            tweet.for_length_calculation(),
            'My Book 001 by @First_Last | http://t.co/1234567890 | #zcomx #comics #FirstLast http://t.co/1234567890'
        )

        # No twitter handle
        data['creator']['twitter'] = None
        tweet = CompletedBookTweet(data)
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
        tweet = CompletedBookTweet.from_data(data)
        self.assertTrue(isinstance(tweet, CompletedBookTweet))
        self.assertEqual(tweet.twitter_data, data)
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

        # Exactly 140 characters
        name = '1234567890123456789012345678901234567890123456789'
        data['book']['formatted_name_no_year'] = name
        tweet = CompletedBookTweet.from_data(data)
        self.assertTrue(isinstance(tweet, CompletedBookTweet))
        self.assertEqual(len(tweet.for_length_calculation()), 140)

        # Long name requires truncation
        name = '1234567890123456789012345678901234567890123456789012345678'
        data['book']['formatted_name_no_year'] = name
        tweet = CompletedBookTweet.from_data(data)
        self.assertTrue(isinstance(tweet, TruncatedCompletedBookTweet))
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
        tweet = CompletedBookTweet(data)

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
        tweet = CompletedBookTweet(data)
        # pylint: disable=line-too-long
        self.assertEqual(
            tweet.status(),
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx #comics #FirstLast'
        )


class TestManyCreatorsOngoingUpdateTweet(WithOngoingPostTestCase):

    _creators = [
        {'name': 'One One', 'twitter': '@one'},
        {'name': 'Two Two', 'twitter': '@two'},
        {'name': 'Three Three', 'twitter': '@three'},
        {'name': 'Four Four', 'twitter': '@four'},
    ]

    def test__creators_in_text_form(self):
        data = copy.deepcopy(self._twitter_data)
        data['ongoing_post']['creators'] = self._creators
        tweet = ManyCreatorsOngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_in_text_form(),
            '@one, @two and others'
        )

    def test__creators_for_post(self):
        data = copy.deepcopy(self._twitter_data)
        data['ongoing_post']['creators'] = self._creators
        tweet = ManyCreatorsOngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_for_post(),
            [
                {'name': 'One One', 'twitter': '@one'},
                {'name': 'Two Two', 'twitter': '@two'},
            ]
        )

    def test_parent_status(self):
        data = copy.deepcopy(self._twitter_data)
        data['ongoing_post']['creators'] = self._creators
        tweet = ManyCreatorsOngoingUpdateTweet(data)
        # pylint: disable=line-too-long
        self.assertEqual(
            tweet.status(),
            'New pages added by @one, @two and others on zco.mx | http://zcomx.tumblr.com/post/123456789012 | #zcomx'
        )


class TestOngoingUpdateTweet(WithOngoingPostTestCase):

    def test__creators_in_text_form(self):
        data = copy.deepcopy(self._twitter_data)

        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_in_text_form(),
            '@joesmoe, @myname'
        )

        data['ongoing_post']['creators'][0]['twitter'] = None
        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_in_text_form(),
            'Joe Smoe, @myname'
        )

        data['ongoing_post']['creators'][1]['twitter'] = None
        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_in_text_form(),
            'Joe Smoe, My Name'
        )

    def test__creators_for_post(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = ManyCreatorsOngoingUpdateTweet(data)
        self.assertEqual(
            tweet.creators_for_post(),
            [
                {'name': 'Joe Smoe', 'twitter': '@joesmoe'},
                {'name': 'My Name', 'twitter': '@myname'},
            ]
        )

    def test__for_length_calculation(self):
        data = copy.deepcopy(self._twitter_data)
        # pylint: disable=line-too-long
        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.for_length_calculation(),
            'New pages added by @joesmoe, @myname on zco.mx | http://t.co/1234567890 | #zcomx #comics'
        )

        # No twitter handle
        data['ongoing_post']['creators'][0]['twitter'] = None
        data['ongoing_post']['creators'][1]['twitter'] = None
        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.for_length_calculation(),
            'New pages added by Joe Smoe, My Name on zco.mx | http://t.co/1234567890 | #zcomx #comics'
        )

    def test__from_data(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = OngoingUpdateTweet.from_data(data)
        self.assertTrue(isinstance(tweet, OngoingUpdateTweet))
        self.assertEqual(tweet.twitter_data, data)
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

        # Exactly 140 characters
        twit = '123456789012345678901234567890123456789012345678901234567890'
        data['ongoing_post']['creators'][0]['twitter'] = twit
        tweet = OngoingUpdateTweet.from_data(data)
        self.assertTrue(isinstance(tweet, OngoingUpdateTweet))
        self.assertEqual(len(tweet.for_length_calculation()), 140)

        # Single creator, long name requires truncation
        twit = '1234567890123456789012345678901234567890123456789012345678901'
        data['ongoing_post']['creators'][0]['twitter'] = twit
        tweet = OngoingUpdateTweet.from_data(data)
        self.assertTrue(isinstance(tweet, TruncatedOngoingUpdateTweet))
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

        # Many creators, long name requires special class
        data['ongoing_post']['creators'] = [
            {'name': 'Very Long', 'twitter': '@very_long_handle'},
            {'name': 'Another Long', 'twitter': '@another_very_long_handle'},
            {'name': 'Yet Long', 'twitter': '@yet_another_very_long_handle'},
            {'name': 'More Long', 'twitter': '@more_another_very_long_handle'},
        ]
        tweet = OngoingUpdateTweet.from_data(data)
        self.assertTrue(isinstance(tweet, ManyCreatorsOngoingUpdateTweet))
        self.assertTrue(len(tweet.for_length_calculation()) <= 140)

    def test__hash_tag_values(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = OngoingUpdateTweet(data)

        self.assertEqual(
            tweet.hash_tag_values(),
            ['zco.mx', 'comics']
        )

    def test__status(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = OngoingUpdateTweet(data)
        # pylint: disable=line-too-long
        self.assertEqual(
            tweet.status(),
            self._expect_status
        )

    def test__tumblr_url(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = OngoingUpdateTweet(data)
        self.assertEqual(
            tweet.tumblr_url(),
            'http://zcomx.tumblr.com/post/123456789012'
        )


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
        # pylint: disable=line-too-long
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
        # pylint: disable=line-too-long
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
        post_id = '123456'
        poster.delete_post(post_id)
        self.assertEqual(
            client.statuses.posts,
            {
                'destroy': {
                    '123456': 'destroyed',
                }
            }
        )

    def test__post_photo(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_photo({'aaa': 'bbb'})
        self.assertEqual(
            client.statuses.posts,
            {
                'update_with_media': {
                    post_id: {'aaa': 'bbb'}
                }
            }
        )

    def test__post_text(self):
        client = DubClient()
        poster = Poster(client)
        post_id = poster.post_text({'aaa': 'bbb'})
        self.assertEqual(
            client.statuses.posts,
            {
                'update': {
                    post_id: {'aaa': 'bbb'}
                }
            }
        )


class TestTextDataPreparer(WithOngoingPostTestCase):

    def test____init__(self):
        preparer = TextDataPreparer({})
        self.assertTrue(preparer)

    def test__data(self):
        preparer = TextDataPreparer(self._twitter_data)
        self.assertEqual(
            preparer.data(),
            {'status': self._expect_status}
        )

    def test__status(self):
        preparer = TextDataPreparer(self._twitter_data)
        self.assertEqual(
            preparer.status(),
            self._expect_status
        )


class TestTruncatedCompletedBookTweet(LocalTestCase):

    def test__hash_tag_values(self):
        data = {
            'site': {
                'name': 'zco.mx',
            },
        }
        tweet = TruncatedCompletedBookTweet(data)

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
        tweet = TruncatedCompletedBookTweet(data)
        # pylint: disable=line-too-long
        self.assertEqual(
            tweet.status(),
            'My Book 001 by @First_Last | http://101.zco.mx/MyBook-001 | #zcomx'
        )


class TestTruncatedOngoingUpdateTweet(WithOngoingPostTestCase):

    def test__hash_tag_values(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = TruncatedOngoingUpdateTweet(data)

        self.assertEqual(
            tweet.hash_tag_values(),
            ['zco.mx']
        )

    def test_parent_status(self):
        data = copy.deepcopy(self._twitter_data)
        tweet = TruncatedOngoingUpdateTweet(data)
        # pylint: disable=line-too-long
        self.assertEqual(
            tweet.status(),
            'New pages added by @joesmoe, @myname on zco.mx | http://zcomx.tumblr.com/post/123456789012 | #zcomx'
        )


class TestFunctions(LocalTestCase):

    def test__creators_in_ongoing_post(self):
        ongoing_post = self.add(OngoingPost, dict(
            post_date=datetime.date.today(),
        ))

        creator_1 = self.add(Creator, dict(
            name_for_url='Creator One',
        ))

        creator_2 = self.add(Creator, dict(
            name_for_url='Creator Two',
        ))

        book_1 = self.add(Book, dict(
            name='Book One',
            creator_id=creator_1.id,
        ))

        book_2 = self.add(Book, dict(
            name='Book Two',
            creator_id=creator_2.id,
        ))

        activity_log_1 = self.add(ActivityLog, dict(
            book_id=book_1.id,
            ongoing_post_id=None,
        ))

        activity_log_2 = self.add(ActivityLog, dict(
            book_id=book_2.id,
            ongoing_post_id=None,
        ))

        # No activity logs associated with ongoing post.
        self.assertEqual(
            creators_in_ongoing_post(ongoing_post),
            []
        )

        # Single activity log associated with ongoing post.
        activity_log_1.update_record(ongoing_post_id=ongoing_post.id)
        db.commit()

        self.assertEqual(
            creators_in_ongoing_post(ongoing_post),
            [creator_1.id]
        )

        # Multiple activity logs associated with ongoing post.
        activity_log_2.update_record(ongoing_post_id=ongoing_post.id)
        db.commit()

        self.assertEqual(
            creators_in_ongoing_post(ongoing_post),
            [creator_1.id, creator_2.id]
        )

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
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
