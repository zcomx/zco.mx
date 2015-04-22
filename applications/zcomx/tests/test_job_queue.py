#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_job_queue.py

Test suite for shared/modules/job_queue.py

"""
import datetime
import os
import subprocess
import time
import unittest
from applications.zcomx.modules.job_queue import \
    CLIOption, \
    CreateAllTorrentQueuer, \
    CreateBookTorrentQueuer, \
    CreateCBZQueuer, \
    CreateCreatorTorrentQueuer, \
    CreateTorrentQueuer, \
    Daemon, \
    DaemonSignalError, \
    DeleteBookQueuer, \
    DeleteImgQueuer, \
    InvalidCLIOptionError, \
    InvalidJobOptionError, \
    InvalidStatusError, \
    JobQueuer, \
    LogDownloadsQueuer, \
    NotifyP2PQueuer, \
    OptimizeCBZImgForReleaseQueuer, \
    OptimizeCBZImgQueuer, \
    OptimizeImgQueuer, \
    OptimizeOriginalImgQueuer, \
    OptimizeWebImgQueuer, \
    PostOnSocialMediaQueuer, \
    PRIORITIES, \
    Queue, \
    QueueEmptyError, \
    QueueLockedError, \
    QueueLockedExtendedError, \
    QueueWithSignal, \
    ReleaseBookQueuer, \
    ReverseReleaseBookQueuer, \
    UpdateIndiciaQueuer
from applications.zcomx.modules.tests.runner import \
    LocalTestCase, \
    TableTracker
from applications.zcomx.modules.utils import \
    NotFoundError


# C0111: *Missing docstring*
# R0904: *Too many public methods (%s/%s)*
# pylint: disable=C0111,R0904

TMP_DIR = '/tmp/test_suite/job_queue'

if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)


class SubJobQueuer(JobQueuer):
    """Sub class of JobQueuer used for testing."""

    program = 'some_program.py'
    default_job_options = {
        'priority': 1,
        'status': 'd'
    }
    default_cli_options = {
        '-a': False,
        '-b': True,
        '-c': 'ccc',
        '-d': ['d1', 'd2']
    }
    valid_cli_options = ['-a', '-b', '-c', '-d', '-e']
    queue_class = Queue

    def __init__(
            self,
            tbl,
            job_options=None,
            cli_options=None,
            cli_args=None,
            delay_seconds=0):

        JobQueuer.__init__(
            self,
            tbl,
            job_options=job_options,
            cli_options=cli_options,
            cli_args=cli_args,
            delay_seconds=delay_seconds
        )


class TestCLIOption(LocalTestCase):

    def test____init__(self):
        cli_option = CLIOption('-a')
        self.assertTrue(cli_option)

    def test____str__(self):
        tests = [
            # (option, value, expect)
            ('-a', None, ''),
            ('-a', False, ''),
            ('-a', True, '-a'),
            ('--action', True, '--action'),
            ('-a', 'list', '-a list'),
            ('-a', 111, '-a 111'),
            ('-a', ['opt1'], '-a opt1'),
            ('-a', ['opt1', 'opt2'], '-a opt1 -a opt2'),
            (
                '-a', """my "list" of 'items'""",
                '-a \'my "list" of \'"\'"\'items\'"\'"\'\''
            ),
            (
                '-a', ["""a'b"c""", """d"e'f"""],
                '-a \'a\'"\'"\'b"c\' -a \'d"e\'"\'"\'f\''
            ),
        ]
        for t in tests:
            cli_option = CLIOption(t[0], value=t[1])
            self.assertEqual(str(cli_option), t[2])


class TestCreateAllTorrentQueuer(LocalTestCase):

    def test_queue(self):
        queuer = CreateAllTorrentQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-v': True},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/create_torrent.py --all -v'
        )

        queuer.cli_options.update({'--creator': True})
        self.assertRaises(InvalidCLIOptionError, queuer.queue)


class TestCreateBookTorrentQueuer(LocalTestCase):

    def test_queue(self):
        queuer = CreateBookTorrentQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-v': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/create_torrent.py -v 123'
        )

        queuer.cli_options = {'--creator': True}
        self.assertRaises(InvalidCLIOptionError, queuer.queue)

        queuer.cli_options = {'--all': True}
        self.assertRaises(InvalidCLIOptionError, queuer.queue)


class TestCreateCBZQueuer(LocalTestCase):

    def test_queue(self):
        queuer = CreateCBZQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-v': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/create_cbz.py -v 123'
        )


class TestCreateCreatorTorrentQueuer(LocalTestCase):

    def test_queue(self):
        queuer = CreateCreatorTorrentQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-v': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/create_torrent.py --creator -v 123'
        )

        queuer.cli_options.update({'--all': True})
        self.assertRaises(InvalidCLIOptionError, queuer.queue)


class TestCreateTorrentQueuer(LocalTestCase):

    def test_queue(self):
        queuer = CreateTorrentQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--all': True, '-v': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/create_torrent.py --all -v 123'
        )


class TestDaemon(LocalTestCase):
    name = 'igeejo_queued'
    pid_filename = '/tmp/test_suite/job_queue/pid'

    def test____init__(self):
        daemon = Daemon(self.name)
        self.assertEqual(daemon.pid_filename, '/tmp/igeejo_queued/pid')

        daemon = Daemon(self.name, pid_filename='/tmp/testing')
        self.assertEqual(daemon.pid_filename, '/tmp/testing')

    def test__read_pid(self):
        daemon = Daemon(self.name, self.pid_filename)

        open(self.pid_filename, 'w').close()        # Empty file
        self.assertEqual(daemon.read_pid(), {})

        with open(self.pid_filename, 'w') as f:
            f.write("a: 1\n")
            f.write("first name: John\n")
            f.write("start time: 2000-01-01 12:59:59\n")
            f.write("nada: \n")
            f.write("empty:\n")

        self.assertEqual(daemon.read_pid(), {
            'a': '1',
            'first name': 'John',
            'start time': '2000-01-01 12:59:59',
            'nada': '',
            'empty': '',
        })

    def test__signal(self):
        daemon = Daemon(self.name, self.pid_filename)
        self.assertRaises(DaemonSignalError, daemon.signal)

        # The details of the method are not easily tested. The method issues
        # an os.kill() command and not recommend to run.

    def test__update_pid(self):
        daemon = Daemon(self.name, self.pid_filename)
        open(self.pid_filename, 'w').close()            # Empty file
        daemon.update_pid()
        params = daemon.read_pid()
        self.assertEqual(params.keys(), ['last'])

        data = {
            'pid': '1234',
            'start': '2003-03-03 03:30:33',
            'last': '',
        }

        daemon.write_pid(data)
        daemon.update_pid()
        params = daemon.read_pid()
        self.assertEqual(sorted(params.keys()), ['last', 'pid', 'start'])
        self.assertEqual(params['pid'], data['pid'])
        self.assertEqual(params['start'], data['start'])
        self.assertNotEqual(params['last'], data['last'])

    def test__write_pid(self):
        daemon = Daemon(self.name, self.pid_filename)
        params = {}
        daemon.write_pid(params)
        self.assertEqual(daemon.read_pid(), {})

        params = {
            'b': '2',
            'last name': 'Smith',
            'start time': '2002-02-02 13:58:58',
            'nothing': '',
            'empty_str': '',
        }

        daemon.write_pid(params)
        self.assertEqual(daemon.read_pid(), params)


class TestDeleteBookQueuer(LocalTestCase):

    def test_queue(self):
        queuer = DeleteBookQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--vv': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/delete_book.py --vv 123'
        )


class TestDeleteImgQueuer(LocalTestCase):

    def test_queue(self):
        queuer = DeleteImgQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-f': True},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py --delete -f'
        )


class TestJobQueuer(LocalTestCase):

    def test____init__(self):
        queuer = JobQueuer(db.job)
        self.assertTrue(queuer)
        self.assertEqual(queuer.queue_class, Queue)
        self.assertEqual(JobQueuer.bin_path, 'applications/zcomx/private/bin')

    def test__command(self):
        queuer = SubJobQueuer(db.job)
        self.assertEqual(
            queuer.command(), 'some_program.py -b -c ccc -d d1 -d d2')

        queuer = SubJobQueuer(db.job, cli_args=['file', 'arg2'])
        self.assertEqual(
            queuer.command(),
            'some_program.py -b -c ccc -d d1 -d d2 file arg2'
        )

        # Disable defaults
        queuer = SubJobQueuer(
            db.job,
            cli_options={
                '-a': False,
                '-b': False,
                '-c': False,
                '-d': False,
            },
            cli_args=['file']
        )
        self.assertEqual(queuer.command(), 'some_program.py file')

        invalid_cli_options = {'-x': 'invalid'}
        queuer = SubJobQueuer(db.job, cli_options=invalid_cli_options)
        self.assertRaises(InvalidCLIOptionError, queuer.command)

        # Handle quotes
        queuer = SubJobQueuer(
            db.job,
            cli_options={
                '-a': False,
                '-b': False,
                '-c': False,
                '-d': False,
                '-e': """A 'B' "C" D""",
            },
            cli_args=['file'],
        )
        self.assertEqual(
            queuer.command(),
            'some_program.py -e \'A \'"\'"\'B\'"\'"\' "C" D\' file'
        )

        queuer = SubJobQueuer(
            db.job,
            cli_options={
                '-a': False,
                '-b': False,
                '-c': False,
            },
            cli_args=["""A 'B' "C" D"""],
        )
        self.assertEqual(
            queuer.command(),
            'some_program.py -d d1 -d d2 \'A \'"\'"\'B\'"\'"\' "C" D\''
        )

    def test__job_data(self):
        then = datetime.datetime.now()
        data = SubJobQueuer(db.job).job_data()
        self.assertEqual(data.status, 'd')
        self.assertEqual(data.priority, 1)
        self.assertEqual(
            data.command,
            'some_program.py -b -c ccc -d d1 -d d2'
        )
        self.assertTrue(data.start >= then)
        diff = data.start - then
        self.assertTrue(diff.total_seconds() >= 0)
        self.assertTrue(diff.total_seconds() < 1)

        invalid_job_options = {'fake_field': 'value'}
        queuer = SubJobQueuer(db.job, job_options=invalid_job_options)
        self.assertRaises(InvalidJobOptionError, queuer.job_data)

        # Test delay_seconds
        then = datetime.datetime.now()
        data = SubJobQueuer(db.job, delay_seconds=100).job_data()
        self.assertTrue(data.start > then)
        diff = data.start - then
        self.assertTrue(diff.total_seconds() >= 100)
        self.assertTrue(diff.total_seconds() < 101)

    def test__queue(self):
        def get_job_ids():
            return sorted([x.id for x in db(db.job).select(db.job.id)])

        job_ids = get_job_ids()

        queuer = SubJobQueuer(db.job)
        new_job = queuer.queue()
        self.assertEqual(
            new_job.command, 'some_program.py -b -c ccc -d d1 -d d2')
        self.assertTrue(new_job.id not in job_ids)
        job_ids = get_job_ids()
        self.assertTrue(new_job.id in job_ids)
        job = db(db.job.id == new_job.id).select().first()
        self._objects.append(job)


class TestLogDownloadsQueuer(LocalTestCase):

    def test_queue(self):
        queuer = LogDownloadsQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-r': True, '-l': '10'},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/log_downloads.py -l 10 -r'
        )


class TestNotifyP2PQueuer(LocalTestCase):

    def test_queue(self):
        queuer = NotifyP2PQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-d': True},
            cli_args=['path/to/file.cbz'],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/notify_p2p_networks.py -d path/to/file.cbz'
        )


class TestOptimizeCBZImgQueuer(LocalTestCase):

    def test_queue(self):
        queuer = OptimizeCBZImgQueuer(
            db.job,
            job_options={'status': 'd'},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.priority,
            PRIORITIES.index('optimize_cbz_img')
        )
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py --size cbz'
        )


class TestOptimizeCBZImgForReleaseQueuer(LocalTestCase):

    def test_queue(self):
        queuer = OptimizeCBZImgForReleaseQueuer(
            db.job,
            job_options={'status': 'd'},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.priority,
            PRIORITIES.index('optimize_cbz_img_for_release')
        )
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py --size cbz'
        )


class TestOptimizeImgQueuer(LocalTestCase):

    def test_queue(self):
        queuer = OptimizeImgQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-f': True},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py -f'
        )


class TestOptimizeOriginalImgQueuer(LocalTestCase):

    def test_queue(self):
        queuer = OptimizeOriginalImgQueuer(
            db.job,
            job_options={'status': 'd'},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.priority,
            PRIORITIES.index('optimize_original_img')
        )
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py --size original'
        )


class TestOptimizeWebImgQueuer(LocalTestCase):

    def test_queue(self):
        queuer = OptimizeWebImgQueuer(
            db.job,
            job_options={'status': 'd'},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.priority,
            PRIORITIES.index('optimize_web_img')
        )
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/process_img.py --size web'
        )


class TestPostOnSocialMediaQueuer(LocalTestCase):

    def test_queue(self):
        queuer = PostOnSocialMediaQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--vv': True},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/post_on_social_media.py --vv 123'
        )


class TestQueue(LocalTestCase):

    @classmethod
    def clear_queue(cls):
        db(db.job.id > 0).delete()
        db.commit()

    def test____init__(self):
        queue = Queue(db.job)
        self.assertTrue(queue)

    def test__add_job(self):
        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        job_data = dict(command='pwd')
        ret = queue.add_job(job_data)
        self._objects.append(ret)
        self.assertEqual(ret.command, job_data['command'])
        self.assertTrue(ret.id > 0)

        self.assertEqual(len(queue.jobs()), 1)

        # Test pre- and post- processiong.
        class MyQueue(Queue):
            """Queue subclass for testing"""
            def __init__(self, tbl):
                Queue.__init__(self, tbl)
                self.trace = []

            def pre_add_job(self):
                """Test override."""
                self.trace.append('pre')

            def post_add_job(self):
                """Test override."""
                self.trace.append('post')

        queue = MyQueue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        ret = queue.add_job(job_data)
        self._objects.append(ret)
        self.assertTrue(ret.id > 0)
        self.assertEqual(queue.trace, ['pre', 'post'])

    def test__job_generator(self):
        queue = Queue(db.job)

        gen = queue.job_generator()
        # No jobs
        self.assertRaises(StopIteration, gen.next)

        job_data = [
            # (command, start, priority, status)
            ('do_a', '2010-01-01 10:00:00', 1, 'a'),
            ('do_b', '2010-01-01 10:00:00', 5, 'a'),
            ('do_c', '2010-01-01 10:00:00', 9, 'a'),
        ]

        job_ids = []
        for j in job_data:
            job = queue.add_job(
                dict(command=j[0], start=j[1], priority=j[2], status=j[3])
            )
            job_ids.append(job.id)

        gen = queue.job_generator()
        job = gen.next()
        self.assertEqual(job.command, 'do_c')
        queue.remove_job(job_ids[2])
        job = gen.next()
        self.assertEqual(job.command, 'do_b')
        queue.remove_job(job_ids[1])
        job = gen.next()
        self.assertEqual(job.command, 'do_a')
        queue.remove_job(job_ids[0])
        self.assertRaises(StopIteration, gen.next)

        for i in job_ids:
            try:
                queue.remove_job(i)
            except NotFoundError:
                pass
        self.assertEqual(queue.stats(), {})

    def test__jobs(self):
        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        job_data = [
            # (number, start, priority, status)
            # Do not use status='a' or status='p' or jobs will be run.
            ('2010-01-01 10:00:00', 0, 'z'),
            ('2010-01-01 10:00:00', 0, 'd'),
            ('2010-01-01 10:00:01', -1, 'z'),
            ('2010-01-01 10:00:01', -1, 'd'),
            ('2010-01-01 10:00:02', 1, 'z'),
            ('2010-01-01 10:00:02', 1, 'd'),
        ]

        job_ids = []
        for j in job_data:
            job_d = dict(command='pwd', start=j[0], priority=j[1], status=j[2])
            job_id = db.job.insert(**job_d)
            job_ids.append(job_id)
        db.commit()

        job_set = queue.jobs()
        self.assertEqual(len(job_set), 6)
        self.assertEqual(
            [x.id for x in job_set],
            job_ids,
        )

        # Test query
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            [x.id for x in job_set],
            [job_ids[0].id, job_ids[2].id, job_ids[4].id]
        )

        query = (db.job.status == 'd') & \
                (db.job.start <= '2010-01-01 10:00:01')
        job_set = queue.jobs(query=query)
        self.assertEqual(len(job_set), 2)
        self.assertEqual(
            [x.id for x in job_set],
            [job_ids[1].id, job_ids[3].id]
        )

        # Test orderby
        # Orderby priority ASC
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=db.job.priority)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            [x.id for x in job_set],
            [job_ids[2].id, job_ids[0].id, job_ids[4].id]
        )

        # Orderby priority DESC
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=~db.job.priority)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            [x.id for x in job_set],
            [job_ids[4].id, job_ids[0].id, job_ids[2].id]
        )

        # Test limitby
        # Highest priority job
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=~db.job.priority, limitby=1)
        self.assertEqual(len(job_set), 1)
        self.assertEqual([x.id for x in job_set], [job_ids[4].id])

    def test__lock(self):
        queue = Queue(db.job)

        # Test lock using default lock file. This test only works if the queue
        # is not currently locked by an outside program.
        if os.path.exists(queue.lock_filename):
            os.unlink(queue.lock_filename)
        self.assertFalse(os.path.exists(queue.lock_filename))
        queue.lock()
        self.assertTrue(os.path.exists(queue.lock_filename))
        queue.unlock()
        self.assertFalse(os.path.exists(queue.lock_filename))

        # Test lock with custom filename.
        lock_file = os.path.join(TMP_DIR, 'test__lock.pid')
        if os.path.exists(lock_file):
            os.unlink(lock_file)
        self.assertFalse(os.path.exists(lock_file))
        queue.lock(filename=lock_file)
        self.assertTrue(os.path.exists(lock_file))

        # Test raise QueueLockedError
        self.assertRaises(QueueLockedError, queue.lock, filename=lock_file)
        # Test raise QueueLockedExtendedError
        time.sleep(2)
        # Lock period < extended seconds, raises QueueLockedError
        self.assertRaises(
            QueueLockedError,
            queue.lock,
            filename=lock_file,
            extended_seconds=9999
        )
        # Lock period > extended seconds, raises QueueLockedExtendedError
        self.assertRaises(
            QueueLockedExtendedError,
            queue.lock,
            filename=lock_file,
            extended_seconds=1
        )
        queue.unlock(filename=lock_file)
        self.assertFalse(os.path.exists(lock_file))

    def test__post_add_job(self):
        # See test__add_job
        pass

    def test__pre_add_job(self):
        # See test__add_job
        pass

    def test__remove_job(self):

        queue = Queue(db.job)
        tracker = TableTracker(db.job)

        job_1 = queue.add_job({'command': '_fake_1_'})
        self._objects.append(job_1)
        job_2 = queue.add_job({'command': '_fake_2_'})
        self._objects.append(job_2)
        job_3 = queue.add_job({'command': '_fake_3_'})
        self._objects.append(job_3)

        self.assertFalse(tracker.had(job_1))
        self.assertFalse(tracker.had(job_2))
        self.assertFalse(tracker.had(job_3))
        self.assertTrue(tracker.has(job_1))
        self.assertTrue(tracker.has(job_2))
        self.assertTrue(tracker.has(job_3))
        queue.remove_job(job_2)
        self.assertTrue(tracker.has(job_1))
        self.assertFalse(tracker.has(job_2))
        self.assertTrue(tracker.has(job_3))

        queue.remove_job(job_1)
        queue.remove_job(job_3)
        self.assertFalse(tracker.has(job_1))
        self.assertFalse(tracker.has(job_2))
        self.assertFalse(tracker.has(job_3))

        # Test remove of non-existent record
        self.assertRaises(NotFoundError, queue.remove_job, -1)
        self.assertRaises(NotFoundError, queue.remove_job, job_1.id)

    def test__run_job(self):

        queue = Queue(db.job)

        def do_run(job_entity):
            try:
                queue.run_job(job_entity)
            except subprocess.CalledProcessError:
                return 1
            else:
                return 0

        job = self.add(db.job, dict(status='a'))
        # No command defined, should fail.
        self.assertFalse(do_run(job))

        tmp_file = os.path.join(TMP_DIR, 'test__run_output.txt')
        text = 'Hello World!'

        script = """
