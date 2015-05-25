#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
process_rss_pre_logs.py

Script to process rss_pre_logs.
* Create rss_log records from rss_pre_log records.
* Delete rss_pre_log records converted thus.
"""
import logging
from optparse import OptionParser
from applications.zcomx.modules.rss import \
    CompletedRSSPreLogSet, \
    MINIMUM_AGE_TO_LOG_IN_SECONDS, \
    PageAddedRSSPreLogSet, \
    RSSPreLogSet


VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    process_rss_pre_logs.py [OPTIONS]

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

    usage = '%prog [options] book_id'
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

    LOG.debug('Starting')
    logs = db(db.rss_pre_log).select(
        db.rss_pre_log.book_id,
        groupby=db.rss_pre_log.book_id,
    )
    for log in logs:
        LOG.debug('Checking book id: %s', log.book_id)
        filters = {'book_id': log.book_id}
        log_set = RSSPreLogSet.load(filters=filters)
        youngest_log = log_set.youngest()
        age = youngest_log.age()
        if age.total_seconds() < MINIMUM_AGE_TO_LOG_IN_SECONDS:
            LOG.debug('Pre log records too young, book_id: %s', log.book_id)
            continue
        LOG.debug('Logging book id: %s', log.book_id)

        page_added_set = PageAddedRSSPreLogSet.load(filters=filters)
        rss_log = page_added_set.as_rss_log()
        if rss_log:
            LOG.debug('Creating rss_log action: %s', rss_log.record['action'])
            rss_log.save()

        completed_set = CompletedRSSPreLogSet.load(filters=filters)
        rss_log = completed_set.as_rss_log()
        if rss_log:
            LOG.debug('Creating rss_log action: %s', rss_log.record['action'])
            rss_log.save()

        for rss_pre_log in log_set.rss_pre_logs:
            rss_pre_log.delete()

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
