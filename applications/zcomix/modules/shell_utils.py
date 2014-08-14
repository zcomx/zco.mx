#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to shell utilities
"""
import os
import pwd
import shutil
import subprocess
import tempfile
from gluon import *


class Cwd:
    """Class representing context manager for changing the current working
    directory
    """

    def __init__(self, path):
        """Constructor

        Args:
            path: string, the directory path to cd to.
        """
        self.path = path
        self.saved_path = None

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, etype, value, traceback):
        if self.saved_path:
            os.chdir(self.saved_path)


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
