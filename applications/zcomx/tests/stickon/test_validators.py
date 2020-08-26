#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/stickon/validators.py

"""
import string
import unittest
from gluon import *
from gluon.storage import Storage
from gluon.validators import (
    ValidationError,
)
from applications.zcomx.modules.creators import Creator
from applications.zcomx.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_NOT_IN_DB_ANYCASE, \
    IS_NOT_IN_DB_SCRUBBED, \
    IS_TWITTER_HANDLE, \
    IS_URL_FOR_DOMAIN, \
    as_per_type

from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestIS_ALLOWED_CHARS(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_ALLOWED_CHARS()
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test__validate(self):
        default_err = 'This is a test error message.'

        def run(validator, value, error):
            result = value
            err_msg = ''
            if error is None:
                result = validator.validate(value)
                self.assertEqual(result, value)
            else:
                try:
                    validator.validate(value)
                except ValidationError as err:
                    err_msg = str(err)
                    pass
                else:
                    self.fail('ValidationError not raised')

            return result, err_msg

        # Test not_allowed default
        validator = IS_ALLOWED_CHARS(error_message=default_err)
        run(validator, string.ascii_letters, None)
        run(validator, string.digits, None)
        run(validator, string.punctuation, None)

        # Test not_allowed as string
        validator = IS_ALLOWED_CHARS(
            not_allowed='a', error_message=default_err)
        run(validator, 'abc', default_err)
        run(validator, 'bcd', None)
        validator = IS_ALLOWED_CHARS(
            not_allowed='a<>$z', error_message=default_err)
        run(validator, 'abc', default_err)
        run(validator, 'bcd', None)
        run(validator, 'xyz', default_err)
        run(validator, 'bbb<', default_err)
        run(validator, 'bbb!', None)

        # Test not_allowed as list
        validator = IS_ALLOWED_CHARS(
            not_allowed=['a', 'c', 'e'], error_message=default_err)
        run(validator, 'abc', default_err)
        run(validator, 'bdf', None)

        # Test not_allowed as tuples
        not_allowed = [
            (r'/', 'slash'),
            ('%', 'percent'),
            ('*', 'asterisk'),
            ('|', 'pipe'),
            ('<', 'less than'),
            ('>', 'greater than'),
        ]
        validator = IS_ALLOWED_CHARS(
            not_allowed=not_allowed, error_message=default_err)
        run(validator, 'abc', None)
        result, err_msg = run(validator, 'ab%c', default_err)
        self.assertTrue(result, 'abc')
        self.assertTrue('percent' in err_msg)


class TestIS_NOT_IN_DB_ANYCASE(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_NOT_IN_DB_ANYCASE(db, db.creator.email)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test__validate(self):
        email = 'anycase@example.com'
        email_2 = 'anycase_2@example.com'
        error_msg = 'is_not_in_db_anycase error'

        db.creator.insert(email=email)
        db.commit()
        creator = Creator.from_key(dict(email=email))
        self.assertTrue(creator)
        self.assertEqual(creator.email, email)
        self._objects.append(creator)

        tests = [
            #(email, error)
            (email, error_msg),           # In db, so not ok
            (email_2, None),              # Not in db, so ok
            (email.upper(), error_msg),   # lowercase is in db, not ok
            (email_2.upper(), None),      # Not in db, so ok
        ]
        for t in tests:
            if t[1] is None:
                self.assertEqual(
                    IS_NOT_IN_DB_ANYCASE(
                        db,
                        db.creator.email,
                        error_message=error_msg,
                    ).validate(t[0]),
                    t[0]
                )
            else:
                self.assertRaises(
                    ValidationError,
                    IS_NOT_IN_DB_ANYCASE(
                        db,
                        db.creator.email,
                        error_message=error_msg,
                    ).validate,
                    t[0]
                )


class TestIS_NOT_IN_DB_SCRUBBED(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_NOT_IN_DB_SCRUBBED(db, db.creator.email)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test__validate(self):

        email = 'scrub@example.com'
        email_2 = 'scrub_2@example.com'
        error_msg = 'is_not_in_db_scrubbed error'

        def rm_underscore_two(text):
            """Remove '_2' from given string."""
            return text.replace('_2', '')

        def rm_b(text):
            """Remove 'b' from given string."""
            return text.replace('b', '')

        db.creator.insert(email=email)
        db.commit()
        creator = Creator.from_key(dict(email=email))
        self.assertTrue(creator)
        self.assertEqual(creator.email, email)
        self._objects.append(creator)

        tests = [
            #(email, scrub_callback, expect)
            (email, None, error_msg),               # In db, so not ok
            (email_2, None, None),                  # Not in db, so ok
            (email.upper(), None, error_msg),       # lowercase in db, not ok
            (email_2.upper(), None, None),          # Not in db, so ok
            (email, 'a_str', error_msg),            # Not callable, like None
            (email_2, 'a_str', None),               # Not callable, like None
            (email, rm_underscore_two, error_msg),  # Doesn't change, in db, not ok
            (email_2, rm_underscore_two, error_msg),           # becomes email, in db, not ok
            (email_2.upper(), rm_underscore_two, error_msg),   # becomes email, in db, not ok
            (email, rm_b, None),                    # becomes unique, so ok
            (email_2, rm_b, None),                  # becomes unique, so ok
        ]
        for t in tests:
            if t[2] is None:
                expect = t[1](t[0]) \
                    if t[1] is not None and callable(t[1]) else t[0]
                self.assertEqual(
                    IS_NOT_IN_DB_SCRUBBED(
                        db,
                        db.creator.email,
                        error_message=error_msg,
                        scrub_callback=t[1],
                    ).validate(t[0]),
                    expect
                )
            else:
                self.assertRaises(
                    ValidationError,
                    IS_NOT_IN_DB_SCRUBBED(
                        db,
                        db.creator.email,
                        error_message=error_msg,
                        scrub_callback=t[1],
                    ).validate,
                    t[0]
                )


class TestIS_TWITTER_HANDLE(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)
    # pylint: disable=C0103

    def test____init__(self):
        domain = 'my_domain.com'
        validator = IS_TWITTER_HANDLE(domain)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test_call__(self):
        err_msg = 'Enter a valid twitter handle, eg @username'
        tests = [
            #(value, error)
            ('@username', None),
            ('@user_name123', None),
            ('@123_user_name', None),
            ('username', err_msg),
            ('@user name', err_msg),
            ('@user-name', err_msg),
            ('@user!name', err_msg),
        ]
        for t in tests:
            if t[1] is None:
                self.assertEqual(
                    IS_TWITTER_HANDLE().validate(t[0]),
                    t[0]
                )
            else:
                self.assertRaises(
                    ValidationError,
                    IS_TWITTER_HANDLE().validate,
                    t[0],
                )


class TestIS_URL_FOR_DOMAIN(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)
    # pylint: disable=C0103

    def test____init__(self):
        domain = 'my_domain.com'
        validator = IS_URL_FOR_DOMAIN(domain)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test__validate(self):
        tests = [
            #(domain, value, result, error)
            ('aaa.com', 'http://www.aaa.com/path', 'http://www.aaa.com/path',
                None),
            ('aaa.com', 'www.aaa.com', 'http://www.aaa.com', None),
            ('aaa.com', 'aaa.com/path', 'http://aaa.com/path', None),
            ('aaa.com', '', '', 'Enter a valid aaa.com URL'),
            ('aaa.com', 'http://www.bbb.com/path', 'http://www.bbb.com/path',
                'Enter a valid aaa.com URL'),
            ('aaa.com', 'http://www.bbb.com/aaa.com',
                'http://www.bbb.com/aaa.com', 'Enter a valid aaa.com URL'),
            ('aaa.com', 'http://aaa.com.com/path', 'http://aaa.com.com/path',
                'Enter a valid aaa.com URL'),
            ('aaa.com', 'bbbaaa.com', 'http://bbbaaa.com',
                'Enter a valid aaa.com URL'),
        ]
        for t in tests:
            if t[3] is None:
                result = IS_URL_FOR_DOMAIN(t[0]).validate(t[1])
                self.assertEqual(result, t[2])
            else:
                try:
                    IS_URL_FOR_DOMAIN(t[0]).validate(t[1])
                except ValidationError as err:
                    self.assertEqual(str(err), t[3])
                else:
                    self.fail('ValidationError not raised')


class TestFunctions(LocalTestCase):
    def test__as_per_type(self):
        table = Storage()
        table.fields = []
        values = {
            'integer': {
                'integer_none': None,
                'integer_valid': '123',
                'integer_invalid': '_invalid_',
            },
            'boolean': {
                'boolean_none': None,
                'boolean_True': True,
                'boolean_T': 'T',
                'boolean_str_True': 'True',
                'boolean_False': False,
                'boolean_F': 'F',
                'boolean_str_False': 'False',
            },
            'double': {
                'double_none': None,
                'double_valid': '1.23',
                'double_invalid': '_invalid_',
            }
        }

        data = {}

        for field_type, fields in list(values.items()):
            for k, v in list(fields.items()):
                table.fields.append(k)
                table[k] = Storage()
                table[k].type = field_type
                data[k] = v

        data['_fake_field_'] = '_fake_value_'

        self.assertEqual(
            as_per_type(table, data),
            {
                'integer_none': None,
                'integer_valid': 123,
                'integer_invalid': 0,
                'boolean_none': None,
                'boolean_True': True,
                'boolean_T': True,
                'boolean_str_True': True,
                'boolean_False': False,
                'boolean_F': False,
                'boolean_str_False': False,
                'double_none': None,
                'double_valid': 1.23,
                'double_invalid': 0.0,
                '_fake_field_': '_fake_value_',
            }
        )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
