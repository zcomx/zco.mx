#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
search_prefetch.py

Script to build search autocomplete prefetch json files.
"""

import os
import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.autocomplete import autocompleter_class
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
TABLES = ['book', 'creator']
DEFAULT_OUTPUT = os.path.join(
    request.folder,
    'static',
    'data',
    '<table>s.json'
)


def man_page():
    """Print manual page-like help"""
    print("""
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
    ))


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

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.debug('Starting')

    tables = [options.table] if options.table is not None else TABLES

    for table in tables:
        output = options.output.replace('<table>', table)
        LOG.debug('Dumping table %s into: %s', table, output)
        completer_class = autocompleter_class(table)
        completer = completer_class()
        completer.dump(output)
    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
