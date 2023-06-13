#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
urlify.py

Script to test urlify commands.
"""
import argparse
import sys
import traceback
from pydal.validators import urlify
from gluon import *
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script tests hard coded urlify commands. Safe to re-run.

USAGE
    urlify.py

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

    parser = argparse.ArgumentParser(prog='urlify.py')

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

    x = urlify('John Smith')
    print('FIXME x: {var}'.format(var=x))

    x = urlify('Jøhn Smith')
    print('FIXME x: {var}'.format(var=x))

    y = db(db.creator.name_for_url == x).select(limitby=(0, 1)).first()
    print('FIXME y: {var}'.format(var=y))
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
