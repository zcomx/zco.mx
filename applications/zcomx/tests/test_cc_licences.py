#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/cc_licences.py
"""
import unittest
from gluon import *
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestCCLicence(LocalTestCase):

    def test__by_code(self):
        cc_licence = CCLicence.by_code('CC0')
        self.assertEqual(cc_licence.code, 'CC0')

    def test__default(self):
        cc_licence = CCLicence.default()
        self.assertEqual(cc_licence.code, 'All Rights Reserved')


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
