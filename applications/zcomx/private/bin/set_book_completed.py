#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
set_book_completed.py

Script to set a book completed
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.book.releasers import (
    ReleaseBook,
    UnreleaseBook,
)
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.job_queue import Requeuer
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    set_book_completed.py [OPTIONS] book_id               # Set completed
    set_book_completed.py [OPTIONS] --reverse book_id     # Reverse it

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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='set_book_completed.py')

    parser.add_argument('book_id', type=int)

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-m', '--max-requeues',
        type=int,
        dest='max_requeues', default=25,
        help='Requeue this script at most this many times. Default 25.',
    )
    parser.add_argument(
        '-r', '--requeues',
        type=int,
        dest='requeues', default=0,
        help='The number of times this script has been requeued.',
    )
    parser.add_argument(
        '--reverse',
        action='store_true', dest='reverse', default=False,
        help='Reverse the release.',
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

    LOG.debug('Starting')
    book_id = args.book_id
    book = Book.from_id(book_id)
    creator = Creator.from_id(book.creator_id)
    release_class = UnreleaseBook if args.reverse else ReleaseBook
    releaser = release_class(book, creator)
    releaser.run()
    if releaser.needs_requeue:
        queuer = release_class.queuer_class(
            db.job,
            cli_args=[str(book_id)],
        )
        requeuer = Requeuer(
            queuer,
            requeues=args.requeues,
            max_requeues=args.max_requeues,
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
        sys.exit(1)
