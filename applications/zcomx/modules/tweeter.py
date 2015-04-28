#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to twitter posts.
"""
import logging
import re
from gluon import *
from twitter import Twitter
from twitter.oauth import OAuth
from applications.zcomx.modules.images import UploadImage

LOG = logging.getLogger('app')
POST_IN_PROGRESS = '__in_progress__'
# Twitter t.co links: https://dev.twitter.com/overview/t.co


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

    tweet_formats = {
        # Twitter appends a photo url (a t.co link) to the end.
        # Append url for length calculations.
        'normal': '{name} by {creator} | {url} | {tags}',
        'length': '{name} by {creator} | {url} | {tags} {url}',
    }

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
        tweet = Tweet.from_data(self.twitter_data)
        return tweet.status()


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


class Tweet(object):
    """Class representing a tweet"""
    TWEET_MAX_CHARS = 140
    SAMPLE_TCO_LINK = 'http://t.co/1234567890'

    tweet_formats = {
        # Twitter appends a photo url (a t.co link) to the end.
        # Append url for length calculations.
        'normal': '{name} by {creator} | {url} | {tags}',
        'length': '{name} by {creator} | {url} | {tags} {url}',
    }

    def __init__(self, twitter_data):
        """Initializer

        Args:
            data: string, first arg
        """
        self.twitter_data = twitter_data

    def creator(self):
        """Return the creator as used in the tweet.

        Returns:
            string
        """
        return self.twitter_data['creator']['twitter'] or \
            self.twitter_data['creator']['name']

    @classmethod
    def from_data(cls, twitter_data):
        """Return a Tweet instance appropriate for the provided data."""
        tweet = cls(twitter_data)
        if len(tweet.for_length_calculation()) > cls.TWEET_MAX_CHARS:
            tweet = TruncatedTweet(twitter_data)
        return tweet

    def for_length_calculation(self):
        """Return the tweet as used for calculating the length.

        Returns:
            string
        """
        tags = formatted_tags(self.hash_tag_values())

        data = {
            'name': self.twitter_data['book']['formatted_name_no_year'],
            'creator': self.creator(),
            'tags': tags,
            'url': self.SAMPLE_TCO_LINK,
        }

        return self.tweet_formats['length'].format(**data)

    def hash_tag_values(self):
        """Return a list of hash tag values.

        Returns:
            list of strings used for hash tags.
        """
        return [
            self.twitter_data['site']['name'],
            'comics',
            self.twitter_data['creator']['name_for_url'],
        ]

    def status(self):
        """Return the status.

        In twitter land, the status is the 140 character tweet.
        """
        tags = self.hash_tag_values()

        data = {
            'name': self.twitter_data['book']['formatted_name_no_year'],
            'creator': self.creator(),
            'tags': formatted_tags(tags),
            'url': self.twitter_data['book']['short_url'],
        }

        return self.tweet_formats['normal'].format(**data)


class TruncatedTweet(Tweet):
    """Class representing a truncated"""

    def hash_tag_values(self):
        return [self.twitter_data['site']['name']]


def formatted_tags(tags):
    """Return tweet hash tags formatted.

    Args:
        list of strings, tag values.

    Returns:
        string, eg '#val1 #val2 #val3'
    """
    # Twitter allows letters, numbers, and underscores.
    scrub = lambda x: re.sub(r'[^\w]+', '', x)
    return ' '.join(['#' + scrub(x) for x in tags])
