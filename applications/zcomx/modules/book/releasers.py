#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to book releasers.
"""
import datetime
import os
from gluon import *
from applications.zcomx.modules.books import \
    Book, \
    get_page, \
    images as book_images
from applications.zcomx.modules.creators import images as creator_images
from applications.zcomx.modules.images_optimize import \
    CBZImagesForRelease
from applications.zcomx.modules.job_queue import \
    CreateAllTorrentQueuer, \
    CreateBookTorrentQueuer, \
    CreateCBZQueuer, \
    CreateCreatorTorrentQueuer, \
    FileshareBookQueuer, \
    NotifyP2PQueuer, \
    PostOnSocialMediaQueuer, \
    ReverseFileshareBookQueuer, \
    ReverseSetBookCompletedQueuer, \
    SetBookCompletedQueuer, \
    UpdateIndiciaForReleaseQueuer
from applications.zcomx.modules.zco import IN_PROGRESS

LOG = current.app.logger


class BaseReleaser(object):
    """Class representing a releaser base class"""

    queuer_class = None

    def __init__(self, book, creator):
        """Constructor

        Args:
            book: Book instance
            creator: Creator instance
        """
        self.book = book
        self.creator = creator
        self.needs_requeue = False

    def run(self, job_options=None):
        """Run the release.

        Args:
            job_options: dict of options to pass any queued jobs for
                the job_options parameter.
        Returns:
            list of Job instances representing jobs created.
        """
        raise NotImplementedError()


class ReleaseBook(BaseReleaser):
    """Class representing a ReleaseBook"""
    queuer_class = SetBookCompletedQueuer

    def run(self, job_options=None):
        db = current.app.db
        jobs = []
        if not self.book.tumblr_post_id:
            job = PostOnSocialMediaQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.book.id)],
            ).queue()
            self.needs_requeue = True
            # Set the tumblr post id to a dummy value to prevent this step
            # from running over and over.
            data = dict(
                tumblr_post_id=IN_PROGRESS,
                twitter_post_id=IN_PROGRESS
            )
            self.book = Book.from_updated(self.book, data)

            self.needs_requeue = True
            return [job]

        # Everythings good. Release the book.
        data = dict(
            release_date=datetime.datetime.today(),
            complete_in_progress=False,
        )
        self.book = Book.from_updated(self.book, data)

        # Log activity
        try:
            first_page = get_page(self.book, page_no='first')
        except LookupError:
            LOG.error('First page not found: %s', self.book.name)
        else:
            db.tentative_activity_log.insert(
                book_id=self.book.id,
                book_page_id=first_page.id,
                action='completed',
                time_stamp=datetime.datetime.now(),
            )
            db.commit()
        return jobs


class UnreleaseBook(BaseReleaser):
    """Class representing a releaser that reverses the release."""
    queuer_class = ReverseSetBookCompletedQueuer

    def run(self, job_options=None):
        # Everythings good. Unrelease the book.
        data = dict(
            release_date=None,
            complete_in_progress=False,
        )

        if self.book.tumblr_post_id == IN_PROGRESS:
            data['tumblr_post_id'] = None
        if self.book.twitter_post_id == IN_PROGRESS:
            data['twitter_post_id'] = None
        self.book = Book.from_updated(self.book, data)
        return []


class FileshareBook(BaseReleaser):
    """Class representing a FileshareBook"""
    queuer_class = FileshareBookQueuer

    def run(self, job_options=None):
        db = current.app.db
        book_image_set = CBZImagesForRelease.from_names(book_images(self.book))
        if book_image_set.has_unoptimized():
            book_image_set.optimize()
            self.needs_requeue = True
            return []

        if not self.creator.indicia_portrait or \
                not self.creator.indicia_landscape:
            job = UpdateIndiciaForReleaseQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.creator.id)],
            ).queue()
            self.needs_requeue = True
            return [job]

        creator_image_set = CBZImagesForRelease.from_names(
            creator_images(self.creator))
        if creator_image_set.has_unoptimized():
            creator_image_set.optimize()
            self.needs_requeue = True
            return

        if not self.book.cbz:
            job = CreateCBZQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.book.id)],
            ).queue()
            self.needs_requeue = True
            return [job]

        if not self.book.torrent:
            book_tor_job = CreateBookTorrentQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.book.id)],
            ).queue()

            creator_tor_job = CreateCreatorTorrentQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.book.creator_id)],
            ).queue()

            all_tor_job = CreateAllTorrentQueuer(
                db.job,
                job_options=job_options,
            ).queue()

            p2p_job = NotifyP2PQueuer(
                db.job,
                job_options=job_options,
                cli_args=[self.book.cbz],
            ).queue()

            self.needs_requeue = True
            return [book_tor_job, creator_tor_job, all_tor_job, p2p_job]

        # Everythings good. Release the book.
        data = dict(
            fileshare_date=datetime.datetime.today(),
            fileshare_in_progress=False,
        )
        self.book = Book.from_updated(self.book, data)
        return []


class UnfileshareBook(BaseReleaser):
    """Class representing a releaser that reverses the release of a book for
    filesharing."""
    queuer_class = ReverseFileshareBookQueuer

    def run(self, job_options=None):
        db = current.app.db
        jobs = []
        if self.book.cbz:
            LOG.debug('Removing cbz file: %s', self.book.cbz)
            if os.path.exists(self.book.cbz):
                os.unlink(self.book.cbz)

            creator_tor_job = CreateCreatorTorrentQueuer(
                db.job,
                job_options=job_options,
                cli_args=[str(self.book.creator_id)],
            ).queue()

            all_tor_job = CreateAllTorrentQueuer(db.job).queue()

            p2p_job = NotifyP2PQueuer(
                db.job,
                job_options=job_options,
                cli_options={'--delete': True},
                cli_args=[self.book.cbz],
            ).queue()
            jobs = [creator_tor_job, all_tor_job, p2p_job]

        if self.book.torrent:
            LOG.debug('Removing torrent file: %s', self.book.torrent)
            if os.path.exists(self.book.torrent):
                os.unlink(self.book.torrent)

        # Everythings good. Unrelease the book.
        data = dict(
            cbz=None,
            torrent=None,
            fileshare_date=None,
            fileshare_in_progress=False,
        )

        self.book = Book.from_updated(self.book, data)
        return jobs
