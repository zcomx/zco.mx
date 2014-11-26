#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/unix_file.py

"""
import inspect
import os
import pwd
import re
import shutil
import socket
import unittest
from applications.zcomx.modules.shell_utils import \
    TempDirectoryMixin, \
    TemporaryDirectory, \
    UnixFile, \
    imagemagick_version, \
    get_owner, \
    set_owner, \
    temp_directory
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestTempDirectoryMixin(LocalTestCase):

    def test____del__(self):
        mixin = TempDirectoryMixin()
        tmp_dir = mixin.temp_directory()
        self.assertTrue(os.path.exists(tmp_dir))
        del mixin
        self.assertFalse(os.path.exists(tmp_dir))

    def test__cleanup(self):
        mixin = TempDirectoryMixin()
        # W0212 (protected-access): *Access to a protected member %%s
        # pylint: disable=W0212
        self.assertTrue(mixin._temp_directory is None)
        tmp_dir = mixin.temp_directory()
        self.assertTrue(os.path.exists(tmp_dir))
        mixin.cleanup()
        self.assertFalse(os.path.exists(tmp_dir))

    def test__temp_directory(self):
        pass        # test_cleanup tests this.


class TestTemporaryDirectory(LocalTestCase):

    def test____init__(self):
        tmp_dir = TemporaryDirectory()
        self.assertTrue(tmp_dir)
        self.assertEqual(tmp_dir.name, None)

    def test____enter__(self):
        with TemporaryDirectory() as tmp_dir:
            self.assertTrue(
                os.path.exists(tmp_dir)
            )

    def test____exit__(self):
        tmp_directory = ''
        with TemporaryDirectory() as tmp_dir:
            tmp_directory = tmp_dir
        self.assertFalse(
            os.path.exists(tmp_directory)
        )


class TestUnixFile(LocalTestCase):

    def test____init__(self):
        filename = inspect.getfile(inspect.currentframe())
        unix_file = UnixFile(filename)
        self.assertTrue(unix_file)

    def test__file(self):
        filename = inspect.getfile(inspect.currentframe())
        unix_file = UnixFile(filename)
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            unix_file.file(),
            ('applications/zcomx/tests/test_shell_utils.py: Python script, ASCII text executable\n', '')
        )


class TestFunctions(LocalTestCase):

    _tmp_backup = None
    _tmp_dir = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        if cls._tmp_backup is None:
            cls._tmp_backup = os.path.join(
                db._adapter.folder, '..', 'uploads', 'tmp_bak')
        if cls._tmp_dir is None:
            cls._tmp_dir = os.path.join(
                db._adapter.folder, '..', 'uploads', 'tmp')

    @classmethod
    def tearDown(cls):
        if cls._tmp_backup and os.path.exists(cls._tmp_backup):
            if os.path.exists(cls._tmp_dir):
                shutil.rmtree(cls._tmp_dir)
            os.rename(cls._tmp_backup, cls._tmp_dir)

    def test__imagemagick_version(self):
        by_host = {
            'dtjimk': '6.7.0-8',
            'jimk': '6.8.8-7',
            'zc': '6.8.8-7'
        }
        version = imagemagick_version()
        self.assertEqual(
            imagemagick_version(),
            by_host[socket.gethostname()]
        )

    def test__get_owner(self):
        pass        # test__set_owner tests this.

    def test__set_owner(self):
        if not os.path.exists(self._tmp_dir):
            os.makedirs(self._tmp_dir)
        filename = os.path.join(self._tmp_dir, 'test__set_owner.txt')
        with open(filename, 'w') as f:
            f.write('test__set_owner testing!')
        self.assertTrue(os.path.exists(filename))

        self.assertEqual(get_owner(filename), ('root', 'root'))
        set_owner(filename)
        self.assertEqual(get_owner(filename), ('http', 'http'))
        set_owner(filename, user='daemon', group='nobody')
        self.assertEqual(get_owner(filename), ('daemon', 'nobody'))

        # Cleanup
        os.unlink(filename)
        self.assertFalse(os.path.exists(filename))

    def test__temp_directory(self):
        def valid_tmp_dir(path):
            """Return if path is tmp dir."""
            # Typical path:
            # 'applications/zcomx/uploads/original/../tmp/tmprHbFAM
            dirs = path.split('/')
            self.assertEqual(dirs[0], 'applications')
            self.assertEqual(dirs[1], 'zcomx')
            self.assertEqual(dirs[2], 'uploads')
            self.assertEqual(dirs[-2], 'tmp')
            self.assertRegexpMatches(
                dirs[-1],
                re.compile(r'tmp[a-zA-Z0-9_].*')
            )

        got = temp_directory()
        valid_tmp_dir(got)
        os.rmdir(got)          # Cleanup

        # Test: tmp directory does not exist.
        if os.path.exists(self._tmp_dir):
            os.rename(self._tmp_dir, self._tmp_backup)

        valid_tmp_dir(temp_directory())
        # Check permissions on tmp subdirectory
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        tmp_path = os.path.join(db._adapter.folder, '..', 'uploads', 'tmp')
        self.assertTrue(os.path.exists(tmp_path))
        stats = os.stat(tmp_path)
        self.assertEqual(stats.st_uid, pwd.getpwnam('http').pw_uid)
        self.assertEqual(stats.st_gid, pwd.getpwnam('http').pw_gid)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
