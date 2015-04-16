#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to torrents.
"""
import os
import subprocess
import sys
from gluon import *
from applications.zcomx.modules.archives import \
    CBZArchive, \
    TorrentArchive
from applications.zcomx.modules.books import \
    torrent_file_name as book_torrent_file_name
from applications.zcomx.modules.creators import \
    creator_name, \
    torrent_file_name as creator_torrent_file_name
from applications.zcomx.modules.shell_utils import TempDirectoryMixin
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row


class TorrentCreateError(Exception):
    """Exception class for a torrent file create error."""
    pass


class BaseTorrentCreator(TempDirectoryMixin):
    """Base class representing a handler for creating a torrent file."""

    announce_url = 'http://bt.zco.mx:6969/announce'
    default_base_path = 'applications/zcomx/private/var'

    def __init__(self, entity=None):
        """Constructor

        Args:
            entity: Row instance or integer representing a database record.
        """
        self.entity = entity
        self._tor_file = None

    def archive(self, base_path=None):
        """Archive the torrent.

        Returns:
            string, name of archive file.
        """
        if base_path is None:
            base_path = self.default_base_path
        archive = TorrentArchive(base_path)
        if self._tor_file is None:
            self.create()
        result = archive.add_file(self._tor_file, self.get_destination())
        return result

    def create(self):
        """Create the torrent file.

        Returns:
            self
        """
        target = self.get_target()
        if not target:
            raise TorrentCreateError('Unable to get torrent target.')

        if not os.path.exists(target):
            raise NotFoundError('Torrent target not found: {t}'.format(
                t=target))

        output_file = os.path.join(self.temp_directory(), 'file.torrent')
        args = ['mktorrent']
        args.append('-a')
        args.append(self.announce_url)
        args.append('-o')
        args.append(output_file)
        args.append(target)
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            print >> sys.stderr, 'mktorrent call failed: {e}'.format(
                e=p_stderr)
            raise TorrentCreateError('Creation of torrent file failed.')
        self._tor_file = output_file
        return self

    def get_destination(self):
        """Return the archive destination of the file.

        Returns:
            string: destination file name
        """
        raise NotImplementedError()

    def get_target(self):
        """Return the mktorrent target directory or file.

        Returns:
            string: name of target directory or file.
        """
        raise NotImplementedError()


class AllTorrentCreator(BaseTorrentCreator):
    """Base class representing a handler for creating a torrent file for all
    books.
    """
    def __init__(self, entity=None):
        """Constructor

        Args:
            entity: Not used.
        """
        BaseTorrentCreator.__init__(self, entity=entity)

    def get_destination(self):
        """Return the archive destination of the file.

        Returns:
            string: destination file name
        """
        tor_archive = TorrentArchive()
        # Add .torrent extension to file
        return '.'.join([tor_archive.name, 'torrent'])

    def get_target(self):
        """Return the mktorrent target directory or file.

        Returns:
            string: name of target directory or file.
        """
        cbz_archive = CBZArchive()

        return os.path.join(
            cbz_archive.base_path,
            cbz_archive.category,
            cbz_archive.name,
        )


class BookTorrentCreator(BaseTorrentCreator):
    """Base class representing a handler for creating a torrent file for a
    book.
    """
    def __init__(self, entity=None):
        """Constructor

        Args:
            entity: Row instance or integer representing a book.
        """
        BaseTorrentCreator.__init__(self, entity=entity)
        db = current.app.db
        self.book = entity_to_row(db.book, self.entity)
        if not self.book:
            raise NotFoundError('Book not found: {e}'.format(e=self.entity))

    def archive(self, base_path=None):
        """Archive the torrent.

        Returns:
            string, name of archive file.
        """
        result = BaseTorrentCreator.archive(self, base_path=base_path)
        if self.book:
            db = current.app.db
            self.book.update_record(torrent=result)
            db.commit()
        return result

    def get_destination(self):
        """Return the archive destination of the file.

        Returns:
            string: destination file name
        """
        db = current.app.db
        creator_record = entity_to_row(db.creator, self.book.creator_id)
        if not creator_record:
            raise NotFoundError('Creator not found, id:{i}'.format(
                i=self.book.creator_id))

        tor_subdir = TorrentArchive.get_subdir_path(
            creator_name(creator_record, use='file'))
        tor_file = book_torrent_file_name(self.book)
        return os.path.join(tor_subdir, tor_file)

    def get_target(self):
        """Return the mktorrent target directory or file.

        Returns:
            string: name of target directory or file.
        """
        return self.book.cbz


class CreatorTorrentCreator(BaseTorrentCreator):
    """Base class representing a handler for creating a torrent file for a
    creator.
    """
    def __init__(self, entity=None):
        """Constructor

        Args:
            entity: Row instance or integer representing a creator.
        """
        BaseTorrentCreator.__init__(self, entity=entity)
        db = current.app.db
        self.creator = entity_to_row(db.creator, self.entity)
        if not self.creator:
            raise NotFoundError('Creator not found: {e}'.format(e=self.entity))
        self._cbz_base_path = None

    def archive(self, base_path=None):
        """Archive the torrent.

        Returns:
            string, name of archive file.
        """
        result = BaseTorrentCreator.archive(self, base_path=base_path)
        if self.creator:
            db = current.app.db
            self.creator.update_record(torrent=result)
            db.commit()
        return result

    def get_destination(self):
        """Return the archive destination of the file.

        Returns:
            string: destination file name
        """
        tor_subdir = TorrentArchive.get_subdir_path(
            creator_name(self.creator, use='file'))

        return os.path.join(
            os.path.dirname(tor_subdir),         # Get the 'letter' subdir
            creator_torrent_file_name(self.creator)
        )

    def get_target(self):
        """Return the mktorrent target directory or file.

        Returns:
            string: name of target directory or file.
            cbz_base_path: string, path to base of CBZ archive.
        """
        cbz_archive = CBZArchive()
        base_path = self._cbz_base_path \
            if self._cbz_base_path is not None \
            else cbz_archive.base_path

        return os.path.join(
            base_path,
            cbz_archive.category,
            cbz_archive.name,
            cbz_archive.get_subdir_path(creator_name(self.creator, use='file'))
        )

    def set_cbz_base_path(self, path):
        """Helper function to designate the cbz_base_path for get_target."""
        self._cbz_base_path = path


class P2PNotifyError(Exception):
    """Exception class for a torrent file create error."""
    pass


class P2PNotifier(object):
    """Class representing a P2PNotifier"""

    def __init__(self, cbz_filename):
        """Constructor

        Args:
            cbz_filename: string, first arg
        """
        self.cbz_filename = cbz_filename

    def notify(self, delete=False):
        """Notify p2p networks of cbz file.

        Args:
            delete: boolean, if True notify of deleting of the cbz file.

        """
        zc_p2p = os.path.abspath(
            os.path.join(current.request.folder, 'private', 'bin', 'zc-p2p.sh')
        )

        real_filename = os.path.abspath(self.cbz_filename)

        args = []
        args.append(zc_p2p)
        if delete:
            args.append('-d')
        args.append(real_filename)
        p = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            print >> sys.stderr, 'Run of zc-p2p call failed: {e}'.format(
                e=p_stderr)
            raise P2PNotifyError('Run of zc-p2p call failed.')
