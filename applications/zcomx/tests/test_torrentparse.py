#!/usr/bin/python
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
from applications.zcomx.modules.test_runner import LocalTestCase



# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


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

    @classmethod
    def setUp(cls):
        cls._test_data_dir = os.path.join(request.folder, 'private/test/data/')

    @classmethod
    def _torrent_path(cls, tor_type='book'):
        name = '{t}.torrent'.format(t=tor_type)
        return os.path.join(cls._test_data_dir, 'torrents', name)

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
        self.assertEqual(parser.get_client_name(), 'mktorrent 1.0')

    def test__get_creation_date(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(parser.get_creation_date(), '2015-02-17T01:05:07')

    def test__get_files_details(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(
            parser.get_files_details(),
            [('Wolf (SO5) (2014) (101.zco.mx).cbz', 5022594)]
        )

    def test__get_tracker_url(self):
        parser = TorrentParser(self._torrent_path('book'))
        self.assertEqual(
            parser.get_tracker_url(),
            'http://bt.zco.mx:6969/announce'
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()