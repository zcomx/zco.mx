#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
queue_create_torrents.py

Script to queue create_torrent jobs. The script should be cronned. It will
queue jobs to create torrents for any creators as necessary, and to create
the 'all' torrent if necessary.
"""

import sys
import traceback
from optparse import OptionParser
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
        exit(1)
