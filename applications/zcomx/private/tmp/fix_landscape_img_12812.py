#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
fix_landscape_img_12812.py

Script to fix landscape images that may have been resized incorrectly.
size: 'web'
width: 750px

* resize images
* optimize images

"""
import logging
import os
import shutil
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.books import \
    Book, \
    images
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.images import \
    ImageDescriptor, \
    store
from applications.zcomx.modules.images_optimize import \
    AllSizesImages

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
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

    --vv,
        More verbose. Print debug messages to stdout.

    """


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--debug',
        action='store_true', dest='debug', default=False,
        help='Display a count of how many images would be resized.',
    )
    parser.add_option(
        '-l', '--limit', type='int',
        dest='limit', default=0,
        help='Only resize/optimize this many images.',
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
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

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
        except IOError as err:
            # LOG.error('Page image error, page id: %s, %s', page_id, str(err))
            continue
        width, unused_height = descriptor.dimensions()
        if width <= 1200:
            continue
        count += 1

        if options.debug:
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

        db(db.book_page.id == page.id).update(image=stored_filename)
        db.commit()
        book_ids.append(page.book_id)

        if options.limit and count >= options.limit:
            LOG.debug('Limit reached, aborting')
            break

    print 'FIXME count: {var}'.format(var=count)

    if not options.debug:
        for book_id in set(book_ids):
            book = Book.from_id(book_id)
            AllSizesImages.from_names(images(book)).optimize()

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
