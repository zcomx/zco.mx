#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/tests/helpers.py

"""
import unittest
from applications.zcomx.modules.tests.helpers import \
    FileTestCase, \
    ImageTestCase, \
    ResizerQuick, \
    WithTestDataDirTestCase
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904
# W0212 (protected-access): *Access to a protected member
# pylint: disable=W0212

class TestFileTestCase(LocalTestCase):
    pass


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
