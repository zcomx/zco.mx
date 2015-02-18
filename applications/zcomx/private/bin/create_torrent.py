#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
create_torrent.py

Script to create a torrent file for a book, creator or all.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.torrents import \
    AllTorrentCreator, \
    BookTorrentCreator, \
    CreatorTorrentCreator
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def all_torrent():
    """Create the torrent for all books."""
    result = AllTorrentCreator().archive()
    LOG.debug('Created: %s', result)


def book_torrent(book_id):
    """Create a torrent for a book."""
    book = entity_to_row(db.book, book_id)
    if not book:
        raise NotFoundError('Book not found, id: {i}'.format(i=book_id))

    result = BookTorrentCreator(book).archive()
    LOG.debug('Created: %s', result)

    creator = entity_to_row(db.creator, book.creator_id)
    if not creator:
        raise NotFoundError('Creator not found, id: {i}'.format(
            i=book.creator_id))

    if not creator.rebuild_torrent:
        creator.update_record(rebuild_torrent=True)
        db.commit()


def creator_torrent(creator_id):
    """Create a torrent for a creator."""

    creator = entity_to_row(db.creator, creator_id)
    if not creator:
        raise NotFoundError('Creator not found, id: {i}'.format(
            i=creator_id))

    result = CreatorTorrentCreator(creator).archive()
    LOG.debug('Created: %s', result)

    if creator.rebuild_torrent:
        creator.update_record(rebuild_torrent=False)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print """
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

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] book_id [book_id book_id ...]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-a', '--all',
        action='store_true', dest='all', default=False,
        help='Create the torrent for all books.',
    )
    parser.add_option(
        '-c', '--creator',
        action='store_true', dest='creator', default=False,
        help='Create creator torrents. Ids are creator record ids.',
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

    if len(args) < 1 and not options.all:
        parser.print_help()
        exit(1)

    if options.all:
        all_torrent()

    for record_id in args:
        if options.creator:
            creator_torrent(record_id)
        else:
            book_torrent(record_id)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
