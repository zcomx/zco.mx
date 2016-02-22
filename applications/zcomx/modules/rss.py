#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to rss feeds.
"""
import datetime
import os
import gluon.contrib.rss2 as rss2
from gluon import *
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.book_pages import \
    BookPage, \
    AbridgedBookPageNumbers
from applications.zcomx.modules.books import \
    Book, \
    formatted_name as book_formatted_name, \
    get_page, \
    page_url
from applications.zcomx.modules.creators import \
    Creator, \
    url as creator_url
from applications.zcomx.modules.images import ImageDescriptor
from applications.zcomx.modules.zco import \
    SITE_NAME, \
    Zco

LOG = current.app.logger

MINIMUM_AGE_TO_LOG_IN_SECONDS = 4 * 60 * 60       # 4 hours


class BaseRSSChannel(object):
    """Class representing a BaseRSSChannel"""

    max_entry_age_in_days = 7

    def __init__(self, record=None):
        """Initializer

        Args:
            record: Record sublcass instance
        """
        self.record = record

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
            activity_log = ActivityLog.from_id(r.id)
            try:
                entry = activity_log_as_rss_entry(activity_log).feed_item()
            except LookupError as err:
                # This may happen if a book deletion is in progress
                # LOG.error(err)
                pass        # This is producing too much noise
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
            gluon.pydal.objects Query instance.
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

        # From RSS spec: (Note, in practice the image <title> and <link>
        # should have the same value as the channel's <title> and <link>.
        return rss2.Image(
            URL(c='static', f='images/zco.mx-logo-small.png', host=True),
            self.title(),
            self.link(),
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

    def __init__(self, record=None):
        """Initializer

        Args:
            record: Book instance
        """
        super(BookRSSChannel, self).__init__(record=record)
        self.book = record
        self.creator = Creator.from_id(self.book.creator_id)

    def description(self):
        return 'Recent activity of {b} by {c} on {s}.'.format(
            b=book_formatted_name(self.book, include_publication_year=False),
            c=self.creator.name,
            s=SITE_NAME
        )

    def filter_query(self):
        db = current.app.db
        return super(BookRSSChannel, self).filter_query() & \
            (db.activity_log.book_id == self.book.id)

    def link(self):
        try:
            first_page = get_page(self.book, page_no='first')
        except LookupError:
            return URL(**Zco().all_rss_url)
        return page_url(first_page, extension=False, host=True)

    def title(self):
        return '{s}: {b} by {c}'.format(
            s=SITE_NAME,
            b=book_formatted_name(self.book, include_publication_year=False),
            c=self.creator.name,
        )


class CartoonistRSSChannel(BaseRSSChannel):
    """Class representing a cartoonist RSS channel"""

    max_entry_age_in_days = 30

    def __init__(self, record=None):
        """Initializer

        Args:
            record: Creator instance
        """
        super(CartoonistRSSChannel, self).__init__(record=record)
        self.creator = record

    def description(self):
        return 'Recent activity of {c} on {s}.'.format(
            c=self.creator.name,
            s=SITE_NAME
        )

    def filter_query(self):
        db = current.app.db
        return super(CartoonistRSSChannel, self).filter_query() & \
            (db.book.creator_id == self.creator.id)

    def link(self):
        return creator_url(self.creator, extension=False, host=True)

    def title(self):
        return '{s}: {c}'.format(
            s=SITE_NAME,
            c=self.creator.name,
        )


class BaseRSSEntry(object):
    """Class representing a BaseRSSEntry"""

    def __init__(self, book_page_ids, time_stamp, activity_log_id):
        """Initializer

        Args:
            book_page_ids: list of integers, ids of book_page records
            time_stamp: datetime.datetime instance representing the time the
                activity took place.
            activity_log_id: integer, id of activity_log record the entry
                is about.
        """
        self.book_page_ids = book_page_ids
        self.time_stamp = time_stamp
        self.activity_log_id = activity_log_id
        if not book_page_ids:
            raise LookupError('No book page ids provided')
        self.first_page = self.first_of_pages()
        if not self.first_page:
            raise LookupError('First page not found within: {e}'.format(
                e=self.book_page_ids))
        self.book = Book.from_id(self.first_page.book_id)
        self.creator = Creator.from_id(self.book.creator_id)

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
        return self.description_fmt().format(
            b=book_formatted_name(self.book, include_publication_year=False),
            c=self.creator.name,
            d=datetime.datetime.strftime(self.time_stamp, '%b %d, %Y')
        )

    def description_fmt(self):
        """Return a format string with suitable convertion flags for
        the description.

        Returns:
            string
        """
        raise NotImplementedError()

    def enclosure(self):
        """Return the enclosure for the entry.

        Returns
            rss2.Enclosure instance.
        """
        url = URL(
            c='images',
            f='download',
            args=self.first_page.image,
            vars={'size': 'web'},
            host=SITE_NAME,
            scheme='http',          # RSS validation suggests this
        )

        length = ImageDescriptor(
            self.first_page.upload_image().fullname(size='web')
        ).size_bytes()

        _, extension = os.path.splitext(self.first_page.image)
        mime_type = 'image/{ext}'.format(ext=extension.lstrip('.'))
        if mime_type == 'image/jpg':
            mime_type = 'image/jpeg'

        return rss2.Enclosure(url, length, mime_type)

    def feed_item(self):
        """Return a dict representing an RSS feed item.

        Returns:
            dict
        """
        return dict(
            title=self.title(),
            link=self.link(),
            description=self.description(),
            enclosure=self.enclosure(),
            guid=self.guid(),
            created_on=self.created_on(),
        )

    def first_of_pages(self):
        """Return a Row instance representing the book_page record that
        is the first of the pages with activity. 'first' is the one with
        the minimum page_no value.

        Returns:
            Row instance representing a book_page record.
        """
        db = current.app.db
        rows = db(db.book_page.id.belongs(self.book_page_ids)).select(
            db.book_page.id,
            orderby=db.book_page.page_no,
            limitby=(0, 1),
        )
        if not rows:
            return

        return BookPage.from_id(rows[0].id)

    def guid(self):
        """Return a guid for the entry.

        Returns:
            string, entry guid.
        """
        fmt = '{site}-{rid:09d}'
        unique_guid = fmt.format(
            site=SITE_NAME,
            rid=self.activity_log_id
        ).replace('.', '')
        return rss2.Guid(str(unique_guid), isPermaLink=False)

    def link(self):
        """Return the link for the entry.

        Returns:
            string, entry link.
        """
        if not self.first_page:
            return
        return page_url(self.first_page, extension=False, host=True)

    def title(self):
        """Return the title for the entry.

        Returns:
            string, entry title.
        """
        pages = [BookPage.from_id(x) for x in self.book_page_ids]
        return "'{b}' {p} by {c}".format(
            b=book_formatted_name(self.book, include_publication_year=False),
            p=' '.join(AbridgedBookPageNumbers(pages).numbers()),
            c=self.creator.name,
        )


class CompletedRSSEntry(BaseRSSEntry):
    """Class representing a 'completed' RSS entry"""

    def description_fmt(self):
        return "Posted: {d} - The book '{b}' by {c} has been set as completed."


class PageAddedRSSEntry(BaseRSSEntry):
    """Class representing a 'page added' RSS entry"""

    def description_fmt(self):
        if len(self.book_page_ids) > 1:
            # line-too-long (C0301): *Line too long (%%s/%%s)*
            # pylint: disable=C0301
            return "Posted: {d} - Several pages were added to the book '{b}' by {c}."
        else:
            return "Posted: {d} - A page was added to the book '{b}' by {c}."


class RSS2WithAtom(rss2.RSS2):
    """Class representing the main RSS class with an atom namespace"""
    rss_attrs = dict(
        rss2.RSS2.rss_attrs,
        **{'xmlns:atom': 'http://www.w3.org/2005/Atom'}
    )

    def publish_extensions(self, handler):
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        rss2._element(
            handler,
            'atom:link',
            None,
            {
                'href': self.link,
                'rel': 'self',
                'type': 'application/rss+xml',
            }
        )


def activity_log_as_rss_entry(activity_log):
    """Factory to create a BaseRSSEntry subclass instance from an activity_log
    record.

    Args:
        activity_log: ActivityLog instance

    Returns:
        BaseRSSEntry subclass instance.
    """
    if not activity_log.book_page_ids:
        raise LookupError('activity_log has no book page ids, id {i}'.format(
            i=activity_log.id))

    book_page_ids = activity_log.verified_book_page_ids()
    if not book_page_ids:
        fmt = 'activity_log has no verifiable book page ids, id {i}'
        raise LookupError(fmt.format(i=activity_log.id))

    entry_class = entry_class_from_action(activity_log.action)
    return entry_class(
        book_page_ids,
        activity_log.time_stamp,
        activity_log.id
    )


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
        return CartoonistRSSChannel(Creator.from_id(record_id))

    if channel_type == 'book':
        return BookRSSChannel(Book.from_id(record_id))

    raise SyntaxError('Invalid rss feed channel: {c}'.format(
        c=channel_type))


def entry_class_from_action(action):
    """Return the appropriate RSS Entry class for the action."""
    if action == 'completed':
        return CompletedRSSEntry
    elif action == 'page added':
        return PageAddedRSSEntry
    else:
        raise LookupError('Invalid RSS entry action: {a}'.format(a=action))


def rss_serializer_with_image(feed):
    """RSS serializer adapted from gluon/serializers def rss().

    Customizations:
        Replace rss2.RSS2 with RSS2WithAtom
        rss2.RSS2(..., image=...)
        rss2.RSSItem(..., guid=...)
        rss2.RSSItem(..., enclosure=...)
    """

    if 'entries' not in feed and 'items' in feed:
        feed['entries'] = feed['items']

    def _safestr(obj, key, default=''):
        """Encode string for safety."""
        return str(obj[key]).decode('utf-8').encode('utf-8', 'replace') \
            if key in obj else default

    now = datetime.datetime.now()
    rss = RSS2WithAtom(
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
                enclosure=entry.get('enclosure', None),
                guid=entry.get('guid', None),
                pubDate=entry.get('created_on', now)
            ) for entry in feed.get('entries', [])
        ]
    )
    return rss.to_xml(encoding='utf-8')
