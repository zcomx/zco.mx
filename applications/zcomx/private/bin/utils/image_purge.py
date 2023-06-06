#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
image_purge.py

Purge unused images.
"""
import os
import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.images import UploadImage
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    image_purge.py [OPTIONS]

OPTIONS

    -d, --dry-run
        Report but don't delete any images.

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

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--dry-run',
        action='store_true', dest='dry_run', default=False,
        help='Dry run. Do not delete any images.',
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

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        sys.exit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.debug('Start')

    folder = os.path.join(
        db.book_page.image.uploadfolder,
        'book_page.image'
    )

    for unused_root, unused_dirs, files in os.walk(folder):
        for filename in files:
            query = (db.book_page.image == filename)
            try:
                book_page = BookPage.from_query(query)
            except LookupError:
                book_page = None

            if book_page:
                continue

            upload_image = UploadImage(db.book_page.image, filename)
            original_name = upload_image.original_name()
            fullname = upload_image.fullname()
            print('======')
            print('        filename: {f}'.format(f=filename))
            print('        fullname: {f}'.format(f=fullname))
            print('   original_name: {f}'.format(f=original_name))
            if not options.dry_run:
                LOG.info('Deleting: %s', fullname)
                os.unlink(fullname)

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
