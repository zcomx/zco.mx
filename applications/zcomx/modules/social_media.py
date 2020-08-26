#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Classes and functions related to social media.
"""
import json
import time
import urllib.parse
from twitter import TwitterHTTPError
from gluon import *
from applications.zcomx.modules.books import \
    get_page, \
    short_page_img_url, \
    short_page_url, \
    short_url, \
    social_media_data as book_social_media_data
from applications.zcomx.modules.creators import \
    Creator, \
    social_media_data as creator_social_media_data
from applications.zcomx.modules.facebook import \
    Authenticator as FbAuthenticator, \
    FacebookAPIError, \
    PhotoDataPreparer as FbPhotoDataPreparer, \
    Poster as FbPoster
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.tumblr import \
    Authenticator, \
    PhotoDataPreparer, \
    Poster
from applications.zcomx.modules.tweeter import \
    Authenticator as TwAuthenticator, \
    PhotoDataPreparer as TwPhotoDataPreparer, \
    Poster as TwPoster
from applications.zcomx.modules.utils import ClassFactory
from applications.zcomx.modules.zco import SITE_NAME

LOG = current.app.logger


class OngoingPost(Record):
    """Class representing a ongoing_post record"""
    db_table = 'ongoing_post'


class SocialMedia(object):
    """Base class representing social media"""

    class_factory = ClassFactory('class_factory_id')
    icon_filename = 'zco.mx-logo-small.png'
    site = None

    def __init__(self, book, creator=None):
        """Constructor

        Args:
            book: Book instance
            creator: Creator instance. If None, it is created from
                book.creator_id.
        """
        self.book = book
        if creator:
            self.creator = creator
        else:
            self.creator = Creator.from_id(self.book.creator_id)

    def follow_url(self):
        """Return a follow url.

        Returns:
            string: url representing a follow link.
        """
        raise NotImplementedError()

    def icon_url(self):
        """Return a url for the icon.

        Returns:
            string: url to the icon.
        """
        if not self.icon_filename:
            return
        return URL(c='static', f='images/{img}'.format(img=self.icon_filename))

    def share_url(self):
        """Return a share url.

        Returns:
            string: url representing a share link.
        """
        raise NotImplementedError()


@SocialMedia.class_factory.register
class FacebookSocialMedia(SocialMedia):
    """Class representing social media: facebook"""

    class_factory_id = 'facebook'
    icon_filename = 'facebook_logo.svg'
    site = 'http://www.facebook.com'

    def follow_url(self):
        """Return a follow url.

        Returns:
            string: url representing a follow link.
        """
        return self.creator.facebook

    def share_url(self):
        """Return a share url.

        Returns:
            string: url representing a share link.
        """
        # 'v' is a cache buster.
        query = {
            'p[url]': short_page_url(get_page(self.book, page_no='first')),
            'v': int(time.mktime(current.request.now.timetuple())),
        }
        return '{site}/sharer.php?{path}'.format(
            site=self.site, path=urllib.parse.urlencode(query))


@SocialMedia.class_factory.register
class TumblrSocialMedia(SocialMedia):
    """Class representing social media: tumblr"""

    class_factory_id = 'tumblr'
    icon_filename = 'tumblr_logo.svg'
    site = 'https://www.tumblr.com'

    def __init__(self, book, creator=None):
        """Constructor"""
        SocialMedia.__init__(self, book, creator=creator)
        self._username = None

    def follow_url(self):
        """Return a follow url.

        Returns:
            string: url representing a follow link.
        """
        username = self.get_username()
        if not username:
            return
        return '{site}/follow/{handle}'.format(site=self.site, handle=username)

    def get_username(self):
        """Get the tumblr username."""
        if not self.creator.tumblr:
            return

        if self._username is None:
            # Extract the user name.
            netloc = urllib.parse.urlparse(self.creator.tumblr).netloc
            if not netloc:
                LOG.debug('Invalid tumblr: %s', self.creator.tumblr)
                return
            self._username = netloc.split('.', 1)[0]
        return self._username

    def share_url(self):
        """Return a share url.

        Returns:
            string: url representing a share link.
        """
        caption_fmt = 'Check out {title} by <a class="tumblelog">{handle}</a>'
        query = {
            'clickthru': short_url(self.book),
            'source': short_page_img_url(get_page(self.book, page_no='first')),
            'caption': caption_fmt.format(
                title=self.book.name,
                handle=self.get_username() or self.creator.name
            ),
        }
        return '{site}/share/photo?{path}'.format(
            site=self.site, path=urllib.parse.urlencode(query))


@SocialMedia.class_factory.register
class TwitterSocialMedia(SocialMedia):
    """Class representing social media: twitter"""

    class_factory_id = 'twitter'
    icon_filename = 'twitter_logo.svg'
    site = 'https://twitter.com'

    def follow_url(self):
        """Return a follow url.

        Returns:
            string: url representing a follow link.
        """
        if not self.creator.twitter:
            return
        return '{site}/intent/follow?screen_name={handle}'.format(
            site=self.site, handle=self.creator.twitter)

    def share_url(self):
        """Return a share url.

        Returns:
            string: url representing a share link.
        """
        query = {
            'url': short_url(self.book),
            'text': "Check out '{title}' by {creator}".format(
                title=self.book.name,
                creator=self.creator.twitter or self.creator.name
            ),
            'hashtage': '',
        }
        return '{site}/share?{path}'.format(
            site=self.site, path=urllib.parse.urlencode(query))


class SocialMediaPostError(Exception):
    """Exception class for errors occurring while posting on social media."""
    pass


class SocialMediaPoster(object):
    """Base class representing a social media poster."""

    authenticate_class = None
    class_factory = ClassFactory('class_factory_id')
    poster_class = None
    photo_data_preparer_class = None

    def __init__(self):
        """Initializer"""
        pass

    def additional_prepare_data(self, data):
        """Do additional preparation of data.

        Subclasses can use this method to provide additional preparation
        of data specific to that class.

        Args:
            data: dict of data used in api post.

        Returns:
            dict
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return data

    def credentials(self):
        """Return the authentication credentials.

        Returns:
            dict of oauth credentials
        """
        raise NotImplementedError

    def post(self, book, creator):
        """Post to social media.

        Args:
            book: Book instance
            creator: Creator instance

        Returns:
            dict
        """
        # not-callable (E1102): *%%s is not callable*
        # pylint: disable=E1102
        client = self.authenticate_class(self.credentials()).authenticate()
        poster = self.poster_class(client)
        return self.post_data(poster, self.prepare_data(book, creator))

    def post_data(self, poster, photo_data):
        """Post the data using the api.

        Args:
            poster: Poster instance
            photo_data: dict of data for photo
        """
        raise NotImplementedError

    def prepare_data(self, book, creator):
        """Prepare the data for the api.

        Args:
            book: Book instance
            creator: Creator instance

        Returns:
            dict
        """
        social_media_data = {
            'book': book_social_media_data(book),
            'creator': creator_social_media_data(creator),
            'site': {'name': SITE_NAME},
        }
        # not-callable (E1102): *%%s is not callable*
        # pylint: disable=E1102
        photo_data = self.photo_data_preparer_class(social_media_data).data()
        return self.additional_prepare_data(photo_data)


