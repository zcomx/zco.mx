#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_job.py

Queue a job.

"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import time
from optparse import OptionParser
import applications.zcomx.modules.job_queuers as job_queuers
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


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
        '-q', '--queuer',
        dest='queuer', default=None,
        help='Use queuer to queue job',
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

    set_cli_logging(LOG, options.verbose, options.vv)

    if not options.queuer and len(args) != 1:
        parser.print_help()
        exit(1)

    if options.queuer:
        try:
            queuer_class = getattr(job_queuers, options.queuer)
        except AttributeError as err:
            queuer_class = None
            LOG.error('Invalid queuer: %s', options.queuer)
            LOG.error(err)
            exit(1)
        if queuer_class:
            queuer = queuer_class(db.job)
            job = queuer.queue()
    else:
        job_d = {
            'command': ' '.join(args),
            'start': options.start,
            'priority': options.priority,
        }

        queue = job_queuers.QueueWithSignal(db.job)
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
