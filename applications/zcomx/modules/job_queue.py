#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
job_queue.py

Classes related to job queues.

"""
import datetime
import os
import pipes
import shlex
import signal
import subprocess
import sys
import time
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.utils import \
    ClassFactory, \
    default_record
from functools import reduce

LOG = current.app.logger


class DaemonSignalError(Exception):
    """Exception indicating and error occurred while signaling the daemon."""
    pass


class InvalidCLIOptionError(Exception):
    """Exception indicating an invalid cli option for job command."""
    pass


class InvalidJobOptionError(Exception):
    """Exception indicating an invalid option for the job."""
    pass


class InvalidStatusError(Exception):
    """Exception indicating an invalid status for a job."""
    pass


class QueueEmptyError(Exception):
    """Exception indicating the Queue is empty."""
    pass


class QueueLockedError(Exception):
    """Exception indicating the Queue is locked."""
    pass


class QueueLockedExtendedError(Exception):
    """Exception indicating the Queue is locked and has been locked for an
    extended period.
    """
    pass


class CLIOption(object):
    """Class representing a cli option for a job command."""
    def __init__(self, option, value=None):
        self.option = option
        self.value = value

    def __str__(self):
        """Return a string version of cli option."""
        if self.value is None:
            return ''

        if self.value is False:
            return ''

        if self.value is True:
            return self.option

        if isinstance(self.value, (list, tuple)):
            options = []
            for v in self.value:
                options.append('{opt} {val}'.format(
                    opt=self.option, val=pipes.quote(v)))
            return ' '.join(options)

        return '{opt} {val}'.format(
            opt=self.option, val=pipes.quote(str(self.value)))


class Daemon(object):
    """Class representing the job queue daemon"""

    def __init__(self, name, pid_filename=''):
        """Constructor

        Args:
            name: string, name of daemon
            pid_filename: string, full path name of file storing PID stats
                defaults to /tmp/{name}/pid
        """
        self.name = name
        self.pid_filename = pid_filename or '/tmp/{name}/pid'.format(
            name=self.name)

    def read_pid(self):
        """Read pid file and return contents.

        Returns:
            dict, dict of pid parameters,  {name1: value1, name2: value2}
        """
        params = {}
        with open(self.pid_filename, 'r') as f:
            for line in f:
                parts = line.rstrip().split(':', 1)
                if len(parts) > 1:
                    params[parts[0].strip()] = parts[1].strip()
                elif len(parts) == 1:
                    params[parts[0]] = ''
        return params

    def signal(self, interrupt=None):
        """Send signal to the daemon to wake it up for processing.

        Args:
            interrupt: What interrupt to raise, defaults to signal.SIGUSR1

        Raises:
            DaemonSignalError
        """
        if not interrupt:
            interrupt = signal.SIGUSR1
        try:
            pid_params = self.read_pid()
        except IOError as err:
            msg = 'Unable to read daemon file {f}: {err}'.format(
                f=self.pid_filename, err=err)
            raise DaemonSignalError(msg)
        if 'pid' not in pid_params or not pid_params['pid']:
            err = 'PID not found'
            msg = 'Unable to signal daemon {name}: {err}'.format(
                name=self.name, err=err)
            raise DaemonSignalError(msg)
        try:
            pid = int(pid_params['pid'])
        except (TypeError, ValueError) as err:
            msg = 'Unable to signal daemon {name}: Invalid pid {err}'.format(
                name=self.name, err=err)
            raise DaemonSignalError(msg)
        try:
            os.kill(pid, interrupt)
        except OSError as err:
            msg = 'Signal daemon {name} failed: {err}'.format(
                name=self.name, err=err)
            raise DaemonSignalError(msg)

    def update_pid(self):
        """Update pid file parameters."""
        params = self.read_pid()
        params['last'] = str(datetime.datetime.now())
        self.write_pid(params)

    def write_pid(self, params):
        """Write pid parameters to file.

        Args:
            dict, dict of pid parameters,  {name1: value1, name2: value2}
        """
        with open(self.pid_filename, 'w') as f:
            for k, v in list(params.items()):
                f.write("{k}: {v}\n".format(k=k, v=v))


class Job(Record):
    """Class representing a job database record."""
    db_table = 'job'


class IgnorableJob(Job):
    """Class representing an ignorable job."""

    def is_ignored(self, status='a', start_limit_seconds=600):
        """Determine if this job should be ignored.

        Args:
            status: str, other existing jobs of this status must exist to
                ignore.
        Returns:
            True if this job should be ignored.

        Logic:
            This job is ignored if there is another similar job queued.
            A similar job must match on:
                command
                priority
            The job must have a specific status (default 'a')
            The start time of the similar job must be on or after the start
            time of this job, and be within start_limit_seconds of this job
            (default: 10 minutes)
        """
        # pylint: disable=arguments-differ
        if not self.ignorable:
            return False

        db = current.app.db

        queries = []
        queries.append((db.job.id != self.id))      # Not this job
        queries.append((db.job.command == self.command))
        queries.append((db.job.priority == self.priority))

        queries.append((db.job.start >= self.start))
        start_limit = \
            self.start + datetime.timedelta(seconds=start_limit_seconds)
        queries.append((db.job.start < start_limit))

        if status:
            queries.append((db.job.status == status))

        query = reduce(lambda x, y: x & y, queries) if queries else None
        rows = db(query).select()
        if rows:
            return True
        return False


class JobHistory(Record):
    """Class representing a job_history database record."""
    db_table = 'job_history'


class JobQueuer(Record):
    """Class representing a job_queuer database record."""
    db_table = 'job_queuer'


class Queue(object):
    """Class representing a job queue."""

    job_statuses = {
        'a': {
            'label': 'queued',
            'css_class': 'status_queued',
        },
        'c': {
            'label': 'complete',
            'css_class': 'status_complete',
        },
        'd': {
            'label': 'FAIL',
            'css_class': 'status_fail',
        },
        'p': {
            'label': 'in progress',
            'css_class': 'status_in_progress',
        },
        'default': {
            'label': None,
            'css_class': 'status_default',
        },
    }

    lock_filename = '/var/run/job_queue.pid'

    def __init__(self, tbl, job_class=Job):
        """Constructor.

        Args:
            tbl: gluon.dal.Table of table jobs are stored in. Eg db.job
            job_class: class to use to create/access jobs with
        """
        self.tbl = tbl
        self.job_class = job_class
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        self.db = self.tbl._db

    def add_job(self, job_data):
        """Add job to queue.

        Args:
            job_data: dict representing job record

        Returns:
           Row instance representing job.
        """
        self.pre_add_job()
        data = default_record(self.tbl, ignore_fields='common')
        data.update(job_data)
        LOG.debug('job_data: %s', job_data)
        job = Job.from_add(data)
        if 'command' in job_data:
            LOG.debug('Queued command: %s', job_data['command'])
        self.post_add_job()
        return job

    def job_generator(self):
        """Generator of jobs returning the top job in queue.

        Yields:
            Job instance
        """
        while True:
            try:
                yield self.top_job()
            except QueueEmptyError:
                break

    def jobs(self, query=None, orderby=None, limitby=None):
        """Return the jobs in the queue.

        Args:
            query: gluon.dal.objects.Query instance used to filter jobs.
                Eg Return only pending jobs:
                    queue = Queue(db.job)
                    query = (queue.tbl.status == 'p')
                    print queue.jobs()
            orderby: list, tuple or string, cmp orderby attribute as per
                    gluon.sql.SQLSet._select()
                    Example: db.person.name
            limitby: integer or tuple. Tuple is format (start, stop). If
                    integer converted to tuple (0, integer)
        Returns:
            list, list of self.job_class instances.
        """
        if query is None:
            query = self.tbl
        if not limitby:
            limitby = None
        elif not hasattr(limitby, '__len__'):
            limitby = (0, int(limitby))         # Convert integer to tuple
        job_ids = self.db(query).select(
            self.db.job.id, orderby=orderby, limitby=limitby)
        return [self.job_class.from_id(x) for x in job_ids]

    def lock(self, filename=None, extended_seconds=0):
        """Lock the queue.

        Notes:
            Locking the queue involves creating a pid file.

        Args:
            filename: string, name of file including path used for locking.
                If not provided, the Queue.lock_filename class property is
                used.
            extended_seconds: integer, if not zero, and the queue is locked and
                the queue has been locked for more then this number of seconds,
                QueueLockedExtendedError is raised.
        Returns:
            String, name of file including path used for locking.

        Raises:
            QueueLockedError, if the queue is already locked.
            QueueLockedExtendedError, if the queue is already lock and has
                been for an extended period of time.
        """
        if not filename:
            filename = self.lock_filename

        if os.path.exists(filename):
            extended = False
            if extended_seconds > 0:
                now = time.mktime(time.localtime())
                statinfo = os.stat(filename)
                diff = now - statinfo.st_mtime
                if diff > extended_seconds:
                    extended = True
            msg = 'Queue is locked: {file}'.format(file=filename)
            if extended:
                raise QueueLockedExtendedError(msg)
            else:
                raise QueueLockedError(msg)

        with open(filename, 'w') as f:
            f.write(str(os.getpid()))
        return filename

    def post_add_job(self):
        """Post-processing after adding a job to queue.

        Override this method in a subclass and add any functionality desired.
        """
        pass

    def pre_add_job(self):
        """Pre-processing before adding a job to queue.

        Override this method in a subclass and add any functionality desired.
        """
        pass

    def run_job(self, job):
        """Run the job command.

        Args:
            job: Job instance.

        The command (job.command) is expected to be a python script with
        optional arguments and options. It is run as:
            $ python <command>
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        if not job.command:
            return
        if job.command.startswith('applications/'):
            # If the command starts with 'applications/' assume it is a web2py
            # script and run it with the web2py handler.
            args = [os.path.join(
                os.getcwd(),
                'applications/zcomx/private/bin/python_web2py.sh'
            )]
        else:
            # Otherwise assume the script is a python command.
            # For security purposes, general commands are not permitted.
            args = [sys.executable]
        args.extend(shlex.split(job.command))
        subprocess.check_output(args, stderr=subprocess.STDOUT)

    def set_job_status(self, job, status):
        """Set the status of a job in the queue.

        Args:
            job: Job instance
            status: string, one of Queue.job_statuses

        Returns:
            Job instance, updated versions
        """
        if status not in self.job_statuses:
            raise InvalidStatusError(
                'Invalid status: {s}'.format(s=status))
        job = Job.from_updated(job, dict(status=status))
        return job

    def stats(self):
        """Return queue stats.

        Returns:
            dict, {status1: count1, status2, count2...}
        """
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212

        db = self.db
        count = self.tbl.status.count()
        rows = db().select(
            count, self.tbl.status, groupby=self.tbl.status)
        return {r.job.status: r[count] for r in rows}

    def top_job(self):
        """Return the highest priority job in the queue.

        Returns:
            self.job_class instance. None, if no job found.
        """
        start = time.strftime('%F %T', time.localtime())    # now
        query = (self.tbl.status == 'a') & \
                (self.tbl.start <= start)
        orderby = ~self.tbl.priority
        top_jobs = self.jobs(query=query, orderby=orderby, limitby=1)
        if len(top_jobs) == 0:
            msg = 'There are no jobs in the queue.'
            raise QueueEmptyError(msg)
        return top_jobs[0]

    def unlock(self, filename=None):
        """Lock the queue.

        Notes:
            Unlocking the queue involves deleting the pid file.

        Args:
            filename: string, name of file including path used for locking.
                If not provided, the Queue.lock_filename class property is
                used.
        """
        if not filename:
            filename = self.lock_filename
        if os.path.exists(filename):
            os.unlink(filename)
        return


