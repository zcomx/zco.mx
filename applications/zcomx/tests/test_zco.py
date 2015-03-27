#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/zco.py

"""
import unittest
from gluon import *
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.zco import Zco

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestZco(LocalTestCase):

    def test____init__(self):
        env = globals()
        session = env['session']
        self.assertTrue('zco' not in session.keys())
        Zco()
        self.assertTrue('zco' in session.keys())

    def test__next_url(self):
        Zco().next_url = 'http://www.aaa.com'
        self.assertEqual(Zco().next_url, 'http://www.aaa.com')
        Zco().next_url = 'http://www.bbb.com'
        self.assertEqual(Zco().next_url, 'http://www.bbb.com')
        del Zco().next_url
        self.assertEqual(Zco().next_url, None)

    def test__paypal_in_progress(self):
        Zco().paypal_in_progress = True
        self.assertEqual(Zco().paypal_in_progress, True)
        Zco().paypal_in_progress = False
        self.assertEqual(Zco().paypal_in_progress, False)
        del Zco().paypal_in_progress
        self.assertEqual(Zco().paypal_in_progress, None)

    def test__all_torrent_url(self):
        self.assertEqual(
            Zco().all_torrent_url,
            {'c': 'zco.mx.torrent', 'f': 'index'}
        )
        self.assertEqual(
            URL(**Zco().all_torrent_url),
            '/zco.mx.torrent'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
