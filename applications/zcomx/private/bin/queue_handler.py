#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue_handler.py

Check queue and run any jobs found.
"""
import argparse
import datetime
import sys
import traceback
from applications.zcomx.modules.job_queue import (
    IgnorableJob,
    JobHistory,
    JobRunFailedError,
    Queue,
)
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='queue_handler.py')

    parser.add_argument(
        '-s', '--summary',
        action='store_true', dest='summary', default=False,
        help='Print summary of jobs checked to stdout',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count', dest='verbose', default=False,
        help='Log debug messages',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    set_cli_logging(LOG, args.verbose)

    stats = {
        'checked': 0,
        'error': 0,
        'ignored': 0,
        'retried': 0,
        'success': 0,
    }

    queue = Queue(db.job, job_class=IgnorableJob)

    ignore_fields = ['id', 'created_on', 'updated_on']

    LOG.info("Checking queue for jobs.")
    for job in queue.job_generator():
        stats['checked'] += 1

        is_ignored = job.is_ignored()
        error = None

        start_now = datetime.datetime.now()
        data = dict(
            start_time=start_now,
            status='p',
        )
        if job.queued_time:
            data['wait_seconds'] = (start_now - job.queued_time).seconds

        job = IgnorableJob.from_updated(job, data)

        if not is_ignored:
            try:
                queue.run_job(job)
            except JobRunFailedError as err:
                error = err

        end_now = datetime.datetime.now()
        data = dict(
            end_time=end_now,
            ignored=is_ignored,
            status='d' if error else 'c',
        )
        if job.start_time:
            data['run_seconds'] = (end_now - job.start_time).seconds

        if error and job.retry_minutes:
            retry_minutes = job.retry_minutes[0]
            data['retry_minutes'] = job.retry_minutes[1:]
            data['start'] = datetime.datetime.now() \
                + datetime.timedelta(minutes=retry_minutes)
            data['status'] = 'a'
            job = IgnorableJob.from_updated(job, data)
            stats['retried'] += 1
            continue

        job = IgnorableJob.from_updated(job, data)

        # Set stats
        stats_status = 'ignored' if is_ignored else \
            'error' if error else 'success'
        stats[stats_status] += 1

        # Log
        if error:
            LOG.error("Job exited with error.")
        log_method = LOG.error if error else LOG.debug
        log_method(
            "job: {job}, {ignored} exit: {exit}".format(
                ignored='ignored' if is_ignored else '',
                job=job.command,
                exit=error.returncode if error else 0,
            )
        )
        if error:
            for line in error.output.split("\n"):
                LOG.error(line)

        # Move job to history
        job_history_data = {}
        for field in db.job.fields:
            if field in ignore_fields:
                continue
            job_history_data[field] = job[field]
        JobHistory.from_add(job_history_data)
        job.delete()

    if args.summary:
        for k, v in sorted(stats.items()):
            print('{k}: {v}'.format(k=k, v=v))

    LOG.info("Done.")


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
