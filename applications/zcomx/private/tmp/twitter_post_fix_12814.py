#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
twitter_post_fix_12814.py

Script to fix book.twitter post_id .
See mod 12814.
"""
import argparse
import csv
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    twitter_post_fix_12814.py file.csv

    # CSV format
    book_id,twitter_post_id

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

    parser = argparse.ArgumentParser(prog='activity_log_fix_13050.py')

    parser.add_argument('csv_filename', metavar='file.csv')

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

    fieldnames = ['book_id', 'twitter_post_id']

    with open(args.csv_filename, encoding='utf-8') as f:
        csv_reader = csv.DictReader(
            f,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL
        )
        for row in csv_reader:
            if not row['book_id']:
                continue
            if not row['twitter_post_id']:
                continue
            if row['book_id'] == 'book_id':
                continue        # ignore header

            book_id = row['book_id']
            twitter_post_id = row['twitter_post_id']

            book = Book.from_id(book_id)
            if not book:
                LOG.error('book not found, id: %s', row)
                continue

            book = Book.from_updated(
                book, dict(twitter_post_id=twitter_post_id))

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
