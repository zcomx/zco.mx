#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to tumblr posts.
"""
import logging
import pytumblr
from gluon import *

LOG = logging.getLogger('app')
POST_IN_PROGRESS = '__in_progress__'


class Authenticator(object):
    """Class representing a tumblr authenticator"""

    def __init__(self, credentials):
        """Constructor

        Args:
            credentials: dict
        """
        self.credentials = credentials

    def authenticate(self):
        """Authenticate on tumblr.

        Returns:
            client,  pytumblr TumblrRestClient instance
        """
        return pytumblr.TumblrRestClient(
            self.credentials['consumer_key'],
            self.credentials['consumer_secret'],
            self.credentials['oauth_token'],
            self.credentials['oauth_secret']
        )


class PhotoDataPreparer(object):
    """Class representing a preparer of data for tumblr photo posting."""

    def __init__(self, tumblr_data):
        """Constructor

        Args:
            tumblr_data: dict like
                {
                    'book': {...},      # book attributes
                    'creator': {...},   # creator attributes
                    'site': {...},      # site attributes
                }
        """
        self.tumblr_data = tumblr_data

    def caption(self):
        """Return a caption."""

        anchor = lambda name, url: str(A(name, _href=url))

        by_links = []
        by_links.append(anchor(
            self.tumblr_data['creator']['url'],
            self.tumblr_data['creator']['url']
        ))
        for name, url in self.tumblr_data['creator']['social_media']:
            if url is None:
                continue
            by_links.append(anchor(name, url))

        title = '###<a href="{u}">{t}</a>###'.format(
            u=self.tumblr_data['book']['url'],
            t=self.tumblr_data['book']['title']
        )

        description_paragraph = ''
        if self.tumblr_data['book']['description']:
            description_paragraph = "\n{d}\n".format(
                d=self.tumblr_data['book']['description'])

        by = 'by {links}'.format(links=' | '.join(by_links))

        return "\n".join([title, description_paragraph, by])

    def data(self):
        return {
            'state': 'published',
            'tags': self.tags(),
            'tweet': None,
            'slug': self.slug(),
            'format': 'markdown',
            'source': self.tumblr_data['book']['source'],
            'link': self.tumblr_data['book']['url'],
            'caption': self.caption(),
        }

    def slug(self):
        """Return the slug."""
        return '{c}-{b}'.format(
            c=self.tumblr_data['creator']['slug_name'],
            b=self.tumblr_data['book']['slug_name'],
        )

    def tags(self):
        """Return the tags."""
        return [
            self.tumblr_data['book']['name'],
            self.tumblr_data['creator']['tag_name'],
            'comics',
            self.tumblr_data['site']['name'],
        ]


class Poster(object):
    """Class representing a tumblr poster"""

    def __init__(self, client):
        """Constructor

        Args:
            client,  pytumblr TumblrRestClient instance
        """
        self.client = client

    def delete_post(self, post_id):
        """Delete a post.

        Args:
            post_id, string, id of tumblr post to delete
        """
        return self.client.delete_post(post_id)

    def post_photo(self, username, photo_data):
        """Post a photo.

        Args:
            username: str, tumblr account username
            photo_data: dict of data required for tumblr photo post.
        """
        return self.client.create_photo(username, **photo_data)
