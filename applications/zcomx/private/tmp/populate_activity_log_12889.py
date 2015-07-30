#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
populate_activity_log_12889.py

Script to populate activity_log table for testing.
"""
import datetime
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.books import \
    Book, \
    get_page
from applications.zcomx.modules.utils import \
    entity_to_row

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def log_completed():
    """Create activity_log records for books set as completed. """
    query = (db.book.release_date != None)
    ids = [x.id for x in db(query).select(db.book.id)]
    for book_id in ids:
        book = Book.from_id(book_id)
        # Check if log exists
        query = (db.activity_log.action == 'completed') & \
                (db.activity_log.book_id == book.id)
        count = db(query).count()
        if not count:
            LOG.debug('Logging completed: %s', book.name)
            try:
                first_page = get_page(book, page_no='first')
            except LookupError:
                LOG.error('First page not found: %s', book.name)
                continue

            db.activity_log.insert(
                book_id=book.id,
                book_page_ids=[first_page.id],
                action='completed',
                time_stamp=datetime.datetime.combine(
                    book.release_date, datetime.datetime.max.time())
            )
            db.commit()


def log_page_added():
    """Create activity_log records for pages added to books."""

    sql = """
        SELECT book_id, substr(created_on, 0, 13), count(*)
        FROM book_page
        GROUP BY book_id, substr(created_on, 0, 13)
        ;
    """
    for row in db.executesql(sql):
        book_id, created_on_grp, count = row
        book = entity_to_row(db.book, book_id)
        action = 'page added'
        time_stamp = datetime.datetime.strptime(
            created_on_grp + ':00:00',
            "%Y-%m-%d %H:%M:%S"
        )

        # Check if log exists
        query = (db.activity_log.action == action) & \
                (db.activity_log.time_stamp == time_stamp) & \
                (db.activity_log.book_id == book.id)
        count = db(query).count()
        if not count:
            page_query = (db.book_page.book_id == book.id) & \
                (db.book_page.created_on.like(created_on_grp + '%'))
            page_id_rows = db(page_query).select(
                db.book_page.id,
                orderby=db.book_page.page_no
            )
            page_ids = [x.id for x in page_id_rows]
            if not page_ids:
                LOG.error('No pages found: %s', book.name)
                continue

            LOG.debug('Logging %s: %s', action, book.name)
            db.activity_log.insert(
                book_id=book.id,
                book_page_ids=page_ids,
                action=action,
                time_stamp=time_stamp
            )
            db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    populate_activity_log_12889.py


OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.

    """


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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    LOG.info('Started.')

    log_completed()
    log_page_added()

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
