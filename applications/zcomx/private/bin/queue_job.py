#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_job.py

Queue a job.

"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
import time
from optparse import OptionParser
from applications.zcomx.modules.job_queue import QueueWithSignal

VERSION = 'Version 0.1'

LOG = logging.getLogger('cli')


def main():
    """Main processing."""

    usage = '%prog [options] command'
    parser = OptionParser(usage=usage, version=VERSION)

    now = time.strftime('%F %T', time.localtime())

    parser.add_option(
        '-p', '--priority', type='int',
        dest='priority', default=0,
        help='job priority, default: 0',
    )
    parser.add_option(
        '-s', '--start',
        dest='start', default=now,
        help='job start time, default: now',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help='print messages to stdout',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose',
    )

    (options, args) = parser.parse_args()

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)

    job_d = {
        'command': ' '.join(args),
        'start': options.start,
        'priority': options.priority,
    }

    queue = QueueWithSignal(db.job)
    job = queue.add_job(job_d)
    LOG.info("Created job id: %s", str(job.id))


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
