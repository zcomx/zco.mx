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
    optimize_images as optimize_book_images, \
    unoptimized_images as unoptimized_book_images
from applications.zcomx.modules.creators import \
    optimize_images as optimize_creator_images, \
    unoptimized_images as unoptimized_creator_images
from applications.zcomx.modules.job_queue import \
    CreateCBZQueuer, \
    CreateTorrentQueuer, \
    ReleaseBookQueuer
from applications.zcomx.modules.utils import \
    NotFoundError

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
            ReleaseBookQueuer(
                db.job,
                cli_options=self.requeue_cli_options(requeues, max_requeues),
                cli_args=[str(self.book.id)],
            ).queue()

    def requeue_cli_options(self, requeues, max_requeues):
        """Return dict of cli options on requeue."""
        return {
            '-r': requeues + 1,
            '-m': max_requeues,
        }

    def run(self):
        """Run the release."""
        raise NotImplementedError()


class ReleaseBook(Releaser):
    """Class representing a ReleaseBook"""

    def __init__(self, book_id):
        """Constructor

        Args:
            book_id: string, first arg
        """
        super(ReleaseBook, self).__init__(book_id)

    def run(self):
        """Run the release."""

        if unoptimized_book_images(self.book):
            optimize_book_images(
                self.book, priority='optimize_img_for_release')
            self.needs_requeue = True
            return

        if unoptimized_creator_images(self.creator):
            optimize_creator_images(
                self.creator, priority='optimize_img_for_release')
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
            # Create book torrent
            CreateTorrentQueuer(
                db.job,
                cli_args=[str(self.book.id)],
            ).queue()
            self.needs_requeue = True
            return

        # Everythings good. Release the book.
        self.book.update_record(
            release_date=datetime.datetime.today(),
            releasing=False,
        )
        db.commit()


class UnreleaseBook(Releaser):
    """Class representing a releaser that reverses the release."""

    def __init__(self, book_id):
        """Constructor

        Args:
            book_id: string, first arg
        """
        super(UnreleaseBook, self).__init__(book_id)

    def requeue_cli_options(self, requeues, max_requeues):
        """Return dict of cli options on requeue."""
        options = super(UnreleaseBook, self).requeue_cli_options(
            requeues, max_requeues)
        options.update({'--reverse': True})
        return options

    def run(self):
        """Run the release."""

        if self.book.cbz:
            LOG.debug('Removing cbz file: %s', self.book.cbz)
            if os.path.exists(self.book.cbz):
                os.unlink(self.book.cbz)

        if self.book.torrent:
            LOG.debug('Removing torrent file: %s', self.book.torrent)
            if os.path.exists(self.book.torrent):
                os.unlink(self.book.torrent)

        # Everythings good. Unrelease the book.
        self.book.update_record(
            cbz=None,
            torrent=None,
            release_date=None,
            releasing=False,
        )
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
