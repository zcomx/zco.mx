#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/social_media.py

"""
import time
import unittest
from applications.zcomx.modules.social_media import \
    SocialMedia, \
    FacebookSocialMedia, \
    TumblrSocialMedia, \
    TwitterSocialMedia
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class BaseTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _auth_user = None
    _book = None
    _creator = None
    _type_id_by_name = {}

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        for t in db(db.book_type).select():
            cls._type_id_by_name[t.name] = t.id

        cls._auth_user = cls.add(db.auth_user, dict(
            name='First Last',
        ))

        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            email='test_social_media@example.com',
            path_name='First Last',
        ))

        cls._book = cls.add(db.book, dict(
            name='Test Social Media',
            creator_id=cls._creator.id,
            book_type_id=cls._type_id_by_name['one-shot'],
        ))

        cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=1,
            image='book_page.image.000.aaa.png',
        ))

        cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=2,
            image='book_page.image.001.aab.png',
        ))


class TestSocialMedia(BaseTestCase):

    def test____init__(self):

        def test_it(media):
            self.assertTrue(media)
            self.assertEqual(media.book, self._book)
            self.assertEqual(media.creator, self._creator)

        # entities are Row instances
        test_it(SocialMedia(self._book, creator_entity=self._creator))
        # entities are integers
        test_it(SocialMedia(self._book.id, creator_entity=self._creator.id))
        # creator_entity is None
        test_it(SocialMedia(self._book))

    def test__follow_url(self):
        media = SocialMedia(self._book, creator_entity=self._creator)
        self.assertRaises(NotImplementedError, media.follow_url)

    def test__icon_url(self):
        media = SocialMedia(self._book, creator_entity=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/zco.mx-logo-small.png')
        media.icon_filename = None
        self.assertEqual(media.icon_url(), None)
        media.icon_filename = 'my_icon.png'
        self.assertEqual(media.icon_url(), '/zcomx/static/images/my_icon.png')

    def test__share_url(self):
        media = SocialMedia(self._book, creator_entity=self._creator)
        self.assertRaises(NotImplementedError, media.share_url)


class TestFacebookSocialMedia(BaseTestCase):

    def test____init__(self):
        media = FacebookSocialMedia(self._book, creator_entity=self._creator)
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
            self._creator.update_record(facebook=t[0])
            db.commit()
            media = FacebookSocialMedia(
                self._book, creator_entity=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test_icon_url(self):
        media = FacebookSocialMedia(self._book, creator_entity=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/facebook_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        media = FacebookSocialMedia(self._book, creator_entity=self._creator)
        v = int(time.mktime(request.now.timetuple()))
        self.assertEqual(
            media.share_url(),
            'http://www.facebook.com/sharer.php?p%5Burl%5D=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media%2F001&v={v}'.format(
                cid=self._creator.id, v=v)
        )


class TestTumblrSocialMedia(BaseTestCase):

    def test____init__(self):
        media = TumblrSocialMedia(self._book, creator_entity=self._creator)
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
            self._creator.update_record(tumblr=t[0])
            db.commit()
            media = TumblrSocialMedia(
                self._book, creator_entity=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test__get_username(self):
        media = TumblrSocialMedia(self._book, creator_entity=self._creator)
        tests = [
            # (tumblr, expect)
            (None, None),
            ('http://auser.tumblr.com', 'auser'),
            ('_invalid_ _tumblr_', None),
            ('www.tumblr.com', None),
        ]
        for t in tests:
            self._creator.update_record(tumblr=t[0])
            db.commit()
            media = TumblrSocialMedia(
                self._book, creator_entity=self._creator)
            self.assertEqual(media.get_username(), t[1])

    def test_icon_url(self):
        media = TumblrSocialMedia(self._book, creator_entity=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/tumblr_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        media = TumblrSocialMedia(self._book, creator_entity=self._creator)
        self._creator.update_record(tumblr=None)
        db.commit()
        self.assertEqual(
            media.share_url(),
            'https://www.tumblr.com/share/photo?source=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media%2F001.png&clickthru=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media&caption=Check+out+Test+Social+Media+by+%3Ca+class%3D%22tumblelog%22%3EFirst+Last%3C%2Fa%3E'.format(cid=self._creator.id)

        )

        self._creator.update_record(tumblr='http://zco.tumblr.com')
        db.commit()
        self.assertEqual(
            media.share_url(),
            'https://www.tumblr.com/share/photo?source=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media%2F001.png&clickthru=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media&caption=Check+out+Test+Social+Media+by+%3Ca+class%3D%22tumblelog%22%3Ezco%3C%2Fa%3E'.format(cid=self._creator.id)
        )


class TestTwitterSocialMedia(BaseTestCase):

    def test____init__(self):
        media = TwitterSocialMedia(self._book, creator_entity=self._creator)
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
            self._creator.update_record(twitter=t[0])
            db.commit()
            media = TwitterSocialMedia(
                self._book, creator_entity=self._creator)
            self.assertEqual(media.follow_url(), t[1])

    def test_icon_url(self):
        media = TwitterSocialMedia(self._book, creator_entity=self._creator)
        self.assertEqual(
            media.icon_url(), '/zcomx/static/images/twitter_logo.svg')

    def test__share_url(self):
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        media = TwitterSocialMedia(self._book, creator_entity=self._creator)
        self._creator.update_record(twitter=None)
        db.commit()
        self.assertEqual(
            media.share_url(),
            'https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media&text=Check+out+%27Test+Social+Media%27+by+First+Last&hashtage='.format(cid=self._creator.id)
        )

        self._creator.update_record(twitter='@zco')
        db.commit()
        self.assertEqual(
            media.share_url(),
            'https://twitter.com/share?url=http%3A%2F%2F{cid}.zco.mx%2FTest_Social_Media&text=Check+out+%27Test+Social+Media%27+by+%40zco&hashtage='.format(cid=self._creator.id)
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
