#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to shell utilities
"""
import grp
import os
import pwd
import shutil
import subprocess
import tempfile
from gluon import *


class TempDirectoryMixin(object):
    """Base class representing an object using temporary directory"""

    _temp_directory = None

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        """Cleanup """
        tmp_dir = self.temp_directory()
        if tmp_dir:
            shutil.rmtree(tmp_dir)
            self._temp_directory = None

    def temp_directory(self):
        """Return a temporary directory where files will be extracted to."""
        if self._temp_directory is None:
            self._temp_directory = temp_directory()
        return self._temp_directory


class TemporaryDirectory(object):
    """tempfile.mkdtemp() usable with "with" statement."""

    def __init__(self):
        self.name = None

    def __enter__(self):
        self.name = temp_directory()
        return self.name

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.name)


class UnixFile(object):
    """Class representing a Unix file."""

    def __init__(self, name):
        """Constructor

        Args:
            name: string, name of file including path.
        """
        self.name = name

    def file(self):
        """Return output of the unix 'file' command

        Returns:
            tuple: (output, errors)
        """
        p = subprocess.Popen(
            ['file', self.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return p.communicate()


def imagemagick_version(host=None):
    """Return the version of the installed ImageMagick suite."""
    args = ['convert', '-version']
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    p_stdout, unused_p_stderr = p.communicate()
    return p_stdout.split("\n")[0].split()[2]


def get_owner(filename):
    """Return the owner of the file.

    Args:
        filename: string, path/to/file

    Returns:
        tuple, (user, group)

    """
    stat_info = os.stat(filename)
    uid = stat_info.st_uid
    gid = stat_info.st_gid
    user = pwd.getpwuid(uid)[0]
    group = grp.getgrgid(gid)[0]
    return (user, group)


def set_owner(filename, user='http', group='http'):
    """Set ownership on a file.
    Args:
        filename: string, path/to/file
        user: string, name of user to set file to
        group: string, name of group to set file to
    """
    os.chown(
        filename,
        pwd.getpwnam(user).pw_uid,
        pwd.getpwnam(group).pw_gid
    )


def temp_directory():
    """Return a temp directory"""
    db = current.app.db
    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    tmp_path = os.path.join(db.book_page.image.uploadfolder, '..', 'tmp')
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
        os.chown(
            tmp_path,
            pwd.getpwnam('http').pw_uid,
            pwd.getpwnam('http').pw_gid,
        )
    return tempfile.mkdtemp(dir=tmp_path)