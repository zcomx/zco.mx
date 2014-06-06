#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/stickon/validators.py

"""
import string
import unittest
from gluon import *
from applications.zcomix.modules.stickon.validators import \
    IS_ALLOWED_CHARS, \
    IS_NOT_IN_DB_ANYCASE, \
    IS_NOT_IN_DB_SCRUBBED
from applications.zcomix.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestIS_ALLOWED_CHARS(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)*
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_ALLOWED_CHARS()
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test____call__(self):
        default_err = 'This is a test error message.'

        def run(validator, value, error):
            result, err_msg = validator(value)
            self.assertEqual(result, value)
            if error is not None:
                self.assertTrue(error in err_msg)
            else:
                self.assertEqual(error, err_msg)
            return result, err_msg

        # Test not_allowed default
        validator = IS_ALLOWED_CHARS(error_message=default_err)
        run(validator, string.ascii_letters, None)
        run(validator, string.digits, None)
        run(validator, string.punctuation, None)

        # Test not_allowed as string
        validator = IS_ALLOWED_CHARS(not_allowed='a', error_message=default_err)
        run(validator, 'abc', default_err)
        run(validator, 'bcd', None)
        validator = IS_ALLOWED_CHARS(not_allowed='a<>$z', error_message=default_err)
        run(validator, 'abc', default_err)
        run(validator, 'bcd', None)
        run(validator, 'xyz', default_err)
        run(validator, 'bbb<', default_err)
        run(validator, 'bbb!', None)

        # Test not_allowed as list
        validator = IS_ALLOWED_CHARS(not_allowed=['a', 'c', 'e'], error_message=default_err)
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
        validator = IS_ALLOWED_CHARS(not_allowed=not_allowed, error_message=default_err)
        run(validator, 'abc', None)
        result, err_msg = run(validator, 'ab%c', default_err)
        self.assertTrue('percent' in err_msg)


class TestIS_NOT_IN_DB_ANYCASE(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)*
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_NOT_IN_DB_ANYCASE(db, db.creator.email)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test____call__(self):
        email = 'anycase@example.com'
        email_2 = 'anycase_2@example.com'
        error_msg = 'is_not_in_db_anycase error'

        def creator_by_email(email):
            """Get creator by email."""
            return db(db.creator.email == email).select(db.creator.ALL).first()

        db.creator.insert(email=email)
        db.commit()
        creator = creator_by_email(email)
        self.assertTrue(creator)
        self.assertEqual(creator.email, email)
        self._objects.append(creator)

        tests = [
            #(email, expect)
            (email, (email, error_msg)),           # In db, so not ok
            (email_2, (email_2, None)),            # Not in db, so ok
            (email.upper(),
                (email.upper(), error_msg)),       # lowercase is in db, not ok
            (email_2.upper(), (email_2.upper(), None)),     # Not in db, so ok
        ]
        for t in tests:
            self.assertEqual(
                IS_NOT_IN_DB_ANYCASE(
                    db,
                    db.creator.email,
                    error_message=error_msg,
                )(t[0]),
                t[1]
            )


class TestIS_NOT_IN_DB_SCRUBBED(LocalTestCase):
    # C0103 (invalid-name): *Invalid name "%%s" for type %%s (should match %%s)*
    # pylint: disable=C0103

    def test____init__(self):
        validator = IS_NOT_IN_DB_SCRUBBED(db, db.creator.email)
        self.assertTrue(validator)
        self.assertTrue(len(validator.error_message) > 0)

    def test____call__(self):

        email = 'scrub@example.com'
        email_2 = 'scrub_2@example.com'
        email_up = 'SCRUB@EXAMPLE.COM'
        email_2_up = 'SCRUB_2@EXAMPLE.COM'
        error_msg = 'is_not_in_db_scrubbed error'

        def creator_by_email(email):
            """Get creator by email."""
            return db(db.creator.email == email).select(db.creator.ALL).first()

        def rm_underscore_two(text):
            """Remove '_2' from given string."""
            return text.replace('_2', '')

        def rm_b(text):
            """Remove 'b' from given string."""
            return text.replace('b', '')

        db.creator.insert(email=email)
        db.commit()
        creator = creator_by_email(email)
        self.assertTrue(creator)
        self.assertEqual(creator.email, email)
        self._objects.append(creator)

        tests = [
            #(email, scrub_callback, expect)
            (email, None, (email, error_msg)),        # In db, so not ok
            (email_2, None, (email_2, None)),         # Not in db, so ok
            (email.upper(), None,
                (email.upper(), error_msg)),          # lowercase in db, not ok
            (email_2.upper(), None,
                (email_2.upper(), None)),             # Not in db, so ok
            (email, 'a_str', (email, error_msg)),     # not callable, like None
            (email_2, 'a_str', (email_2, None)),      # not callable, like None
            (email, rm_underscore_two,
                (email, error_msg)),            # doesn't change, in db, not ok
            (email_2, rm_underscore_two,
                (email_2, error_msg)),           # becomes email, in db, not ok
            (email_2.upper(), rm_underscore_two,
                (email_2.upper(), error_msg)),   # becomes email, in db, not ok
            (email, rm_b, (email, None)),               # becomes unique, so ok
            (email_2, rm_b, (email_2, None)),           # becomes unique, so ok
        ]
        for t in tests:
            self.assertEqual(
                IS_NOT_IN_DB_SCRUBBED(
                    db,
                    db.creator.email,
                    error_message=error_msg,
                    scrub_callback=t[1],
                )(t[0]),
                t[2]
            )


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
