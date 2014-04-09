#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/unix_file.py

"""
import inspect
import os
import unittest
from applications.zcomix.modules.unix_file import UnixFile
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


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
            ('applications/zcomix/tests/test_unix_file.py: Python script, ASCII text executable\n', '')
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
