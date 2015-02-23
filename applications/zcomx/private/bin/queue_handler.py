#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_handler.py

Check queue and run any jobs found.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import logging
import subprocess
from optparse import OptionParser
from applications.zcomx.modules.job_queue import Queue

VERSION = 'Version 0.1'

# LOG = logging.getLogger('cli')
LOG = logging.getLogger('cli_w_time')


def main():
    """Main processing."""

    usage = '%prog [options]'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '-s', '--summary',
        action='store_true', dest='summary', default=False,
        help='Print summary of jobs checked to stdout',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='print messages to stdout',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose',
    )

    (options, unused_args) = parser.parse_args()

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]
    else:
        # Quiet all loggers so cron doesn't create noise in logs
        level = logging.WARNING
        unused_h = [h.setLevel(level) for h in LOG.handlers]

    stats = {
        'checked': 0,
        'error': 0,
        'success': 0,
    }

    queue = Queue(db.job)

    LOG.info("Checking queue for jobs.")
    for job in queue.job_generator():
        stats['checked'] += 1
        queue.set_job_status(job, 'p')        # In progress
        try:
            queue.run_job(job)
        except subprocess.CalledProcessError as err:
            # This command reveals location of log file:
            # $ grep -P '^LOG_FILE|^DAEMON' /etc/rc.d/igeejo_queued
            LOG.error("Job exited with error.")
            LOG.error("job: %s, exit: %s", job.command, err.returncode)
            for line in err.output.split("\n"):
                LOG.error(line)
            queue.set_job_status(job, 'd')        # Disabled
            stats['error'] += 1
        else:
            LOG.debug("job: %s, exit: %s", job.command, '0')
            queue.remove_job(job)
            stats['success'] += 1

    if options.summary:
        for k, v in sorted(stats.items()):
            print '{k}: {v}'.format(k=k, v=v)

    LOG.info("Done.")


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
