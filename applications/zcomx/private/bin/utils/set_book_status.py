#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
set_book_status.py

Script to set the status of a book.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import (
    calc_status,
    generator,
    set_status,
)
from applications.zcomx.modules.zco import BOOK_STATUS_DISABLED
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='set_book_status.py')

    parser.add_argument(
        'book_ids', nargs='*', default=[], metavar='book_id [book_id ...]')

    parser.add_argument(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Set the status of all books.',
    )
    parser.add_argument(
        '-d', '--disable',
        action='store_true', dest='disable', default=False,
        help='Set the status to disabled.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    if args.all:
        generator_query = (db.book)
    else:
        generator_query = (db.book.id.belongs(args.book_ids))

    for book in generator(generator_query):
        LOG.debug('Updating: %s', book.name)
        if args.disable:
            book = set_status(book, BOOK_STATUS_DISABLED)
        else:
            book = set_status(book, calc_status(book))


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
