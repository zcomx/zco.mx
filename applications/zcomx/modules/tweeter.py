#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to twitter posts.
"""
import logging
from gluon import *
from twitter import Twitter
from twitter.oauth import OAuth
from applications.zcomx.modules.images import UploadImage

LOG = logging.getLogger('app')
POST_IN_PROGRESS = '__in_progress__'


class Authenticator(object):
    """Class representing a twitter authenticator"""

    def __init__(self, credentials):
        """Constructor

        Args:
            credentials: dict
        """
        self.credentials = credentials

    def authenticate(self):
        """Authenticate on twitter.

        Returns:
            client,  python-twitter Twitter instance
        """
        return Twitter(auth=OAuth(
            self.credentials['oauth_token'],
            self.credentials['oauth_secret'],
            self.credentials['consumer_key'],
            self.credentials['consumer_secret']
        ))


class PhotoDataPreparer(object):
    """Class representing a preparer of data for twitter photo posting."""

    def __init__(self, twitter_data):
        """Constructor

        Args:
            twitter_data: dict like
                {
                    'book': {...},      # book attributes
                    'creator': {...},   # creator attributes
                    'site': {...},      # site attributes
                }
        """
        self.twitter_data = twitter_data

    def data(self):
        """Return the data for the photo."""
        return {
            'media[]': self.media(),
            'status': self.status(),
        }

    def media(self):
        """Return the tweet media."""
        db = current.app.db
        upload_image = UploadImage(
            db.book_page.image,
            self.twitter_data['book']['cover_image_name']
        )
        img = upload_image.fullname(size='web')
        file_h = open(img, "rb")
        contents = file_h.read()
        file_h.close()

        return contents

    def status(self):
        """Return the status.

        In twitter land, the status is the 140 character tweet.
        """
        creator = self.twitter_data['creator']['twitter'] or \
            self.twitter_data['creator']['name']

        tags = [
            self.twitter_data['site']['name'].replace('.', ''),
            'comics',
            self.twitter_data['creator']['name_for_url'],
        ]

        tags_str = ' '.join(['#' + x for x in tags])

        return '{name} by {creator} | {url} | {tags}'.format(
            name=self.twitter_data['book']['formatted_name_no_year'],
            creator=creator,
            tags=tags_str,
            url=self.twitter_data['book']['short_url'],
        )


class Poster(object):
    """Class representing a twitter poster"""

    def __init__(self, client):
        """Constructor

        Args:
            client,  python-twitter Twitter instance
        """
        self.client = client

    def delete_post(self, post_id):
        """Delete a post.

        Args:
            post_id, string, id of twitter post to delete
        """
        return self.client.statuses.destroy(post_id)

    def post_photo(self, photo_data):
        """Post a photo.

        Args:
            photo_data: dict of data required for twitter photo post.
        """
        return self.client.statuses.update_with_media(**photo_data)
