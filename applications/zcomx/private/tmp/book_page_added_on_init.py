#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
book_page_added_on_init.py

Script to initialize book.page_added_on field.
"""
import logging
import sys
import traceback
from gluon import *
from optparse import OptionParser
from applications.zcomx.modules.books import Book

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def set_page_added_on(book_id):
    """Set the book.page_added_on value

    Args:
        book_id: integer, id of book
    """
    book = Book.from_id(book_id)
    LOG.debug('Checking book: %s', book.name)

    max_created_on = db.book_page.created_on.max()
    query = (db.book_page.book_id == book.id)
    rows = db(query).select(max_created_on)
    if not rows:
        return
    page_added_on = rows[0][max_created_on]
    if page_added_on:
        LOG.debug('Updating book: %s %s', book.name, page_added_on)
        book = Book.from_updated(book, dict(page_added_on=page_added_on))


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    book_page_added_on_init.py

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

    query = (db.book.page_added_on == None)
    ids = [x.id for x in db(query).select(db.book.id)]
    for book_id in ids:
        set_page_added_on(book_id)

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
