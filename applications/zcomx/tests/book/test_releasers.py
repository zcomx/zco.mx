#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/book/releasers.py

"""
import datetime
import unittest
from gluon import *
from applications.zcomx.modules.activity_logs import TentativeActivityLog
from applications.zcomx.modules.book.releasers import \
    BaseReleaser, \
    FileshareBook, \
    ReleaseBook, \
    UnfileshareBook, \
    UnreleaseBook
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.images_optimize import OptimizeImgLog
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.tests.trackers import TableTracker
from applications.zcomx.modules.zco import IN_PROGRESS


# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class WithObjectsTestCase(LocalTestCase):
    """ Base class for test cases. Sets up test data."""

    _book = None
    _book_page = None
    _creator = None
    _job_options = {'status': 'd'}

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    def setUp(self):

        self._creator = self.add(Creator, dict(
            email='releasers_creator@gmail.com',
        ))

        self._book = self.add(Book, dict(
            name='Releasers Test Book',
            creator_id=self._creator.id,
        ))

        self._book_page = self.add(BookPage, dict(
            book_id=self._book.id,
            page_no=1,
        ))

        super(WithObjectsTestCase, self).setUp()

    def _get_activity_logs(self):
        query = (db.tentative_activity_log.book_id == self._book.id)
        try:
            logs = Records.from_query(
                TentativeActivityLog,
                query,
                orderby=db.tentative_activity_log.id
            ).records
        except LookupError:
            logs = []
        return logs


class TestBaseReleaser(WithObjectsTestCase):

    def test____init__(self):
        releaser = BaseReleaser(self._book, self._creator)
        self.assertTrue(releaser)
        self.assertEqual(releaser.needs_requeue, False)

    def test__run(self):
        releaser = BaseReleaser(Book(), Creator())
        self.assertRaises(NotImplementedError, releaser.run)


class TestFileshareBook(WithObjectsTestCase):
    def test__run(self):
        # Test: creator needs indicia portrait
        data = dict(
            indicia_portrait=None,
            indicia_landscape=None,
        )
        self._creator = Creator.from_updated(self._creator, data)

        releaser = FileshareBook(self._book, self._creator)
        tracker = TableTracker(db.job)
        jobs = releaser.run(job_options=self._job_options)
        for job in jobs:
            self.assertFalse(tracker.had(job))
            self.assertTrue(tracker.has(job))
            self._objects.append(job)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            jobs[0].command,
            'applications/zcomx/private/bin/update_creator_indicia.py -o -r {i}'.format(i=self._creator.id)
        )
        self.assertEqual(releaser.needs_requeue, True)

        # Test: creator is fine, cbz needed
        data = dict(
            indicia_portrait='_fileshare_portrait_fake_',
            indicia_landscape='_fileshare_landscape_fake_',
        )
        self._creator = Creator.from_updated(self._creator, data)
        # Prevent foo when creator obj is deleted
        db.creator.indicia_portrait.custom_delete = lambda x: None
        db.creator.indicia_landscape.custom_delete = lambda x: None
        # Create optimize_img_log records so images appear optimized
        self.add(OptimizeImgLog, dict(
            image='_fileshare_portrait_fake_',
            size='cbz',
        ))
        self.add(OptimizeImgLog, dict(
            image='_fileshare_landscape_fake_',
            size='cbz',
        ))

        data = dict(
            cbz=None,
            torrent=None,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = FileshareBook(self._book, self._creator)
        tracker = TableTracker(db.job)
        jobs = releaser.run(job_options=self._job_options)
        for job in jobs:
            self.assertFalse(tracker.had(job))
            self.assertTrue(tracker.has(job))
            self._objects.append(job)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            jobs[0].command,
            'applications/zcomx/private/bin/create_cbz.py {i}'.format(i=self._book.id)
        )
        self.assertEqual(releaser.needs_requeue, True)

        # Test: torrent needed
        data = dict(
            cbz='_fake_cbz_',
            torrent=None,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = FileshareBook(self._book, self._creator)
        tracker = TableTracker(db.job)
        jobs = releaser.run(job_options=self._job_options)
        for job in jobs:
            self.assertFalse(tracker.had(job))
            self.assertTrue(tracker.has(job))
            self._objects.append(job)
        self.assertEqual(len(jobs), 4)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            jobs[0].command,
            'applications/zcomx/private/bin/create_torrent.py {i}'.format(i=self._book.id)
        )
        self.assertEqual(
            jobs[1].command,
            'applications/zcomx/private/bin/create_torrent.py --creator {i}'.format(i=self._creator.id)
        )
        self.assertEqual(
            jobs[2].command,
            'applications/zcomx/private/bin/create_torrent.py --all'
        )
        self.assertEqual(
            jobs[3].command,
            'applications/zcomx/private/bin/notify_p2p_networks.py _fake_cbz_'
        )
        self.assertEqual(releaser.needs_requeue, True)

        # Test: all requires met, set as fileshared.
        data = dict(
            cbz='_fake_cbz_',
            torrent='_fake_torrent_',
            fileshare_date=None,
            fileshare_in_progress=True,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = FileshareBook(self._book, self._creator)
        jobs = releaser.run(job_options=self._job_options)
        self.assertEqual(jobs, [])

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.fileshare_date, datetime.date.today())
        self.assertEqual(book.fileshare_in_progress, False)


class TestReleaseBook(WithObjectsTestCase):
    def test__run(self):
        # Test: needs to be posted on social media
        data = dict(
            release_date=None,
            tumblr_post_id=None,
            twitter_post_id=None,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = ReleaseBook(self._book, self._creator)
        tracker = TableTracker(db.job)
        jobs = releaser.run(job_options=self._job_options)
        for job in jobs:
            self.assertFalse(tracker.had(job))
            self.assertTrue(tracker.has(job))
            self._objects.append(job)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            jobs[0].command,
            'applications/zcomx/private/bin/social_media/post_book_completed.py {i}'.format(i=self._book.id)
        )

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.release_date, None)
        self.assertEqual(book.tumblr_post_id, IN_PROGRESS)
        self.assertEqual(book.twitter_post_id, IN_PROGRESS)
        self.assertEqual(releaser.needs_requeue, True)

        # Test: posted on social media, needs to be completed
        self.assertEqual(self._get_activity_logs(), [])
        data = dict(
            release_date=None,
            complete_in_progress=True,
            tumblr_post_id='_fake_post_id_',
            twitter_post_id='_fake_post_id_',
        )
        self._book = Book.from_updated(self._book, data)
        releaser = ReleaseBook(self._book, self._creator)
        jobs = releaser.run(job_options=self._job_options)
        self.assertEqual(jobs, [])

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.release_date, datetime.date.today())
        self.assertEqual(book.complete_in_progress, False)
        self.assertEqual(releaser.needs_requeue, False)
        logs = self._get_activity_logs()
        self.assertEqual(len(logs), 1)
        self._objects.append(logs[0])
        self.assertEqual(logs[0].book_id, self._book.id)
        self.assertEqual(logs[0].book_page_id, self._book_page.id)
        self.assertEqual(logs[0].action, 'completed')
        self.assertAlmostEqual(
            logs[0].time_stamp,
            datetime.datetime.now(),
            delta=datetime.timedelta(minutes=1)
        )


class TestUnfileshareBook(WithObjectsTestCase):

    def test__run(self):
        data = dict(
            cbz='_fake_cbz_',
            torrent='_fake_torrent_',
            fileshare_date=datetime.date.today(),
            fileshare_in_progress=True,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = UnfileshareBook(self._book, self._creator)
        tracker = TableTracker(db.job)
        jobs = releaser.run(job_options=self._job_options)
        for job in jobs:
            self.assertFalse(tracker.had(job))
            self.assertTrue(tracker.has(job))
            self._objects.append(job)
        self.assertEqual(len(jobs), 3)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            jobs[0].command,
            'applications/zcomx/private/bin/create_torrent.py --creator {i}'.format(i=self._creator.id)
        )
        self.assertEqual(
            jobs[1].command,
            'applications/zcomx/private/bin/create_torrent.py --all'
        )
        self.assertEqual(
            jobs[2].command,
            'applications/zcomx/private/bin/notify_p2p_networks.py --delete _fake_cbz_'
        )
        self.assertEqual(releaser.needs_requeue, False)

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.cbz, '')
        self.assertEqual(book.torrent, '')
        self.assertEqual(book.fileshare_date, None)
        self.assertEqual(book.fileshare_in_progress, False)

        # Test: where no jobs should be required
        data = dict(
            cbz=None,
            torrent=None,
            fileshare_date=datetime.date.today(),
            fileshare_in_progress=True,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = UnfileshareBook(self._book, self._creator)
        jobs = releaser.run(job_options=self._job_options)
        self.assertEqual(jobs, [])

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.fileshare_date, None)
        self.assertEqual(book.fileshare_in_progress, False)


class TestUnreleaseBook(WithObjectsTestCase):

    def test__run(self):
        data = dict(
            release_date=datetime.date.today(),
            complete_in_progress=True,
        )
        self._book = Book.from_updated(self._book, data)
        releaser = UnreleaseBook(self._book, self._creator)
        jobs = releaser.run(job_options=self._job_options)
        self.assertEqual(jobs, [])
        self.assertEqual(releaser.needs_requeue, False)

        book = Book.from_id(self._book.id)      # reload
        self.assertEqual(book.release_date, None)
        self.assertEqual(book.complete_in_progress, False)

        tests = [
            # (post_id, expect)
            ('', ''),
            ('_fake_post_id_', '_fake_post_id_'),
            (IN_PROGRESS, ''),
        ]
        for t in tests:
            data = dict(
                tumblr_post_id=t[0],
                twitter_post_id=t[0],
            )
            self._book = Book.from_updated(self._book, data)
            releaser = UnreleaseBook(self._book, self._creator)
            jobs = releaser.run(job_options=self._job_options)
            self.assertEqual(jobs, [])
            book = Book.from_id(self._book.id)      # reload
            self.assertEqual(book.tumblr_post_id, t[1])
            self.assertEqual(book.twitter_post_id, t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
