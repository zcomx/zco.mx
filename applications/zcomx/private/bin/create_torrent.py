#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create_torrent.py

Script to create a torrent file for a book, creator or all.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.torrents import (
    AllTorrentCreator,
    BookTorrentCreator,
    CreatorTorrentCreator,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def all_torrent():
    """Create the torrent for all books."""
    result = AllTorrentCreator().archive()
    LOG.debug('Created: %s', result)


def book_torrent(book_id):
    """Create a torrent for a book."""
    book = Book.from_id(book_id)
    result = BookTorrentCreator(book).archive()
    LOG.debug('Created: %s', result)

    creator = Creator.from_id(book.creator_id)
    if not creator.rebuild_torrent:
        creator = Creator.from_updated(creator, dict(rebuild_torrent=True))


def creator_torrent(creator_id):
    """Create a torrent for a creator."""
    creator = Creator.from_id(creator_id)
    result = CreatorTorrentCreator(creator).archive()
    LOG.debug('Created: %s', result)

    if creator.rebuild_torrent:
        creator = Creator.from_updated(creator, dict(rebuild_torrent=False))


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    # Create torrents for books.
    create_torrent.py [OPTIONS] book_id [book_id book_id ...]

    # Create torrents for creators
    create_torrent.py [OPTIONS] -c creator_id [creator_id creator_id ...]

    # Create 'all' torrent
    create_torrent.py [OPTIONS] --all


OPTIONS
    -a, --all
        Create torrent for all zco.mx books.

    -c, --creator
        The record ids provided on the cli are assumed ids of book records by
        default. With this option, they are interpreted as ids of creator
        records. The script creates a torrent containing all a creator's books
        for each creator id provided.

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

    parser = argparse.ArgumentParser(prog='create_torrent.py')

    parser.add_argument(
        'record_ids',
        type=int, nargs='*',
        default=[],
        metavar='record_id [record_id ...]'
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Create the torrent for all books.',
    )
    parser.add_argument(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Create creator torrents. Ids are creator record ids.',
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

    if args.all:
        all_torrent()

    for record_id in args.record_ids:
        if args.creator:
            creator_torrent(record_id)
        else:
            book_torrent(record_id)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
