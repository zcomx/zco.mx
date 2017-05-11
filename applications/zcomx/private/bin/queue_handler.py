#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
queue_handler.py

Check queue and run any jobs found.
"""
# W0404: *Reimport %r (imported line %s)*
# pylint: disable=W0404
import subprocess
from optparse import OptionParser
from applications.zcomx.modules.job_queue import \
    IgnorableJob, \
    Queue
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


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

    set_cli_logging(LOG, options.verbose, options.vv, with_time=True)

    stats = {
        'checked': 0,
        'error': 0,
        'ignored': 0,
        'success': 0,
    }

    queue = Queue(db.job, job_class=IgnorableJob)

    LOG.info("Checking queue for jobs.")
    for job in queue.job_generator():
        stats['checked'] += 1

        if job.is_ignored():
            LOG.debug(
                "job: {job}, ignored exit: {exit}".format(
                    job=job.command, exit=0
                )
            )
            job.delete()
            stats['ignored'] += 1
            continue

        queue.set_job_status(job, 'p')        # In progress
        try:
            queue.run_job(job)
        except subprocess.CalledProcessError as err:
            LOG.error("Job exited with error.")
            LOG.error("job: %s, exit: %s", job.command, err.returncode)
            for line in err.output.split("\n"):
                LOG.error(line)
            queue.set_job_status(job, 'd')        # Disabled
            stats['error'] += 1
        else:
            LOG.debug("job: %s, exit: %s", job.command, '0')
            job.delete()
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
