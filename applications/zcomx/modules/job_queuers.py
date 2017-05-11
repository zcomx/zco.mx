#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
job_queue.py

Classes related to job queues.

"""
import os
from gluon import *
from applications.zcomx.modules.job_queue import \
    Daemon, \
    DaemonSignalError, \
    JobQueuer, \
    Queue

DAEMON_NAME = 'zco_queued'
PRIORITIES = list(reversed([
    # Highest
    'optimize_cbz_img_for_release',
    'optimize_img_for_release',
    'update_creator_indicia_for_release',
    'create_cbz',
    'create_book_torrent',
    'post_book_completed',
    'set_book_completed',
    'fileshare_book',
    'optimize_cbz_img',
    'optimize_img',
    'update_creator_indicia',
    'optimize_web_img',
    'create_creator_torrent',
    'create_all_torrent',
    'notify_p2p_networks',
    'reverse_fileshare_book',               # above reverse_set_book_completed
    'reverse_set_book_completed',           # above delete_book
    'delete_book',
    'delete_img',
    'log_downloads',
    'optimize_original_img',
    'search_prefetch',
    'purge_torrents',
    # Lowest
]))


LOG = current.app.logger


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


class FileshareBookQueuer(JobQueuer):
    """Class representing a queuer for fileshare_book jobs."""
    program = os.path.join(JobQueuer.bin_path, 'fileshare_book.py')
    default_job_options = {
        'priority': PRIORITIES.index('fileshare_book'),
        'status': 'a',
    }
    valid_cli_options = [
        '-m', '--max-requeues',
        '-r', '--requeues',
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
    """Class representing a queuer for post_book_completed on social_media
    jobs.
    """
    program = os.path.join(
        JobQueuer.bin_path, 'social_media', 'post_book_completed.py')
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


class ReverseFileshareBookQueuer(FileshareBookQueuer):
    """Class representing a queuer for reversing fileshare_book jobs."""
    program = os.path.join(JobQueuer.bin_path, 'fileshare_book.py')
    default_job_options = dict(FileshareBookQueuer.default_job_options)
    default_job_options['priority'] = \
        PRIORITIES.index('reverse_fileshare_book')
    default_cli_options = {'--reverse': True}
    valid_cli_options = list(FileshareBookQueuer.valid_cli_options)
    valid_cli_options.append('--reverse')


class SearchPrefetchQueuer(JobQueuer):
    """Class representing a queuer for search_prefetch jobs."""
    program = os.path.join(JobQueuer.bin_path, 'search_prefetch.py')
    default_job_options = {
        'priority': PRIORITIES.index('search_prefetch'),
        'status': 'a',
    }
    valid_cli_options = [
        '-o', '--output',
        '-t', '--table',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class SetBookCompletedQueuer(JobQueuer):
    """Class representing a queuer for set_book_completed jobs."""
    program = os.path.join(JobQueuer.bin_path, 'set_book_completed.py')
    default_job_options = {
        'priority': PRIORITIES.index('set_book_completed'),
        'status': 'a',
    }
    valid_cli_options = [
        '-m', '--max-requeues',
        '-r', '--requeues',
        '-v', '--vv',
    ]
    queue_class = QueueWithSignal


class ReverseSetBookCompletedQueuer(SetBookCompletedQueuer):
    """Class representing a queuer for reversing set_book_completed jobs."""
    program = os.path.join(JobQueuer.bin_path, 'set_book_completed.py')
    default_job_options = dict(SetBookCompletedQueuer.default_job_options)
    default_job_options['priority'] = \
        PRIORITIES.index('reverse_set_book_completed')
    default_cli_options = {'--reverse': True}
    valid_cli_options = list(SetBookCompletedQueuer.valid_cli_options)
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


class UpdateIndiciaForReleaseQueuer(UpdateIndiciaQueuer):
    """Class representing a queuer for update_creator_indicia for release jobs.
    """
    default_job_options = dict(UpdateIndiciaQueuer.default_job_options)
    default_job_options['priority'] = PRIORITIES.index(
        'update_creator_indicia_for_release')


def queue_search_prefetch():
    """Convenience function. Queues a search prefetch job.

    Since the job is generally not critical, apart from a log,
    failures are ignored.
    """
    db = current.app.db
    job = SearchPrefetchQueuer(db.job).queue()
    if not job:
        LOG.error('Failed to create search prefetch job')
    return job