@SocialMediaPoster.class_factory.register
class FacebookPoster(SocialMediaPoster):
    """Class representing a poster for posting material on facebook."""

    authenticate_class = FbAuthenticator
    class_factory_id = 'facebook'
    poster_class = FbPoster
    photo_data_preparer_class = FbPhotoDataPreparer

    def credentials(self):
        settings = current.app.local_settings
        return {
            'email': settings.facebook_email,
            'password': settings.facebook_password,
            'client_id': settings.facebook_client_id,
            'redirect_uri': settings.facebook_redirect_uri,
            'page_name': settings.facebook_page_name
        }

    def post_data(self, poster, photo_data):
        """Post the data using the api."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        error = None
        try:
            result = poster.post_photo(photo_data)
        except FacebookAPIError as err:
            error = str(err)
            result = {}

        if 'id' not in result:
            msg = error or 'Facebook post failed'
            raise SocialMediaPostError(msg)

        post_id = result['id']
        LOG.debug('post_id: %s', post_id)
        return post_id


@SocialMediaPoster.class_factory.register
class TumblrPoster(SocialMediaPoster):
    """Class representing a poster for posting material on tumblr."""

    authenticate_class = Authenticator
    class_factory_id = 'tumblr'
    poster_class = Poster
    photo_data_preparer_class = PhotoDataPreparer

    def additional_prepare_data(self, data):
        settings = current.app.local_settings
        if settings.tumblr_post_state:
            data['state'] = settings.tumblr_post_state
        return data

    def credentials(self):
        settings = current.app.local_settings
        return {
            'consumer_key': settings.tumblr_consumer_key,
            'consumer_secret': settings.tumblr_consumer_secret,
            'oauth_token': settings.tumblr_oauth_token,
            'oauth_secret': settings.tumblr_oauth_secret,
        }

    def post_data(self, poster, photo_data):
        """Post the data using the api."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        settings = current.app.local_settings
        result = poster.post_photo(settings.tumblr_username, photo_data)
        if 'id' not in result:
            errors = []
            # Try to get an error message.
            if 'meta' in result:
                if 'status' in result['meta'] and 'msg' in result['meta']:
                    errors.append('Status: {s}, msg: {m}'.format(
                        s=result['meta']['status'],
                        m=result['meta']['msg']
                    ))

            if 'response' in result and 'errors' in result['response']:
                for error in result['response']['errors']:
                    errors.append(error)
            err_msg = "\n".join(errors)
            raise SocialMediaPostError(err_msg)

        post_id = result['id']
        LOG.debug('post_id: %s', post_id)
        return post_id


@SocialMediaPoster.class_factory.register
class TwitterPoster(SocialMediaPoster):
    """Class representing a poster for posting material on twitter."""

    authenticate_class = TwAuthenticator
    class_factory_id = 'twitter'
    poster_class = TwPoster
    photo_data_preparer_class = TwPhotoDataPreparer

    def credentials(self):
        settings = current.app.local_settings
        return {
            'consumer_key': settings.twitter_consumer_key,
            'consumer_secret': settings.twitter_consumer_secret,
            'oauth_token': settings.twitter_oauth_token,
            'oauth_secret': settings.twitter_oauth_secret,
        }

    def post_data(self, poster, photo_data):
        """Post the data using the api."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        error = None
        try:
            result = poster.post_photo(photo_data)
        except TwitterHTTPError as err:
            error = err
            result = {}

        if 'id' not in result:
            err_msg = 'Twitter post failed'
            if error:
                json_data = error.response_data.strip('"')
                response_data = json.loads(json_data)
                if 'errors' in response_data and response_data['errors']:
                    err_msg = 'Code: {c}, msg: {m}'.format(
                        c=response_data['errors'][0]['code'],
                        m=response_data['errors'][0]['message'],
                    )
            raise SocialMediaPostError(err_msg)

        post_id = result['id']
        LOG.debug('post_id: %s', post_id)
        return post_id
