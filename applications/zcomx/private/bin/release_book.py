#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
release_book.py

Script to release a book.
"""
import datetime
import logging
from optparse import OptionParser
from applications.zcomx.modules.books import \
    optimize_images as optimize_book_images, \
    unoptimized_images as unoptimized_book_images
from applications.zcomx.modules.creators import \
    optimize_images as optimize_creator_images, \
    unoptimized_images as unoptimized_creator_images
from applications.zcomx.modules.job_queue import \
    CreateCBZQueuer, \
    CreateTorrentQueuer, \
    ReleaseBookQueuer
from applications.zcomx.modules.utils import \
    NotFoundError

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    release_book.py [OPTIONS] book_id

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -m NUM, --max-requeues=NUM
        The script will be requeued at most NUM times. Use this to
        prevent endless requeueing. Default 25.

    -r NUM, --requeues=NUM
        The script has been requeued NUM times. This value is incremented
        everytime the script is queued. Use in conjunction with --max-requeues
        to prevent endless requeueing.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] book_id'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-m', '--max-requeues',
        type='int',
        dest='max_requeues', default=25,
        help='Requeue this script at most this many times. Default 25.',
    )
    parser.add_option(
        '-r', '--requeues',
        type='int',
        dest='requeues', default=0,
        help='The number of times this script has been requeued.',
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

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')

    requeue = False

    book_id = args[0]
    book = db(db.book.id == book_id).select().first()
    if not book:
        raise NotFoundError('Book not found, id: %s', book_id)

    creator = db(db.creator.id == book.creator_id).select().first()
    if not creator:
        raise NotFoundError('Creator not found, id: %s', book.creator_id)

    if unoptimized_book_images(book):
        optimize_book_images(book, priority='optimize_img_for_release')
        requeue = True
    elif unoptimized_creator_images(creator):
        optimize_creator_images(creator, priority='optimize_img_for_release')
        requeue = True
    elif not book.cbz:
        CreateCBZQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        requeue = True
    elif not book.torrent:
        # Create book torrent
        CreateTorrentQueuer(
            db.job,
            cli_args=[str(book.id)],
        ).queue()
        requeue = True
    else:
        # Everythings good. Release the book.
        book.update_record(
            release_date=datetime.datetime.today(),
            releasing=False,
        )
        db.commit()

    if requeue and options.requeues < options.max_requeues:
        ReleaseBookQueuer(
            db.job,
            cli_options={
                '-r': options.requeues + 1,
                '-m': options.max_requeues,
            },
            cli_args=[str(book.id)],
        ).queue()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
