#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue_create_torrents.py

Script to queue create_torrent jobs. The script should be cronned. It will
queue jobs to create torrents for any creators as necessary, and to create
the 'all' torrent if necessary.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.job_queuers import \
    CreateAllTorrentQueuer, \
    CreateCreatorTorrentQueuer
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
The script should be cronned. It will queue jobs to create torrents for any
creators as necessary, and to create the 'all' torrent if necessary.

USAGE
    queue_create_torrents.py [OPTIONS]


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

    parser = argparse.ArgumentParser(prog='queue_create_torrents.py')

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

    query = (db.creator.rebuild_torrent == True)
    ids = [x.id for x in db(query).select(db.creator.id)]
    for creator_id in ids:
        LOG.debug(
            'Queuing job to create torrent for creator, id: %s', creator_id)
        CreateCreatorTorrentQueuer(
            db.job,
            cli_args=[str(creator_id)],
        ).queue()

    if len(ids) > 0:
        LOG.debug('Queuing job to create "all" torrent for creator')
        CreateAllTorrentQueuer(
            db.job,
        ).queue()


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