#!/usr/bin/python

def main():
    import sys
    with open('{file}', 'w') as f:
        f.write("{text}")
        f.write("\\n")
        for c, arg in enumerate(sys.argv):
            if c == 0:
                continue
            f.write(str(c) + ': ' + arg + "\\n")

if __name__ == '__main__':
    main()
    """.format(file=tmp_file, text=text)

        script_name = os.path.join(TMP_DIR, 'test__run.py')
        with open(script_name, 'w') as f:
            f.write(script.strip())
        os.chmod(script_name, 0700)

        # Test without args or options
        job.command = script_name
        self.assertEqual(do_run(job), 0)

        expect = """Hello World!
"""
        got = ''
        with open(tmp_file, 'r') as f:
            got = f.read()
        self.assertEqual(got, expect)

        # Test with args or options
        job.command = "{script} -v -a delete 123".format(script=script_name)
        self.assertEqual(do_run(job), 0)
        expect = """Hello World!
1: -v
2: -a
3: delete
4: 123
"""
        got = ''
        with open(tmp_file, 'r') as f:
            got = f.read()
        self.assertEqual(got, expect)

    def test__set_job_status(self):
        queue = Queue(db.job)
        job = self.add(db.job, dict(command='pwd', status='d'))

        new_job = db(db.job.id == job.id).select().first()
        self.assertEqual(new_job.status, 'd')

        for status in ['a', 'd', 'p']:
            queue.set_job_status(job.id, status)
            new_job = db(db.job.id == job.id).select().first()
            self.assertEqual(new_job.status, status)

        # Invalid job id
        self.assertRaises(NotFoundError, queue.set_job_status, -1, 'a')

        # Invalid status
        self.assertRaises(InvalidStatusError, queue.set_job_status, job, 'z')

    def test__stats(self):
        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        self.add(db.job, dict(status='a'))
        self.add(db.job, dict(status='a'))
        self.add(db.job, dict(status='d'))
        self.add(db.job, dict(status='p'))
        self.assertEqual(queue.stats(), {'a': 2, 'd': 1, 'p': 1})

    def test__top_job(self):
        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        self.assertRaises(QueueEmptyError, queue.top_job)

        jobs = [
            # (command, start, priority)
            ('do_a', '2010-01-01 10:00:00', 0),
            ('do_b', '2010-01-01 10:00:01', -1),
            ('do_c', '2010-01-01 10:00:02', 1),
            ('do_d', '2999-12-31 23:59:59', 1),
        ]

        for j in jobs:
            self.add(db.job, dict(command=j[0], start=j[1], priority=j[2]))

        job = queue.top_job()
        self.assertEqual(job.command, 'do_c')

    def test__unlock(self):
        # See test__lock()
        pass


class TestQueueWithSignal(LocalTestCase):

    def test____init__(self):
        queue = QueueWithSignal(db.job)
        self.assertTrue(queue)

    def test__post_add_job(self):
        queue = QueueWithSignal(db.job)
        # There isn't a real test here. Just make the call and ensure it works
        # without errors.
        # W0702: *No exception type(s) specified*
        # pylint: disable=W0702
        try:
            queue.post_add_job()
        except:
            self.fail('post_add_job produced exception.')


class TestReleaseBookQueuer(LocalTestCase):

    def test_queue(self):
        queuer = ReleaseBookQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--requeues': '4', '-m': '10'},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/release_book.py --requeues 4 -m 10 123'
        )


class TestReverseReleaseBookQueuer(LocalTestCase):

    def test_queue(self):
        queuer = ReverseReleaseBookQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--requeues': '4', '-m': '10'},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/release_book.py --requeues 4 --reverse -m 10 123'
        )


class TestUpdateIndiciaQueuer(LocalTestCase):

    def test_queue(self):
        queuer = UpdateIndiciaQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={},
            cli_args=[str(123)],
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/update_creator_indicia.py -o -r 123'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
