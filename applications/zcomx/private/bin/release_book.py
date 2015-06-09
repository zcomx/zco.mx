#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
release_book.py

Script to release a book.
"""
import datetime
import logging
import os
from optparse import OptionParser
from applications.zcomx.modules.books import \
    get_page, \
    images as book_images
from applications.zcomx.modules.creators import \
    images as creator_images
from applications.zcomx.modules.images_optimize import \
    CBZImagesForRelease
from applications.zcomx.modules.job_queue import \
    CreateAllTorrentQueuer, \
    CreateBookTorrentQueuer, \
    CreateCBZQueuer, \
    CreateCreatorTorrentQueuer, \
    NotifyP2PQueuer, \
    PostOnSocialMediaQueuer, \
    ReleaseBookQueuer
from applications.zcomx.modules.utils import \
    NotFoundError
from applications.zcomx.modules.zco import IN_PROGRESS

VERSION = 'Version 0.1'
LOG = logging.getLogger('cli')


class Releaser(object):
    """Class representing a Releaser"""

    def __init__(self, book_id):
        """Constructor

        Args:
            book_id: string, first arg
        """
        self.book_id = book_id
        self.book = db(db.book.id == book_id).select().first()
        if not self.book:
            raise NotFoundError('Book not found, id: %s', book_id)

        query = (db.creator.id == self.book.creator_id)
        self.creator = db(query).select().first()
        if not self.creator:
            raise NotFoundError(
                'Creator not found, id: %s', self.book.creator_id)
        self.needs_requeue = False

    def requeue(self, requeues, max_requeues):
        """Requeue release job."""
        if requeues < max_requeues:
            queuer = ReleaseBookQueuer(
                db.job,
                cli_options=self.requeue_cli_options(requeues, max_requeues),
                cli_args=[str(self.book.id)],
            )
            queuer.queue()

    def requeue_cli_options(self, requeues, max_requeues):
        """Return dict of cli options on requeue."""

        # R0201: *Method could be a function*
        # pylint: disable=R0201

        return {
            '-r': requeues + 1,
            '-m': max_requeues,
        }

    def run(self):
        """Run the release."""
        raise NotImplementedError()


class ReleaseBook(Releaser):
    """Class representing a ReleaseBook"""

    def run(self):

        book_image_set = CBZImagesForRelease.from_names(book_images(self.book))
        if book_image_set.has_unoptimized():
            book_image_set.optimize()
            self.needs_requeue = True
            return

        creator_image_set = CBZImagesForRelease.from_names(
            creator_images(self.creator))
        if creator_image_set.has_unoptimized():
            creator_image_set.optimize()
            self.needs_requeue = True
            return

        if not self.book.cbz:
            CreateCBZQueuer(
                db.job,
                cli_args=[str(self.book.id)],
            ).queue()
            self.needs_requeue = True
            return

        if not self.book.torrent:
            CreateBookTorrentQueuer(
                db.job,
                cli_args=[str(self.book.id)],
            ).queue()

            CreateCreatorTorrentQueuer(
                db.job,
                cli_args=[str(self.book.creator_id)],
            ).queue()

            CreateAllTorrentQueuer(db.job).queue()

            NotifyP2PQueuer(
                db.job,
                cli_args=[self.book.cbz],
            ).queue()

            self.needs_requeue = True
            return

        if not self.book.tumblr_post_id:
            PostOnSocialMediaQueuer(
                db.job,
                cli_args=[str(self.book.id)],
            ).queue()
            self.needs_requeue = True
            # Set the tumblr post id to a dummy value to prevent this step
            # from running over and over.
            data = dict(
                tumblr_post_id=IN_PROGRESS,
                twitter_post_id=IN_PROGRESS
            )
            self.book.update_record(**data)
            db.commit()

            self.needs_requeue = True
            return

        # Everythings good. Release the book.
        data = dict(
            release_date=datetime.datetime.today(),
            releasing=False,
        )
        self.book.update_record(**data)
        db.commit()

        # Log activity
        try:
            first_page = get_page(self.book, page_no='first')
        except NotFoundError:
            LOG.error('First page not found: %s', self.book.name)
        else:
            db.tentative_activity_log.insert(
                book_id=self.book.id,
                book_page_id=first_page.id,
                action='completed',
                time_stamp=datetime.datetime.now(),
            )
            db.commit()


class UnreleaseBook(Releaser):
    """Class representing a releaser that reverses the release."""

    def requeue_cli_options(self, requeues, max_requeues):
        """Return dict of cli options on requeue."""
        options = super(UnreleaseBook, self).requeue_cli_options(
            requeues, max_requeues)
        options.update({'--reverse': True})
        return options

    def run(self):

        if self.book.cbz:
            LOG.debug('Removing cbz file: %s', self.book.cbz)
            if os.path.exists(self.book.cbz):
                os.unlink(self.book.cbz)

            CreateCreatorTorrentQueuer(
                db.job,
                cli_args=[str(self.book.creator_id)],
            ).queue()

            CreateAllTorrentQueuer(db.job).queue()

            NotifyP2PQueuer(
                db.job,
                cli_options={'--delete': True},
                cli_args=[self.book.cbz],
            ).queue()

        if self.book.torrent:
            LOG.debug('Removing torrent file: %s', self.book.torrent)
            if os.path.exists(self.book.torrent):
                os.unlink(self.book.torrent)

        # Everythings good. Unrelease the book.
        data = dict(
            cbz=None,
            torrent=None,
            release_date=None,
            releasing=False,
        )

        if self.book.tumblr_post_id == IN_PROGRESS:
            data['tumblr_post_id'] = None
        if self.book.twitter_post_id == IN_PROGRESS:
            data['twitter_post_id'] = None

        self.book.update_record(**data)
        db.commit()


def man_page():
    """Print manual page-like help"""
    print """
