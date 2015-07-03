#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
process_activity_logs.py

Script to process activity_log records.
* Create activity_log records from tentative_activity_log records.
* Delete tentative_activity_log records converted thus.
"""
import logging
from optparse import OptionParser
from applications.zcomx.modules.activity_logs import \
    CompletedTentativeLogSet, \
    MINIMUM_AGE_TO_LOG_IN_SECONDS, \
    PageAddedTentativeLogSet, \
    TentativeLogSet


VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    process_activity_logs.py [OPTIONS]

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -m, --minimum-age
        Tentative activity log records must have this minimum age in order
        to be processed. Age is in seconds. Default: {m}

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """.format(m=MINIMUM_AGE_TO_LOG_IN_SECONDS)


def main():
    """Main processing."""

    usage = '%prog [options] book_id'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-m', '--minimum-age', type='int',
        dest='minimum_age', default=MINIMUM_AGE_TO_LOG_IN_SECONDS,
        help='Minimum age of tentative log to process.',
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

    LOG.debug('Starting')
    logs = db(db.tentative_activity_log).select(
        db.tentative_activity_log.book_id,
        groupby=db.tentative_activity_log.book_id,
    )
    for log in logs:
        LOG.debug('Checking book id: %s', log.book_id)
        filters = {'book_id': log.book_id}
        log_set = TentativeLogSet.load(filters=filters)
        youngest_log = log_set.youngest()
        age = youngest_log.age()
        if age.total_seconds() < options.minimum_age:
            LOG.debug(
                'Tentative log records too young, book_id: %s', log.book_id)
            continue
        LOG.debug('Logging book id: %s', log.book_id)

        page_added_set = PageAddedTentativeLogSet.load(filters=filters)
        activity_log = page_added_set.as_activity_log()
        if activity_log:
            LOG.debug(
                'Creating activity_log action: %s',
                activity_log.action
            )
            activity_log.save()

        completed_set = CompletedTentativeLogSet.load(filters=filters)
        activity_log = completed_set.as_activity_log()
        if activity_log:
            LOG.debug(
                'Creating activity_log action: %s',
                activity_log.action
            )
            activity_log.save()

        for tentative_activity_log in log_set.tentative_records:
            tentative_activity_log.delete()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
