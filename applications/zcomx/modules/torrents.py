#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Classes and functions related to torrents.
"""
import os
import subprocess
from gluon import *
from applications.zcomx.modules.archives import \
    CBZArchive, \
    TorrentArchive
from applications.zcomx.modules.books import \
    Book, \
    torrent_file_name as book_torrent_file_name
from applications.zcomx.modules.creators import \
    Creator, \
    creator_name, \
    torrent_file_name as creator_torrent_file_name
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    os_nice
from applications.zcomx.modules.zco import NICES

LOG = current.app.logger


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

    def create(self, nice=NICES['mktorrent']):
        """Create the torrent file.

        Returns:
            self
        """
        target = self.get_target()
        if not target:
            raise TorrentCreateError('Unable to get torrent target.')

        if not os.path.exists(target):
            raise LookupError('Torrent target not found: {t}'.format(
                t=target))

        output_file = os.path.join(self.temp_directory(), 'file.torrent')
        args = ['mktorrent']
        args.append('-a')
        args.append(self.announce_url)
        args.append('-o')
        args.append(output_file)
        args.append(target)
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os_nice(nice),
        )
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            LOG.error('mktorrent call failed: %s', p_stderr)
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
            entity: Book instance
        """
        BaseTorrentCreator.__init__(self, entity=entity)
        self.book = entity

    def archive(self, base_path=None):
        """Archive the torrent.

        Returns:
            string, name of archive file.
        """
        result = BaseTorrentCreator.archive(self, base_path=base_path)
        if self.book:
            self.book = Book.from_updated(self.book, dict(torrent=result))
        return result

    def get_destination(self):
        """Return the archive destination of the file.

        Returns:
            string: destination file name
        """
        creator = Creator.from_id(self.book.creator_id)
        tor_subdir = TorrentArchive.get_subdir_path(
            creator_name(creator, use='file'))
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
            entity: Creator instance
        """
        BaseTorrentCreator.__init__(self, entity=entity)
        self.creator = entity
        self._cbz_base_path = None

    def archive(self, base_path=None):
        """Archive the torrent.

        Returns:
            string, name of archive file.
        """
        result = BaseTorrentCreator.archive(self, base_path=base_path)
        if self.creator:
            data = dict(torrent=result)
            self.creator = Creator.from_updated(self.creator, data)
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

    def notify(self, delete=False, nice=NICES['zc-p2p']):
        """Notify p2p networks of cbz file.

        Args:
            delete: boolean, if True notify of deleting of the cbz file.

        """
        zc_p2p = os.path.abspath(
            os.path.join(current.request.folder, 'private', 'bin', 'zc-p2p.sh')
        )

        real_filename = os.path.abspath(self.cbz_filename)

        args = []
        args.append('sudo')
        args.append(zc_p2p)
        if delete:
            args.append('-d')
        args.append(real_filename)
        LOG.debug('zc-p2p.sh args: %s', args)
        p = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os_nice(nice),
        )
        unused_stdout, p_stderr = p.communicate()
        # E1101 (no-member): *%%s %%r has no %%r member*      # p.returncode
        # pylint: disable=E1101
        if p.returncode:
            LOG.error('Run of zc-p2p call failed: %s', p_stderr)
            raise P2PNotifyError('Run of zc-p2p call failed.')
