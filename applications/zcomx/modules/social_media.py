#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to social media.
"""
import logging
import urllib
import urlparse
from gluon import *
from applications.zcomx.modules.books import \
    get_page, \
    short_page_img_url, \
    short_url
from applications.zcomx.modules.creators import formatted_name
from applications.zcomx.modules.utils import entity_to_row

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
    site = 'https://www.facebook.com'

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
        query = {
            's': '100',
            'p[url]': short_page_img_url(get_page(self.book, page_no='first')),
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
        query = {
            'clickthru': short_url(self.book),
            'source': short_page_img_url(get_page(self.book, page_no='first')),
            'caption': 'Check out {title} by <a class="tumblelog">{handle}</a>'.format(
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
