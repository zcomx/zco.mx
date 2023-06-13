#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
original_images.py

Script to print a report on the original images of a book.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from applications.zcomx.modules.argparse.actions import ManPageAction
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
        try:
            width, height = descriptor.dimensions()
        except FileNotFoundError as err:
            LOG.error(err)
            width, height = '0', '0'
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
OVERVIEW
    Print a report on the original images of a book.
    No database changes are made.

USAGE
    original_images.py [OPTIONS] book_id [book_id ...]


OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print extended help.

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.

    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='original_images.py')

    parser.add_argument('book_ids', metavar='book_id [book_id...]')

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

    if not args:
        parser.print_help()
        sys.exit(1)

    set_cli_logging(LOG, args.verbose)

    LOG.info('Started.')
    for book_id in args.book_ids:
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
        sys.exit(1)
