#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
queue_job.py

Queue a job.
"""
import argparse
import sys
import time
import traceback
from pydal.helpers.methods import bar_decode_integer
from applications.zcomx.modules.argparse.actions import ManPageAction
from applications.zcomx.modules.job_queue import (
    Job,
    parse_cli_options,
)
import applications.zcomx.modules.job_queuers as job_queuers
from applications.zcomx.modules.logger import set_cli_logging

VERSION = 'Version 0.1'


def print_queuers():
    """Print a list of valid queuers."""
    print('')
    print('Queuers')
    print('=======')
    print('')
    jqd = job_queuers.__dict__
    queuers = sorted([
        k for k, v in jqd.items() if (
            isinstance(v, type) and
            v.__module__ == job_queuers.__name__
        )
    ])
    for queuer in queuers:
        print(queuer)


def man_page():
    """Print manual page-like help"""
    print("""
USAGE

    # Queue a job
    queue_job.py 'applications/zcomx/private/bin/purge_torrents -d'

    # Queue a job using a queuer.
    queue_job.py --queuer PurgeTorrentsQueuer


OPTIONS
    --cli-args ARGS
        Command line args for the queuer. Only applies with --queuer option.
        Combine multiple args in quotes. Eg --cli-args 'arg1 arg2 arg3'

    --cli-options OPTS
        Command line options for the queuer. Only applies with --queuer option.
        Combine multiple options or options with values in quotes.
        Eg --cli-options '-a -b 1 -vv'


    --version
        Print the script version.
    -h, --help
        Print a brief help.

    -l, --list-queuers
        Print a list of valid queuers that can be used with --queuer option,
        and exit.

    --man
        Print man page-like help.

    -p PRI, --priority=PRI
        The job created will be assigned priority PRI.
        Default: 0             (lowest priority possible)

    -q QUEUER, --queuer=QUEUER
        Create a job using queuer QUEUER. QUEUER should be a class defined
        in modules/job_queuers.py. Use --list-queuers option to list valid
        queuers.

    -r MINS, --retry-minutes=MINS
        The job created will be assigned retry_minutes MINS. Default: ''

    -s START, --start=START
        The job created will be assigned start START. Default: now

    -v, --verbose
        Print information messages to stdout.

    -vv,
        More verbose. Print debug messages to stdout.

    --version
        Print the script version.
    """)


def main():
    """Main processing."""

    parser = argparse.ArgumentParser(prog='queue_job.py')

    now = time.strftime('%F %T', time.localtime())

    parser.add_argument('command', nargs='*', default=[])

    parser.add_argument(
        '--cli-args',
        dest='cli_args', default='',
        help='Queuer command line args.',
    )
    parser.add_argument(
        '--cli-options',
        dest='cli_options', default='',
        help='Queuer command line options.',
    )
    parser.add_argument(
        '-l', '--list-queuers',
        action='store_true', dest='list_queuers', default=False,
        help='Print queuers and exit.',
    )
    parser.add_argument(
        '--man',
        action=ManPageAction, dest='man', default=False,
        callback=man_page,
        help='Display manual page-like help and exit.',
    )
    parser.add_argument(
        '-p', '--priority', type=int,
        dest='priority', default=0,
        help='job priority, default: 0',
    )
    parser.add_argument(
        '-q', '--queuer',
        dest='queuer', default=None,
        help='Use queuer to queue job',
    )
    parser.add_argument(
        '-r', '--retry-minutes',
        dest='retry_minutes', default='',
        help='job retry_minutes, default: ""',
    )
    parser.add_argument(
        '-s', '--start',
        dest='start', default=now,
        help='job start time, default: now',
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        dest='verbose',
        default=0,
        help='Log debug messages',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=VERSION,
        help='Print the script version'
    )

    args = parser.parse_args()

    if args.list_queuers:
        print_queuers()
        sys.exit(0)

    if not args.queuer and not args.command:
        parser.print_help()
        sys.exit(1)

    set_cli_logging(LOG, args.verbose)

    job_d = {
        'start': args.start,
        'priority': args.priority,
        'queued_time': now,
        'status': 'a',
    }
    if args.retry_minutes:
        job_d['retry_minutes'] = bar_decode_integer(args.retry_minutes)

    if not args.queuer:
        job_d['command'] = ' '.join(args.command)

    if args.queuer:
        try:
            queuer_class = getattr(job_queuers, args.queuer)
        except AttributeError as err:
            queuer_class = None
            LOG.error('Invalid queuer: %s', args.queuer)
            LOG.error(err)
            sys.exit(1)
        if queuer_class:
            cli_args = args.cli_args.split() if args.cli_args else None
            cli_options = parse_cli_options(args.cli_options)
            queuer = queuer_class(
                db.job,
                cli_args=cli_args,
                cli_options=cli_options,
            )
            queuer.default_job_options.update(job_d)
            job = queuer.queue()
    else:
        job = Job(db.job, **job_d)
        queue = job_queuers.QueueWithSignal(db.job)
        job = queue.add_job(job)

    LOG.info("Created job id: {id}".format(id=job.id))


if __name__ == '__main__':
    # pylint: disable=broad-except
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
