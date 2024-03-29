#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/access.py
"""
import unittest
from gluon.storage import Storage
from applications.zcomx.modules.access import \
    requires_admin_ip, \
    requires_agreed_to_terms, \
    requires_login_if_configured
from applications.zcomx.modules.creators import \
    AuthUser, \
    Creator
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestFunctions(LocalTestCase):
    # pylint: disable=invalid-name

    _auth_user = None
    _request_client = None
    _admin_ip = None
    _non_admin_ip = '123.123.123.123'

    @classmethod
    def setUpClass(cls):
        env = globals()
        auth = env['auth']
        cls._auth_user = auth.user
        request = env['request']
        cls._request_client = request.client
        cls._admin_ip = env['local_settings'].admin_ips.split(',')[0]

    @classmethod
    def tearDownClass(cls):
        env = globals()
        auth = env['auth']
        auth.user = cls._auth_user
        request = env['request']
        request.client = cls._request_client

    def test__requires_admin_ip(self):
        env = globals()
        request = env['request']
        auth = env['auth']

        def otherwise():
            return 'Not logged in'

        @requires_admin_ip(requires_login=False, otherwise=otherwise)
        def func():
            return 'Success'

        @requires_admin_ip(requires_login=True, otherwise=otherwise)
        def login_func():
            return 'Success'

        # Valid ip, not logged in
        request.client = self._admin_ip
        auth.user = None
        self.assertEqual(func(), 'Success')
        self.assertEqual(login_func(), 'Not logged in')

        # Valid ip, logged in
        request.client = self._admin_ip
        auth.user = 'myuser'          # Anything truthy will work
        self.assertEqual(func(), 'Success')
        self.assertEqual(login_func(), 'Success')

        # Invalid ip, (login status should be irrelevant.
        request.client = self._non_admin_ip
        self.assertRaisesHTTP(303, func)
        self.assertRaisesHTTP(303, login_func)

    def test__requires_agreed_to_terms(self):
        env = globals()
        auth = env['auth']
        session = env['session']
        session.auth = Storage({})              # Not logged in

        auth_user = self.add(AuthUser, dict(
            email='tests__requires_agreed_to_terms@example.com',
        ))

        creator = self.add(Creator, dict(
            auth_user_id=auth_user.id,
            agreed_to_terms=False,
        ))

        auth.user = auth_user

        @requires_agreed_to_terms()
        def func():
            return 'Success'

        # agreed_to_terms=False, should not permit access
        self.assertRaisesHTTP(303, func)

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
        self.assertRaisesHTTP(303, func)

        # agreed_to_terms=False, should permit access
        Creator.from_updated(creator, dict(agreed_to_terms=True))
        self.assertEqual(func(), 'Success')

    def test__requires_login_if_configured(self):
        env = globals()
        auth = env['auth']

        def otherwise():
            return 'Not logged in'

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
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
