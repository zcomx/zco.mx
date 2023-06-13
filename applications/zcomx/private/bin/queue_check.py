#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue_check.py

Check job queue for old or invalid jobs.
"""
import argparse
import datetime
import os
import sys
import traceback
from gluon.shell import env
from applications.zcomx.modules.argparse.actions import ManPageAction
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='queue_check.py')

    parser.add_argument(
        '-a', '--age', type=int,
        dest='age', default=1440,
        help='Age in minutes where jobs are considered old.',
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

    LOG.info('Started.')

    LOG.debug('Checking for multiple pending jobs.')
    jobs = Records.from_key(Job, dict(status='p'))
    if len(jobs) > 1:
        LOG.error("Multiple pending jobs in queue.")

    LOG.debug('Checking for jobs started %s minutes ago.', args.age)
    threshold = datetime.datetime.now() - \
        datetime.timedelta(minutes=args.age)
    query = (db.job.start < threshold)
    jobs = Records.from_query(Job, query)
    if len(jobs) > 0:
        LOG.error('Jobs older than %s minutes found in queue.', args.age)

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
