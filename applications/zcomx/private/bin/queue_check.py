#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue_check.py

Check job queue for old or invalid jobs.
"""
import datetime
import os
import sys
import traceback
from optparse import OptionParser
from gluon.shell import env
from applications.zcomx.modules.job_queue import Job
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# pylint: disable=invalid-name
db = APP_ENV['db']


def man_page():
    """Print manual page-like help"""
    print("""
OPTIONS
    -h, --help
        Print a brief help.

    -a AGE, --age=AGE
        Age in minutes that a job should be considered old. Any job whose
        start time is this many minutes old is reported.
        Default: 1440 (24 hours).

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
        '-a', '--age', type='int',
        dest='age', default=1440,
        help='Age in minutes where jobs are considered old.',
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

    (options, _) = parser.parse_args()

    if options.man:
        man_page()
        sys.exit(0)

    set_cli_logging(LOG, options.verbose, options.vv)

    LOG.info('Started.')

    LOG.debug('Checking for multiple pending jobs.')
    jobs = Records.from_key(Job, dict(status='p'))
    if len(jobs) > 1:
        LOG.error("Multiple pending jobs in queue.")

    LOG.debug('Checking for jobs started %s minutes ago.', options.age)
    threshold = datetime.datetime.now() - \
        datetime.timedelta(minutes=options.age)
    query = (db.job.start < threshold)
    jobs = Records.from_query(Job, query)
    if len(jobs) > 0:
        LOG.error('Jobs older than %s minutes found in queue.', options.age)

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
