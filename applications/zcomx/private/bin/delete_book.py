#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
delete_book.py

Script to delete a book.
"""
import logging
from optparse import OptionParser
from applications.zcomx.modules.books import book_tables
from applications.zcomx.modules.job_queue import queue_search_prefetch
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def delete_records(book):
    """Delete all records related to the book.

    Args:
        book: Row instance representing book record.
    """
    # Delete all records associated with book
    for t in book_tables():
        if t == 'book_to_link':
            continue             # Handle links below
        db(db[t].book_id == book.id).delete()
        db.commit()

    # Delete all links associated with the book.
    query = db.book_to_link.book_id == book.id
    for row in db(query).select(db.book_to_link.link_id):
        db(db.link.id == row['link_id']).delete()
        db.commit()
    db(db.book_to_link.book_id == book.id).delete()
    db.commit()

    # Delete the book
    db(db.book.id == book.id).delete()
    db.commit()


def man_page():
    """Print manual page-like help"""
    print """
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
    """


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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')

    book_id = args[0]
    book = entity_to_row(db.book, book_id)
    if not book:
        raise NotFoundError('Book not found, id: %s', book_id)

    delete_records(book)
    queue_search_prefetch()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
