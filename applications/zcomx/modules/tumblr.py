#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to tumblr posts.
"""
import pytumblr
from gluon import *
from applications.zcomx.modules.book_pages import \
    AbridgedBookPageNumbers, \
    BookPage
from applications.zcomx.modules.books import \
    Book, \
    formatted_name as book_formatted_name, \
    page_url, \
    url as book_url
from applications.zcomx.modules.creators import \
    Creator, \
    short_url as creator_short_url
from applications.zcomx.modules.utils import joined_list
from applications.zcomx.modules.zco import SITE_NAME


LOG = current.app.logger


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

        title = '<h3><a href="{u}">{t}</a></h3>'.format(
            u=self.tumblr_data['book']['url'],
            t=self.tumblr_data['book']['formatted_name']
        )

        description_paragraph = ''
        if self.tumblr_data['book']['description']:
            description_paragraph = "<p>{d}</p>".format(
                d=self.tumblr_data['book']['description'])

        by = '<p>by {links}</p>'.format(links=' | '.join(by_links))

        return ''.join([title, description_paragraph, by])

    def data(self):
        """Return data for a tumblr photo posting."""
        photo_data = {
            'state': 'published',
            'tags': self.tags(),
            'tweet': None,
            'slug': self.slug(),
            'format': 'html',
            'source': self.tumblr_data['book']['download_url'],
            'link': self.tumblr_data['book']['url'],
            'caption': self.caption(),
        }
        return photo_data

    def slug(self):
        """Return the slug."""
        return '{c}-{b}'.format(
            c=self.tumblr_data['creator']['name_for_search'],
            b=self.tumblr_data['book']['name_for_search'],
        )

    def tags(self):
        """Return the tags."""
        return [
            self.tumblr_data['book']['name'],
            self.tumblr_data['creator']['name_for_url'],
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

    def post_text(self, username, text_data):
        """Post text.

        Args:
            username: str, tumblr account username
            text_data: dict of data required for tumblr text post.
        """
        return self.client.create_text(username, **text_data)


class TextDataPreparer(object):
    """Class representing a preparer of data for tumblr text posting."""

    def __init__(self, date, activity_log_generator):
        """Initializer

        Args:
            date: datetime.date instance representing reporting date of
                posting.
            activity_log_generator: RecordGenerator instance.
        """
        self.date = date
        self.activity_log_generator = activity_log_generator

    def body(self):
        """Return the body of the post."""
        lis = []
        for count, book_listing in enumerate(self.book_listing_generator()):
            components = []
            if count:
                components.append(SPAN(' --- ', _class='hidden'))
            components.extend(book_listing.components())
            lis.append(LI(components))
        return str(UL(lis))

    def book_listing_generator(self):
        """Generator producting OngoingBookListing instances for books to be
        included in the ongoing tumblr post.

        Returns:
            yields OngoingBookListing instance
        """
        for activity_log in self.activity_log_generator.generator():
            book_listing = OngoingBookListing.from_activity_log(activity_log)
            yield book_listing

    def data(self):
        """Return data for a tumblr text posting."""
        return {
            'state': 'published',
            'tags': self.tags(),
            'slug': self.slug(),
            'format': 'html',
            'title': self.title(),
            'body': self.body(),
        }

    def slug(self):
        """Return the slug."""
        return 'ongoing-books-update-{d}'.format(
            d=str(self.date)
        )

    def tags(self):
        """Return the tags."""
        # R0201: *Method could be a function*
        # pylint: disable=R0201
        return [
            'comics',
            SITE_NAME,
        ]

    def title(self):
        """Return the title of the post."""
        fmt = 'Updated Ongoing Books for {d}'
        return fmt.format(
            d=self.date.strftime('%a, %b %d, %Y')
        )


class OngoingBookListing(object):
    """Class representing a OngoingBookListing"""

    def __init__(self, book, book_pages, creator=None):
        """Initializer

        Args:
            book: Book instance
            book_pages: list of BookPage instances
            creator: Creator instance
        """
        self.book = book
        self.book_pages = book_pages
        self.creator = creator
        if self.creator is None:
            self.creator = Creator.from_id(self.book.creator_id)

    def components(self):
        """Return the components of a book listing.

        Returns:
            list of components (strings or gluon.html.XmlComponent subclasses)
        """
        parts = [
            I(A(
                book_formatted_name(
                    self.book, include_publication_year=False),
                _href=book_url(self.book, extension=False, host=SITE_NAME),
            )),
            ' by ',
            book_listing_creator(self.creator).link(),
            ' - ',
        ]

        page_links = AbridgedBookPageNumbers(self.book_pages).links(
            url_func=page_url)
        parts.extend(joined_list(page_links, ' '))
        return parts

    @classmethod
    def from_activity_log(cls, activity_log):
        """Return OngoingBookListing instance associated with an activity_log.

        Args:
            activity_log: Row instance representing an activity_log record.

        Returns:
            OngoingBookListing instance
        """
        book = Book.from_id(activity_log.book_id)
        book_pages = [BookPage.from_id(x) for x in activity_log.book_page_ids]
        creator = Creator.from_id(book.creator_id)
        return cls(book, book_pages, creator=creator)


class BookListingCreator(object):
    """Class representing a BookListingCreator"""

    def __init__(self, creator):
        """Initializer

        Args:
            creator: Creator instance
        """
        self.creator = creator

    def link(self):
        """Return the creator link for a book listing.

        Returns:
            string
        """
        return A(
            self.creator.name,
            _href=creator_short_url(self.creator)
        )


class BookListingCreatorWithTumblr(BookListingCreator):
    """Class representing a BookListingCreator with a tumblr account."""

    def link(self):
        return A(
            self.creator.name,
            _href=self.creator.tumblr,
        )


def book_listing_creator(creator):
    """Return the BookListingCreator instance for the creator.

    Args:
        creator: Creator instance

    Returns
        BookListingCreator or subclass instance
    """
    listing_class = BookListingCreatorWithTumblr \
        if creator.tumblr is not None \
        else BookListingCreator
    return listing_class(creator)


def postable_activity_log_ids():
    """Return a list of ids of activity_log records that need a tumblr post
    created.

    Returns:
        list of integers
    """
    db = current.app.db
    query = (db.activity_log.action == 'page added') & \
        (db.book.release_date == None) & \
        (db.book.id != None) & \
        (db.activity_log.ongoing_post_id == None)
    rows = db(query).select(
        db.activity_log.id,
        left=[
            db.book.on(db.activity_log.book_id == db.book.id),
        ],
        orderby=db.activity_log.time_stamp,
    )
    return [x.id for x in rows]
