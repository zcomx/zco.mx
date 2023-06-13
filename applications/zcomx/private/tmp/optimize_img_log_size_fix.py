#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
optimize_img_log_size_fix.py

Script to create sizes for existing optimize_img_log records.
"""
import argparse
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.images import SIZES
from applications.zcomx.modules.images_optimize import OptimizeImgLog
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def add_sizes(log):
    """Add sizes for the log record.

    Args:
        log: optimize_img_log Row
    """
    LOG.debug('Updating: %s', log.image)
    data = log.as_dict()
    del data['id']
    for size in SIZES:
        if size == 'original':
            continue
        data['size'] = size
        OptimizeImgLog.from_add(data)
    OptimizeImgLog.from_update(log, dict(size='original'))


def man_page():
    """Print manual page-like help"""
    print("""
OVERVIEW
    Script to create sizes for existing optimize_img_log records.
    For every optimize_img_log record where size is null, create records for
    each size.

USAGE
    optimize_img_log_size_fix.py


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

    parser = argparse.ArgumentParser(prog='optimize_img_log_size_fix.py')

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
    for log in Records.from_key(OptimizeImgLog, dict(size=None)):
        add_sizes(log)
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
