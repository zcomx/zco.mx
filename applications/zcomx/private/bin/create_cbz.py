#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create_cbz.py

Script to create a cbz file for a book.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.cbz import (
    CBZCreateError,
    archive,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    create_cbz.py [OPTIONS] book_id [book_id book_id ...]

OPTIONS
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

    parser = argparse.ArgumentParser(prog='create_cbz.py')

    parser.add_argument('book_ids', nargs='+', metavar='book_id')

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

    exit_status = 0
    for book_id in args.book_ids:
        try:
            book = Book.from_id(book_id)
        except LookupError:
            LOG.error('Book not found, id: %s', book_id)
            exit_status = 1
            continue

        LOG.debug('Creating cbz for: %s', book.name)
        try:
            archive(book)
        except (CBZCreateError, LookupError) as err:
            LOG.error('%s, %s', err, book.name)
            exit_status = 1
    if exit_status:
        sys.exit(exit_status)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
