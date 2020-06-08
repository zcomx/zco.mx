#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fileshare_book.py

Script to release a book for filesharing.
"""
from __future__ import print_function
import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.book.releasers import \
    FileshareBook, \
    UnfileshareBook
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.job_queue import Requeuer
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    fileshare_book.py [OPTIONS] book_id               # Release book
    fileshare_book.py [OPTIONS] --reverse book_id     # Reverse the release

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

    --reverse
        Reverse the release of a book.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


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
        '--reverse',
        action='store_true', dest='reverse', default=False,
        help='Reverse the release.',
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

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')
    book_id = args[0]
    book = Book.from_id(book_id)
    if not options.reverse and not book.release_date:
        fmt = 'Release for fileshare fail. Book not set completed, id: {i}'
        raise SyntaxError(fmt.format(i=book_id))
    creator = Creator.from_id(book.creator_id)
    release_class = UnfileshareBook if options.reverse else FileshareBook
    releaser = release_class(book, creator)
    releaser.run()
    if releaser.needs_requeue:
        queuer = release_class.queuer_class(
            db.job,
            cli_args=[str(book_id)],
        )
        requeuer = Requeuer(
            queuer,
            requeues=options.requeues,
            max_requeues=options.max_requeues,
        )
        requeuer.requeue()

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
