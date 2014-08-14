#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/unix_file.py

"""
import inspect
import os
import pwd
import re
import shutil
import unittest
from applications.zcomix.modules.shell_utils import \
    TemporaryDirectory, \
    UnixFile, \
    temp_directory
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


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
        self.assertEqual(
            unix_file.file(),
            ('applications/zcomix/tests/test_shell_utils.py: Python script, ASCII text executable\n', '')
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

    def test__temp_directory(self):
        def valid_tmp_dir(path):
            """Return if path is tmp dir."""
            # Typical path:
            # 'applications/zcomix/uploads/original/../tmp/tmprHbFAM
            dirs = path.split('/')
            self.assertEqual(dirs[0], 'applications')
            self.assertEqual(dirs[1], 'zcomix')
            self.assertEqual(dirs[2], 'uploads')
            self.assertEqual(dirs[-2], 'tmp')
            self.assertRegexpMatches(dirs[-1], re.compile(r'tmp[a-zA-Z0-9].*'))

        valid_tmp_dir(temp_directory())

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
