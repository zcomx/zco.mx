#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_environ.py

Test suite for zcomx/modules/environ.py

"""
import os
import unittest
from gluon.globals import Request
from applications.zcomx.modules.environ import \
        ServerEnvironmentError, \
        has_terminal, \
        server_production_mode
from applications.zcomx.modules.test_runner import LocalTestCase
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    _env = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._env = os.environ.copy()

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._env.items():
            os.environ[k] = v

    def test__has_terminal(self):

        tests = [
                #(user, term, has_terminal, expect)
                ('', '', False, False),
                ('', '', True, True),
                ('http', '_fake_', None, False),
                ('root', '_fake_', None, True),
                ('root', None, None, False),
                ]

        for t in tests:
            os.environ['USER'] = t[0]
            if t[1]:
                os.environ['TERM'] = t[1]
            else:
                if 'TERM' in os.environ:
                    del os.environ['TERM']
            if t[2]:
                os.environ['HAS_TERMINAL'] = 'True'
            else:
                if 'HAS_TERMINAL' in os.environ:
                    del os.environ['HAS_TERMINAL']
            self.assertEqual(has_terminal(), t[3])

    def test__server_production_mode(self):
        default = '_test__server_production_mode_'

        # Test that environment is prepared properly.
        self.assertTrue('SERVER_PRODUCTION_MODE' in os.environ)
        self.assertTrue('MYSQL_TCP_PORT' in os.environ)

        request = Request(globals())
        if 'SERVER_PRODUCTION_MODE' in os.environ:
            del os.environ['SERVER_PRODUCTION_MODE']
        self.assertRaises(ServerEnvironmentError, server_production_mode,
                request)

        request.env.server_production_mode = default
        self.assertRaises(ServerEnvironmentError, server_production_mode,
                request)

        request.env.http_host = '_something_'   # Anything but '127.0.0.1:8000'
        self.assertEqual(server_production_mode(request), default)

        request.env.server_production_mode = None
        request.env.http_host = '127.0.0.1:8000'
        self.assertRaises(ServerEnvironmentError, server_production_mode,
                request)

        os.environ['SERVER_PRODUCTION_MODE'] = default
        self.assertEqual(server_production_mode(request), default)


if __name__ == '__main__':
    unittest.main()
