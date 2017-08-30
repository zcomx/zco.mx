#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
notify_p2p_networks.py

Script to notify p2p networks of addition or deletion of a cbz file.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
from __future__ import print_function
from optparse import OptionParser
from applications.zcomx.modules.torrents import \
    P2PNotifier
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    notify_p2p_networks.py [OPTIONS] path/to/file.cbz


OPTIONS

    -d, --delete
        By default, p2p networks are notified of the addition of the cbz file.
        With this option, the p2p networks are notified of the deletion
        of the file. With this option, the cbz file does not have to exist.

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

    usage = '%prog [options] file.cbz'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-d', '--delete',
        action='store_true', dest='delete', default=False,
        help='Notify p2p networks of deletion of cbz file.',
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if len(args) < 1:
        parser.print_help()
        exit(1)

    for cbz_filename in args:
        notifier = P2PNotifier(cbz_filename)
        notifier.notify(delete=options.delete)


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
