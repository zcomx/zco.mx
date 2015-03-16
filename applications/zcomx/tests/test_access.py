#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/access.py
"""
import unittest
import urllib2
from gluon.http import HTTP
from applications.zcomx.modules.access import requires_admin_ip
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
        auth.user= None
        self.assertEqual(func(), 'Success')
        self.assertEqual(login_func(), 'Not logged in')

        # Valid ip, logged in
        request.client = admin_ip
        auth.user= 'myuser'          # Anything truthy will work
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


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
