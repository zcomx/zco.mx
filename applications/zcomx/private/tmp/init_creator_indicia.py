#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
init_creator_indicia.py

Script to initialize creator.indicia_portrait and creator.indicia_landscape
fields.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.creators import \
    Creator, \
    queue_update_indicia
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    Script to initialize creator.indicia_portrait and creator.indicia_landscape
    fields.

    When a creator is added, the indicia fields get initialized to the default
    indicia image. Some old records didn't get updated. This script will fix
    it.

    This script is safe to rerun.

    All it does is queue jobs to run update_creator_indicia.py for the creators
    that weren't initialized properly.

USAGE
    init_creator_indicia.py

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

    parser = argparse.ArgumentParser(prog='init_creator_indicia.py')

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

    LOG.info('Started.')
    ids = [x.id for x in db(db.creator).select(db.creator.id)]
    for creator_id in ids:
        creator = Creator.from_id(creator_id)
        if not creator.indicia_portrait or not creator.indicia_landscape:
            LOG.debug('Queueing creator: %s', creator.name_for_url)
            queue_update_indicia(creator)
    LOG.info('Done.')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
