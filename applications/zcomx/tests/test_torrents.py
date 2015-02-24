#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/torrents.py

"""
import os
import shutil
import unittest
from gluon import *
from applications.zcomx.modules.torrentparse import TorrentParser
from applications.zcomx.modules.torrents import \
    AllTorrentCreator, \
    BaseTorrentCreator, \
    BookTorrentCreator, \
    CreatorTorrentCreator, \
    TorrentCreateError
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import NotFoundError

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class SubBaseTorrentCreator(BaseTorrentCreator):
    # W0201: *Attribute %r defined outside __init__*
    # pylint: disable=W0201
    def get_destination(self):
        return self._destination

    def get_target(self):
        return self._target

    def set_destination(self, dst):
        """Helper function to allow the destination to be provided."""
        self._destination = dst

    def set_target(self, target):
        """Helper function to allow the target to be provided."""
        self._target = target


class TorrentTestCase(LocalTestCase):

    _tmp_dir = '/tmp/test_torrent'
    _test_file = None
    _test_path = None
    _test_creator_path = None
    _cbz_base_path = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls._tmp_dir):
            os.makedirs(cls._tmp_dir)
        # Create some files to used for testing

        cls._test_file = os.path.join(cls._tmp_dir, 'file.cbz')
        if not os.path.exists(cls._test_file):
            with open(cls._test_file, 'w') as f:
                f.write('Testing')

        cls._test_path = os.path.join(cls._tmp_dir, 'subdir')
        if not os.path.exists(cls._test_path):
            os.makedirs(cls._test_path)
            for filename in ['a.cbz', 'b.cbz', 'c.cbz']:
                with open(os.path.join(cls._test_path, filename), 'w') as f:
                    f.write('Testing')

        cls._test_creator_path = os.path.join(
            cls._tmp_dir, 'cbz', 'zco.mx', 'F', 'First Last', 'subdir')
        if not os.path.exists(cls._test_creator_path):
            os.makedirs(cls._test_creator_path)
            for filename in ['a.cbz', 'b.cbz', 'c.cbz']:
                fullname = os.path.join(cls._test_creator_path, filename)
                with open(fullname, 'w') as f:
                    f.write('Testing')

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls._tmp_dir):
            shutil.rmtree(cls._tmp_dir)


class TestBaseTorrentCreator(TorrentTestCase):

    def test____init__(self):
        tor_creator = BaseTorrentCreator()
        self.assertTrue(tor_creator)

    def test__archive(self):
        tor_creator = SubBaseTorrentCreator()
        tor_creator.set_target(self._test_file)
        tor_creator.set_destination('F/First Last/file.torrent')
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        self.assertEqual(
            tor_file,
            '/tmp/test_torrent/tor/zco.mx/F/First Last/file.torrent'
        )
        self.assertTrue(os.path.exists(tor_file))

        parser = TorrentParser(tor_file)
        self.assertEqual(
            parser.get_tracker_url(),
            'http://bt.zco.mx:6969/announce'
        )
        self.assertEqual(
            parser.get_client_name(),
            'mktorrent 1.0'
        )
        self.assertEqual(
            parser.get_files_details(),
            [('file.cbz', 7)]
        )

    def test__create(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212

        tor_creator = SubBaseTorrentCreator()

        # Test creating torrent for a file.
        tor_creator.set_target(self._test_file)
        tor_creator.create()

        tor_file = os.path.join(tor_creator.temp_directory(), 'file.torrent')
        self.assertEqual(
            tor_creator._tor_file,
            tor_file
        )
        self.assertTrue(os.path.exists(tor_file))

        # Check that it's a torrent file
        parser = TorrentParser(tor_file)
        self.assertEqual(
            parser.get_tracker_url(),
            'http://bt.zco.mx:6969/announce'
        )
        self.assertEqual(
            parser.get_client_name(),
            'mktorrent 1.0'
        )
        self.assertEqual(
            parser.get_files_details(),
            [('file.cbz', 7)]
        )

        # Test creating torrent for a directory.
        tor_creator = SubBaseTorrentCreator()
        tor_creator.set_target(self._test_path)
        tor_creator.create()

        tor_file = os.path.join(tor_creator.temp_directory(), 'file.torrent')
        self.assertEqual(
            tor_creator._tor_file,
            tor_file
        )
        self.assertTrue(os.path.exists(tor_file))

        # Check that it's a torrent file
        parser = TorrentParser(tor_file)
        self.assertEqual(
            parser.get_tracker_url(),
            'http://bt.zco.mx:6969/announce'
        )
        self.assertEqual(
            parser.get_client_name(),
            'mktorrent 1.0'
        )
        self.assertEqual(
            parser.get_files_details(),
            [('a.cbz', 7), ('b.cbz', 7), ('c.cbz', 7)]
        )

    def test__get_destination(self):
        tor_creator = BaseTorrentCreator()
        self.assertRaises(NotImplementedError, tor_creator.get_destination)

    def test__get_target(self):
        tor_creator = BaseTorrentCreator()
        self.assertRaises(NotImplementedError, tor_creator.get_target)


class TestAllTorrentCreator(TorrentTestCase):

    def test____init__(self):
        tor_creator = AllTorrentCreator()
        self.assertTrue(tor_creator)

    def test__get_destination(self):
        tor_creator = AllTorrentCreator()
        self.assertEqual(
            tor_creator.get_destination(),
            'zco.mx.torrent'
        )

    def test__get_target(self):
        tor_creator = AllTorrentCreator()
        self.assertEqual(
            tor_creator.get_target(),
            'applications/zcomx/private/var/cbz/zco.mx'
        )


class TestBookTorrentCreator(TorrentTestCase):

    def test____init__(self):
        # No book entity
        self.assertRaises(NotFoundError, BookTorrentCreator)

        book = self.add(db.book, dict(
            name='Test Book Torrent Creator'
        ))
        tor_creator = BookTorrentCreator(book)
        self.assertTrue(tor_creator)

    def test__archive(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))
        book = self.add(db.book, dict(
            name='Test Book Torrent Creator',
            creator_id=creator.id,
        ))
        tor_creator = BookTorrentCreator(book)
        # book.cbz is not defined, should fail
        self.assertRaises(TorrentCreateError, tor_creator.archive)

        book.update_record(cbz=self._test_file)
        db.commit()
        tor_creator = BookTorrentCreator(book)
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        self.assertEqual(
            tor_file,
            '/tmp/test_torrent/tor/zco.mx/F/First Last/file.cbz.torrent'
        )

        book_record = db(db.book.id == book.id).select().first()
        self.assertEqual(book_record.torrent, tor_file)

    def test__get_destination(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))

        book = self.add(db.book, dict(
            name='Test Book Torrent Creator',
            creator_id=creator.id,
            cbz='/path/to/file.cbz',
        ))

        tor_creator = BookTorrentCreator(book)
        self.assertEqual(
            tor_creator.get_destination(),
            'F/First Last/file.cbz.torrent'
        )

        # Test invalid creator
        book.update_record(creator_id=-1)
        db.commit()
        self.assertRaises(NotFoundError, tor_creator.get_destination)

    def test__get_target(self):
        book = self.add(db.book, dict(
            name='Test Book Torrent Creator',
            cbz='/path/to/file.cbz',
        ))
        tor_creator = BookTorrentCreator(book)
        self.assertEqual(
            tor_creator.get_target(),
            '/path/to/file.cbz'
        )


class TestCreatorTorrentCreator(TorrentTestCase):

    def test____init__(self):
        # No creator entity
        self.assertRaises(NotFoundError, CreatorTorrentCreator)

        creator = self.add(db.creator, dict(
            path_name='Test Creator Torrent Creator'
        ))
        tor_creator = CreatorTorrentCreator(creator)
        self.assertTrue(tor_creator)

    def test__archive(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))
        tor_creator = CreatorTorrentCreator(creator)
        # The target cbz directory won't exist
        self.assertRaises(NotFoundError, tor_creator.archive)

        tor_creator = CreatorTorrentCreator(creator)
        tor_creator.set_cbz_base_path(self._tmp_dir)
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        self.assertEqual(
            tor_file,
            '/tmp/test_torrent/tor/zco.mx/F/First Last.torrent'
        )

        creator_record = db(db.creator.id == creator.id).select().first()
        self.assertEqual(creator_record.torrent, tor_file)

    def test__get_destination(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(
            tor_creator.get_destination(),
            'F/First Last ({cid}.zco.mx).torrent'.format(cid=creator.id)
        )

    def test__get_target(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(
            tor_creator.get_target(),
            'applications/zcomx/private/var/cbz/zco.mx/F/First Last'
        )

    def test__set_cbz_base_path(self):
        creator = self.add(db.creator, dict(
            path_name='First Last',
        ))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(tor_creator._cbz_base_path, None)
        tor_creator.set_cbz_base_path(self._tmp_dir)
        self.assertEqual(tor_creator._cbz_base_path, self._tmp_dir)

class TestTorrentCreateError(LocalTestCase):
    def test_parent_init(self):
        msg = 'This is an error message.'
        try:
            raise TorrentCreateError(msg)
        except TorrentCreateError as err:
            self.assertEqual(str(err), msg)
        else:
            self.fail('TorrentCreateError not raised')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
