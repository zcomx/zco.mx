#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to archives.
"""
import os
import shutil
from gluon import *
from applications.zcomx.modules.shell_utils import set_owner


class BaseArchive():
    """Class representing a handler for an archive."""

    def __init__(self, base_path, category=None, name=None):
        """Constructor

        Args:
            base_path: string, path pointing to location of archive.
                The base_path must exist.
            category: string, the category of archive. Used as a subdirectory
                under base_path.
            name: string, the name of the archive, used as a subdirectory under
                category. Eg base_path/category/name

        Notes:
            Archive has the follow directory structure
                base_path/category/name/[A-Z]/subdir/file.cbz
        """
        self.base_path = base_path
        self.category = category or 'archive'
        self.name = name or 'root'

    def add_file(self, src, dst):
        """Add a file to the archive.

        Args:
            src: string, name of file to copy to archive, path/to/file.cbz
            dst: string, name of file (not directory) in archive where file is
                stored relative to base_path/category/name.

                Eg file:  F/First Last/file.cbz
                    Stored as:  base_path/category/name/F/First Last/file.cbz

        Returns:
            string: path/to/file.cbz relative to base_path.
                Eg base_path/category/name/F/First Last/file.cbz

        Notes: the src file is *moved* not copied to the destination. If
            successful, src will no longer exist.
                mv src base_path/category/name/dst
        """
        if not os.path.exists(self.base_path):
            raise LookupError('Base path not found: {f}'.format(
                f=self.base_path))

        if not os.path.exists(src):
            raise LookupError('File not found: {f}'.format(f=src))

        dst_filename = os.path.join(
            self.base_path,
            self.category,
            self.name,
            dst
        )

        dst_dirname = os.path.dirname(dst_filename)
        if not os.path.exists(dst_dirname):
            os.makedirs(dst_dirname)
            set_owner(dst_dirname)

        shutil.move(src, dst_filename)
        set_owner(dst_filename)
        return dst_filename

    @classmethod
    def get_subdir_path(cls, subdir, include_subdir=True):
        """Return the archive path for a subdir.

        Args:
            subdir: string, subdir name
            include_subdir: If True include the subdir itself in the path


        Returns:
            string, subdir path

        Eg
            subdir          include_subdir=True    include_subdir=False
            ''              ''                      ''
            'Abe Adams'     'A/Abe Adams'           'A'
            'Zeke Zull'     'Z/Zeke Zull'           'Z'
            'zeke zull'     'Z/zeke zull'           'Z'
            123             '1/123'                 '1'
        """
        if not subdir:
            return ''

        letter = str(subdir)[0].upper()
        if include_subdir:
            return os.path.join(letter, str(subdir))
        return letter

    def remove_file(self, filename):
        """Remove file from the archive.

        Args:
            filename: string, name of file/directory in archive where file is
                stored relative to base_path/category/name.
        """
        full_filename = os.path.join(
            self.base_path,
            self.category,
            self.name,
            filename
        )
        if not os.path.exists(full_filename):
            raise LookupError('File not found: {f}'.format(f=full_filename))
        os.unlink(full_filename)


class ZcoMxArchive(BaseArchive):
    """Class representing a handler for a zco.mx archive.

    Args:
        see BaseArchive

    Can be used as a base class. Predefines the base_path and name.
    """
    def __init__(
            self,
            base_path=None,
            category=None,
            name=None):

        BaseArchive.__init__(
            self,
            base_path=base_path or 'applications/zcomx/private/var',
            category=category or 'archive',
            name=name or 'zco.mx'
        )


class CBZArchive(ZcoMxArchive):
    """Class representing a handler for the zco.mx archive of cbz files."""

    def __init__(self, base_path=None, category='cbz', name=None):
        """Constructor

        Args:
            see BaseArchive
        """
        ZcoMxArchive.__init__(
            self,
            base_path=base_path,
            category=category,
            name=name
        )


class TorrentArchive(ZcoMxArchive):
    """Class representing a handler for the zco.mx archive of torrent files."""

    def __init__(self, base_path=None, category='tor', name=None):
        """Constructor

        Args:
            see BaseArchive
        """
        ZcoMxArchive.__init__(
            self,
            base_path=base_path,
            category=category,
            name=name
        )
