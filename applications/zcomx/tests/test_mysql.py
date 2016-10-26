#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/mysql.py

"""

import os
import unittest
from gluon.storage import Storage
from applications.zcomx.modules.mysql import \
    LocalMySQL, \
    soundex
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=C0111
# R0904: *Too many public methods (%%s/%%s)*
# pylint: disable=R0904


class TestLocalMySQL(LocalTestCase):

    def test____init__(self):
        local_mysql = LocalMySQL()
        self.assertTrue(local_mysql)  # Creates object
        self.assertTrue(local_mysql.port)  # Sets port
        self.assertTrue(local_mysql.sqldb)  # Sets sqldb
        return

    def test__set_port(self):
        port_1 = '1111'
        port_2 = '2222'
        port_3 = '3333'
        local_mysql = LocalMySQL(port=port_1)
        self.assertTrue(local_mysql.port, port_1)  # Provided port is used

        save_env_port = os.environ.get('MYSQL_TCP_PORT')

        del os.environ['MYSQL_TCP_PORT']
        local_mysql = LocalMySQL()
        # No port, no http env var, no uses env var, not set
        self.assertFalse(local_mysql.port)

        os.environ['MYSQL_TCP_PORT'] = port_2
        local_mysql = LocalMySQL()
        # No port, no http env var, uses env var
        self.assertTrue(local_mysql.port, port_2)

        request = Storage()
        request.env = Storage()
        request.env.mysql_tcp_port = port_3

        local_mysql = LocalMySQL()
        self.assertTrue(local_mysql.port, port_3)  # No port, uses http env var

        os.environ['MYSQL_TCP_PORT'] = save_env_port
        return

    def test__set_sqldb(self):
        sqldb_1 = '__test_sqldb_1__'
        local_mysql = LocalMySQL(sqldb=sqldb_1)
        self.assertEqual(local_mysql.sqldb, sqldb_1)  # Uses provided

        local_mysql.database = 'DB'
        local_mysql.user = 'USER'
        local_mysql.password = 'PWD'
        local_mysql.hostname = 'HOSTNAME'
        local_mysql.port = 'PORT'
        local_mysql.charset = 'CHARS'
        local_mysql.set_sqldb()
        self.assertEqual(local_mysql.sqldb,
                         'mysql://USER:PWD@HOSTNAME:PORT/DB?set_encoding=CHARS'
                         )
        return

    def test____repr__(self):
        # C0301: *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        sqldb_1 = '_test____repr__'
        local_mysql = LocalMySQL(sqldb=sqldb_1)
        port = os.environ.get('MYSQL_TCP_PORT') or '3306'
        self.assertEqual(local_mysql.__repr__(),
            """LocalMySQL(user=None, password=None, hostname='127.0.0.1', port='{p}', database=None, charset='utf8')""".format(p=port))
        local_mysql = LocalMySQL(
            user='username',
            password='12345',
            database='mydb',
        )
        self.assertEqual(local_mysql.__repr__(),
            """LocalMySQL(user='username', password='12345', hostname='127.0.0.1', port='{p}', database='mydb', charset='utf8')""".format(p=port))


class TestFunctions(LocalTestCase):
    def test__soundex(self):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        if db._dbname != 'mysql':
            return
        tests = [
                #(value, expect)
                ('', ''),
                (None, ''),
                ('abc', 'A120'),
                ('ABC', 'A120'),
                ('remington firearm', 'R5235165'),
                ("""a!@#$%^&*()_+{}|[]\:"<>?;',./a""", 'A000'),
                ]
        for t in tests:
            self.assertEqual(soundex(db, t[0]), t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
