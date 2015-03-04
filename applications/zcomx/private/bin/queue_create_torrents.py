#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_create_torrents.py

Script to queue create_torrent jobs. The script should be cronned. It will
queue jobs to create torrents for any creators as necessary, and to create
the 'all' torrent if necessary.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
from optparse import OptionParser
from applications.zcomx.modules.job_queue import CreateTorrentQueuer

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
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
    """


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

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) > 0:
        parser.print_help()
        exit(1)

    query = (db.creator.rebuild_torrent == True)
    ids = [x.id for x in db(query).select(db.creator.id)]
    for creator_id in ids:
        LOG.debug(
            'Queuing job to create torrent for creator, id: %s', creator_id)
        CreateTorrentQueuer(
            db.job,
            cli_options={'-c': True},
            cli_args=[str(creator_id)],
        ).queue()

    if len(ids) > 0:
        LOG.debug('Queuing job to create "all" torrent for creator')
        CreateTorrentQueuer(
            db.job,
            cli_options={'--all': True},
        ).queue()


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)