#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
set_book_status.py

Script to set the status of a book.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.books import \
    calc_status, \
    set_status
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row
from applications.zcomx.modules.zco import BOOK_STATUS_DISABLED

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def book_generator(query):
    """Generate book records.

    Args:
        query: gluon.dal.Expr query.


    Yields:
        Row instance representing a book record.
    """
    ids = [x.id for x in db(query).select(db.book.id)]
    for book_id in ids:
        book = entity_to_row(db.book, book_id)
        if not book:
            raise NotFoundError('Book not found, id: {i}'.format(i=book_id))
        yield book


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    # Set the status of a books based on their calculated status
    set_book_status.py [OPTIONS] book_id [book_id book_id ...]

    # Disable a book
    set_book_status.py [OPTIONS] --disable book_id [book_id  ...]

    # Set the status of all books
    set_book_status.py [OPTIONS] --all

OPTIONS
    -a, --all
        Set the status of all zco.mx books.

    -d, --disable
        Set the status to disabled.

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

    usage = '%prog [options] book_id [book_id book_id ...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Set the status of all books.',
    )
    parser.add_option(
        '-d', '--disable',
        action='store_true', dest='disable', default=False,
        help='Set the status to disabled.',
    )
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

    if len(args) < 1 and not options.all:
        parser.print_help()
        exit(1)

    if options.all:
        generator_query = (db.book)
    else:
        generator_query = (db.book.id.belongs(args))

    for book in book_generator(generator_query):
        LOG.debug('Updating: %s', book.name)
        if options.disable:
            set_status(book, BOOK_STATUS_DISABLED)
        else:
            set_status(book, calc_status(book))


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
