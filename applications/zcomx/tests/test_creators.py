#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/creators.py

"""
import unittest
from gluon import *
from gluon.contrib.simplejson import loads
from gluon.storage import Storage
from applications.zcomx.modules.creators import \
    add_creator, \
    for_path, \
    image_as_json, \
    set_creator_path_name, \
    set_path_name, \
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

        user_id = db.auth_user.insert(
            name='First Last',
            email=email,
        )
        db.commit()
        user = db(db.auth_user.id == user_id).select().first()
        self._objects.append(user)

        add_creator(form)
        creator = creator_by_email(email)
        self.assertTrue(creator)
        self._objects.append(creator)
        self.assertEqual(creator.email, email)
        self.assertEqual(creator.auth_user_id, user_id)
        self.assertEqual(creator.path_name, 'First Last')

        before = db(db.creator).count()
        add_creator(form)
        after = db(db.creator).count()
        self.assertEqual(before, after)

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

    def test__set_creator_path_name(self):
        auth_user_id = db.auth_user.insert(
            name='Test Set Creator Path Name'
        )
        auth_user = entity_to_row(db.auth_user, auth_user_id)
        self._objects.append(auth_user)

        creator_id = db.creator.insert(
            email='test_set_creator_path_name@example.com',
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

        self.assertEqual(creator.path_name, None)

        # form has no email
        form = Storage({'vars': Storage()})
        set_creator_path_name(form)
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, None)

        # creator.auth_user_id not set
        form.vars.id = auth_user.id
        set_creator_path_name(form)
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        set_creator_path_name(form)
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, 'Test Set Creator Path Name')

    def test__set_path_name(self):

        auth_user_id = db.auth_user.insert(
            name='Test Set Path Name'
        )
        db.commit()
        auth_user = entity_to_row(db.auth_user, auth_user_id)
        self._objects.append(auth_user)

        creator_id = db.creator.insert(
            email='test_set_path_name@example.com'
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

        self.assertEqual(creator.path_name, None)
        set_path_name(creator)
        # creator.auth_user_id not set
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, None)

        creator.update_record(auth_user_id=auth_user.id)
        db.commit()
        set_path_name(creator)
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, 'Test Set Path Name')

        # Test with creator_id
        # Reset
        creator.update_record(path_name=None)
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, None)
        set_path_name(creator_id)
        creator = entity_to_row(db.creator, creator_id)
        self.assertEqual(creator.path_name, 'Test Set Path Name')

    def test__url(self):
        creator_id = db.creator.insert(
            email='test__url@example.com'
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

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
        creator_id = db.creator.insert(
            email='test__url_name@example.com'
        )
        db.commit()
        creator = entity_to_row(db.creator, creator_id)
        self._objects.append(creator)

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
