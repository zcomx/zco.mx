#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
test_job_queue.py

Test suite for zcomx/modules/job_queue.py

"""
import datetime
import os
import subprocess
import time
import unittest
from gluon import *
from applications.zcomx.modules.job_queue import \
    CLIOption, \
    Daemon, \
    DaemonSignalError, \
    IgnorableJob, \
    InvalidCLIOptionError, \
    InvalidJobOptionError, \
    InvalidStatusError, \
    Job, \
    JobHistory, \
    JobQueuer, \
    Queue, \
    QueueEmptyError, \
    QueueLockedError, \
    QueueLockedExtendedError, \
    Queuer, \
    Requeuer
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.tests.trackers import TableTracker

# C0111: *Missing docstring*
# R0904: *Too many public methods (%s/%s)*
# pylint: disable=C0111,R0904

TMP_DIR = '/tmp/test_suite/job_queue'

if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)


class SubQueuer(Queuer):
    """Sub class of Queuer used for testing."""
    class_factory_id = 'some_program'
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

        Queuer.__init__(
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


class TestDaemon(LocalTestCase):
    name = 'zco_queued'
    pid_filename = '/tmp/test_suite/job_queue/pid'

    def test____init__(self):
        daemon = Daemon(self.name)
        self.assertEqual(daemon.pid_filename, '/tmp/zco_queued/pid')

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
        self.assertEqual(list(params.keys()), ['last'])

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


class TestIgnorableJob(LocalTestCase):

    def test__is_ignored(self):
        now = datetime.datetime.now()
        nine_minutes_ago = now - datetime.timedelta(minutes=9)
        eleven_minutes_ago = now - datetime.timedelta(minutes=11)

        command = 'test__is_ignored'
        priority = 10

        data = dict(
            command=command,
            priority=priority,
            start=now,
            status='d',
            ignorable=True,
        )

        reset_data = dict(data)

        def reset(job):
            return IgnorableJob.from_updated(job, reset_data)

        job_1 = IgnorableJob.from_add(data)
        self._objects.append(job_1)

        job_2 = IgnorableJob.from_add(data)
        self._objects.append(job_2)

        job_1 = reset(job_1)
        job_2 = reset(job_2)
        self.assertTrue(job_1.is_ignored(status='d'))

        for ignorable in [True, False]:
            data = dict(ignorable=ignorable)
            job_1 = IgnorableJob.from_updated(job_1, data)
            self.assertEqual(job_1.is_ignored(status='d'), ignorable)

        job_1 = reset(job_1)

        tests = [
            # (job_1.start, start_limit_seconds, expect)
            (now, None, True),
            (nine_minutes_ago, None, True),
            (eleven_minutes_ago, None, False),
            (nine_minutes_ago, 539, False),
            (nine_minutes_ago, 540, False),
            (nine_minutes_ago, 541, True),
        ]
        for t in tests:
            data = dict(start=t[0])
            job_1 = IgnorableJob.from_updated(job_1, data)
            if t[1] is None:
                self.assertEqual(job_1.is_ignored(status='d'), t[2])
            else:
                self.assertEqual(
                    job_1.is_ignored(status='d', start_limit_seconds=t[1]),
                    t[2]
                )


class TestJob(LocalTestCase):
    pass            # Record subclass


class TestJobHistory(LocalTestCase):
    def test_init__(self):
        query = (db.job_history)
        job_history = JobHistory.from_query(query)
        self.assertTrue(job_history)


class TestJobQueuer(LocalTestCase):
    def test_init__(self):
        query = (db.job_queuer.code == 'search_prefetch')
        job_queuer = JobQueuer.from_query(query)
        self.assertTrue(job_queuer)


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

        now = datetime.datetime.now()
        job_data = dict(
            command='pwd',
            priority=1,
            start=now,
        )
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

        my_queue = MyQueue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(my_queue.jobs()), 0)

        ret = my_queue.add_job(job_data)
        self._objects.append(ret)
        self.assertTrue(ret.id > 0)
        self.assertEqual(my_queue.trace, ['pre', 'post'])

    def test__job_generator(self):
        queue = Queue(db.job)

        gen = queue.job_generator()
        # No jobs
        self.assertRaises(StopIteration, gen.__next__)

        job_data = [
            # (command, start, priority, status)
            ('do_a', '2010-01-01 10:00:00', 1, 'a'),
            ('do_b', '2010-01-01 10:00:00', 5, 'a'),
            ('do_c', '2010-01-01 10:00:00', 9, 'a'),
        ]

        all_jobs = []
        for j in job_data:
            job = queue.add_job(
                dict(command=j[0], start=j[1], priority=j[2], status=j[3])
            )
            all_jobs.append(job)

        gen = queue.job_generator()
        job = next(gen)
        self.assertEqual(job.command, 'do_c')
        all_jobs[2].delete()
        job = next(gen)
        self.assertEqual(job.command, 'do_b')
        all_jobs[1].delete()
        job = next(gen)
        self.assertEqual(job.command, 'do_a')
        all_jobs[0].delete()
        self.assertRaises(StopIteration, gen.__next__)

        for j in all_jobs:
            try:
                j.delete()
            except LookupError:
                pass
        self.assertEqual(queue.stats(), {})

    def test__jobs(self):
        # Add a new 'z' status to test with.
        db.job.status.requires = IS_IN_SET(['a', 'd', 'p', 'z'])

        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        job_data = [
            # (start, priority, status)
            # Do not use status='a' or status='p' or jobs will be run.
            ('2010-01-01 10:00:00', 0, 'z'),
            ('2010-01-01 10:00:00', 0, 'd'),
            ('2010-01-01 10:00:01', -1, 'z'),
            ('2010-01-01 10:00:01', -1, 'd'),
            ('2010-01-01 10:00:02', 1, 'z'),
            ('2010-01-01 10:00:02', 1, 'd'),
        ]

        all_jobs = []
        for j in job_data:
            job_d = dict(command='pwd', start=j[0], priority=j[1], status=j[2])
            job = Job.from_add(job_d)
            self._objects.append(job)
            all_jobs.append(job)

        job_set = queue.jobs()
        self.assertEqual(len(job_set), 6)
        self.assertEqual(job_set, all_jobs)

        # Test query
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            job_set,
            [all_jobs[0], all_jobs[2], all_jobs[4]]
        )

        query = (db.job.status == 'd') & \
                (db.job.start <= '2010-01-01 10:00:01')
        job_set = queue.jobs(query=query)
        self.assertEqual(len(job_set), 2)
        self.assertEqual(
            job_set,
            [all_jobs[1], all_jobs[3]]
        )

        # Test orderby
        # Orderby priority ASC
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=db.job.priority)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            job_set,
            [all_jobs[2], all_jobs[0], all_jobs[4]]
        )

        # Orderby priority DESC
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=~db.job.priority)
        self.assertEqual(len(job_set), 3)
        self.assertEqual(
            job_set,
            [all_jobs[4], all_jobs[0], all_jobs[2]]
        )

        # Test limitby
        # Highest priority job
        query = (db.job.status == 'z')
        job_set = queue.jobs(query=query, orderby=~db.job.priority, limitby=1)
        self.assertEqual(len(job_set), 1)
        self.assertEqual(job_set, [all_jobs[4]])

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

    def test__run_job(self):

        queue = Queue(db.job)

        def do_run(job):
            try:
                queue.run_job(job)
            except subprocess.CalledProcessError:
                return 1
            else:
                return 0

        job = Job(dict(command=None, status='a'))
        # No command defined, should fail.
        self.assertFalse(do_run(job))

        tmp_file = os.path.join(TMP_DIR, 'test__run_output.txt')
        text = 'Hello World!'

        script = """