class Queuer(object):
    """Class representing a job queuer base class.

    A job queuer instance is used to queue jobs for a specific program,
    defined by the class program property, with the option of changing
    both the job parameters and the job command cli options.
    """
    class_factory = ClassFactory('class_factory_id')
    program = ''
    default_job_options = {'start': datetime.datetime.now(), 'status': 'a'}
    default_cli_options = {}
    valid_cli_options = []
    queue_class = None
    bin_path = 'applications/zcomx/private/bin'

    def __init__(
            self,
            tbl,
            job_options=None,
            cli_options=None,
            cli_args=None,
            delay_seconds=0):

        """Constructor

        Args:
            tbl: gluon.dal.Table of table jobs are stored in. Eg db.job
            job_options: dict, job record attributes
            cli_options: dict, options for command
            cli_args: list, arguments for command
            delay_seconds: integer, number of seconds to postpone start of job.
        """
        self.tbl = tbl
        self.job_options = job_options or {}
        self.cli_options = cli_options or {}
        self.cli_args = cli_args or []
        self.delay_seconds = delay_seconds
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        self.db = self.tbl._db
        if not self.queue_class:
            self.queue_class = Queue

    def command(self):
        """Return the command for the job to be queued."""
        # Validate cli options
        options = []
        cli_options = dict(self.default_cli_options)
        if self.cli_options:
            cli_options.update(self.cli_options)
        for k, v in sorted(cli_options.items()):
            if k not in self.valid_cli_options:
                raise InvalidCLIOptionError(
                    'Invalid cli option: {opt}'.format(opt=k))
            options.append(CLIOption(k, value=v))
        options_str = ' '.join([str(x) for x in options if str(x)])
        args_str = ' '.join([pipes.quote(x) for x in self.cli_args])
        return '{prg} {opts} {args}'.format(
            prg=self.program,
            opts=options_str,
            args=args_str
        ).strip().replace('  ', ' ')

    def job_data(self):
        """Return the data representing job to be queued.

        Returns:
            Storage: representing job (equivalent to db.job Row.as_dict())
        """
        db = current.app.db
        attributes = Storage(dict(self.default_job_options))
        if self.job_options:
            attributes.update(self.job_options)
        for k in sorted(attributes.keys()):
            if k not in self.tbl.fields:
                raise InvalidJobOptionError(
                    'Invalid job option: {opt}'.format(opt=k))
        now = datetime.datetime.now()

        job_queuer = None
        if self.class_factory_id:
            query = (db.job_queuer.code == self.class_factory_id)
            job_queuer = db(query).select().first()

        attributes['job_queuer_id'] = job_queuer.id if job_queuer else 0

        if 'command' not in attributes:
            attributes['command'] = self.command()
        if 'start' not in attributes:
            attributes['start'] = now
        if self.delay_seconds:
            attributes['start'] = attributes['start'] + \
                datetime.timedelta(seconds=self.delay_seconds)
        attributes['queued_time'] = now
        return attributes

    def queue(self):
        """Queue the job."""
        return self.queue_class(self.tbl).add_job(self.job_data())


class Requeuer(object):
    """Class representing a job requeuer. A requeuer queues a job
    repeatedly up to a maximum number of times.
    """

    def __init__(self, queuer, requeues=0, max_requeues=1):
        """Initializer

        Args:
            queuer: Queuer instance
            requeues: integer, the number of times the job has been requeued
            max_requeues: integer, the maximum number of times to requeue job

        """
        self.queuer = queuer
        self.requeues = requeues
        self.max_requeues = max_requeues

    def requeue(self):
        """Requeue the job.

        Args:
            self.assertRaises(exception, func, arguments)g

        Returns:
            Job instance representing job requeued.

        Raises:
            StopIteration if max_requeues reached.
        """
        if self.requeues >= self.max_requeues:
            msg = 'The maximum requeues, {m}, reached.'.format(
                m=self.max_requeues)
            raise StopIteration(msg)

        self.queuer.cli_options.update(self.requeue_cli_options())
        return self.queuer.queue()

    def requeue_cli_options(self):
        """Return dict of cli options on requeue."""

        return {
            '--requeues': self.requeues + 1,
            '--max-requeues': self.max_requeues,
        }
