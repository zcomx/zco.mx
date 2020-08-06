#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/shell_utils.py

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
    TthSumError, \
    UnixFile, \
    get_owner, \
    imagemagick_version, \
    os_nice, \
    set_owner, \
    temp_directory, \
    tthsum
from applications.zcomx.modules.tests.runner import LocalTestCase

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
        filename = 'applications/zcomx/tests/test_shell_utils.py'
        unix_file = UnixFile(filename)
        output, errors = unix_file.file()
        # pylint: disable=line-too-long
        self.assertEqual(
            output.decode(),
            'applications/zcomx/tests/test_shell_utils.py: Python script, ASCII text executable\n'
        )
        self.assertEqual(errors.decode(), '')


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

    def tearDown(self):
        if self._tmp_backup and os.path.exists(self._tmp_backup):
            if os.path.exists(self._tmp_dir):
                shutil.rmtree(self._tmp_dir)
            os.rename(self._tmp_backup, self._tmp_dir)

    def test__get_owner(self):
        pass        # test__set_owner tests this.

    def test__imagemagick_version(self):
        by_host = {
            'dtjimk': '6.7.0-8',
            'jimk': '6.9.10-16',
            'zc': '6.9.10-16',
        }
        self.assertEqual(
            imagemagick_version(),
            by_host[socket.gethostname()]
        )

    def test__os_nice(self):
        tests = [
            # (value, expect increment)
            (None, 0),
            (True, 10),
            (False, 0),
            ('default', 10),
            ('max', 19),
            ('min', -20),
            ('off', 0),
            (6, 6),
            (-6, -6),
            ('_invalid_', 0),
        ]

        for t in tests:
            got = os_nice(t[0])
            self.assertEqual(got.args[0], t[1])

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
            self.assertRegex(
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

    def test__tthsum(self):
        tmp_dir = temp_directory()
        tests = [
            # ( string, expect tthsum )
            ('aaa', 'C4YOYCDDBHQ2YWOMOU4OPOKM2I5I6QMJFQW4OQI'),
            ('bbb', 'BZSKLI5NXFLOJUEKJXYHMCIAE72ROQED2TOL5MY'),
            ('ccc', 'VCH27UY3P7QOOIDV2PGF44WTQO32N6S4MEP7QJY'),
            ('"special" (chars)', 'DGYZJQS4VWRQBLFDXTUGI4ZQI5XGSX5ODYDDWUA'),
        ]
        for t in tests:
            filename = os.path.join(tmp_dir, '{n}.txt'.format(n=t[0]))
            with open(filename, 'w') as f:
                f.write(t[0])
            got = tthsum(filename)
            self.assertEqual(got, t[1])

        # Test no files
        self.assertEqual(tthsum(None), None)

        # Test non-existent file
        self.assertRaises(TthSumError, tthsum, '/tmp/_fake_file.txt')

        # Cleanup
        shutil.rmtree(tmp_dir)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
