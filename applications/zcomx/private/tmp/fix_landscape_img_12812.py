#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fix_landscape_img_12812.py

Script to fix landscape images that may have been resized incorrectly.
size: 'web'
width: 750px

* resize images
* optimize images
"""
import argparse
import os
import shutil
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import (
    Book,
    images,
)
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.images import (
    ImageDescriptor,
    store,
)
from applications.zcomx.modules.images_optimize import (
    AllSizesImages
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    This script fixes landscape images that may have been resized incorrectly.
    size: 'web'
    width: 750px
    * resize images
    * optimize images

USAGE
    fix_landscape_img_12812.py

OPTIONS
    -d, --debug
        Get a count of the images but don't resize or optimize.

    -h, --help
        Print a brief help.

    -l LIMIT, --limit=LIMIT
        Only resize/optimize LIMIT number of images.

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

    parser = argparse.ArgumentParser(prog='fix_landscape_img_12812.py')

    parser.add_argument(
        '-d', '--debug',
        action='store_true', dest='debug', default=False,
        help='Display a count of how many images would be resized.',
    )
    parser.add_argument(
        '-l', '--limit', type=int,
        dest='limit', default=0,
        help='Only resize/optimize this many images.',
    )
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

    tmp_dir = '/tmp/fix_landscape_img'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    count = 0
    book_ids = []

    ids = [x.id for x in db(db.book_page).select(db.book_page.id)]
    for page_id in ids:
        page = BookPage.from_id(page_id)
        descriptor = ImageDescriptor(page.upload_image().fullname(size='web'))
        try:
            if descriptor.orientation() != 'landscape':
                continue
        except IOError:
            # LOG.error('Page image error, page id: %s, %s', page_id, str(err))
            continue
        width, unused_height = descriptor.dimensions()
        if width <= 1200:
            continue
        count += 1

        if args.debug:
            LOG.debug('Debug, not fixing page: %s', page_id)
            continue

        LOG.debug(
            'Updating book_id: %s, page_id: %s, page_no: %s',
            page.book_id,
            page.id,
            page.page_no
        )
        # copy original to a tmp directory renaming it to what it was
        # originally called so we can preserve the original name.
        original_name = page.upload_image().original_name()
        image_filename = page.upload_image().fullname(size='original')

        src_filename = os.path.abspath(image_filename)

        dst_filename = os.path.join(tmp_dir, original_name)
        shutil.copy(src_filename, dst_filename)

        image_filename = dst_filename

        try:
            stored_filename = store(db.book_page.image, image_filename)
        except IOError as err:
            LOG.error('IOError: %s', str(err))
            return

        page = BookPage.from_updated(page, dict(image=stored_filename))
        book_ids.append(page.book_id)

        if args.limit and count >= args.limit:
            LOG.debug('Limit reached, aborting')
            break

    print('FIXME count: {var}'.format(var=count))

    if not args.debug:
        for book_id in set(book_ids):
            book = Book.from_id(book_id)
            AllSizesImages.from_names(images(book)).optimize()

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
