#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
search_prefetch.py

Script to build search autocomplete prefetch json files.
"""
import argparse
import os
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """.format(
        tables=' and '.join(TABLES)
    ))


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='search_prefetch.py')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-o', '--output',
        dest='output', default=DEFAULT_OUTPUT,
        help='Name of output file.',
    )
    parser.add_argument(
        '-t', '--table',
        dest='table', default=None,
        choices=TABLES,
        help='Table to print prefetch json for.',
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
        help='Print the script version.',
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    LOG.debug('Starting')

    tables = [args.table] if args.table is not None else TABLES

    for table in tables:
        output = args.output.replace('<table>', table)
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
        sys.exit(1)