#!/usr/bin/python3

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
        os.chmod(script_name, 0o700)

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
        job = self.add(Job, dict(command='pwd', status='d'))
        self.assertEqual(job.status, 'd')

        for status in ['a', 'd', 'p']:
            got = queue.set_job_status(job, status)
            self.assertEqual(got.status, status)

        # Invalid status
        self.assertRaises(InvalidStatusError, queue.set_job_status, job, 'z')

    def test__stats(self):
        queue = Queue(db.job)
        TestQueue.clear_queue()
        self.assertEqual(len(queue.jobs()), 0)

        self.add(Job, dict(status='a'))
        self.add(Job, dict(status='a'))
        self.add(Job, dict(status='d'))
        self.add(Job, dict(status='p'))
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
            self.add(Job, dict(command=j[0], start=j[1], priority=j[2]))

        job = queue.top_job()
        self.assertEqual(job.command, 'do_c')

    def test__unlock(self):
        # See test__lock()
        pass


class TestQueuer(LocalTestCase):

    def test____init__(self):
        queuer = Queuer(db.job)
        self.assertTrue(queuer)
        self.assertEqual(queuer.queue_class, Queue)
        self.assertEqual(Queuer.bin_path, 'applications/zcomx/private/bin')

    def test__command(self):
        queuer = SubQueuer(db.job)
        self.assertEqual(
            queuer.command(), 'some_program.py -b -c ccc -d d1 -d d2')

        queuer = SubQueuer(db.job, cli_args=['file', 'arg2'])
        self.assertEqual(
            queuer.command(),
            'some_program.py -b -c ccc -d d1 -d d2 file arg2'
        )

        # Disable defaults
        queuer = SubQueuer(
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
        queuer = SubQueuer(db.job, cli_options=invalid_cli_options)
        self.assertRaises(InvalidCLIOptionError, queuer.command)

        # Handle quotes
        queuer = SubQueuer(
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

        queuer = SubQueuer(
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
        data = SubQueuer(db.job).job_data()
        self.assertEqual(data.job_queuer_id, 0)
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
        self.assertEqual(data.start, data.queued_time)

        invalid_job_options = {'fake_field': 'value'}
        queuer = SubQueuer(db.job, job_options=invalid_job_options)
        self.assertRaises(InvalidJobOptionError, queuer.job_data)

        # Test delay_seconds
        then = datetime.datetime.now()
        data = SubQueuer(db.job, delay_seconds=100).job_data()
        self.assertTrue(data.start > then)
        diff = data.start - then
        self.assertTrue(diff.total_seconds() >= 100)
        self.assertTrue(diff.total_seconds() < 101)

    def test__queue(self):
        def get_job_ids():
            return sorted([x.id for x in db(db.job).select(db.job.id)])

        job_ids = get_job_ids()

        queuer = SubQueuer(db.job)
        new_job = queuer.queue()
        self.assertEqual(
            new_job.command, 'some_program.py -b -c ccc -d d1 -d d2')
        self.assertTrue(new_job.id not in job_ids)
        job_ids = get_job_ids()
        self.assertTrue(new_job.id in job_ids)
        job = Job.from_id(new_job.id)
        self._objects.append(job)


class TestRequeuer(LocalTestCase):

    def test____init__(self):
        queuer = SubQueuer(db.job)
        requeuer = Requeuer(queuer)
        self.assertTrue(requeuer)
        self.assertEqual(requeuer.requeues, 0)
        self.assertEqual(requeuer.max_requeues, 1)

    def test__requeue(self):
        sub_queuer = SubQueuer(db.job)
        requeuer = Requeuer(sub_queuer)
        self.assertRaises(InvalidCLIOptionError, requeuer.requeue)

        class ReQueuer(SubQueuer):
            valid_cli_options = ['-a', '-c', '--requeues', '--max-requeues']
            default_cli_options = {
                '-a': True,
                '-c': 'ccc',
            }

        queuer = ReQueuer(db.job)
        requeuer = Requeuer(queuer)
        tracker = TableTracker(db.job)
        job = requeuer.requeue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'some_program.py --max-requeues 1 --requeues 1 -a -c ccc'
        )

        requeuer = Requeuer(queuer, requeues=33, max_requeues=99)
        tracker = TableTracker(db.job)
        job = requeuer.requeue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'some_program.py --max-requeues 99 --requeues 34 -a -c ccc'
        )

        requeuer = Requeuer(queuer, requeues=99, max_requeues=99)
        self.assertRaises(StopIteration, requeuer.requeue)

        requeuer = Requeuer(queuer, requeues=100, max_requeues=99)
        self.assertRaises(StopIteration, requeuer.requeue)

    def test__requeue_cli_options(self):

        requeuer = Requeuer(Queuer(db.job))
        self.assertEqual(
            requeuer.requeue_cli_options(),
            {
                '--requeues': 1,
                '--max-requeues': 1,
            }
        )

        requeuer = Requeuer(Queuer(db.job), requeues=33, max_requeues=99)
        self.assertEqual(
            requeuer.requeue_cli_options(),
            {
                '--requeues': 34,
                '--max-requeues': 99,
            }
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
