#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
integrity.py

Script to run integrity checks.
"""
import datetime
import os
import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.archives import (
    TorrentArchive,
)
from applications.zcomx.modules.books import (
    Book,
)
from applications.zcomx.modules.creators import (
    Creator,
)
from applications.zcomx.modules.torrents import (
    AllTorrentCreator,
)
from applications.zcomx.modules.zco import IN_PROGRESS
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


class BaseChecker():
    """Base class representing a checker."""

    def __init__(self, social_media):
        """Initializer

        Args:
            social_media: string, eg 'tumblr' or 'twitter'
        """
        self.social_media = social_media
        self.post_field = '{s}_post_id'.format(s=self.social_media)

    def check(self, age_buffer=None):
        """Check for invalid records.

        Args:
            age_buffer: datetime.datetime, record activity must older
                than this time to be reported.
        """
        query = self.filter_query()
        if age_buffer and self.table[self.aged_fieldname]:
            query = query & (self.table[self.aged_fieldname] < age_buffer)

        log_fields = [
            self.table['id'],
            self.table[self.log_description_fieldname]
        ]
        rows = db(query).select(*log_fields)
        for r in rows:
            LOG.error(
                self.log_fmt,
                self.social_media,
                r.id,
                r[self.log_description_fieldname]
            )

    def filter_query(self):
        """Query to filter on.

        Returns:
            gluon.dal.Expr instance
        """
        raise NotImplementedError()


class StalledPostInProgressChecker(BaseChecker):
    """Class representing a checker for stalled posts in progress"""

    table = db.book
    aged_fieldname = 'release_date'
    log_description_fieldname = 'name'
    log_fmt = 'Completed %s post may be stalled for book: %s - %s'

    def filter_query(self):
        return (db.book.release_date != None) & \
            (db.book[self.post_field] == IN_PROGRESS)


class IncompleteOngoingPostChecker(BaseChecker):
    """Class representing a checker for incomplete ongoing posts."""

    table = db.ongoing_post
    aged_fieldname = 'created_on'
    log_description_fieldname = 'post_date'
    log_fmt = 'Ongoing %s post may be stalled, ongoing_post: %s - %s'

    def filter_query(self):
        return db.ongoing_post[self.post_field] == None


def book_generator(query, orderby=None):
    """Generate book records.

    Args:
        query: gluon.dal.Expr query.
        orderby: pydal.objects.Field instance or list of Field instance.

    Yields:
        Book instance
    """
    if orderby is None:
        orderby = [db.book.creator_id, db.book.id]

    ids = [x.id for x in db(query).select(db.book.id, orderby=orderby)]
    for book_id in ids:
        book = Book.from_id(book_id)
        yield book


def creator_generator(query):
    """Generate creator records.

    Args:
        query: gluon.dal.Expr query.

    Yields:
        Creator instance
    """
    ids = [x.id for x in db(query).select(db.creator.id)]
    for creator_id in ids:
        creator = Creator.from_id(creator_id)
        yield creator


def check_cbz_files():
    """Run checks on cbz files."""
    # Books
    query = (db.book.cbz != '')
    for book in book_generator(query):
        LOG.debug('Checking: %s', book.name)
        if not os.path.exists(book.cbz):
            LOG.error(
                'Book cbz file does not exist: %s - %s',
                book.id,
                book.cbz,
            )


def check_torrent_files():
    """Run checks on torrent files."""
    # zco.mx
    torrent_creator = AllTorrentCreator()
    archive = TorrentArchive(base_path=torrent_creator.default_base_path)
    torrent_filename = os.path.join(
        archive.base_path,
        archive.category,
        archive.name,
        torrent_creator.get_destination(),
    )
    if not os.path.exists(torrent_filename):
        LOG.error('zco.mx torrent file does not exist: %s', torrent_filename)

    # Creators
    query = (db.creator.torrent != '')
    for creator in creator_generator(query):
        LOG.debug('Checking: %s', creator.name_for_url)
        if not os.path.exists(creator.torrent):
            LOG.error(
                'Creator torrent file does not exist: %s - %s',
                creator.id,
                creator.torrent,
            )

    # Books
    query = (db.book.torrent != '')
    for book in book_generator(query):
        LOG.debug('Checking: %s', book.name)
        if not os.path.exists(book.torrent):
            LOG.error(
                'Book torrent file does not exist: %s - %s',
                book.id,
                book.torrent,
            )


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script is used to run integrity checks.

USAGE
    integrity.py [OPTIONS]

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        sys.exit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.debug('Starting')

    one_hour_ago = datetime.datetime.now() \
        - datetime.timedelta(seconds=(60 * 60))
    StalledPostInProgressChecker('tumblr').check(age_buffer=one_hour_ago)
    StalledPostInProgressChecker('twitter').check(age_buffer=one_hour_ago)
    IncompleteOngoingPostChecker('tumblr').check(age_buffer=one_hour_ago)
    IncompleteOngoingPostChecker('twitter').check(age_buffer=one_hour_ago)

    check_cbz_files()
    check_torrent_files()

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
