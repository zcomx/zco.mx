#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/creators.py

"""
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from applications.zcomx.modules.creators import \
    add_creator, \
    book_for_contributions, \
    can_receive_contributions, \
    contribute_link, \
    for_path, \
    formatted_name, \
    image_as_json, \
    on_change_name, \
    profile_onaccept, \
    torrent_link, \
    torrent_name, \
    torrent_url, \
    url, \
    url_name
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__add_creator(self):
        email = 'test__add_creator@example.com'

        def user_by_email(email):
            query = (db.auth_user.email == email)
            return db(query).select(db.auth_user.ALL).first()

        def creator_by_email(email):
            query = (db.creator.email == email)
            return db(query).select(db.creator.ALL).first()

        self.assertEqual(creator_by_email(email), None)
        self.assertEqual(user_by_email(email), None)

        # form has no email
        form = Storage({'vars': Storage()})
        add_creator(form)
        self.assertEqual(creator_by_email(email), None)

        # auth_user doesn't exist
        form.vars.email = email
        add_creator(form)
        self.assertEqual(creator_by_email(email), None)

        user = self.add(db.auth_user, dict(
            name='First Last',
            email=email,
        ))

        add_creator(form)
        creator = creator_by_email(email)
        self.assertTrue(creator)
        self._objects.append(creator)
        self.assertEqual(creator.email, email)
        self.assertEqual(creator.auth_user_id, user.id)
        self.assertEqual(creator.path_name, 'First Last')
        self.assertEqual(creator.urlify_name, 'first-last')

        before = db(db.creator).count()
        add_creator(form)
        after = db(db.creator).count()
        self.assertEqual(before, after)

    def test__book_for_contributions(self):
        creator = self.add(db.creator, dict(
            path_name='test__book_for_contributions',
        ))

        # Has no books
        self.assertEqual(book_for_contributions(db, creator), None)

        book_1 = self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=100.00,
        ))

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_1)

        # With two books, the higher remaining should be returned.
        book_2 = self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=99.00,
        ))

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_1)

        # If contributions are applied to book so that its remaining is
        # lower, the higher book should be returned.
        book_1.update_record(contributions_remaining=98.00)
        db.commit()

        got = book_for_contributions(db, creator)
        self.assertEqual(got, book_2)

    def test__can_receive_contributions(self):
        creator = self.add(db.creator, dict(
            path_name='test__can_receive_contributions',
            paypal_email='',
        ))

        self.assertFalse(can_receive_contributions(db, creator))

        tests = [
            #(paypal_email, expect)
            (None, False),
            ('', False),
            ('paypal@paypal.com', True),
        ]

        # With no book, all tests should return False
        for t in tests:
            creator.update_record(paypal_email=t[0])
            db.commit()
            self.assertFalse(can_receive_contributions(db, creator))

        self.add(db.book, dict(
            creator_id=creator.id,
            contributions_remaining=100.00,
        ))

        for t in tests:
            creator.update_record(paypal_email=t[0])
            db.commit()
            self.assertEqual(can_receive_contributions(db, creator), t[1])

    def test__contribute_link(self):
        empty = '<span></span>'

        creator = self.add(db.creator, dict(
            path_name='test__contribute_link',
        ))

        # As integer, creator_id
        link = contribute_link(db, creator.id)
        # Eg   <a href="/contributions/paypal?creator_id=3713" target="_blank">
        #       Contribute
        #      </a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?creator_id={i}'.format(i=creator.id)
        )

        # As Row, creator
        link = contribute_link(db, creator)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?creator_id={i}'.format(i=creator.id)
        )

        # Invalid id
        link = contribute_link(db, -1)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = contribute_link(db, creator, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = contribute_link(db, creator, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = contribute_link(db, creator, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'Contribute')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__for_path(self):

        # These names should remain unchanged.
        tests = [
            'Fred Smith',
            "Sean O'Reilly",
            'Sverre Årnes',
            'Bjørn Eidsvåg',
            'Frode Øverli',
            'Dražen Kovačević',
            'Yıldıray Çınar',
            'Alain Saint-Ogan',
            'José Muñoz',
            'Ralf König',
            'Ted Benoît',
            'Gilbert G. Groud',
            'Samuel (Mark) Clemens',
            'Alfa _Rant_ Tamil',
            'Too     Close',
        ]
        for t in tests:
            self.assertEqual(for_path(t), t)

        # These names are scrubed
        tests = [
            #(name, expect)
            ('Fred/ Smith', 'Fred Smith'),
            (r'Fred\ Smith', 'Fred Smith'),
            ('Fred? Smith', 'Fred Smith'),
            ('Fred% Smith', 'Fred Smith'),
            ('Fred* Smith', 'Fred Smith'),
            ('Fred: Smith', 'Fred Smith'),
            ('Fred| Smith', 'Fred Smith'),
            ('Fred" Smith', 'Fred Smith'),
            ('Fred< Smith', 'Fred Smith'),
            ('Fred> Smith', 'Fred Smith'),
            ('Kevin "Kev" Walker', 'Kevin Kev Walker'),
        ]

        for t in tests:
            self.assertEqual(for_path(t[0]), t[1])

    def test__formatted_name(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test Name'
        ))

        creator = self.add(db.creator, dict(
            email='test_name@example.com'
        ))

        # creator.auth_user_id not set
        self.assertEqual(formatted_name(creator), None)

        # Invalid auth_user.id
        creator.update_record(auth_user_id=-1)
        db.commit()
        self.assertEqual(formatted_name(creator), None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        # By Row instance
        self.assertEqual(formatted_name(creator), 'Test Name')
        # By integer instance
        self.assertEqual(formatted_name(creator.id), 'Test Name')

    def test__image_as_json(self):
        query = (db.creator.image != None)
        creator = db(query).select(db.creator.ALL).first()
        self.assertTrue(creator)

        image_json = image_as_json(db, creator.id)
        image = loads(image_json)
        self.assertTrue('files' in image.keys())
        self.assertEqual(len(image['files']), 1)
        self.assertEqual(
            sorted(image['files'][0].keys()),
            [
                'deleteType',
                'deleteUrl',
                'name',
                'size',
                'thumbnailUrl',
                'url',
            ]
        )

    def test__on_change_name(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test On Change Name'
        ))

        creator = self.add(db.creator, dict(
            email='test_on_change_name@example.com'
        ))

        self.assertEqual(creator.path_name, None)
        on_change_name(creator)
        # creator.auth_user_id not set
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, None)
        self.assertEqual(creator.urlify_name, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        on_change_name(creator)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, 'Test On Change Name')
        self.assertEqual(creator.urlify_name, 'test-on-change-name')

        # Test with creator.id
        # Reset
        creator.update_record(path_name=None, urlify_name=None)
        db.commit()
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, None)
        self.assertEqual(creator.urlify_name, None)
        on_change_name(creator.id)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, 'Test On Change Name')
        self.assertEqual(creator.urlify_name, 'test-on-change-name')

        # Modify creator name/handle unicode.
        auth_user.update_record(name="Slèzé d'Ruñez")
        db.commit()
        on_change_name(creator.id)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, "Slèzé d'Ruñez")
        self.assertEqual(creator.urlify_name, 'sleze-drunez')

    def test__profile_onaccept(self):
        auth_user = self.add(db.auth_user, dict(
            name='Test Profile Onaccept'
        ))

        creator = self.add(db.creator, dict(
            email='test_profile_onaccept@example.com',
        ))

        self.assertEqual(creator.path_name, None)
        self.assertEqual(creator.urlify_name, None)

        # form has no email
        form = Storage({'vars': Storage()})
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, None)
        self.assertEqual(creator.urlify_name, None)

        # creator.auth_user_id not set
        form.vars.id = auth_user.id
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, None)
        self.assertEqual(creator.urlify_name, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        profile_onaccept(form)
        creator = entity_to_row(db.creator, creator.id)
        self.assertEqual(creator.path_name, 'Test Profile Onaccept')
        self.assertEqual(creator.urlify_name, 'test-profile-onaccept')

    def test__torrent_link(self):
        empty = '<span></span>'

        creator = self.add(db.creator, dict(
            email='test__torrent_linke@example.com',
            path_name='First Last'
        ))

        # As integer, creator.id
        link = torrent_link(creator.id)
        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        # Eg  <a data-w2p_disable_with="default"
        #    href="/zcomx/FIXME/FIXME/all-first_last.torrent">all-first_last.torrent</a>
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'all-first_last.torrent')
        self.assertEqual(
            anchor['href'],
            '/zcomx/FIXME/FIXME/all-first_last.torrent'
        )

        # As Row, creator
        link = torrent_link(creator)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'all-first_last.torrent')
        self.assertEqual(
            anchor['href'],
            '/zcomx/FIXME/FIXME/all-first_last.torrent'
        )

        # Invalid id
        link = torrent_link(-1)
        self.assertEqual(str(link), empty)

        # Test components param
        components = ['aaa', 'bbb']
        link = torrent_link(creator, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'aaabbb')

        components = [IMG(_src='http://www.img.com', _alt='')]
        link = torrent_link(creator, components)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        img = anchor.img
        self.assertEqual(img['src'], 'http://www.img.com')

        # Test attributes
        attributes = dict(
            _href='/path/to/file',
            _class='btn btn-large',
            _target='_blank',
        )
        link = torrent_link(creator, **attributes)
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        self.assertEqual(anchor.string, 'all-first_last.torrent')
        self.assertEqual(anchor['href'], '/path/to/file')
        self.assertEqual(anchor['class'], 'btn btn-large')
        self.assertEqual(anchor['target'], '_blank')

    def test__torrent_name(self):
        creator = self.add(
            db.creator,
            dict(email='test__torrent_linke@example.com')
        )
        tests = [
            # (path_name, expect)
            (None, None),
            ('Prince', 'all-prince.torrent'),
            ('First Last', 'all-first_last.torrent'),
            ('first last', 'all-first_last.torrent'),
            ("Hélè d'Eñça",
                "all-h\xc3\xa9l\xc3\xa8_d'e\xc3\xb1\xc3\xa7a.torrent"),
        ]

        for t in tests:
            creator.update_record(path_name=t[0])
            db.commit()
            self.assertEqual(torrent_name(creator), t[1])

    def test__torrent_url(self):
        creator = self.add(
            db.creator,
            dict(email='test__torrent_linke@example.com')
        )

        # line-too-long (C0301): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        tests = [
            # (path_name, expect)
            (None, None),
            ('Prince', '/zcomx/FIXME/FIXME/all-prince.torrent'),
            ('First Last', '/zcomx/FIXME/FIXME/all-first_last.torrent'),
            ('first last', '/zcomx/FIXME/FIXME/all-first_last.torrent'),
            ("Hélè d'Eñça",
                '/zcomx/FIXME/FIXME/all-h%C3%A9l%C3%A8_d%27e%C3%B1%C3%A7a.torrent'),
        ]

        for t in tests:
            creator.update_record(path_name=t[0])
            db.commit()
            self.assertEqual(torrent_url(creator), t[1])

    def test__url(self):
        creator = self.add(db.creator, dict(email='test__url@example.com'))

        tests = [
            # (path_name, expect)
            (None, None),
            ('Prince', '/Prince'),
            ('First Last', '/First_Last'),
            ('first last', '/first_last'),
            ("Hélè d'Eñça", '/H%C3%A9l%C3%A8_d%27E%C3%B1%C3%A7a'),
        ]

        for t in tests:
            creator.update_record(path_name=t[0])
            db.commit()
            self.assertEqual(url(creator), t[1])

    def test__url_name(self):
        creator = self.add(db.creator, dict(
            email='test__url_name@example.com'
        ))

        tests = [
            # (path_name, expect)
            (None, None),
            ('Prince', 'Prince'),
            ('First Last', 'First_Last'),
            ('first last', 'first_last'),
            ("Hélè d'Eñça", "H\xc3\xa9l\xc3\xa8_d'E\xc3\xb1\xc3\xa7a"),
        ]

        for t in tests:

            creator.update_record(path_name=t[0])
            db.commit()
            self.assertEqual(url_name(creator), t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
