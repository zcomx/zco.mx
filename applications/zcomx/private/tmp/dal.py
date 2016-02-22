#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
dal.py

Script to test dal commands.
"""
import sys
import traceback
from gluon import *
from optparse import OptionParser
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    dal.py

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

    usage = '%prog [options]'
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

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')
    groupby = db.book_page.book_id
    page_count = db.book.id.count()
    max_on = db.book_page.created_on.max()
    page2 = db.book_page.with_alias('page2')

    rows = db(db.book).select(
        db.book.id,
        db.book.name,
        page_count,
        max_on,
        left=[
            db.creator.on(db.book.creator_id == db.creator.id),
            db.auth_user.on(
                db.creator.auth_user_id == db.auth_user.id
            ),
            db.book_page.on(db.book_page.book_id == db.book.id),
            page2.on(
                (page2.book_id == db.book.id) &
                (page2.id != db.book_page.id) &
                (page2.created_on < db.book_page.created_on)
            ),
        ],
        groupby=groupby,
    )
    for r in rows:
        print r.book.id, ' ', r.book.name, ' ', r[page_count], r[max_on]
    # protected-access (W0212): *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    print 'FIXME db._lastsql: {var}'.format(var=db._lastsql)

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
