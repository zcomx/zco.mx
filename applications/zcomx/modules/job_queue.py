#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
job_queue.py

Classes related to job queues.

"""
import datetime
import logging
import os
import pipes
import shlex
import signal
import subprocess
import sys
import time
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.utils import \
    NotFoundError, \
    default_record, \
    entity_to_row


DAEMON_NAME = 'zco_queued'
PRIORITIES = list(reversed([
    # Highest
    'optimize_cbz_img_for_release',
    'optimize_img_for_release',
    'create_cbz',
    'create_book_torrent',
    'post_book_completed',
    'release_book',
    'optimize_cbz_img',
    'optimize_img',
    'update_creator_indicia',
    'optimize_web_img',
    'create_creator_torrent',
    'create_all_torrent',
    'notify_p2p_networks',
    'reverse_release_book',
    'delete_book',
    'delete_img',
    'log_downloads',
    'optimize_original_img',
    'purge_torrents',
    # Lowest
]))


LOG = logging.getLogger('app')


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

        if hasattr(self.value, '__iter__'):
            # Assume list
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
            for k, v in params.items():
                f.write("{k}: {v}\n".format(k=k, v=v))


class JobQueuer(object):
    """Class representing a job queuer base class.

    A job queuer instance is used to queue jobs for a specific program,
    defined by the class program property, with the option of changing
    both the job parameters and the job command cli options.
    """
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
        attributes = Storage(dict(self.default_job_options))
        if self.job_options:
            attributes.update(self.job_options)
        for k in sorted(attributes.keys()):
            if k not in self.tbl.fields:
                raise InvalidJobOptionError(
                    'Invalid job option: {opt}'.format(opt=k))
        if 'command' not in attributes:
            attributes['command'] = self.command()
        if 'start' not in attributes:
            attributes['start'] = datetime.datetime.now()
        if self.delay_seconds:
            attributes['start'] = attributes['start'] + \
                datetime.timedelta(seconds=self.delay_seconds)
        return attributes

    def queue(self):
        """Queue the job."""
        return self.queue_class(self.tbl).add_job(self.job_data())


class Queue(object):
    """Class representing a job queue."""
    job_statuses = {
        'a': 'Active',
        'd': 'Disabled',
        'p': 'In Progress',
    }

    lock_filename = '/var/run/job_queue.pid'

    def __init__(self, tbl):
        """Constructor.

        Args:
            tbl: gluon.dal.Table of table jobs are stored in. Eg db.job
        """
        self.tbl = tbl
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
        job_id = self.tbl.insert(**data)
        self.db.commit()
        if 'command' in job_data:
            LOG.debug('Queued command: %s', job_data['command'])
        self.post_add_job()
        return entity_to_row(self.tbl, job_id)

    def job_generator(self):
        """Generator of jobs returning the top job in queue."""
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
            list, list of Job object instances.
        """
        if query is None:
            query = self.tbl
        if not limitby:
            limitby = None
        elif not hasattr(limitby, '__len__'):
            limitby = (0, int(limitby))         # Convert integer to tuple
        return self.db(query).select(orderby=orderby, limitby=limitby)

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

    def run_job(self, job_entity):
        """Run the job command.

        The command is expected to be a python script with optional arguments
        and options. It is run as:
            $ python <command>
        """
        # E1101: *%s %r has no %r member*
        # pylint: disable=E1101
        job_record = entity_to_row(self.tbl, job_entity)
        if not job_record:
            raise NotFoundError('Job not found: {j}'.format(j=job_entity))
        if not job_record.command:
            return
        if job_record.command.startswith('applications/'):
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
        args.extend(shlex.split(job_record.command))
        subprocess.check_output(args, stderr=subprocess.STDOUT)

    def remove_job(self, job_entity):
        """Remove a job from the the queue.

        Args:
            job_entity: Row instance or integer representing a job record.
        """
        job_record = entity_to_row(self.tbl, job_entity)
        if not job_record:
            raise NotFoundError('Job not found: {j}'.format(j=job_entity))
        job_record.delete_record()
        self.db.commit()

    def set_job_status(self, job_entity, status):
        """Set the status of a job in the queue.

        Args:
            job_entity: Row instance or integer representing a job record.
            status: string, one of Queue.job_statuses

        """
        job_record = entity_to_row(self.tbl, job_entity)
        if not job_record:
            raise NotFoundError('Job not found: {j}'.format(j=job_entity))
        if status not in self.job_statuses:
            raise InvalidStatusError(
                'Invalid status: {s}'.format(s=status))
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        job_record.update_record(status=status)
        self.tbl._db.commit()

    def stats(self):
        """Return queue stats.

        Returns:
            dict, {status1: count1, status2, count2...}
        """
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212

        db = self.db
        _count = self.tbl.status.count()
        rows = db().select(
            _count, self.tbl.status, groupby=self.tbl.status)
        return {r.job.status: r[_count] for r in rows}

    def top_job(self):
        """Return the highest priority job in the queue.

        Returns:
            Row instance representing a job record. None, if no job found.
        """
        start = time.strftime('%F %T', time.localtime())    # now
        query = (self.tbl.status == 'a') & \
                (self.tbl.start <= start)
        orderby = ~self.tbl.priority
        top_jobs = self.jobs(query=query, orderby=orderby, limitby=1)
        if len(top_jobs) == 0:
            msg = 'There are no jobs in the queue.'
            raise QueueEmptyError(msg)
        return top_jobs.first()

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


