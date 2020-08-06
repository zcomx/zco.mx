#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
delete_book.py

Script to delete a book.
"""

import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.books import \
    Book, \
    book_tables
from applications.zcomx.modules.job_queuers import (
    queue_create_sitemap,
    queue_search_prefetch,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def delete_records(book):
    """Delete all records related to the book.

    Args:
        book: Row instance representing book record.
    """
    # Delete all records associated with book
    for t in book_tables():
        db(db[t].book_id == book.id).delete()
        db.commit()

    # Delete all links associated with the book.
    query = (db.link.record_table == 'book') & \
        (db.link.record_id == book.id)
    for row in db(query).select():
        row.delete_record()
        db.commit()

    # Delete the book
    book.delete()


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    delete_book.py [OPTIONS] book_id

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

    usage = '%prog [options] book_id'
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

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')

    book_id = args[0]
    book = Book.from_id(book_id)
    delete_records(book)
    queue_search_prefetch()
    queue_create_sitemap()

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
