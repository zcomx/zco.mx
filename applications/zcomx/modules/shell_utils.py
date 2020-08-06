#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Classes and functions related to shell utilities
"""
import functools
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


def imagemagick_version():
    """Return the version of the installed ImageMagick suite.

    Returns:
        string, version of ImageMagick. Eg '6.9.0-0'
    """
    args = ['convert', '-version']
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    p_stdout, unused_p_stderr = p.communicate()
    return p_stdout.decode().split("\n")[0].split()[2]


def os_nice(value):
    """Return a function for adding a nice value to a process.

    Args:
        value: boolean, integer, or string, boolean used to determine
            the nice increment value.

            value       nice command

            None        nice -n 0
            True        nice -n 10
            False       nice -n 0
            'default'   nice -n 10
            'max'       nice -n 19
            'min'       nice -n -20
            'off'       nice -n 0
            n           nice -n n

    Returns:
        function

    Usage:
        p = subprocess.Popen(
            args,
            preexec_fn=os_nice(19),
        )
    """
    nices = {
        'default': 10,
        'max': 19,
        'min': -20,
        'off': 0
    }

    increment = nices['off']
    if value is None or value is False:
        increment = nices['off']
    elif value is True:
        increment = nices['default']
    elif isinstance(value, str) and value in nices:
        increment = nices[value]
    elif isinstance(value, int):
        increment = value

    def _nice(increment):
        """Apply nice function."""
        os.nice(increment)

    return functools.partial(_nice, increment)


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


class TthSumError(Exception):
    """Exception class for tthsum errors."""
    pass


def tthsum(filename):
    """Return tthsum hashes for a list of files.

    Args:
        filename: name of file to get tthsum for

    Returns:
        str: tthsum hash
    """
    if not filename:
        return

    args = ['tthsum']
    args.append(filename)
    p = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p_stdout, p_stderr = p.communicate()
    tthsum_hash = ''
    if p_stdout:
        tthsum_hash, filename = \
            p_stdout.decode().strip().split("\n")[0].split(None, 1)

    if p_stderr:
        msg = 'tthsum error: {msg}'.format(msg=p_stderr)
        raise TthSumError(msg)

    return tthsum_hash
