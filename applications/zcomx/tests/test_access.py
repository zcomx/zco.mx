#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/access.py
"""
import unittest
from gluon.http import HTTP
from gluon.storage import Storage
from applications.zcomx.modules.access import \
    requires_admin_ip, \
    requires_agreed_to_terms, \
    requires_login_if_configured
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__requires_admin_ip(self):
        env = globals()
        request = env['request']
        auth = env['auth']

        admin_ip = '108.162.141.78'
        fake_ip = '123.123.123.123'

        otherwise = lambda: 'Not logged in'

        @requires_admin_ip(requires_login=False, otherwise=otherwise)
        def func():
            return 'Success'

        @requires_admin_ip(requires_login=True, otherwise=otherwise)
        def login_func():
            return 'Success'

        # Valid ip, not logged in
        request.client = admin_ip
        auth.user = None
        self.assertEqual(func(), 'Success')
        self.assertEqual(login_func(), 'Not logged in')

        # Valid ip, logged in
        request.client = admin_ip
        auth.user = 'myuser'          # Anything truthy will work
        self.assertEqual(func(), 'Success')
        self.assertEqual(login_func(), 'Success')

        # Invalid ip, (login status should be irrelevant.
        request.client = fake_ip
        try:
            func()
        except HTTP as err:
            self.assertEqual(str(err), '303 SEE OTHER')
        else:
            self.fail('HTTP exception not raised.')

        try:
            login_func()
        except HTTP as err:
            self.assertEqual(str(err), '303 SEE OTHER')
        else:
            self.fail('HTTP exception not raised.')

    def test__requires_agreed_to_terms(self):
        env = globals()
        auth = env['auth']
        session = env['session']
        session.auth = Storage({})              # Not logged in

        auth_user = self.add(db.auth_user, dict(
            email='tests__requires_agreed_to_terms@example.com',
        ))

        creator = self.add(db.creator, dict(
            auth_user_id=auth_user.id,
            agreed_to_terms=False,
        ))

        auth.user = auth_user

        @requires_agreed_to_terms()
        def func():
            return 'Success'

        # agreed_to_terms=False, should not permit access
        try:
            func()
        except HTTP as err:
            self.assertEqual(str(err), '303 SEE OTHER')
        else:
            self.fail('HTTP exception not raised.')

        # auth_user is impersonating, should permit access
        # Simulate a logged in session
        session.auth = Storage(
            user=auth_user,
            impersonator='_fake_impersonator_'
        )
        self.assertTrue(auth.is_logged_in())
        self.assertTrue(auth.is_impersonating())
        self.assertEqual(func(), 'Success')

        # Reset membership
        session.auth = Storage(user=auth_user)   # No longer impersonating
        try:
            func()
        except HTTP as err:
            self.assertEqual(str(err), '303 SEE OTHER')
        else:
            self.fail('HTTP exception not raised.')

        # agreed_to_terms=False, should permit access
        creator.update_record(agreed_to_terms=True)
        db.commit()
        self.assertEqual(func(), 'Success')

    def test__requires_login_if_configured(self):
        env = globals()
        auth = env['auth']

        otherwise = lambda: 'Not logged in'

        local_settings = Storage({'require_login': True})
        @requires_login_if_configured(local_settings, otherwise=otherwise)
        def as_true():
            return 'Success'

        local_settings = Storage({'require_login': False})
        @requires_login_if_configured(local_settings, otherwise=otherwise)
        def as_false():
            return 'Success'

        # Not logged in
        auth.user = None
        self.assertEqual(as_true(), 'Not logged in')
        self.assertEqual(as_false(), 'Success')

        # Logged in
        auth.user = 'myuser'          # Anything truthy will work
        self.assertEqual(as_true(), 'Success')
        self.assertEqual(as_false(), 'Success')


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
