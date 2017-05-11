#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_job_queue.py

Test suite for zcomx/modules/job_queue.py

"""
import os
import unittest
from gluon import *
from applications.zcomx.modules.job_queue import InvalidCLIOptionError
from applications.zcomx.modules.job_queuers import \
    CreateAllTorrentQueuer, \
    CreateBookTorrentQueuer, \
    CreateCBZQueuer, \
    CreateCreatorTorrentQueuer, \
    CreateTorrentQueuer, \
    DeleteBookQueuer, \
    DeleteImgQueuer, \
    FileshareBookQueuer, \
    LogDownloadsQueuer, \
    NotifyP2PQueuer, \
    OptimizeCBZImgForReleaseQueuer, \
    OptimizeCBZImgQueuer, \
    OptimizeImgQueuer, \
    OptimizeOriginalImgQueuer, \
    OptimizeWebImgQueuer, \
    PRIORITIES, \
    PostOnSocialMediaQueuer, \
    PurgeTorrentsQueuer, \
    QueueWithSignal, \
    ReverseFileshareBookQueuer, \
    ReverseSetBookCompletedQueuer, \
    SearchPrefetchQueuer, \
    SetBookCompletedQueuer, \
    UpdateIndiciaQueuer, \
    UpdateIndiciaForReleaseQueuer, \
    queue_search_prefetch

from applications.zcomx.modules.tests.runner import \
    LocalTestCase, \
    TableTracker

# C0111: *Missing docstring*
# R0904: *Too many public methods (%s/%s)*
# pylint: disable=C0111,R0904

TMP_DIR = '/tmp/test_suite/job_queue'

if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)


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


class TestFileshareBookQueuer(LocalTestCase):

    def test_queue(self):
        queuer = FileshareBookQueuer(
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
            'applications/zcomx/private/bin/fileshare_book.py --requeues 4 -m 10 123'
        )


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
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/social_media/post_book_completed.py --vv 123'
        )


class TestPurgeTorrentsQueuer(LocalTestCase):

    def test_queue(self):
        queuer = PurgeTorrentsQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'--vv': True},
        )
        tracker = TableTracker(db.job)
        job = queuer.queue()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/purge_torrents.py --vv'
        )


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


class TestReverseFileshareBookQueuer(LocalTestCase):

    def test_queue(self):
        queuer = ReverseFileshareBookQueuer(
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
            'applications/zcomx/private/bin/fileshare_book.py --requeues 4 --reverse -m 10 123'
        )


class TestReverseSetBookCompletedQueuer(LocalTestCase):

    def test_queue(self):
        queuer = ReverseSetBookCompletedQueuer(
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
            'applications/zcomx/private/bin/set_book_completed.py --requeues 4 --reverse -m 10 123'
        )


class TestSearchPrefetchQueuer(LocalTestCase):

    def test_queue(self):
        queuer = SearchPrefetchQueuer(
            db.job,
            job_options={'status': 'd'},
            cli_options={'-t': 'book'},
            cli_args=[],
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
            'applications/zcomx/private/bin/search_prefetch.py -t book'
        )


class TestSetBookCompletedQueuer(LocalTestCase):

    def test_queue(self):
        queuer = SetBookCompletedQueuer(
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
            'applications/zcomx/private/bin/set_book_completed.py --requeues 4 -m 10 123'
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


class TestUpdateIndiciaForReleaseQueuer(LocalTestCase):

    def test_queue(self):
        queuer = UpdateIndiciaForReleaseQueuer(
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


class TestFunctions(LocalTestCase):

    def test__queue_search_prefetch(self):
        tracker = TableTracker(db.job)
        job = queue_search_prefetch()
        self.assertFalse(tracker.had(job))
        self.assertTrue(tracker.has(job))
        self._objects.append(job)
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            job.command,
            'applications/zcomx/private/bin/search_prefetch.py'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
