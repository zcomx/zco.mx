#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test suite for shared/modules/tests/trackers.py
"""
import datetime
import unittest
from applications.zcomx.modules.job_queue import Job
from applications.zcomx.modules.tests.trackers import TableTracker
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import default_record

# pylint: disable=missing-docstring


class TestTableTracker(LocalTestCase):
    jobs = {}
    jobs_ids = []
    query = None
    now = None

    def setUp(self):
        self.now = datetime.datetime.now()
        self.query = (db.job.command == 'test__TableTracker')

        db.job.truncate()
        job_commands = ['test__TableTracker', 'test__TableTracker_2']
        for count, command in enumerate(job_commands):
            job = self.create_job(command=command)
            self.jobs[count + 1] = job
            self.jobs_ids.append(job.id)

    def create_job(self, command='pwd'):
        data = default_record(db.job, ignore_fields='common')
        data.update(dict(
            start=self.now,
            command=command,
            status='d',                 # Prevent job from running
        ))
        job = Job.from_add(data)
        self._objects.append(job)
        return job

    def test____init__(self):
        tracker = TableTracker(db.job)
        self.assertTrue(tracker)
        # pylint: disable=protected-access
        self.assertEqual(tracker._ids, self.jobs_ids)

        query_tracker = TableTracker(db.job, query=self.query)
        self.assertTrue(query_tracker)
        self.assertEqual(query_tracker._ids, [self.jobs[1].id])

    def test__diff(self):
        tracker = TableTracker(db.job)
        self.assertEqual(tracker.diff(), [])

        query_tracker = TableTracker(db.job, query=self.query)
        self.assertEqual(query_tracker.diff(), [])

        job_3 = self.create_job(command='test_diff')

        got = tracker.diff()
        self.assertEqual(
            sorted([x.id for x in got]),
            sorted([job_3.id])
        )
        self.assertEqual(query_tracker.diff(), [])

        job_4 = self.create_job(command='test__TableTracker')

        got = tracker.diff()
        self.assertEqual(
            sorted([x.id for x in got]),
            sorted([job_3.id, job_4.id])
        )
        got = query_tracker.diff()
        self.assertEqual(
            sorted([x.id for x in got]),
            sorted([job_4.id])
        )

        job_3.delete()

        got = tracker.diff()
        self.assertEqual(
            sorted([x.id for x in got]),
            sorted([job_4.id])
        )
        got = query_tracker.diff()
        self.assertEqual(
            sorted([x.id for x in got]),
            sorted([job_4.id])
        )

        job_4.delete()

        self.assertEqual(tracker.diff(), [])
        self.assertEqual(query_tracker.diff(), [])

    def test__had(self):
        tracker = TableTracker(db.job)
        self.assertTrue(tracker.had(self.jobs[1]))
        self.assertTrue(tracker.had(self.jobs[2]))

        query_tracker = TableTracker(db.job, query=self.query)
        self.assertTrue(query_tracker.had(self.jobs[1]))
        self.assertFalse(query_tracker.had(self.jobs[2]))

        job = self.create_job(command='test__TableTracker')

        self.assertFalse(tracker.had(job))
        self.assertFalse(query_tracker.had(job))

        job.delete()

    def test__has(self):
        # Test: job added after tracker created.
        tracker = TableTracker(db.job)
        self.assertTrue(tracker.has(self.jobs[1]))
        self.assertTrue(tracker.has(self.jobs[2]))

        query_tracker = TableTracker(db.job, query=self.query)
        self.assertTrue(query_tracker.has(self.jobs[1]))
        self.assertFalse(query_tracker.has(self.jobs[2]))

        job = self.create_job(command='test__TableTracker')

        self.assertTrue(tracker.has(job))
        self.assertTrue(query_tracker.has(job))

        job.delete()


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
