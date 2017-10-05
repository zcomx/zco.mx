#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fix_bot_book_views.py

Remove book_view records created by bots.
"""
from __future__ import print_function
import time
from optparse import OptionParser
from applications.zcomx.modules.events import (
    BookView,
    DownloadClick,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def fix_book_view(download_click):
    """Fix book view for a given download_click."""
    # Delete one book_view for each of these that could register a book_view
    # This won't be exact but reasonable close.
    # * front page
    # * creator page Read button
    # * book page read link
    # * page slider/scroller toggle
    limit = 4
    query = (db.book_view.book_id == download_click.record_id) & \
        (db.book_view.created_on.like(
            str(download_click.created_on.date()) + '%'))
    for book_view_id in db(query).select(db.book_view.id, limitby=(0, limit)):
        book_view = BookView.from_id(book_view_id)
        LOG.info('Deleting: %s - %s', book_view.id, book_view.created_on)
        book_view.delete()


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    fix_bot_book_views.py [OPTIONS]

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

    LOG.debug('Start')
    query = (db.download_click.record_table == 'book') &\
        (db.download_click.is_bot == True)
    count = 0
    for download_click_id in db(query).select(db.download_click.id):
        download_click = DownloadClick.from_id(download_click_id)
        fix_book_view(download_click)

        # Don't lock up db.
        count += 1
        if count % 10 == 0:
            time.sleep(1)

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
