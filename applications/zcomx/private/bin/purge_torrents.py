#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
purge_torrents.py

This script purges empty creator and 'all' torrent files as necessary.
"""

import errno
import os
import sys
import traceback
from optparse import OptionParser
from applications.zcomx.modules.archives import TorrentArchive
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def creators_needing_purge():
    """Generator of Row instances representing creator records for
    creators whose torrents need purging.

    Returns:
        Creator instance
    """
    query = (db.creator.torrent != None)
    ids = [x.id for x in db(query).select(db.creator.id)]
    for creator_id in ids:
        query = (db.book.creator_id == creator_id) & \
                (db.book.cbz != None)
        if db(query).count() > 0:
            continue
        yield Creator.from_id(creator_id)


def delete_all_torrent():
    """Delete the 'all' torrent. """
    tor_archive = TorrentArchive()
    # Add .torrent extension to file
    filename = '.'.join([tor_archive.name, 'torrent'])

    torrent_filename = os.path.join(
        tor_archive.base_path,
        tor_archive.category,
        tor_archive.name,
        filename
    )

    if os.path.exists(torrent_filename):
        LOG.debug('Deleting: %s', torrent_filename)
        os.unlink(torrent_filename)


def delete_torrent(creator):
    """Delete the torrent related to the creator.

    Args:
        creator: Row instance representing creator record.
    """
    if not creator.torrent:
        return

    LOG.debug('Deleting: %s', creator.torrent)
    # Eg creator.torrent
    # applications/zcomx/private/var/tor/zco.mx/F/First Last.torrent
    try:
        os.unlink(creator.torrent)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise


def num_books_with_cbz():
    """Return the number books that have a cbz file created.

    Returns:
        integer, number of books with a cbz file.
    """
    query = (db.book.cbz != None)
    return db(query).count()


def man_page():
    """Print manual page-like help"""
    print("""
This script deletes unneeded torrent files.
Creators: if a creator torrent file exists but the creator no longer has
    any released books, the torrent file is deleted.

All: if the 'all' torrent file exists, but there no longer are any
    released books, the 'all' torrent file is deleted.

USAGE
    purge_torrents.py [OPTIONS]

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """)


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) > 0:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')

    for creator in creators_needing_purge():
        LOG.debug('Purging torrent for creator: %s', creator.name)
        delete_torrent(creator)
        data = dict(
            torrent=None,
            rebuild_torrent=False,
        )
        creator = Creator.from_updated(creator, data)

    count = num_books_with_cbz()
    LOG.debug('Number of books with cbz file: %s', count)
    if count == 0:
        delete_all_torrent()
    else:
        LOG.debug('"All" torrent required, not deleting.')

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
