#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/archives.py

"""
import os
import shutil
import unittest
from gluon import *
from applications.zcomx.modules.archives import \
    BaseArchive, \
    CBZArchive, \
    TorrentArchive, \
    ZcoMxArchive
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestBaseArchive(LocalTestCase):
    _base_path = '/tmp/base_archive'

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls._base_path):
            os.makedirs(cls._base_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._base_path):
            shutil.rmtree(cls._base_path)

    def test____init__(self):
        archive = BaseArchive(self._base_path)
        self.assertTrue(archive)
        self.assertEqual(archive.category, 'archive')
        self.assertEqual(archive.name, 'root')

    def test__add_file(self):
        filename = os.path.join(self._base_path, 'test.cbz')

        archive = BaseArchive(self._base_path)

        tests = [
            # (dst, expect)
            (
                'aaa.txt',
                '/tmp/base_archive/archive/root/aaa.txt'
            ),
            (
                'A/Adam Ant.cbz',
                '/tmp/base_archive/archive/root/A/Adam Ant.cbz'
            ),
            (
                'A/Adam Ant/Title.cbz',
                '/tmp/base_archive/archive/root/A/Adam Ant/Title.cbz'
            ),
        ]

        for t in tests:
            with open(filename, 'w') as f:
                f.write('Testing')
            got = archive.add_file(filename, t[0])
            self.assertEqual(got, t[1])
            self.assertTrue(os.path.exists(got))
            subdir = t[1].replace('/tmp/base_archive/archive/root/', '')
            archive.remove_file(subdir)
            self.assertFalse(os.path.exists(got))

        # Test: src does not exist
        self.assertRaises(
            LookupError, archive.add_file, '/tmp/_fake_', 'F/First Last')

        # Test: base_path does not exist
        archive = BaseArchive('/tmp/_invalid_')
        with open(filename, 'w') as f:
            f.write('Testing')
        self.assertRaises(
            LookupError, archive.add_file, filename, 'F/First Last')

    def test__get_subdir_path(self):
        archive = BaseArchive(self._base_path)
        tests = [
            # (subdir, expect, expect include_subdir=False)
            (None, '', ''),
            ('', '', ''),
            (123, '1/123', '1'),
            ('Abe Adams', 'A/Abe Adams', 'A'),
            ('Zach Zellers', 'Z/Zach Zellers', 'Z'),
            ('zach zellers', 'Z/zach zellers', 'Z'),
        ]

        for t in tests:
            self.assertEqual(archive.get_subdir_path(t[0]), t[1])
            self.assertEqual(
                archive.get_subdir_path(t[0], include_subdir=False),
                t[2]
            )

    def test__remove_file(self):
        pass                # See test__add_file


class TestCBZArchive(LocalTestCase):

    def test____init__(self):
        archive = CBZArchive()
        self.assertTrue(archive)
        self.assertEqual(archive.base_path, 'applications/zcomx/private/var')
        self.assertEqual(archive.category, 'cbz')
        self.assertEqual(archive.name, 'zco.mx')


class TestTorrentArchive(LocalTestCase):

    def test____init__(self):
        archive = TorrentArchive()
        self.assertTrue(archive)
        self.assertEqual(archive.base_path, 'applications/zcomx/private/var')
        self.assertEqual(archive.category, 'tor')
        self.assertEqual(archive.name, 'zco.mx')


class TestZcoMxArchive(LocalTestCase):

    def test____init__(self):
        archive = ZcoMxArchive()
        self.assertTrue(archive)
        self.assertEqual(archive.base_path, 'applications/zcomx/private/var')
        self.assertEqual(archive.category, 'archive')
        self.assertEqual(archive.name, 'zco.mx')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
