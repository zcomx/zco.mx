#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dal.py

Script to test dal commands.
"""
import argparse
import sys
import traceback
from gluon import *
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    Script to test dal commands. Commands are hard coded in the script.

USAGE
    dal.py

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

    parser = argparse.ArgumentParser(prog='dal.py')

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
        print(r.book.id, ' ', r.book.name, ' ', r[page_count], r[max_on])
    # pylint: disable=protected-access
    print('FIXME db._lastsql: {var}'.format(var=db._lastsql))

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
