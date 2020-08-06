#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/stickon/tools.py
"""
import os
import unittest
from configparser import NoSectionError
from bs4 import BeautifulSoup
from gluon.shell import env
from gluon.storage import Storage
from applications.zcomx.modules.stickon.tools import (
    ExposeImproved,
    MigratedModelDb,
    ModelDb,
    SettingsLoader,
)
from applications.zcomx.modules.tests.runner import LocalTestCase

# R0904: Too many public methods
# pylint: disable=C0111,R0904

APPLICATION = __file__.split(os.sep)[-4]
APP_ENV = env(APPLICATION, import_models=False)


class TestExposeImproved(LocalTestCase):

    def test____init__(self):
        expose = ExposeImproved()
        self.assertTrue('.svg' in expose.image_extensions)

    def test__isimage(self):
        tests = [
            # (path, expect),
            ('/path/to/file.bmp', True),
            ('/path/to/file.png', True),
            ('/path/to/file.jpg', True),
            ('/path/to/file.jpeg', True),
            ('/path/to/file.gif', True),
            ('/path/to/file.tiff', True),
            ('/path/to/file.svg', True),
            ('/path/to/file.doc', False),
            ('/path/to/file.txt', False),
            ('/path/to/file', False),
        ]
        for t in tests:
            self.assertEqual(ExposeImproved.isimage(t[0]), t[1])

    def test__xml(self):
        base = 'applications/zcomx/static'
        basename = 'Test Xml'
        expose = ExposeImproved(base=base, basename=basename)
        xml = expose.xml()
        soup = BeautifulSoup(str(xml), 'html.parser')

        h2 = soup.find('h2')
        self.assertEqual(h2.span.a.string, basename)

        h3s = soup.findAll('h3')
        self.assertEqual(len(h3s), 2)
        self.assertEqual(h3s[0].string, 'Folders')
        self.assertEqual(h3s[1].string, 'Files')

        folders_table = h3s[0].nextSibling
        anchors = folders_table.findAll('a')
        folder_names = [x.string for x in anchors]
        self.assertTrue('css' in folder_names)

        files_table = h3s[1].nextSibling
        anchors = files_table.findAll('a')
        file_names = [x.string for x in anchors]
        self.assertTrue('404.html' in file_names)

        expose = ExposeImproved(
            base=base, basename=basename, display_breadcrumbs=False)
        xml = expose.xml()
        soup = BeautifulSoup(str(xml), 'html.parser')
        # print soup.prettify()

        h2s = soup.findAll('h2')
        self.assertEqual(len(h2s), 0)


class TestMigratedModelDb(LocalTestCase):

    def test_parent__init__(self):
        model_db = MigratedModelDb(APP_ENV)
        self.assertTrue(model_db)
        self.assertEqual(model_db.migrate, True)


class TestModelDb(LocalTestCase):

    def test____init__(self):
        model_db = ModelDb(APP_ENV)
        self.assertTrue(model_db)

    def test__load(self):
        # W0212: *Access to a protected member %s of a client class*
        # pylint: disable=W0212

        #
        # Test with default config file.
        #
        model_db = ModelDb(APP_ENV)
        model_db.load()

        self.assertEqual(model_db.migrate, False)

        # response.static_version is set
        self.assertRegex(
            model_db.environment['response'].static_version,
            r'\d+\.\d+\.\d+'
        )

        #
        # Test with custom config file.
        #
        config_text = """
{
    "web2py": {
        "auth": {
            "settings": {
                "registration_requires_verification": true,
                "registration_requires_approval": false
            }
        },
        "mail": {
            "settings": {
                "server": "smtp.mymailserver.com:587",
                "sender": "myusername@example.com",
                "login": "myusername:fakepassword"
            }
        },
        "response": {
            "static_version": "2013.11.291"
        }
    },
    "app": {
        "admin_email": "myadmin@example.com",
        "database": "shared",
        "db_adapter": "sqlite",
        "db_uri": "http://zcomx.sqlite",
        "hmac_key": "12345678901234",
        "version": "0.1"
    }
}
"""
        f_text = '/tmp/TestModelDb_test__init__.json'
        _config_file_from_text(f_text, config_text)

        model_db = ModelDb(APP_ENV, config_file=f_text)
        model_db.load(init_all=False)

        self.assertEqual(
            model_db.environment['response'].static_version, '2013.11.291')

        os.unlink(f_text)

    def test__get_server_mode(self):
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        model_db = ModelDb(APP_ENV)
        model_db.load(init_all=False)
        # get_server_mode doesn't get called  if init_all=False
        self.assertEqual(model_db._server_mode, None)

        # Test cache access
        model_db._server_mode = None
        self.assertEqual(model_db.get_server_mode(), 'test')
        model_db._server_mode = '_fake_'
        self.assertEqual(model_db.get_server_mode(), '_fake_')
        model_db._server_mode = None       # Reset
        self.assertEqual(model_db.get_server_mode(), 'test')

    def test__verify_email_onaccept(self):
        pass        # Not testable


class TestSettingsLoader(LocalTestCase):

    def test____init__(self):
        settings_loader = SettingsLoader()
        self.assertTrue(settings_loader)  # Creates object
        # No config file, no settings
        self.assertEqual(settings_loader.settings, {})

    def test____repr__(self):
        settings_loader = SettingsLoader(config_file=None, application='app')
        self.assertEqual(
            settings_loader.__repr__(),
            """SettingsLoader(config_file=None, application='app'"""
        )

    def test__get_settings(self):
        settings_loader = SettingsLoader()
        settings_loader.get_settings()
        # No config file, no settings
        self.assertEqual(settings_loader.settings, {})

        tests = [
            {
                'label': 'empty file',
                'expect': {},
                'raise': ValueError,
                'text': '',
            },
            {
                'label': 'empty json struct',
                'expect': {},
                'raise': None,
                'text': '{}',
            },
            {
                'label': 'no web2py section',
                'expect': {},
                'raise': None,
                'text': """
{
    "fake_section": {
        "setting": "value"
    }
}
""",
            },
            {
                'label': 'web2py section empty',
                'expect': {},
                'raise': None,
                'text': """
{
    "web2py": {}
}
""",
            },
            {
                'label': 'web2py one local setting',
                'expect': {'app': {'version': '1.11'}},
                'raise': None,
                'text': """
{
    "app": {
        "version": "1.11"
    }
}
""",
            },
            {
                'label': 'web2py two local setting',
                'expect': {
                    'app': {'username': 'jimk', 'version': '1.11'}
                },
                'raise': None,
                'text': """
{
    "app": {
        "username": "jimk",
        "version": "1.11"
    }
}
""",
            },
            {
                'label': 'app section',
                'expect': {
                    'app': {
                        'email': 'abc@gmail.com',
                        'version': '2.22'
                    },
                    'username': 'jimk',
                    'version': '1.11'
                },
                'raise': None,
                'text': """
{
    "web2py": {
        "username": "jimk",
        "version": "1.11"
    },
    "app": {
        "version": "2.22",
        "email": "abc@gmail.com"
    }
}
""",
            },
            {
                'label': 'app section auth/mail',
                'expect': {
                    'auth': {
                        'settings': {'username': 'admin', 'version': '5.55'},
                    },
                    'mail': {
                        'settings': {'username': 'mailer', 'version': '6.66'},
                    },
                    'app': {
                        'email': 'abc@gmail.com',
                        'username': 'jimk',
                        'version': '2.22'
                    }
                },
                'raise': None,
                'text': """
{
    "web2py": {
        "auth": {
            "settings": {
                "username": "admin",
                "version": "5.55"
            }
        },
        "mail": {
            "settings": {
                "username": "mailer",
                "version": "6.66"
            }
        }
    },
    "app": {
        "email": "abc@gmail.com",
        "username": "jimk",
        "version": "2.22"
    }
}
""",
            },
        ]

        f_text = '/tmp/settings_loader_config.json'
        for t in tests:
            settings_loader = SettingsLoader()
            _config_file_from_text(f_text, t['text'])
            settings_loader.config_file = f_text
            settings_loader.application = 'app'
            if t['raise']:
                self.assertRaises(t['raise'],
                                  settings_loader.get_settings)
            else:
                settings_loader.get_settings()
            self.assertEqual(settings_loader.settings, t['expect'])

        # Test datatype handling.
        text = \
            """
{
    "app": {
        "s01_true": true,
        "s02_false": false,
        "s03_int": 123,
        "s04_float": 123.45,
        "s05_str1": "my setting",
        "s06_str2": "'my setting'",
        "s07_str_true": "True",
        "s08_str_int": "123",
        "s09_str_float": "123.45"
    }
}
"""
        settings_loader = SettingsLoader()
        _config_file_from_text(f_text, text)
        settings_loader.config_file = f_text
        settings_loader.application = 'app'
        settings_loader.get_settings()

        self.assertEqual(
            sorted(settings_loader.settings['app'].keys()),
            [
                's01_true',
                's02_false',
                's03_int',
                's04_float',
                's05_str1',
                's06_str2',
                's07_str_true',
                's08_str_int',
                's09_str_float',
            ]
        )

        s_app = settings_loader.settings['app']
        self.assertEqual(s_app['s01_true'], True)
        self.assertEqual(s_app['s02_false'], False)
        self.assertEqual(s_app['s03_int'], 123)
        self.assertEqual(s_app['s04_float'], 123.45)
        self.assertEqual(s_app['s05_str1'], 'my setting')
        self.assertEqual(s_app['s06_str2'], "'my setting'")
        self.assertEqual(s_app['s07_str_true'], 'True')
        self.assertEqual(s_app['s08_str_int'], '123')
        self.assertEqual(s_app['s09_str_float'], '123.45')

        os.unlink(f_text)

    def test__import_settings(self):
        settings_loader = SettingsLoader()
        settings_loader.get_settings()
        application = 'app'
        group = 'app'
        storage = Storage()
        self.assertEqual(list(storage.keys()), [])  # Initialized storage is empty
        settings_loader.import_settings(group, storage)
        # No config file, storage unchanged
        self.assertEqual(list(storage.keys()), [])

        f_text = '/tmp/settings_loader_config.json'

        # Test defaults and section overrides
        text = \
            """
{
    "web2py": {
        "username": "jimk",
        "version": "1.11"
    },
    "app": {
        "email": "abc@gmail.com",
        "username": "jimk",
        "version": "2.22"
    }
}
"""
        _config_file_from_text(f_text, text)
        settings_loader.config_file = f_text
        settings_loader.application = application

        settings_loader.get_settings()
        settings_loader.import_settings('zzz', storage)
        # Group has no settings, storage unchanged
        self.assertEqual(list(storage.keys()), [])
        settings_loader.import_settings(group, storage)
        self.assertEqual(
            sorted(storage.keys()),
            ['email', 'username', 'version']
        )

        # Group has settings, storage changed
        self.assertEqual(storage['email'], 'abc@gmail.com')
        self.assertEqual(storage['username'], 'jimk')
        self.assertEqual(storage['version'], '2.22')

        os.unlink(f_text)

    def test__scrub_unicode(self):
        tests = [
            # (raw_value, expect)
            ('abc', 'abc'),
            (123, 123),
            ('abc', 'abc'),
            (['abc'], ['abc']),
        ]
        for t in tests:
            self.assertEqual(SettingsLoader.scrub_unicode(t[0]), t[1])


def _config_file_from_text(filename, text):

    # R0201: *Method could be a function*
    # pylint: disable=R0201

    f = open(filename, 'w')
    f.write(text)
    f.close()
    return


if __name__ == '__main__':
    unittest.main()
