#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
optimize_images.py

Utility script to optimize all images for a book, creator or all.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import \
    Book, \
    images as book_images
from applications.zcomx.modules.creators import \
    Creator, \
    images as creator_images
from applications.zcomx.modules.images_optimize import \
    AllSizesImages
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def optimize_all_images(debug=False, force=False):
    """Optimize all images."""

    # All books
    ids = [x.id for x in db(db.book).select(db.book.id)]
    for book_id in ids:
        optimize_book_images(book_id, debug=debug, force=force)

    # All creators
    ids = [x.id for x in db(db.creator).select(db.creator.id)]
    for creator_id in ids:
        optimize_creator_images(creator_id, debug=debug, force=force)


def optimize_book_images(book_id, debug=False, force=False):
    """Optimize all images associated with a book."""
    book = Book.from_id(book_id)
    LOG.debug('Optimizing images for book: %s', book.name)
    if not debug:
        images = book_images(book)
        if force:
            for image in images:
                query = (db.optimize_img_log.image == image)
                db(query).delete()
                db.commit()
        AllSizesImages.from_names(images).optimize()


def optimize_creator_images(creator_id, debug=False, force=False):
    """Optimize all images associated with a creator."""
    creator = Creator.from_id(creator_id)
    if not creator:
        raise LookupError('Creator not found, id: {i}'.format(
            i=creator_id))

    LOG.debug('Optimizing images for creator: %s', creator.name_for_url)
    if not debug:
        images = creator_images(creator)
        if force:
            for image in images:
                query = (db.optimize_img_log.image == image)
                db(query).delete()
                db.commit()
        AllSizesImages.from_names(images).optimize()


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    # Optimize all images, ie for all books and creators.
    optimize_images.py [OPTIONS]

    # Optimize the book images for books
    optimize_images.py [OPTIONS] book_id [book_id book_id ...]

    # Optimize the creator images for creators
    optimize_images.py [OPTIONS] -c creator_id [creator_id creator_id ...]

OPTIONS
    -c, --creator
        The record ids provided on the cli are assumed ids of book records by
        default. With this option, they are interpreted as ids of creator
        records. The script optimizes all the images associated with the
        creator (mug shot, indicia images, etc) with the creator id(s)
        provided.

    -d, --debug
        Show what books/creators would have their images optimized but do not
        optimize.

    -f, --force
        Force image optimization. Logs of previous optimization are deleting
        forcing images to be optimized again.

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

    parser = argparse.ArgumentParser(prog='optimize_images.py')

    parser.add_argument(
        'record_ids',
        nargs='*',
        default=[],
        metavar='record_id [record_id ...]',
    )

    parser.add_argument(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Optimize creator images. Ids are creator record ids.',
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true', dest='debug', default=False,
        help='Debug mode. Show what would be done but do not do it.',
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Force optimization even if it was done previously.',
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

    if not args.record_ids:
        optimize_all_images(debug=args.debug, force=args.force)
    else:
        for record_id in args.record_ids:
            if args.creator:
                optimize_creator_images(
                    record_id, debug=args.debug, force=args.force)
            else:
                optimize_book_images(
                    record_id, debug=args.debug, force=args.force)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
