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
from applications.zcomx.modules.zco import TUMBLR_USERNAME

LOG = logging.getLogger('app')


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
        tweet = CompletedBookTweet.from_data(self.twitter_data)
        return tweet.status()


class TextDataPreparer(object):
    """Class representing a preparer of data for twitter text posting."""

    def __init__(self, twitter_data):
        """Constructor

        Args:
            twitter_data: dict like
                {
                    'ongoing_post': {...},      # ongoing_post attributes
                    'site': {...},              # site attributes
                }
        """
        self.twitter_data = twitter_data

    def data(self):
        """Return the data for the text tweet."""
        return {
            'status': self.status(),
        }

    def status(self):
        """Return the status.

        In twitter land, the status is the 140 character tweet.
        """
        tweet = OngoingUpdateTweet.from_data(self.twitter_data)
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

    def post_text(self, text_data):
        """Post a text tweet.

        Args:
            text_data: dict of data required for twitter text post.
        """
        return self.client.statuses.update(**text_data)


class BaseTweet(object):
    """Base class representing a tweet."""
    TWEET_MAX_CHARS = 140
    # Twitter t.co links: https://dev.twitter.com/overview/t.co
    SAMPLE_TCO_LINK = 'http://t.co/1234567890'

    def __init__(self, twitter_data):
        """Initializer

        Args:
            twitter_data: dict of data for tweet.
        """
        self.twitter_data = twitter_data


class CompletedBookTweet(BaseTweet):
    """Class representing a tweet annoucing a completed book."""

    tweet_formats = {
        # Twitter appends a photo url (a t.co link) to the end.
        # Append url for length calculations.
        'normal': '{name} by {creator} | {url} | {tags}',
        'length': '{name} by {creator} | {url} | {tags} {url}',
    }

    def creator(self):
        """Return the creator as used in the tweet.

        Returns:
            string
        """
        return self.twitter_data['creator']['twitter'] or \
            self.twitter_data['creator']['name']

    def for_length_calculation(self):
        """Return the tweet as used for calculating the length.

        Returns:
            string
        """
        data = {
            'name': self.twitter_data['book']['formatted_name_no_year'],
            'creator': self.creator(),
            'tags': formatted_tags(self.hash_tag_values()),
            'url': self.SAMPLE_TCO_LINK,
        }

        return self.tweet_formats['length'].format(**data)

    @classmethod
    def from_data(cls, twitter_data):
        """Return a CompletedBookTweet instance appropriate for the provided
        data.
        """
        tweet = cls(twitter_data)
        if len(tweet.for_length_calculation()) > cls.TWEET_MAX_CHARS:
            tweet = TruncatedCompletedBookTweet(twitter_data)
        return tweet

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


class TruncatedCompletedBookTweet(CompletedBookTweet):
    """Class representing a truncated completed book tweet."""

    def hash_tag_values(self):
        return [self.twitter_data['site']['name']]


class OngoingUpdateTweet(BaseTweet):
    """Class representing a tweet annoucing a ongoing book updates."""

    tweet_formats = {
        'normal': 'New pages added by {creators} on {site} | {url} | {tags}',
        'length': 'New pages added by {creators} on {site} | {url} | {tags}',
    }

    def creators_in_text_form(self):
        """Return the list of creators in text form for post.

        Returns:
            string
        """
        names = []
        for creator_data in self.creators_for_post():
            names.append(
                creator_data['twitter'] or creator_data['name']
            )
        return ', '.join(names)

    def creators_for_post(self):
        """Return a list of creators to be included in post.

        Returns:
            list of strings.
        """
        return self.twitter_data['ongoing_post']['creators']

    def for_length_calculation(self):
        """Return the tweet as used for calculating the length.

        Returns:
            string
        """
        data = {
            'creators': self.creators_in_text_form(),
            'site': self.twitter_data['site']['name'],
            'tags': formatted_tags(self.hash_tag_values()),
            'url': self.SAMPLE_TCO_LINK,
        }

        return self.tweet_formats['length'].format(**data)

    @classmethod
    def from_data(cls, twitter_data):
        """Return a CompletedBookTweet instance appropriate for the provided
        data.
        """
        tweet = cls(twitter_data)
        if len(tweet.for_length_calculation()) > cls.TWEET_MAX_CHARS:
            minimum = ManyCreatorsOngoingUpdateTweet.minimum_number_of_creators
            if len(twitter_data['ongoing_post']['creators']) >= minimum:
                tweet = ManyCreatorsOngoingUpdateTweet(twitter_data)
            else:
                tweet = TruncatedOngoingUpdateTweet(twitter_data)
        return tweet

    def hash_tag_values(self):
        """Return a list of hash tag values.

        Returns:
            list of strings used for hash tags.
        """
        return [
            self.twitter_data['site']['name'],
            'comics',
        ]

    def status(self):
        """Return the status.

        In twitter land, the status is the 140 character tweet.
        """
        tags = self.hash_tag_values()

        data = {
            'creators': self.creators_in_text_form(),
            'site': self.twitter_data['site']['name'],
            'tags': formatted_tags(tags),
            'url': self.tumblr_url(),
        }

        return self.tweet_formats['normal'].format(**data)

    def tumblr_url(self):
        """Return the tumblr url.

        Returns string.
        """
        return 'http://{user}.tumblr.com/post/{post_id}'.format(
            user=TUMBLR_USERNAME,
            post_id=self.twitter_data['ongoing_post']['tumblr_post_id']
        )


class TruncatedOngoingUpdateTweet(OngoingUpdateTweet):
    """Class representing a truncated ongoing book updates tweet."""

    def hash_tag_values(self):
        return [self.twitter_data['site']['name']]


class ManyCreatorsOngoingUpdateTweet(TruncatedOngoingUpdateTweet):
    """Class representing a truncated ongoing book updates tweet that includes
    many creators.

    The number of creators can make the tweet too long. This class includes
    functionality for truncating the list of creators.
    """
    minimum_number_of_creators = 4
    num_creators_to_post = 2

    def creators_in_text_form(self):
        text = super(
            ManyCreatorsOngoingUpdateTweet, self).creators_in_text_form()
        return text + ' and others'

    def creators_for_post(self):
        creators = self.twitter_data['ongoing_post']['creators']
        return creators[:self.num_creators_to_post]


def creators_in_ongoing_post(ongoing_post):
    """Return the ids of creators involved in an ongoing post.

    Args:
        ongoing_post: OngoingPost instance

    Returns:
        list of integers, creator record ids
    """
    db = current.app.db
    query = (db.activity_log.ongoing_post_id == ongoing_post.id)
    rows = db(query).select(
        db.creator.id,
        left=[
            db.book.on(db.activity_log.book_id == db.book.id),
            db.creator.on(db.book.creator_id == db.creator.id),
        ],
        distinct=True,
        orderby=db.creator.id,
    )

    return [x.id for x in rows]


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
