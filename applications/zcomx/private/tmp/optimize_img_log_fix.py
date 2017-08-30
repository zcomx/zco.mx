#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
optimize_img_log_fix.py

Script to initialize the image field in existing optimize_img_log records.
"""
from __future__ import print_function
import os
import sys
import traceback
from optparse import OptionParser
from gluon import *
from gluon.shell import env
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
USAGE
    optimize_img_log_fix.py


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

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')
    for optimize_img_log in db(db.optimize_img_log).select():
        LOG.info(
            'Updating: %s - %s',
            optimize_img_log.record_field,
            optimize_img_log.record_id,
        )
        table, field = optimize_img_log.record_field.split('.')
        record = db(db[table].id == optimize_img_log.record_id).select(
            limitby=(0, 1)).first()
        if not record:
            LOG.info(
                'Record not found: %s - %s',
                optimize_img_log.record_field,
                optimize_img_log.record_id,
            )
            continue
        optimize_img_log.update_record(image=record[field])
        db.commit()
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)
