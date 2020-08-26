#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
original_images.py

Script to print a report on the original images of a book.
"""

import os
import sys
import traceback
from optparse import OptionParser
from gluon import *
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.images import ImageDescriptor
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def print_report(book):
    """Print report for a book.

    Args:
        book: Book instance
    """
    fmt = '{p:4s} {w:>4s}x{h:>4s} {n:30s} {f}'
    original_path = os.path.join(
        current.request.folder, 'uploads', 'original', 'book_page.image')
    print((fmt + ' in {o}').format(
        p='Pg#', n='Name', w='Wdth', h='Hght', f='Filename', o=original_path))
    for book_page in book.pages():
        upload_image = book_page.upload_image()
        descriptor = ImageDescriptor(upload_image.fullname())
        # unpacking-non-sequence (W0633): *Attempting to unpack a non-sequence
        # pylint: disable=W0633
        width, height = descriptor.dimensions()
        fullname = upload_image.fullname().replace(original_path, '')
        print(fmt.format(
            p=str(book_page.page_no),
            n=upload_image.original_name(),
            w=str(width),
            h=str(height),
            f=fullname,
        ))


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    original_images.py [OPTIONS] book_id [book_id ...]


OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print extended help.

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

    if not args:
        parser.print_help()
        quit(1)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')
    for book_id in args:
        try:
            book = Book.from_id(book_id)
        except LookupError as err:
            LOG.error(err)
            continue
        print_report(book)

    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
