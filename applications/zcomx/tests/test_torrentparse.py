#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/torrentparse.py
"""
import os
import unittest
from gluon import *
from applications.zcomx.modules.torrentparse import \
    ParsingError, \
    TorrentParser
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestParsingError(LocalTestCase):
    def test____init__(self):
        msg = 'This is an error message.'
        try:
            raise ParsingError(msg)
        except ParsingError as err:
            self.assertEqual(str(err), repr(msg))
        else:
            self.fail('ParsingError not raised')

    def test____str__(self):
        pass            # Tested in test____init__


class TestTorrentParser(LocalTestCase):
    _test_data_dir = None

    def setUp(self):
        self._test_data_dir = os.path.join(
            request.folder,
            'private/test/data/'
        )

    def _torrent_path(self, tor_type='book'):
        name = '{t}.torrent'.format(t=tor_type)
        return os.path.join(self._test_data_dir, 'torrents', name)

    def test____init__(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertTrue(parser)
        self.assertEqual(
            sorted(parser.parsed_content.keys()),
            ['announce', 'created by', 'creation date', 'info']
        )

        # Test exceptions
        self.assertRaises(ValueError, TorrentParser, None)
        self.assertRaises(IOError, TorrentParser, '/tmp/_invalid_path')

    def test__get_client_name(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(parser.get_client_name(), b'mktorrent 1.0')

    def test__get_creation_date(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(parser.get_creation_date(), '2015-02-17T01:05:07')

    def test__get_files_details(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(
            parser.get_files_details(),
            [(b'Wolf (SO5) (2014) (101.zco.mx).cbz', 5022594)]
        )

    def test__get_tracker_url(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(
            parser.get_tracker_url(),
            b'http://bt.zco.mx:6969/announce'
        )


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
