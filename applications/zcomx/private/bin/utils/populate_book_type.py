#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
populate_book_type.py

Script to populate the book_type table.
"""
import os
import sys
import traceback
from optparse import OptionParser
from gluon import *
from gluon.shell import env
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
    for r in rows:
        print('{rid} {name:20s} {seq}'.format(
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

    --vv,
        More verbose. Print debug messages to stdout.

    """)


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-c', '--clear',
        action='store_true', dest='clear', default=False,
        help='Truncate table and exit.',
    )
    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not create records. Only report what would be done.',
    )
    parser.add_option(
        '-l', '--list',
        action='store_true', dest='list', default=False,
        help='List existing records and exit.',
    )
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
        sys.exit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    if options.list:
        list_records()
        sys.exit(0)

    if options.clear:
        LOG.info('Truncating book_type table')
        db.book_type.truncate()
        db.commit()
        sys.exit(0)

    if len(args) > 1:
        parser.print_help()
        sys.exit(1)

    LOG.info('Started.')
    create_records(dry_run=options.dry_run)
    update_books(dry_run=options.dry_run)
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
