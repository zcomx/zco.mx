#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/cc_licences.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# (C0301): *Line too long (%%s/%%s)*
# pylint: disable=C0301
# C0302: *Too many lines in module (%%s)*
# pylint: disable=C0302


class TestCCLicence(LocalTestCase):

    def test__by_code(self):
        cc_licence = CCLicence.by_code('CC0')
        self.assertEqual(cc_licence.code, 'CC0')

    def test__default(self):
        cc_licence = CCLicence.default()
        self.assertEqual(cc_licence.code, 'All Rights Reserved')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
