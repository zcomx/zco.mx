#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
process_activity_logs.py

Script to process activity_log records.
* Create activity_log records from tentative_activity_log records.
* Delete tentative_activity_log records converted thus.
"""
import argparse
import sys
import traceback
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.activity_logs import (
    ActivityLog,
    CompletedTentativeLogSet,
    MINIMUM_AGE_TO_LOG_IN_SECONDS,
    PageAddedTentativeLogSet,
    TentativeLogSet,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def man_page():
    """Print manual page-like help"""
    print("""
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

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """.format(m=MINIMUM_AGE_TO_LOG_IN_SECONDS))


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='process_activity_logs.py')

    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-m', '--minimum-age', type=int,
        dest='minimum_age', default=MINIMUM_AGE_TO_LOG_IN_SECONDS,
        help='Minimum age of tentative log to process.',
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
        help='Print the script version',
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    LOG.debug('Starting')
    logs = db(db.tentative_activity_log).select(
        db.tentative_activity_log.book_id,
        groupby=db.tentative_activity_log.book_id,
    )
    for log in logs:
        LOG.debug('Checking book id: %s', log.book_id)
        filters = {'book_id': log.book_id}
        tentative_log_set = TentativeLogSet.load(filters=filters)
        youngest_log = tentative_log_set.youngest()
        age = youngest_log.age()
        if age.total_seconds() < args.minimum_age:
            LOG.debug(
                'Tentative log records too young, book_id: %s', log.book_id)
            continue
        LOG.debug('Logging book id: %s', log.book_id)

        log_set_classes = [
            PageAddedTentativeLogSet,
            CompletedTentativeLogSet,
        ]
        for log_set_class in log_set_classes:
            log_set = log_set_class.load(filters=filters)
            activity_log_data = log_set.as_activity_log()
            if activity_log_data:
                activity_log = ActivityLog.from_add(activity_log_data)
                LOG.debug(
                    'Created activity_log action: %s',
                    activity_log.action
                )

        for tentative_activity_log in tentative_log_set.tentative_records:
            tentative_activity_log.delete()

    LOG.debug('Done')


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
