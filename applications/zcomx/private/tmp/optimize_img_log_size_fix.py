#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
optimize_img_log_size_fix.py

Script to create sizes for existing optimize_img_log records.
For every optimize_img_log record where size is null, create records for each
size.

"""
import logging
import os
import sys
import traceback
from gluon import *
from gluon.shell import env
from optparse import OptionParser
from applications.zcomx.modules.images import SIZES
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


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
        db.optimize_img_log.insert(**data)

    log.update_record(size='original')
    db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    optimize_img_log_size_fix.py


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

    (options, unused_args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    LOG.info('Started.')
    ids = [
        x.id for x in
        db(db.optimize_img_log.size == None).select(db.optimize_img_log.id)]
    for log_id in ids:
        log = entity_to_row(db.optimize_img_log, log_id)
        if not log:
            raise NotFoundError('Log not found, id: %s', log_id)
        add_sizes(log)
    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        exit(1)