USAGE
    release_book.py [OPTIONS] book_id               # Release book
    release_book.py [OPTIONS] --reverse book_id     # Reverse the release

OPTIONS
    -h, --help
        Print a brief help.

    --man
        Print man page-like help.

    -m NUM, --max-requeues=NUM
        The script will be requeued at most NUM times. Use this to
        prevent endless requeueing. Default 25.

    -r NUM, --requeues=NUM
        The script has been requeued NUM times. This value is incremented
        everytime the script is queued. Use in conjunction with --max-requeues
        to prevent endless requeueing.

    --reverse
        Reverse the release of a book.

    -v, --verbose
        Print information messages to stdout.

    --vv,
        More verbose. Print debug messages to stdout.
    """


def main():
    """Main processing."""

    usage = '%prog [options] book_id'
    parser = OptionParser(usage=usage, version=VERSION)

    parser.add_option(
        '--man',
        action='store_true', dest='man', default=False,
        help='Display manual page-like help and exit.',
    )
    parser.add_option(
        '-m', '--max-requeues',
        type='int',
        dest='max_requeues', default=25,
        help='Requeue this script at most this many times. Default 25.',
    )
    parser.add_option(
        '-r', '--requeues',
        type='int',
        dest='requeues', default=0,
        help='The number of times this script has been requeued.',
    )
    parser.add_option(
        '--reverse',
        action='store_true', dest='reverse', default=False,
        help='Reverse the release.',
    )
    parser.add_option(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='Print messages to stdout.',
    )
    parser.add_option(
        '--vv',
        action='store_true', dest='vv', default=False,
        help='More verbose.',
    )

    (options, args) = parser.parse_args()

    if options.man:
        man_page()
        quit(0)

    if options.verbose or options.vv:
        level = logging.DEBUG if options.vv else logging.INFO
        unused_h = [
            h.setLevel(level) for h in LOG.handlers
            if h.__class__ == logging.StreamHandler
        ]

    if len(args) != 1:
        parser.print_help()
        exit(1)

    LOG.debug('Starting')
    book_id = args[0]
    release_class = UnreleaseBook if options.reverse else ReleaseBook
    releaser = release_class(book_id)
    releaser.run()
    if releaser.needs_requeue:
        releaser.requeue(options.requeues, options.max_requeues)

    LOG.debug('Done')


if __name__ == '__main__':
    # W0703: *Catch "Exception"*
    # pylint: disable=W0703
    try:
        main()
    except Exception as err:
        LOG.exception(err)
        exit(1)
