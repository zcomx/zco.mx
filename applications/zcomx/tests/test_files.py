#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/files.py
"""
import unittest
from applications.zcomx.modules.files import (
    FileName,
    TitleFileName,
    for_file,
    for_title_file,
)
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestFileName(LocalTestCase):

    def test_init__(self):
        filename = FileName('abc.txt')
        self.assertTrue(filename)
        # Test that filename has str properties.
        self.assertTrue(hasattr(filename, 'replace'))
        self.assertTrue(hasattr(filename, 'strip'))

    def test__pre_scrub(self):
        tests = [
            # (raw filename, expect)
            'abc.txt',
            '0123456789.txt',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt',
            'abcdefghijklmnopqrstuvwxyz.txt',
            "[]_²´àáäèéñô.txt",
            "! #&'()+,-. .txt",
            'a/b.txt',
            'a\\b.txt',
            'a?b.txt',
            'a%b.txt',
            'a*b.txt',
            'a:b.txt',
            'a|b.txt',
            'a"b.txt',
            'a<b.txt',
            'a>b.txt',
        ]

        for t in tests:
            self.assertEqual(FileName(t).pre_scrub(), t)

    def test__scrubbed(self):
        tests = [
            # (raw filename, expect)
            ('abc.txt', 'abc.txt'),
            ('0123456789.txt', '0123456789.txt'),        # digits are valid
            (
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt',
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt'
            ),
            (
                'abcdefghijklmnopqrstuvwxyz.txt',
                'abcdefghijklmnopqrstuvwxyz.txt'
            ),
            ("[]_²´àáäèéñô.txt", "[]_²´àáäèéñô.txt"),
            ("! #&'()+,-. .txt", "! #&'()+,-. .txt"),
            ('a/b.txt', 'ab.txt'),            # / is invalid
            (r'a\b.txt', 'ab.txt'),           # \ is invalid
            ('a?b.txt', 'ab.txt'),            # ? is invalid
            ('a%b.txt', 'ab.txt'),            # % is invalid
            ('a*b.txt', 'ab.txt'),            # * is invalid
            ('a:b.txt', 'ab.txt'),            # > is invalid
            ('a|b.txt', 'ab.txt'),            # | is invalid
            ('a"b.txt', 'ab.txt'),            # " is invalid
            ('a<b.txt', 'ab.txt'),            # < is invalid
            ('a>b.txt', 'ab.txt'),            # > is invalid
        ]

        for t in tests:
            self.assertEqual(FileName(t[0]).scrubbed(), t[1])


class TestTitleFileName(LocalTestCase):

    def test_init__(self):
        filename = TitleFileName('abc.txt')
        self.assertTrue(filename)

    def test__pre_scrub(self):
        tests = [
            # (raw filename, expect)
            ('abc.txt', 'abc.txt'),
            ('0123456789.txt', '0123456789.txt'),        # digits are valid
            (
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt',
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt'
            ),
            (
                'abcdefghijklmnopqrstuvwxyz.txt',
                'abcdefghijklmnopqrstuvwxyz.txt'
            ),
            ("[]_²´àáäèéñô.txt", "[]_²´àáäèéñô.txt"),
            ("! #&'()+,-. .txt", "! #&'()+,-. .txt"),
            ('a/\\?%*|"<>b.txt', 'a/\\?%*|"<>b.txt'),            # / is invalid
            ('a:b.txt', 'a - b.txt'),         # colon is treated specifically.
            ('a: b.txt', 'a - b.txt'),        # colon variation
            ('a :b.txt', 'a - b.txt'),        # colon variation
            ('a : b.txt', 'a - b.txt'),       # colon variation
            ('a  :  b.txt', 'a - b.txt'),     # colon variation
        ]

        for t in tests:
            self.assertEqual(TitleFileName(t[0]).pre_scrub(), t[1])

    def test_parent_scrubbed(self):
        tests = [
            # (raw filename, expect)
            ('abc.txt', 'abc.txt'),
            ('0123456789.txt', '0123456789.txt'),        # digits are valid
            (
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt',
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ.txt'
            ),
            (
                'abcdefghijklmnopqrstuvwxyz.txt',
                'abcdefghijklmnopqrstuvwxyz.txt'
            ),
            ("[]_²´àáäèéñô.txt", "[]_²´àáäèéñô.txt"),
            ("! #&'()+,-. .txt", "! #&'()+,-. .txt"),
            ('a/b.txt', 'ab.txt'),            # / is invalid
            ('a\\b.txt', 'ab.txt'),           # \ is invalid
            ('a?b.txt', 'ab.txt'),            # ? is invalid
            ('a%b.txt', 'ab.txt'),            # % is invalid
            ('a*b.txt', 'ab.txt'),            # * is invalid
            ('a|b.txt', 'ab.txt'),            # | is invalid
            ('a"b.txt', 'ab.txt'),            # " is invalid
            ('a<b.txt', 'ab.txt'),            # < is invalid
            ('a>b.txt', 'ab.txt'),            # > is invalid
            ('a:b.txt', 'a - b.txt'),         # colon is treated specifically.
            ('a: b.txt', 'a - b.txt'),        # colon variation
            ('a :b.txt', 'a - b.txt'),        # colon variation
            ('a : b.txt', 'a - b.txt'),       # colon variation
            ('a  :  b.txt', 'a - b.txt'),     # colon variation
        ]

        for t in tests:
            self.assertEqual(TitleFileName(t[0]).scrubbed(), t[1])


class TestFunctions(LocalTestCase):

    def test__for_file(self):
        self.assertEqual(for_file('a/?>b.txt'), 'ab.txt')

    def test__for_title_file(self):
        self.assertEqual(for_title_file('a?: b>.t/xt'), 'a - b.txt')


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
