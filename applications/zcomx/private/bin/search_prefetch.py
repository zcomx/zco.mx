#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
search_prefetch.py

Script to build search autocomplete prefetch json files.
"""
import logging
import os
import shutil
from gluon.contrib.simplejson import dumps
from optparse import OptionParser
from applications.zcomx.modules.books import \
    formatted_name as formatted_book_name
from applications.zcomx.modules.creators import \
    formatted_name as formatted_creator_name
from applications.zcomx.modules.shell_utils import TemporaryDirectory
from applications.zcomx.modules.zco import BOOK_STATUS_DISABLED

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')
TABLES = ['book', 'creator']
DEFAULT_OUTPUT = os.path.join(
    request.folder,
    'static',
    'data',
    '<table>s.json'
)


def dump_books(output):
    """Dump books into output file.

    Args:
        output: string, name of output file.
    """
    LOG.debug('Dumping books into: %s', output)

    items = []
    query = (db.book.status != BOOK_STATUS_DISABLED)
    rows = db(query).select(
        db.book.id,
        orderby=db.book.name,
        distinct=True,
    )

    for r in rows:
        items.append(
            {
                'id': r.id,
                'table': 'book',
                'value': formatted_book_name(
                    db, r.id, include_publication_year=False)
            }
        )

    with TemporaryDirectory() as tmp_dir:
        out_file = os.path.join(tmp_dir, 'output.json')
        with open(out_file, 'w') as outfile:
            outfile.write(dumps(items))
        shutil.move(out_file, output)


def dump_creators(output):
    """Dump creators into output file.

    Args:
        output: string, name of output file.
    """
    LOG.debug('Dumping creators into: %s', output)

    items = []
    query = (db.book.id != None)
    rows = db(query).select(
        db.creator.id,
        left=[
            db.book.on(db.book.creator_id == db.creator.id)
        ],
        orderby=db.creator.name_for_search,
        distinct=True,
    )

    for r in rows:
        items.append(
            {
                'id': r.id,
                'table': 'creator',
                'value': formatted_creator_name(r.id),
            }
        )

    with TemporaryDirectory() as tmp_dir:
        out_file = os.path.join(tmp_dir, 'output.json')
        with open(out_file, 'w') as outfile:
            outfile.write(dumps(items))
        shutil.move(out_file, output)


def man_page():
    """Print manual page-like help"""
    print """
OVERVIEW
    This script creates search autocomplete prefetch json files.

USAGE
    search_prefetch.py [OPTIONS]

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -o, --output
        Filename where output is stored. The string <table> is replaced
        with the table name. Default:
        applications/zcomx/static/data/<table>s.json

    -t, --table
        Create a prefetch json file for this table only. By default json files
        are created for all tables, ie {tables}.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """.format(
        tables=' and '.join(TABLES)
    )


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
        '-o', '--output',
        dest='output', default=DEFAULT_OUTPUT,
        help='Name of output file.',
    )
    parser.add_option(
        '-t', '--table',
        dest='table', default=None,
        choices=TABLES,
        help='Table to print prefetch json for.',
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

    LOG.debug('Starting')

    tables = [options.table] if options.table is not None else TABLES

    if 'book' in tables:
        output = options.output.replace('<table>', 'book')
        dump_books(output)

    if 'creator' in tables:
        output = options.output.replace('<table>', 'creator')
        dump_creators(output)

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
