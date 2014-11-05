#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
dal_tests.py

Script to test dal queries.
"""
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    dal_tests.py


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

    usage = '%prog [options] [file...]'
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

    query = (db.book)
    num_of_pages = db.book_page.id.count()
    # drive_target = 10 * db.book_page.id.count()
    min_page_query = (10 * db.book_page.id.count() - db.book.contributions > 0)


    rows = db(query).select(
        db.book.id,
        db.book.name,
        db.book.contributions,
        num_of_pages,
        left=[
            db.book_page.on(db.book_page.book_id == db.book.id)
        ],
        groupby=db.book.id,
        having=min_page_query,
        orderby=num_of_pages,
    )

    for r in rows:
        print '{id:2d} {name:>45s} {num:3d} {cont:3.02f} {tar:3.02f}'.format(
            id=r['book'].id,
            name=r['book'].name,
            num=r[num_of_pages],
            cont=r['book'].contributions,
            tar=1,
        )

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
