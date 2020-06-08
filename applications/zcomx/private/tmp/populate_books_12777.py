#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
populate_books_12777.py

Script to populate books table for testing mod 12777.
"""
from __future__ import print_function
import datetime
import os
import sys
import traceback
from optparse import OptionParser
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    populate_books_12777.py 100         # Create 100 book records.


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

    usage = '%prog [options] number'
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

    LOG.info('Started.')

    now = datetime.datetime.now()
    number = int(args[0])
    for num in range(1, number + 1):
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
        exit(1)
