#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
names_fix.py

Script to set the names_for_* fields of existing records in a table.

Tables:
    book
    creator
Fields
    name_for_search
    name_for_url

"""
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.books import \
    names as book_names
from applications.zcomx.modules.creators import \
    formatted_name
from applications.zcomx.modules.names import \
    CreatorName, \
    names
from applications.zcomx.modules.utils import entity_to_row

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def fix_names(tablename):
    """Fix the names for a table.

    Args:
        tablename: name of table
    """
    ids = [x.id for x in db(db[tablename]).select(db[tablename].id)]
    for record_id in ids:
        LOG.debug('Updating %s id: %s', tablename, record_id)
        record = entity_to_row(db[tablename], record_id)
        if not record:
            LOG.error('Record not found, %s, id: %s', tablename, record_id)
            continue
        if tablename == 'book':
            data = book_names(record.as_dict(), fields=db[tablename].fields)
        elif tablename == 'creator':
            creator_name = CreatorName(formatted_name(record))
            data = names(creator_name, fields=db[tablename].fields)
        else:
            continue
        record.update_record(**data)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    names_fix.py table [table2]

EXAMPLES:
    names_fix.py book
    names_fix.py creator
    names_fix.py book creator

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

    usage = '%prog [options] table [table2]'
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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if not args:
        parser.print_help()
        quit(1)

    valid_tables = ['book', 'creator']

    for table in args:
        if table not in valid_tables:
            print >> sys.stderr, 'Invalid table: {t}'.format(t=table)
            quit(1)

    LOG.info('Started.')
    for table in args:
        LOG.debug('Updating: %s', table)
        fix_names(table)
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
