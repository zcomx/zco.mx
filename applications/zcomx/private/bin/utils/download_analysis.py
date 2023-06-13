#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
download_analysis.py

Analyze download records.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def check_book(book_id):
    """Check a book

    Args:
        book_id: int, id of book
    """
    book = Book.from_id(book_id)

    query = (db.activity_log.book_id == book.id) & \
        (db.activity_log.action == 'completed')
    rows = db(query).select(
        db.activity_log.time_stamp,
        orderby=~db.activity_log.time_stamp
    )

    if not rows:
        return

    time_stamp = rows[0].time_stamp

    book_count = 0
    creator_count = 0
    all_count = 0

    query = (db.download_click.loggable == True) & \
        (db.download_click.time_stamp >= time_stamp) & \
        (db.download_click.record_table == 'book') & \
        (db.download_click.record_id == book.id)
    book_count = db(query).count()

    query = (db.download_click.loggable == True) & \
        (db.download_click.time_stamp >= time_stamp) & \
        (db.download_click.record_table == 'creator') & \
        (db.download_click.record_id == book.creator_id)
    creator_count = db(query).count()

    query = (db.download_click.loggable == True) & \
        (db.download_click.time_stamp >= time_stamp) & \
        (db.download_click.record_table == 'all')
    all_count = db(query).count()

    count = book_count + creator_count + all_count

    if count != book.downloads:
        diff = book.downloads - count
        print('FIXME book: {i} {d} {c} {f}'.format(
            i=book.id, c=count, d=book.downloads, f=diff))


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    download_analysis.py [OPTIONS]

OPTIONS

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

    parser = argparse.ArgumentParser(prog='download_analysis.py')

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

    query = (db.book.release_date != None) & \
        (db.book.torrent != '')
    rows = db(query).select(db.book.id)
    for r in rows:
        check_book(r.id)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
