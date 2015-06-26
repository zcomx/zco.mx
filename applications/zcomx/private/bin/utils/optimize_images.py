#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
optimize_images.py

Utility script to optimize all images for a book, creator or all.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.books import images as book_images
from applications.zcomx.modules.creators import images as creator_images
from applications.zcomx.modules.images_optimize import \
    AllSizesImages
from applications.zcomx.modules.utils import \
    entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


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
    book = entity_to_row(db.book, book_id)
    if not book:
        raise LookupError('Book not found, id: {i}'.format(i=book_id))

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
    creator = entity_to_row(db.creator, creator_id)
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
    print """
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

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] [book_id book_id ...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Optimize creator images. Ids are creator record ids.',
    )
    parser.add_option(
        '-d', '--debug',
        action='store_true', dest='debug', default=False,
        help='Debug mode. Show what would be done but do not do it.',
    )
    parser.add_option(
        '-f', '--force',
        action='store_true', dest='force', default=False,
        help='Force optimization even if it was done previously.',
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

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if not args:
        optimize_all_images(debug=options.debug, force=options.force)
    else:
        for record_id in args:
            if options.creator:
                optimize_creator_images(
                    record_id, debug=options.debug, force=options.force)
            else:
                optimize_book_images(
                    record_id, debug=options.debug, force=options.force)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
