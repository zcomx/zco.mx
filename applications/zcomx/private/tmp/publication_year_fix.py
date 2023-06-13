#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
publication_year_fix.py

Script to set the book.publication_year field based on metadata.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.indicias import \
    BookPublicationMetadata
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script to sets the book.publication_year field based on metadata.

USAGE
    publication_year_fix.py

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

    parser = argparse.ArgumentParser(prog='publication_year_fix.py')

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

    LOG.info('Started.')
    ids = [x.id for x in db(db.book).select(db.book.id)]
    for book_id in ids:
        book = Book.from_id(book_id)
        meta = BookPublicationMetadata.from_book(book)
        try:
            publication_year = meta.publication_year()
        except ValueError:
            continue        # This is expected if the metadata is not set.

        if book.publication_year == publication_year:
            continue
        LOG.debug('Updating: %s to %s', book.name, publication_year)
        book = Book.from_updated(book, dict(publication_year=publication_year))
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
