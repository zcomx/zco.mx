#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
create_cbz.py

Script to create a cbz file for a book.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404

import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.cbz import \
    CBZCreateError, \
    archive
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    create_cbz.py [OPTIONS] book_id [book_id book_id ...]

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options] book_id [book_id book_id ...]'
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) < 1:
        parser.print_help()
        exit(1)

    exit_status = 0
    for book_id in args:
        try:
            book = Book.from_id(book_id)
        except LookupError:
            LOG.error('Book not found, id: %s', book_id)
            exit_status = 1
            continue

        LOG.debug('Creating cbz for: %s', book.name)
        try:
            archive(book)
        except (CBZCreateError, LookupError) as err:
            LOG.error('%s, %s', err, book.name)
            exit_status = 1
    if exit_status:
        exit(exit_status)

if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
