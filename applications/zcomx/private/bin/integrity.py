#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
integrity.py

Script to run integrity checks.
"""
from __future__ import print_function
import datetime
from optparse import OptionParser
from applications.zcomx.modules.zco import IN_PROGRESS
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


class BaseChecker(object):
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
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.debug('Starting')
    one_hour_ago = datetime.datetime.now() \
        - datetime.timedelta(seconds=(60 * 60))
    StalledPostInProgressChecker('tumblr').check(age_buffer=one_hour_ago)
    StalledPostInProgressChecker('twitter').check(age_buffer=one_hour_ago)
    IncompleteOngoingPostChecker('tumblr').check(age_buffer=one_hour_ago)
    IncompleteOngoingPostChecker('twitter').check(age_buffer=one_hour_ago)
    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
