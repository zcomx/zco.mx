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
            db.rss_log.id,
            left=[
                db.book.on(db.book.id == db.rss_log.book_id),
            ],
            orderby=~db.rss_log.time_stamp,
        )
        for r in rows:
            rss_log = entity_to_row(db.rss_log, r.id)
            items.append(rss_log_as_entry(rss_log).feed_item())
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
        """Define a query to filter rss_log records to include in feed.

        Return
            gluon.dal.objects Query instance.
        """
        db = current.app.db
        now = datetime.datetime.now()
        min_time_stamp = now - \
            datetime.timedelta(days=self.max_entry_age_in_days)
        return db.rss_log.time_stamp > min_time_stamp

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
            (db.rss_log.book_id == self.book.id)

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


class BaseRSSLog(object):
    """Class representing a BaseRSSLog"""

    def __init__(self, record):
        """Initializer

        Args:
            record: dict,
                {
                    'id': <id>,
                    'book_id': <book_id>,
                    'book_page_id': <book_page_id>,
                    'action': <action>,
                    'time_stamp': <time_stamp>,
                }
        """
        self.record = record

    def age(self, as_of=None):
        """Return the age of the record in seconds.

        Args:
            as_of: datetime.datetime instance, the time to determine the age
                 of. Default: datetime.datetime.now()

        Returns:
            datetime.timedelta instance representing the age.
        """
        if as_of is None:
            as_of = datetime.datetime.now()
        if not self.record or 'time_stamp' not in self.record:
            raise SyntaxError('rss log has no timestamp, age indeterminate')
        return as_of - self.record['time_stamp']

    def delete(self):
        """Delete the record from the db"""
        raise NotImplementedError()

    def save(self):
        """Save the record to the db."""
        raise NotImplementedError()


class RSSLog(BaseRSSLog):
    """Class representing a rss_log record"""

    def delete(self):
        db = current.app.db
        db(db.rss_log.id == self.record['id']).delete()
        db.commit()

    def save(self):
        db = current.app.db
        record_id = db.rss_log.insert(**self.record)
        db.commit()
        return record_id


class RSSPreLog(BaseRSSLog):
    """Class representing a rss_pre_log record"""

    def delete(self):
        db = current.app.db
        db(db.rss_pre_log.id == self.record['id']).delete()
        db.commit()

    def save(self):
        db = current.app.db
        record_id = db.rss_pre_log.insert(**self.record)
        db.commit()
        return record_id


class BaseRSSPreLogSet(object):
    """Base class representing a set of RSSPreLog instances"""

    def __init__(self, rss_pre_logs):
        """Initializer

        Args:
            rss_pre_logs: list of RSSPreLog instances
        """
        self.rss_pre_logs = rss_pre_logs

    def as_rss_log(self, rss_log_class=RSSLog):
        """Return an RSSLog instance representing the rss_pre_log records.

        Args:
            rss_log_class: class used to create instance returned.

        Returns:
            RssLog instance
        """
        raise NotImplementedError()

    @classmethod
    def load(cls, filters=None, rss_pre_log_class=RSSPreLog):
        """Load rss_pre_log records into set.

        Args:
            filters: dict of rss_pre_log fields and values to filter on.
                Example {'book_id': 123, 'action': 'page added'}
            rss_pre_log_class: class used to create log instances stored in
                    self.rss_pre_logs
        Returns:
            BaseRssPreLogSet (or subclass) instance
        """
        db = current.app.db
        rss_pre_logs = []
        queries = []
        if filters:
            for field, value in filters.iteritems():
                if field not in db.rss_pre_log.fields:
                    continue
                queries.append((db.rss_pre_log[field] == value))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        rows = db(query).select()
        for r in rows:
            rss_pre_logs.append(rss_pre_log_class(r.as_dict()))
        return cls(rss_pre_logs)

    def youngest(self):
        """Return the youngest rss_pre_log record in the set.

        Returns:
            RSSPreLog instance representing the youngest.
        """
        if not self.rss_pre_logs:
            return

        by_age = sorted(
            self.rss_pre_logs,
            key=lambda k: k.record['time_stamp'],
            reverse=True
        )
        return by_age[0]


class RSSPreLogSet(BaseRSSPreLogSet):
    """Class representing a set of RSSPreLog instances, all actions"""

    def as_rss_log(self, rss_log_class=RSSLog):
        # This method doesn't apply.
        return


class CompletedRSSPreLogSet(BaseRSSPreLogSet):
    """Class representing a set of RSSPreLog instances, action=completed"""
    def as_rss_log(self, rss_log_class=RSSLog):

        youngest_log = self.youngest()
        if not youngest_log:
            return

        record = dict(
            book_id=youngest_log.record['book_id'],
            book_page_id=youngest_log.record['book_page_id'],
            action='completed',
            time_stamp=youngest_log.record['time_stamp'],
        )

        return rss_log_class(record)

    @classmethod
    def load(cls, filters=None, rss_pre_log_class=RSSPreLog):
        super_filters = dict(filters) if filters else {}
        if 'action' not in super_filters:
            super_filters['action'] = 'completed'
        return super(CompletedRSSPreLogSet, cls).load(
            filters=super_filters, rss_pre_log_class=rss_pre_log_class)


class PageAddedRSSPreLogSet(BaseRSSPreLogSet):
    """Class representing a set of RSSPreLog instances, action=page added"""
    def as_rss_log(self, rss_log_class=RSSLog):
        youngest_log = self.youngest()
        if not youngest_log:
            return

        record = dict(
            book_id=youngest_log.record['book_id'],
            book_page_id=youngest_log.record['book_page_id'],
            action=self.rss_log_action(),
            time_stamp=youngest_log.record['time_stamp'],
        )

        return rss_log_class(record)

    @classmethod
    def load(cls, filters=None, rss_pre_log_class=RSSPreLog):
        super_filters = dict(filters) if filters else {}
        if 'action' not in super_filters:
            super_filters['action'] = 'page added'
        return super(PageAddedRSSPreLogSet, cls).load(
            filters=super_filters, rss_pre_log_class=rss_pre_log_class)

    def rss_log_action(self):
        """Return the action to be used in the rss_log record.

        Returns:
            string, one of 'page added' or 'pages added'
        """
        if len(self.rss_pre_logs) > 1:
            return 'pages added'
        return 'page added'


def channel_from_args(channel_type, record_id=None):
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


def rss_log_as_entry(rss_log_entity):
    """Factory to create a BaseRSSEntry subclass instance from an rss_log.

    Args:
        rss_log_entity: Row instance or id representing a rss_log record.

    Returns:
        BaseRSSEntry subclass instance.
    """
    db = current.app.db
    rss_log = entity_to_row(db.rss_log, rss_log_entity)
    if not rss_log:
        raise NotFoundError('rss_log not found, {e}'.format(e=rss_log_entity))

    entry_class = entry_class_from_action(rss_log.action)
    return entry_class(rss_log.book_page_id, rss_log.time_stamp)


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
