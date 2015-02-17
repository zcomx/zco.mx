#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Unit test helper classes and functions.
"""
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.tests.runner import LocalTestCase


class ZcoTestCase(LocalTestCase):
    """Class for testing."""

    # test_data = Storage({})
    test_data = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        pass    # FIXME

    @classmethod
    def tearDownClass(cls):
        pass    # FIXME

    @classmethod
    def _setup(cls):
        """Setup test data."""
        cls.test_data = cls.want
