#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/link_types.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.link_types import LinkType
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestLinkType(LocalTestCase):

    def test_parent__init__(self):
        link_type = LinkType({'code': 'fake_code'})
        self.assertEqual(link_type.db_table, 'link_type')
        self.assertEqual(link_type.code, 'fake_code')

    def test__by_code(self):
        link_type = LinkType.by_code('buy_book')
        expect = db(db.link_type.code == 'buy_book').select().first()
        self.assertEqual(link_type, expect)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
