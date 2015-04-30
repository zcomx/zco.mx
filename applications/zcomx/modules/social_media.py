#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to social media.
"""
import json
import logging
import time
import urllib
import urlparse
from twitter import TwitterHTTPError
from gluon import *
from applications.zcomx.modules.books import \
    get_page, \
    short_page_img_url, \
    short_page_url, \
    short_url, \
    social_media_data as book_social_media_data
from applications.zcomx.modules.creators import \
    social_media_data as creator_social_media_data
from applications.zcomx.modules.creators import formatted_name
from applications.zcomx.modules.tumblr import \
    Authenticator, \
    PhotoDataPreparer, \
    Poster
from applications.zcomx.modules.tweeter import \
    Authenticator as TwAuthenticator, \
    PhotoDataPreparer as TwPhotoDataPreparer, \
    Poster as TwPoster
from applications.zcomx.modules.utils import entity_to_row
from applications.zcomx.modules.zco import SITE_NAME

LOG = logging.getLogger('app')


class SocialMedia(object):
    """Base class representing social media"""

    icon_filename = 'zco.mx-logo-small.png'
    site = None

    def __init__(self, book_entity, creator_entity=None):
        """Constructor

        Args:
            book_entity: Row instance or integer representing a book record
            creator_entity: Row instance or integer representing a creator
                record. If None, it is created from book_entity.creator_id.
        """
        self.book_entity = book_entity
        self.creator_entity = creator_entity
        db = current.app.db
        self.book = entity_to_row(db.book, self.book_entity)
        self.creator = entity_to_row(
            db.creator,
            self.creator_entity if self.creator_entity is not None
            else self.book.creator_id
        )

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


class FacebookSocialMedia(SocialMedia):
    """Class representing social media: facebook"""

    icon_filename = 'facebook_logo.svg'
    site = 'http://www.facebook.com'

    def __init__(self, book_entity, creator_entity=None):
        """Constructor

        Args:
            book_entity: Row instance or integer representing a book record
            creator_entity: Row instance or integer representing a creator
                record. If None, it is created from book_entity.creator_id.
        """
        SocialMedia.__init__(self, book_entity, creator_entity=creator_entity)

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
            site=self.site, path=urllib.urlencode(query))


class TumblrSocialMedia(SocialMedia):
    """Class representing social media: tumblr"""

    icon_filename = 'tumblr_logo.svg'
    site = 'https://www.tumblr.com'

    def __init__(self, book_entity, creator_entity=None):
        """Constructor

        Args:
            book_entity: Row instance or integer representing a book record
            creator_entity: Row instance or integer representing a creator
                record. If None, it is created from book_entity.creator_id.
        """
        SocialMedia.__init__(self, book_entity, creator_entity=creator_entity)
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
            netloc = urlparse.urlparse(self.creator.tumblr).netloc
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
                handle=self.get_username() or formatted_name(self.creator)
            ),
        }
        return '{site}/share/photo?{path}'.format(
            site=self.site, path=urllib.urlencode(query))


class TwitterSocialMedia(SocialMedia):
    """Class representing social media: twitter"""

    icon_filename = 'twitter_logo.svg'
    site = 'https://twitter.com'

    def __init__(self, book_entity, creator_entity=None):
        """Constructor

        Args:
            book_entity: Row instance or integer representing a book record
            creator_entity: Row instance or integer representing a creator
                record. If None, it is created from book_entity.creator_id.
        """
        SocialMedia.__init__(self, book_entity, creator_entity=creator_entity)

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
                creator=self.creator.twitter or formatted_name(self.creator)
            ),
            'hashtage': '',
        }
        return '{site}/share?{path}'.format(
            site=self.site, path=urllib.urlencode(query))


SOCIAL_MEDIA_CLASSES = {
    'twitter': TwitterSocialMedia,
    'tumblr': TumblrSocialMedia,
    'facebook': FacebookSocialMedia,
}


class SocialMediaPostError(Exception):
    """Exception class for errors occurring while posting on social media."""
    pass


class SocialMediaPoster(object):
    """Base class representing a social media poster."""

    authenticate_class = None
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
        return data

    def credentials(self):
        """Return the authentication credentials.

        Returns:
            dict of oauth credentials
        """
        raise NotImplementedError

    def post(self, book, creator):
        client = self.authenticate_class(self.credentials()).authenticate()
        poster = self.poster_class(client)
        return self.post_data(poster, self.prepare_data(book, creator))

    def prepare_data(self, book, creator):
        """Prepare the data for the api."""
        social_media_data = {
            'book': book_social_media_data(book),
            'creator': creator_social_media_data(creator),
            'site': {'name': SITE_NAME},
        }
        photo_data = self.photo_data_preparer_class(social_media_data).data()
        return self.additional_prepare_data(photo_data)


class TumblrPoster(SocialMediaPoster):
    """Class representing a poster for posting material on tumblr."""

    authenticate_class = Authenticator
    poster_class = Poster
    photo_data_preparer_class = PhotoDataPreparer

    def credentials(self):
        settings = current.app.local_settings
        return {
            'consumer_key': settings.tumblr_consumer_key,
            'consumer_secret': settings.tumblr_consumer_secret,
            'oauth_token': settings.tumblr_oauth_token,
            'oauth_secret': settings.tumblr_oauth_secret,
        }

    def additional_prepare_data(self, data):
        settings = current.app.local_settings
        if settings.tumblr_post_state:
            data['state'] = settings.tumblr_post_state
        return data

    def post_data(self, poster, photo_data):
        """Post the data using the api."""
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


class TwitterPoster(SocialMediaPoster):
    """Class representing a poster for posting material on twitter."""

    authenticate_class = TwAuthenticator
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

    def post(self, book, creator):
        client = self.authenticate_class(self.credentials()).authenticate()
        poster = self.poster_class(client)
        return self.post_data(poster, self.prepare_data(book, creator))

    def post_data(self, poster, photo_data):
        """Post the data using the api."""
        error = None
        try:
            result = poster.post_photo(photo_data)
        except TwitterHTTPError as err:
            error = err
            result = {}

        if 'id' not in result:
            err_msg = ''
            if error:
                response_data = json.loads(error.response_data)
                if 'errors' in response_data and response_data['errors']:
                    err_msg = 'Code: {c}, msg: {m}'.format(
                        c=response_data['errors'][0]['code'],
                        m=response_data['errors'][0]['message'],
                    )
            raise SocialMediaPostError(err_msg)

        post_id = result['id']
        LOG.debug('post_id: %s', post_id)
        return post_id


POSTER_CLASSES = {
    'tumblr': TumblrPoster,
    'twitter': TwitterPoster,
}
