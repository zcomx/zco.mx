#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/social_media.py

"""
import io
import time
import unittest
import urllib.error
from twitter import TwitterHTTPError
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.facebook import FacebookAPIError
from applications.zcomx.modules.social_media import \
    FacebookPoster, \
    FacebookSocialMedia, \
    OngoingPost, \
    SocialMedia, \
    SocialMediaPoster, \
    SocialMediaPostError, \
    TumblrPoster, \
    TumblrSocialMedia, \
    TwitterPoster, \
    TwitterSocialMedia
from applications.zcomx.modules.tests.helpers import DubMeta
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class BaseTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _auth_user = None
    _book = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):

        self._auth_user = self.add(AuthUser, dict(
            name='First Last',
        ))

        self._creator = self.add(Creator, dict(
            auth_user_id=self._auth_user.id,
            email='test_social_media@example.com',
        ))

        self._book = self.add(Book, dict(
            name='Test Social Media',
            creator_id=self._creator.id,
            book_type_id=BookType.by_name('one-shot').id,
            name_for_url='TestSocialMedia',
        ))

        self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
            image='book_page.image.000.aaa.png',
        ))

        self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=2,
            image='book_page.image.001.aab.png',
        ))


class TestOngoingPost(LocalTestCase):

    def test_parent__init__(self):
        post = self.add(
            OngoingPost, dict(facebook_post_id='_test_parent__init__'))
        got = OngoingPost.from_id(post.id)
        self.assertTrue(got)
        self.assertEqual(got.facebook_post_id, '_test_parent__init__')


class TestSocialMedia(BaseTestCase):

    def test____init__(self):

        def test_it(media):
            self.assertTrue(media)
            self.assertEqual(media.book, self._book)
            self.assertEqual(media.creator, self._creator)

        test_it(SocialMedia(self._book, creator=self._creator))
        test_it(SocialMedia(self._book))

    def test_class_factory(self):
        social_media = SocialMedia.class_factory('facebook', self._book)
        self.assertTrue(isinstance(social_media, FacebookSocialMedia))
        social_media = SocialMedia.class_factory('tumblr', self._book)
        self.assertTrue(isinstance(social_media, TumblrSocialMedia))
        social_media = SocialMedia.class_factory('twitter', self._book)
        self.assertTrue(isinstance(social_media, TwitterSocialMedia))

    def test__follow_url(self):
        media = SocialMedia(self._book, creator=self._creator)
        self.assertRaises(NotImplementedError, media.follow_url)

    def test__icon_url(self):
        media = SocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/zco.mx-logo-small.png')
        media.icon_filename = None
        self.assertEqual(media.icon_url(), None)
        media.icon_filename = 'my_icon.png'
        self.assertEqual(media.icon_url(), '/zcomx/static/images/my_icon.png')

    def test__share_url(self):
        media = SocialMedia(self._book, creator=self._creator)
        self.assertRaises(NotImplementedError, media.share_url)


class TestSocialMediaPoster(BaseTestCase):

    def test____init__(self):
        social_media = SocialMediaPoster()
        self.assertTrue(social_media)

    def test_class_factory(self):
        social_media = SocialMediaPoster.class_factory('facebook')
        self.assertTrue(isinstance(social_media, FacebookPoster))
        social_media = SocialMediaPoster.class_factory('tumblr')
        self.assertTrue(isinstance(social_media, TumblrPoster))
        social_media = SocialMediaPoster.class_factory('twitter')
        self.assertTrue(isinstance(social_media, TwitterPoster))

    def test__additional_prepare_data(self):
        poster = SocialMediaPoster()
        data = {'aaa': 111}
        self.assertEqual(
            poster.additional_prepare_data(data),
            {'aaa': 111}
        )

    def test__credentials(self):
        social_media = SocialMediaPoster()
        self.assertRaises(NotImplementedError, social_media.credentials)

    def test__post(self):
        class DubPoster(object):
            def __init__(self, client):
                self.client = client

        class DubAuthenticator(object):
            def __init__(self, credentials):
                self.credentials = credentials

            def authenticate(self):
                # pylint: disable=no-self-use
                return 'fake_client'

        class DubSocialMediaPoster(SocialMediaPoster, metaclass=DubMeta):
            # pylint: disable=abstract-method
            _dub_methods = [
                'credentials',
                'post_data',
                'prepare_data',
            ]
            authenticate_class = DubAuthenticator
            poster_class = DubPoster

        DubSocialMediaPoster.dub.credentials['return'] = {'username': 'abcdef'}
        DubSocialMediaPoster.dub.post_data['return'] = 'post id 123456'
        DubSocialMediaPoster.dub.prepare_data['return'] = {'book': 'My Title'}

        poster = DubSocialMediaPoster()
        got = poster.post(self._book, self._creator)
        self.assertEqual(got, 'post id 123456')

        self.assertEqual(len(poster.calls), 3)
        self.assertEqual(poster.calls[0], ('credentials', (), {}))
        self.assertEqual(
            poster.calls[1], ('prepare_data', (self._book, self._creator), {}))
        self.assertEqual(poster.calls[2][0], 'post_data')
        poster_call_arg_1 = poster.calls[2][1][0]
        self.assertTrue(isinstance(poster_call_arg_1, DubPoster))
        self.assertEqual(poster.calls[2][1][1], {'book': 'My Title'})

    def test__post_data(self):
        social_media = SocialMediaPoster()
        self.assertRaises(
            NotImplementedError, social_media.post_data, None, {})

    def test__prepare_data(self):
        class DubPhotoDataPreparer(object):
            def __init__(self, social_media_data):
                self.social_media_data = social_media_data

            def data(self):
                return {
                    'caption': 'My Caption',
                    'description': self.social_media_data['book']['name'],
                    'name': self.social_media_data['creator']['name'],
                }

        class DubSocialMediaPoster(SocialMediaPoster, metaclass=DubMeta):
            # pylint: disable=abstract-method
            _dub_methods = [
                'additional_prepare_data',
            ]
            photo_data_preparer_class = DubPhotoDataPreparer

        DubSocialMediaPoster.dub.additional_prepare_data['return'] = \
            {'username': 'abcdef'}

        poster = DubSocialMediaPoster()
        got = poster.prepare_data(self._book, self._creator)
        self.assertEqual(got, {'username': 'abcdef'})

        self.assertEqual(len(poster.calls), 1)
        self.assertEqual(
            poster.calls[0],
            (
                'additional_prepare_data',
                ({
                    'caption': 'My Caption',
                    'description': 'Test Social Media',
                    'name': 'First Last',
                },),
                {}
            )
        )


class TestFacebookPoster(BaseTestCase):

    def test__credentials(self):
        poster = FacebookPoster()
        credentials = poster.credentials()
        expect = [
            # (key, regexp),
            ('redirect_uri', 'https://zco.mx/z/about'),
            ('page_name', 'zco.mx test page'),
            ('email', r'\w+@gmail.com'),
            ('password', r'\w{15}'),
            ('client_id', r'\w{16}'),
        ]
        for e in expect:
            self.assertRegex(str(credentials[e[0]]), e[1])

    def test__post_data(self):
        class DubPoster(object):
            def __init__(self, client):
                self.client = client

            def post_photo(self, data):
                # pylint: disable=no-self-use
                if data['make_it'] == 'succeed':
                    return {'id': '12345'}
                elif data['make_it'] == 'have_no_id':
                    return {'key': 'value'}
                elif data['make_it'] == 'raise_exception':
                    raise FacebookAPIError('fake message')

        dub_poster = DubPoster('abcdef')
        poster = FacebookPoster()
        got = poster.post_data(dub_poster, {'make_it': 'succeed'})
        self.assertEqual(got, '12345')

        try:
            poster.post_data(dub_poster, {'make_it': 'have_no_id'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'Facebook post failed')
        else:
            self.fail('SocialMediaPostError not raised.')

        try:
            poster.post_data(dub_poster, {'make_it': 'raise_exception'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'fake message')
        else:
            self.fail('SocialMediaPostError not raised.')


class TestFacebookSocialMedia(BaseTestCase):

    def test_parent__init__(self):
        media = FacebookSocialMedia(self._book, creator=self._creator)
        self.assertTrue(media)
        self.assertEqual(media.book, self._book)
        self.assertEqual(media.creator, self._creator)

    def test__follow_url(self):
        tests = [
            # (facebook, expect)
            (None, None),
            ('http://www.facebook.com/auser', 'http://www.facebook.com/auser'),
        ]
        for t in tests:
            data = dict(facebook=t[0])
            self._creator = Creator.from_updated(self._creator, data)
            media = FacebookSocialMedia(
                self._book, creator=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test_icon_url(self):
        media = FacebookSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/facebook_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        media = FacebookSocialMedia(self._book, creator=self._creator)
        v = int(time.mktime(request.now.timetuple()))
        self.assertEqual(
            media.share_url(),
            'http://www.facebook.com/sharer.php?p%5Burl%5D=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia%2F001&v={v}'.format(
                cid=self._creator.id, v=v)
        )


class TestTumblrPoster(BaseTestCase):

    def test__additional_prepare_data(self):
        poster = TumblrPoster()
        data = {'aaa': 111}
        self.assertEqual(
            poster.additional_prepare_data(data),
            {'aaa': 111, 'state': 'draft'}
        )

    def test__credentials(self):
        poster = TumblrPoster()
        credentials = poster.credentials()
        expect = [
            # (key, regexp),
            ('consumer_key', r'\w{50}'),
            ('consumer_secret', r'\w{50}'),
            ('oauth_secret', r'\w{50}'),
            ('oauth_token', r'\w{50}'),
        ]
        for e in expect:
            self.assertRegex(str(credentials[e[0]]), e[1])

    def test__post_data(self):
        class DubPoster(object):
            def __init__(self, client):
                self.client = client

            def post_photo(self, unused_username, data):
                # pylint: disable=no-self-use
                if data['make_it'] == 'succeed':
                    return {'id': '12345'}
                elif data['make_it'] == 'meta_error':
                    return {
                        'meta': {
                            'msg': 'Meta error',
                            'status': 'FAIL',
                        }
                    }
                elif data['make_it'] == 'response_errors':
                    return {'response': {'errors': ['Error 1', 'Error 2']}}

        dub_poster = DubPoster('abcdef')
        poster = TumblrPoster()
        got = poster.post_data(dub_poster, {'make_it': 'succeed'})
        self.assertEqual(got, '12345')

        try:
            poster.post_data(dub_poster, {'make_it': 'meta_error'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'Status: FAIL, msg: Meta error')
        else:
            self.fail('SocialMediaPostError not raised.')

        try:
            poster.post_data(dub_poster, {'make_it': 'response_errors'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'Error 1\nError 2')
        else:
            self.fail('SocialMediaPostError not raised.')


class TestTumblrSocialMedia(BaseTestCase):

    def test____init__(self):
        media = TumblrSocialMedia(self._book, creator=self._creator)
        self.assertTrue(media)
        self.assertEqual(media.book, self._book)
        self.assertEqual(media.creator, self._creator)

    def test__follow_url(self):
        tests = [
            # (tumblr, expect)
            (None, None),
            ('http://auser.tumblr.com', 'https://www.tumblr.com/follow/auser'),
        ]
        for t in tests:
            data = dict(tumblr=t[0])
            self._creator = Creator.from_updated(self._creator, data)
            media = TumblrSocialMedia(
                self._book, creator=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test__get_username(self):
        media = TumblrSocialMedia(self._book, creator=self._creator)
        data = dict(tumblr='http://auser.tumblr.com')
        self._creator = Creator.from_updated(self._creator, data)
        media = TumblrSocialMedia(self._book, creator=self._creator)
        self.assertEqual(media.get_username(), 'auser')

    def test_icon_url(self):
        media = TumblrSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/tumblr_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = dict(tumblr=None)
        self._creator = Creator.from_updated(self._creator, data)
        media = TumblrSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.share_url(),
            'https://www.tumblr.com/share/photo?clickthru=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia&source=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia%2F001.png&caption=Check+out+Test+Social+Media+by+%3Ca+class%3D%22tumblelog%22%3EFirst+Last%3C%2Fa%3E'.format(cid=self._creator.id)

        )

        data = dict(tumblr='http://zco.tumblr.com')
        self._creator = Creator.from_updated(self._creator, data)
        media = TumblrSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.share_url(),
            'https://www.tumblr.com/share/photo?clickthru=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia&source=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia%2F001.png&caption=Check+out+Test+Social+Media+by+%3Ca+class%3D%22tumblelog%22%3Ezco%3C%2Fa%3E'.format(cid=self._creator.id)
        )


class TestTwitterPoster(BaseTestCase):

    def test__credentials(self):
        poster = TwitterPoster()
        credentials = poster.credentials()
        expect = [
            # (key, regexp),
            ('consumer_key', r'\w{25}'),
            ('consumer_secret', r'\w{50}'),
            ('oauth_secret', r'\w{45}'),
            ('oauth_token', r'[\w-]{52}'),
        ]
        for e in expect:
            self.assertRegex(str(credentials[e[0]]), e[1])

    def test__post_data(self):

        class DubPoster(object):
            def __init__(self, client):
                self.client = client

            def post_photo(self, data):
                # pylint: disable=no-self-use
                if data['make_it'] == 'succeed':
                    return {'id': '12345'}
                elif data['make_it'] == 'have_no_id':
                    return {
                        'meta': {
                            'msg': 'Meta error',
                            'status': 'FAIL',
                        }
                    }
                elif data['make_it'] == 'raise_exception':
                    j = b'"{"errors": [{"code": "A", "message": "Foo A"}]}"'
                    fp = io.BytesIO()
                    fp.write(j)
                    fp.seek(0)
                    e = urllib.error.HTTPError('url', 'code', 'msg', 'hdrs', fp)
                    e.code = 999
                    e.headers = {'Content-Encoding': 'notgzip'}
                    raise TwitterHTTPError(e, 'uri', 'json', {})

        dub_poster = DubPoster('abcdef')
        poster = TwitterPoster()
        got = poster.post_data(dub_poster, {'make_it': 'succeed'})
        self.assertEqual(got, '12345')

        try:
            poster.post_data(dub_poster, {'make_it': 'have_no_id'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'Twitter post failed')
        else:
            self.fail('SocialMediaPostError not raised.')

        try:
            poster.post_data(dub_poster, {'make_it': 'raise_exception'})
        except SocialMediaPostError as err:
            self.assertEqual(str(err), 'Code: A, msg: Foo A')
        else:
            self.fail('SocialMediaPostError not raised.')


class TestTwitterSocialMedia(BaseTestCase):

    def test_parent__init__(self):
        media = TwitterSocialMedia(self._book, creator=self._creator)
        self.assertTrue(media)
        self.assertEqual(media.book, self._book)
        self.assertEqual(media.creator, self._creator)

    def test__follow_url(self):
        tests = [
            # (twitter, expect)
            (None, None),
            ('@zco', 'https://twitter.com/intent/follow?screen_name=@zco'),
        ]
        for t in tests:
            data = dict(twitter=t[0])
            self._creator = Creator.from_updated(self._creator, data)
            media = TwitterSocialMedia(
                self._book, creator=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test_icon_url(self):
        media = TwitterSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/twitter_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        data = dict(twitter=None)
        self._creator = Creator.from_updated(self._creator, data)
        media = TwitterSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.share_url(),
            'https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia&text=Check+out+%27Test+Social+Media%27+by+First+Last&hashtage='.format(cid=self._creator.id)
        )
        data = dict(twitter='@zco')
        self._creator = Creator.from_updated(self._creator, data)
        media = TwitterSocialMedia(self._book, creator=self._creator)
        self.assertEqual(
            media.share_url(),
            'https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FTestSocialMedia&text=Check+out+%27Test+Social+Media%27+by+%40zco&hashtage='.format(cid=self._creator.id)
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
