#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
populate_books_12777.py

Script to populate books table for testing mod 12777.
"""
import argparse
import datetime
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script populates the book table for testing. See mod 12777.

USAGE
    populate_books_12777.py 100         # Create 100 book records.

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

    parser = argparse.ArgumentParser(prog='populate_books_12777.py')

    parser.add_argument('number_to_create', type=int)

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

    now = datetime.datetime.now()
    for num in range(1, args.number_to_create + 1):
        print('FIXME num: {var}'.format(var=num))
        data = dict(
            name='POC {n:06d}'.format(n=num),
            release_date=now,
            torrent='aaa',
        )
        db.book.insert(**data)
        db.commit()

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