class QueueWithSignal(Queue):
    """Class representing a job queue."""

    def __init__(self, tbl):
        """Constructor.

        Args:
            tbl: gluon.dal.Table of table jobs are stored in.
        """
        self.tbl = tbl
        Queue.__init__(self, tbl)

    def post_add_job(self):
        """Post-processing after adding a job to queue. """
        daemon = Daemon(DAEMON_NAME)
        try:
            daemon.signal()
        except DaemonSignalError as err:
            LOG.error(err)


class CreateCBZQueuer(JobQueuer):
    """Class representing a queuer for create_cbz jobs."""
    program = os.path.join(JobQueuer.bin_path, 'create_cbz.py')
    default_job_options = {
        'priority': PRIORITIES.index('create_cbz'),
        'status': 'a',
    }
    valid_cli_options = [
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class CreateTorrentQueuer(JobQueuer):
    """Class representing a queuer for create torrent jobs."""
    program = os.path.join(JobQueuer.bin_path, 'create_torrent.py')
    default_job_options = {
        'priority': PRIORITIES.index('create_book_torrent'),
        'status': 'a',
    }
    valid_cli_options = [
        '-a', '--all',
        '-c', '--creator',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class CreateAllTorrentQueuer(CreateTorrentQueuer):
    """Class representing a queuer for create_all_torrent jobs."""
    default_job_options = dict(CreateTorrentQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index('create_all_torrent')
    default_cli_options = {'--all': True}
    valid_cli_options = [
        '-a', '--all',
        '-v', '--vv',
    ]


class CreateBookTorrentQueuer(CreateTorrentQueuer):
    """Class representing a queuer for create_book_torrent jobs."""
    valid_cli_options = [
        '-v', '--vv',
    ]


class CreateCreatorTorrentQueuer(CreateTorrentQueuer):
    """Class representing a queuer for create_creator_torrent jobs."""
    default_job_options = dict(CreateTorrentQueuer.default_job_options)
    default_job_options['priority'] = \
        PRIORITIES.index('create_creator_torrent')
    default_cli_options = {'--creator': True}
    valid_cli_options = [
        '-c', '--creator',
        '-v', '--vv',
    ]


class DeleteBookQueuer(JobQueuer):
    """Class representing a queuer for delete_book jobs."""
    program = os.path.join(JobQueuer.bin_path, 'delete_book.py')
    default_job_options = {
        'priority': PRIORITIES.index('delete_book'),
        'status': 'a',
    }
    valid_cli_options = [
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class LogDownloadsQueuer(JobQueuer):
    """Class representing a queuer for 'log downloads' jobs."""
    program = os.path.join(JobQueuer.bin_path, 'log_downloads.py')
    default_job_options = {
        'priority': PRIORITIES.index('log_downloads'),
        'status': 'a',
    }
    valid_cli_options = [
        '-l', '--limit',
        '-r', '--requeue',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class NotifyP2PQueuer(JobQueuer):
    """Class representing a queuer for notify p2p network jobs."""
    program = os.path.join(JobQueuer.bin_path, 'notify_p2p_networks.py')
    default_job_options = {
        'priority': PRIORITIES.index('notify_p2p_networks'),
        'status': 'a',
    }
    valid_cli_options = [
        '-d', '--delete',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class OptimizeImgQueuer(JobQueuer):
    """Class representing a queuer for optimize_img jobs."""
    program = os.path.join(JobQueuer.bin_path, 'process_img.py')
    default_job_options = {
        'priority': PRIORITIES.index('optimize_img'),
        'status': 'a',
    }
    valid_cli_options = [
        '-f', '--force',
        '-s', '--size',
        '-u', '--uploads-path',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class DeleteImgQueuer(OptimizeImgQueuer):
    """Class representing a queuer for deleting an image jobs."""
    default_job_options = dict(OptimizeImgQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index('delete_img')
    default_cli_options = {'--delete': True}
    valid_cli_options = list(OptimizeImgQueuer.valid_cli_options)
    valid_cli_options.append('-d')
    valid_cli_options.append('--delete')


class OptimizeCBZImgQueuer(OptimizeImgQueuer):
    """Class representing a queuer for optimizing cbz images."""
    default_job_options = dict(OptimizeImgQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index(
        'optimize_cbz_img')
    default_cli_options = {'--size': 'cbz'}


class OptimizeOriginalImgQueuer(OptimizeImgQueuer):
    """Class representing a queuer for optimizing original images."""
    default_job_options = dict(OptimizeImgQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index(
        'optimize_original_img')
    default_cli_options = {'--size': 'original'}


class OptimizeWebImgQueuer(OptimizeImgQueuer):
    """Class representing a queuer for optimizing web images."""
    default_job_options = dict(OptimizeImgQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index(
        'optimize_web_img')
    default_cli_options = {'--size': 'web'}


class OptimizeCBZImgForReleaseQueuer(OptimizeImgQueuer):
    """Class representing a queuer for optimizing cbz images for release."""
    default_job_options = dict(OptimizeImgQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index(
        'optimize_cbz_img_for_release')
    default_cli_options = {'--size': 'cbz'}


class PostOnSocialMediaQueuer(JobQueuer):
    """Class representing a queuer for post_book_completed on social_media jobs."""
    program = os.path.join(JobQueuer.bin_path, 'social_media', 'post_book_completed.py')
    default_job_options = {
        'priority': PRIORITIES.index('post_book_completed'),
        'status': 'a',
    }
    valid_cli_options = [
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class PurgeTorrentsQueuer(JobQueuer):
    """Class representing a queuer for purge_torrent jobs."""
    program = os.path.join(JobQueuer.bin_path, 'purge_torrents.py')
    default_job_options = {
        'priority': PRIORITIES.index('purge_torrents'),
        'status': 'a',
    }
    valid_cli_options = [
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class ReleaseBookQueuer(JobQueuer):
    """Class representing a queuer for release_book jobs."""
    program = os.path.join(JobQueuer.bin_path, 'release_book.py')
    default_job_options = {
        'priority': PRIORITIES.index('release_book'),
        'status': 'a',
    }
    valid_cli_options = [
        '-m', '--max-requeues',
        '-r', '--requeues',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class ReverseReleaseBookQueuer(ReleaseBookQueuer):
    """Class representing a queuer for reversing release_book jobs."""
    program = os.path.join(JobQueuer.bin_path, 'release_book.py')
    default_job_options = dict(ReleaseBookQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index('reverse_release_book')
    default_cli_options = {'--reverse': True}
    valid_cli_options = list(ReleaseBookQueuer.valid_cli_options)
    valid_cli_options.append('--reverse')


class UpdateIndiciaQueuer(JobQueuer):
    """Class representing a queuer for update_creator_indicia jobs."""
    program = os.path.join(JobQueuer.bin_path, 'update_creator_indicia.py')
    default_job_options = {
        'priority': PRIORITIES.index('update_creator_indicia'),
        'status': 'a',
    }
    default_cli_options = {'-o': True, '-r': True}
    valid_cli_options = [
        '-c', '--clear',
        '-o', '--optimize',
        '-r', '--resize',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal
