#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
notify_p2p_networks.py

Script to notify p2p networks of addition or deletion of a cbz file.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='notify_p2p_networks.py')

    parser.add_argument(
        '-d', '--delete',
        action='store_true', dest='delete', default=False,
        help='Notify p2p networks of deletion of cbz file.',
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

    for cbz_filename in args:
        notifier = P2PNotifier(cbz_filename)
        notifier.notify(delete=args.delete)


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
