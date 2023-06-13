#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
populate_book_type.py

Script to populate the book_type table.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import DEFAULT_BOOK_TYPE
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']

TYPES = [
    # (sequence, name, description)
    (1, 'ongoing', 'Ongoing (eg 001, 002, 003, etc)'),
    (2, 'mini-series', 'Mini-series (eg 01 of 04)'),
    (3, 'one-shot', 'One-shot/Graphic Novel'),
]


def create_records(dry_run=False):
    """Create records."""
    fields = ['sequence', 'name', 'description']
    for record in TYPES:
        book_type = dict(list(zip(fields, record)))
        LOG.debug('book_type: {var}'.format(var=book_type))
        query = (db.book_type.name == book_type['name'])
        row = db(query).select(db.book_type.ALL).first()
        if not row:
            LOG.info('{dry}Creating record: {var}'.format(
                dry='!! DRY RUN !! ' if dry_run else '',
                var=book_type['name']))
            if not dry_run:
                db.book_type.insert(name=book_type['name'])
                db.commit()
        LOG.info('{dry}Updating record: {var}'.format(
            dry='!! DRY RUN !! ' if dry_run else '',
            var=book_type['name']))
        if not dry_run:
            db(query).update(**book_type)
            db.commit()


def list_records():
    """List records."""
    rows = db().select(db.book_type.ALL)
    print('ID Name               Seq')
    for r in rows:
        print('{rid:2d} {name:20s} {seq}'.format(
            rid=r.id, name=r.name, seq=r.sequence))


def update_books(dry_run=False):
    """Update the book_type field on book records."""
    query = (db.book_type.name == DEFAULT_BOOK_TYPE)
    book_type = db(query).select(db.book_type.ALL).first()
    query = (db.book.book_type_id == None)
    if not dry_run:
        db(query).update(book_type_id=book_type.id)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    populate_book_type.py [OPTIONS]

    This script is safe to be rerun without the -c, --clear option.
    The -c, --clear option is *not* safe. It may corrupt references to
    the book_type table.


OPTIONS
    -c, --clear
        Truncate the book_type table and exit.

    -d, --dry-run
        Do not create records, only report what would be done.

    -h, --help
        Print a brief help.

    -l, --list
        List existing book_types.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='populate_book_type.py')

    parser.add_argument(
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Truncate table and exit.',
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create records. Only report what would be done.',
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true', dest='list', default=False,
        help='List existing records and exit.',
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

    if args.list:
        list_records()
        sys.exit(0)

    if args.clear:
        LOG.info('Truncating book_type table')
        db.book_type.truncate()
        db.commit()
        sys.exit(0)

    LOG.info('Started.')
    create_records(dry_run=args.dry_run)
    update_books(dry_run=args.dry_run)
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
