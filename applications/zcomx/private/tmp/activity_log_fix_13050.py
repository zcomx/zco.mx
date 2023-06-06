#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
activity_log_fix_13050.py

Script to fix activity_log records.
Set activity_log.deleted_book_page_ids where applicable.
See mod 13050.
"""
import os
import sys
import traceback
from optparse import OptionParser
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.activity_logs import ActivityLog
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def set_deleted(activity_log):
    """Set the deleted book_page_ids for activity_log.

    Args:
        activity_log: ActivityLog instance
    """
    LOG.debug('Checking activity_log: %s', activity_log.id)
    if not activity_log.book_page_ids:
        return
    for book_page_id in activity_log.book_page_ids:
        try:
            book_page = BookPage.from_id(book_page_id)
        except LookupError:
            LOG.debug('Setting deleted book_page: %s', book_page_id)
            book_page = BookPage(id=book_page_id)
            activity_log = activity_log.set_page_deleted(book_page)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    activity_log_fix_13050.py


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

    LOG.info('Started.')
    ids = [x.id for x in db(db.activity_log).select(db.activity_log.id)]
    for activity_log_id in ids:
        activity_log = ActivityLog.from_id(activity_log_id)
        set_deleted(activity_log)
    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
