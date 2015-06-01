#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to rss feeds.
"""
import datetime
import logging
import gluon.contrib.rss2 as rss2
from gluon import *
from applications.zcomx.modules.books import \
    formatted_name as book_formatted_name, \
    get_page, \
    page_url
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name, \
    url as creator_url
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row
from applications.zcomx.modules.zco import \
    SITE_NAME, \
    Zco

LOG = logging.getLogger('app')

MINIMUM_AGE_TO_LOG_IN_SECONDS = 4 * 60 * 60       # 4 hours


class BaseRSSChannel(object):
    """Class representing a BaseRSSChannel"""

    max_entry_age_in_days = 7

    def __init__(self, entity=None):
        """Initializer

        Args:
            entity: string, first arg
        """
        self.entity = entity

    def description(self):
        """Return the description for the channel.

        Returns:
            string, channel description.
        """
        raise NotImplementedError()

    def entries(self):
        """Return of list of feed entries.

        Returns:
            list of dicts.
        """
        db = current.app.db
        items = []
        query = self.filter_query()
        rows = db(query).select(
            db.activity_log.id,
            left=[
                db.book.on(db.book.id == db.activity_log.book_id),
            ],
            orderby=~db.activity_log.time_stamp,
        )
        for r in rows:
            activity_log = entity_to_row(db.activity_log, r.id)
            try:
                entry = activity_log_as_rss_entry(activity_log).feed_item()
            except NotFoundError as err:
                # This may happen if a book deletion is in progress
                LOG.error(err)
            else:
                items.append(entry)
        return items

    def feed(self):
        """Return a feed for the channel."""
        return dict(
            title=self.title(),
            link=self.link(),
            description=self.description(),
            created_on=datetime.datetime.now(),
            image=self.image(),
            entries=self.entries(),
        )

    def filter_query(self):
        """Define a query to filter activity_log records to include in feed.

        Return
            gluon.dal.objects Query instance.
        """
        db = current.app.db
        now = datetime.datetime.now()
        min_time_stamp = now - \
            datetime.timedelta(days=self.max_entry_age_in_days)
        return db.activity_log.time_stamp > min_time_stamp

    def image(self):
        """Return the RSS image.

        Returns
            rss2.Image instance.
        """
        # R0201: *Method could be a function*
        # pylint: disable=R0201
        return rss2.Image(
            URL(c='static', f='images/zco.mx-logo-small.png', host=True),
            SITE_NAME,
            URL(c='default', f='index', host=True),
        )

    def link(self):
        """Return the link for the channel.

        Returns:
            string, channel link.
        """
        raise NotImplementedError()

    def title(self):
        """Return the title for the channel.

        Returns:
            string, channel title.
        """
        raise NotImplementedError()


class AllRSSChannel(BaseRSSChannel):
    """Class representing a RSS channel for all zco.mx activity."""

    def description(self):
        return 'Recent activity on {s}.'.format(s=SITE_NAME)

    def link(self):
        return URL(host=True, **Zco().all_rss_url)

    def title(self):
        return SITE_NAME


class BookRSSChannel(BaseRSSChannel):
    """Class representing a book RSS channel"""

    max_entry_age_in_days = 30

    def __init__(self, entity=None):
        """Initializer

        Args:
            entity: string, first arg
        """
        super(BookRSSChannel, self).__init__(entity=entity)
        db = current.app.db
        self.book = entity_to_row(db.book, self.entity)
        if not self.book:
            raise NotFoundError('Book not found: {e}'.format(e=self.entity))
        self.creator = entity_to_row(db.creator, self.book.creator_id)
        if not self.creator:
            raise NotFoundError('Creator not found: {e}'.format(e=self.entity))

    def description(self):
        db = current.app.db
        return 'Recent activity of {b} by {c} on {s}.'.format(
            b=book_formatted_name(
                db, self.book, include_publication_year=False),
            c=creator_formatted_name(self.creator),
            s=SITE_NAME
        )

    def filter_query(self):
        db = current.app.db
        return super(BookRSSChannel, self).filter_query() & \
            (db.activity_log.book_id == self.book.id)

    def link(self):
        try:
            first_page = get_page(self.book, page_no='first')
        except NotFoundError:
            return URL(**Zco().all_rss_url)
        return page_url(first_page, extension=False, host=True)

    def title(self):
        db = current.app.db
        return '{b} by {c} on {s}'.format(
            b=book_formatted_name(
                db, self.book, include_publication_year=False),
            c=creator_formatted_name(self.creator),
            s=SITE_NAME
        )


class CartoonistRSSChannel(BaseRSSChannel):
    """Class representing a cartoonist RSS channel"""

    max_entry_age_in_days = 30

    def __init__(self, entity=None):
        """Initializer

        Args:
            entity: string, first arg
        """
        super(CartoonistRSSChannel, self).__init__(entity=entity)
        db = current.app.db
        self.creator = entity_to_row(db.creator, self.entity)
        if not self.creator:
            raise NotFoundError('Creator not found: {e}'.format(e=self.entity))

    def description(self):
        return 'Recent activity of {c} on {s}.'.format(
            c=creator_formatted_name(self.creator),
            s=SITE_NAME
        )

    def filter_query(self):
        db = current.app.db
        return super(CartoonistRSSChannel, self).filter_query() & \
            (db.book.creator_id == self.creator.id)

    def link(self):
        return creator_url(self.creator, extension=False, host=True)

    def title(self):
        return '{c} on {s}'.format(
            c=creator_formatted_name(self.creator),
            s=SITE_NAME
        )


class BaseRSSEntry(object):
    """Class representing a BaseRSSEntry"""

    description_fmt = 'Entry for the book {b} by {c}.'

    def __init__(self, book_page_entity, time_stamp):
        """Initializer

        Args:
            arg: string, first arg
        """
        self.book_page_entity = book_page_entity
        self.time_stamp = time_stamp
        db = current.app.db
        self.book_page = entity_to_row(db.book_page, self.book_page_entity)
        if not self.book_page:
            raise NotFoundError('Book page not found: {e}'.format(
                e=self.book_page_entity))
        self.book = entity_to_row(db.book, self.book_page.book_id)
        if not self.book:
            raise NotFoundError('Book not found: {e}'.format(
                e=self.book_entity))
        self.creator = entity_to_row(db.creator, self.book.creator_id)
        if not self.creator:
            raise NotFoundError('Creator not found: {e}'.format(e=self.entity))

    def created_on(self):
        """Return the created_on value for the entry.

        Returns:
            string, entry created_on value.
        """
        return self.time_stamp

    def description(self):
        """Return the description for the entry.

        Returns:
            string, entry description.
        """
        db = current.app.db
        return self.description_fmt.format(
            b=book_formatted_name(
                db, self.book, include_publication_year=False),
            c=creator_formatted_name(self.creator),
        )

    def feed_item(self):
        """Return a dict representing an RSS feed item.

        Returns:
            dict
        """
        return dict(
            title=self.title(),
            link=self.link(),
            description=self.description(),
            created_on=self.created_on(),
        )

    def link(self):
        """Return the link for the entry.

        Returns:
            string, entry link.
        """
        return page_url(self.book_page, extension=False, host=True)

    def title(self):
        """Return the title for the entry.

        Returns:
            string, entry title.
        """
        db = current.app.db
        return '{b} by {c}'.format(
            b=book_formatted_name(
                db, self.book, include_publication_year=False),
            c=creator_formatted_name(self.creator),
        )


class CompletedRSSEntry(BaseRSSEntry):
    """Class representing a 'completed' RSS entry"""
    description_fmt = 'The book {b} by {c} has been set as completed.'


class PageAddedRSSEntry(BaseRSSEntry):
    """Class representing a 'page added' RSS entry"""
    description_fmt = 'A page was added to the book {b} by {c}.'


class PagesAddedRSSEntry(BaseRSSEntry):
    """Class representing a 'pages added' RSS entry"""
    description_fmt = 'Several pages were added to the book {b} by {c}.'


def activity_log_as_rss_entry(activity_log_entity):
    """Factory to create a BaseRSSEntry subclass instance from an activity_log
    record.

    Args:
        activity_log_entity: Row instance or id representing a activity_log
            record.

    Returns:
        BaseRSSEntry subclass instance.
    """
    db = current.app.db
    activity_log = entity_to_row(db.activity_log, activity_log_entity)
    if not activity_log:
        raise NotFoundError('activity_log not found, {e}'.format(
            e=activity_log_entity))

    entry_class = entry_class_from_action(activity_log.action)
    return entry_class(activity_log.book_page_id, activity_log.time_stamp)


def channel_from_type(channel_type, record_id=None):
    """Factory for returning a RSSChannel instance from args.

    Args:
        channel_type: string, one of 'all', 'book', 'creator'
        record_id: integer, id of record
    """
    if not channel_type:
        raise SyntaxError('Invalid rss feed channel: {c}'.format(
            c=channel_type))

    if channel_type == 'all':
        return AllRSSChannel()

    if channel_type == 'creator':
        return CartoonistRSSChannel(record_id)

    if channel_type == 'book':
        return BookRSSChannel(record_id)

    raise SyntaxError('Invalid rss feed channel: {c}'.format(
        c=channel_type))


def entry_class_from_action(action):
    """Return the appropriate RSS Entry class for the action."""
    if action == 'completed':
        return CompletedRSSEntry
    elif action == 'page added':
        return PageAddedRSSEntry
    elif action == 'pages added':
        return PagesAddedRSSEntry
    else:
        raise NotFoundError('Invalid RSS entry action: {a}'.format(a=action))


def rss_serializer_with_image(feed):
    """RSS serializer adapted from gluon/serializers def rss()."""

    if 'entries' not in feed and 'items' in feed:
        feed['entries'] = feed['items']

    def _safestr(obj, key, default=''):
        """Encode string for safety."""
        return str(obj[key]).decode('utf-8').encode('utf-8', 'replace') \
            if key in obj else default

    now = datetime.datetime.now()
    rss = rss2.RSS2(
        title=_safestr(feed, 'title'),
        link=_safestr(feed, 'link'),
        description=_safestr(feed, 'description'),
        lastBuildDate=feed.get('created_on', now),
        image=feed.get('image', None),                  # <--- customization
        items=[
            rss2.RSSItem(
                title=_safestr(entry, 'title', '(notitle)'),
                link=_safestr(entry, 'link'),
                description=_safestr(entry, 'description'),
                pubDate=entry.get('created_on', now)
            ) for entry in feed.get('entries', [])
        ]
    )
    return rss.to_xml(encoding='utf-8')
