#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_check.py

Check job queue for old or invalid jobs.
"""
import datetime
import logging
import os
from gluon.shell import env
from optparse import OptionParser

VERSION = 'Version 0.1'
APP_ENV = env(__file__.split(os.sep)[-3], import_models=True)
# C0103: *Invalid name "%%s" (should match %%s)*
# pylint: disable=C0103
db = APP_ENV['db']

LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
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
    """


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option('-a', '--age', type='int',
        dest='age', default=1440,
        help='Age in minutes where jobs are considered old.',
        )
    parser.add_option('--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
        )
    parser.add_option('-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
        )
    parser.add_option('--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
        )

    (options, _) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [h.setLevel(level) for h in LOG.handlers
                if h.__class__ == logging.StreamHandler]

    LOG.info('Started.')

    LOG.debug('Checking for multiple pending jobs.')
    count = db(db.job.status == 'p').count()
    if count > 1:
        LOG.error("Multiple pending jobs in queue.")

    LOG.debug('Checking for jobs started {m} minutes ago.'.format(
        m=options.age))
    threshold = datetime.datetime.now() - \
            datetime.timedelta(minutes=options.age)
    count = db(db.job.start < threshold).count()
    if count > 0:
        LOG.error('Jobs older than {age} minutes found in queue.'.format(
            age=options.age))

    LOG.info('Done.')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
