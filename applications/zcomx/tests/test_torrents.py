#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/torrents.py

"""
import os
import shutil
import unittest
from gluon import *
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.torrentparse import TorrentParser
from applications.zcomx.modules.torrents import \
    AllTorrentCreator, \
    BaseTorrentCreator, \
    BookTorrentCreator, \
    CreatorTorrentCreator, \
    P2PNotifier, \
    P2PNotifyError, \
    TorrentCreateError
from applications.zcomx.modules.tests.runner import LocalTestCase

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
            cls._tmp_dir, 'cbz', 'zco.mx', 'F', 'FirstLast', 'subdir')
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
        tor_creator.set_destination('F/FirstLast/file.torrent')
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        self.assertEqual(
            tor_file,
            '/tmp/test_torrent/tor/zco.mx/F/FirstLast/file.torrent'
        )
        self.assertTrue(os.path.exists(tor_file))

        parser = TorrentParser(tor_file)
        self.assertEqual(
            parser.get_tracker_url(),
            'http://bt.zco.mx:6969/announce'
        )
        self.assertEqual(
            parser.get_client_name(),
            'mktorrent 1.1'
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
            'mktorrent 1.1'
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
            'mktorrent 1.1'
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
        book = self.add(Book, dict(
            name='Test Book Torrent Creator'
        ))
        tor_creator = BookTorrentCreator(book)
        self.assertTrue(tor_creator)

    def test__archive(self):
        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))
        book = self.add(Book, dict(
            name='My Book',
            publication_year=1999,
            creator_id=creator.id,
            book_type_id=BookType.by_name('one-shot').id,
        ))
        tor_creator = BookTorrentCreator(book)
        # book.cbz is not defined, should fail
        self.assertRaises(TorrentCreateError, tor_creator.archive)

        book = Book.from_updated(book, dict(cbz=self._test_file))
        tor_creator = BookTorrentCreator(book)
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        self.assertEqual(
            tor_file,
            os.path.join(
                '/tmp/test_torrent/tor/zco.mx',
                'F/FirstLast/My Book (1999) ({i}.zco.mx).cbz.torrent'.format(
                    i=creator.id)
            )
        )

        got = Book.from_id(book.id)
        self.assertEqual(got.torrent, tor_file)

    def test__get_destination(self):
        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))

        book = self.add(Book, dict(
            name='My Book',
            publication_year=1999,
            creator_id=creator.id,
            book_type_id=BookType.by_name('one-shot').id,
        ))

        tor_creator = BookTorrentCreator(book)
        self.assertEqual(
            tor_creator.get_destination(),
            'F/FirstLast/My Book (1999) ({i}.zco.mx).cbz.torrent'.format(
                i=creator.id)
        )

    def test__get_target(self):
        book = self.add(Book, dict(
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
        creator = Creator(dict(
            email='test____init__@gmail.com'
        ))
        tor_creator = CreatorTorrentCreator(creator)
        self.assertTrue(tor_creator)

    def test__archive(self):
        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))

        tor_creator = CreatorTorrentCreator(creator)
        # The target cbz directory won't exist
        self.assertRaises(LookupError, tor_creator.archive)

        tor_creator = CreatorTorrentCreator(creator)
        tor_creator.set_cbz_base_path(self._tmp_dir)
        tor_file = tor_creator.archive(base_path=self._tmp_dir)
        fmt = '/tmp/test_torrent/tor/zco.mx/F/FirstLast ({i}.zco.mx).torrent'
        self.assertEqual(tor_file, fmt.format(i=creator.id))

        updated_creator = Creator.from_id(creator.id)
        self.assertEqual(updated_creator.torrent, tor_file)

    def test__get_destination(self):
        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(
            tor_creator.get_destination(),
            'F/FirstLast ({cid}.zco.mx).torrent'.format(cid=creator.id)
        )

    def test__get_target(self):
        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(
            tor_creator.get_target(),
            'applications/zcomx/private/var/cbz/zco.mx/F/FirstLast'
        )

    def test__set_cbz_base_path(self):
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212

        auth_user = self.add(AuthUser, dict(name='First Last'))
        creator = self.add(Creator, dict(auth_user_id=auth_user.id))

        tor_creator = CreatorTorrentCreator(creator)
        self.assertEqual(tor_creator._cbz_base_path, None)
        tor_creator.set_cbz_base_path(self._tmp_dir)
        self.assertEqual(tor_creator._cbz_base_path, self._tmp_dir)


class TestP2PNotifier(TorrentTestCase):

    def test____init__(self):
        notifier = P2PNotifier('aaa.cbz')
        self.assertTrue(notifier)

    def test__notify(self):
        notifier = P2PNotifier(self._test_file)

        # This test should fail. The test server doesn't have the
        # required tools installed. If the exception is raised, it's
        # proof the script was run, which is all we need to test.
        self.assertRaises(
            P2PNotifyError,
            notifier.notify
        )


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
