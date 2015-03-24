#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/strings.py

"""
import string
import unittest
from gluon import *
from applications.zcomx.modules.strings import \
    camelcase, \
    replace_punctuation, \
    squeeze_whitespace
from applications.zcomx.modules.tests.runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__camelcase(self):
        tests = [
            # (text, repl, expect)
            (None, None),
            ('', ''),
            ('aaa', 'Aaa'),
            ('Aaa', 'Aaa'),
            ('aAa', 'AAa'),
            ('aaA', 'AaA'),
            ('aaa bbb ccc', 'AaaBbbCcc'),
            ("Hélè d'Eñça", "HélèD'Eñça"),
        ]
        for t in tests:
            self.assertEqual(camelcase(t[0]), t[1])

    def test__replace_punctuation(self):
        tests = [
            # (text, repl, expect)
            (None, None, None),
            ('', None, ''),
            (string.punctuation, '', ''),
            ("Name: Isn't it great?", ' ', 'Name  Isn t it great '),
            ("Hélè d'Eñça", ' ', "Hélè d Eñça"),
        ]
        for t in tests:
            kwargs = {}
            if t[1] is not None:
                kwargs['repl'] = t[1]
            self.assertEqual(replace_punctuation(t[0], **kwargs), t[2])

        # Test punctuation param
        text = r"""!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~"""
        got = replace_punctuation(text, repl='X', punctuation="""$'@""")
        self.assertEqual(
            got,
            r"""!"#X%&\X()*+,-./:;<=>?X[\\]^_`{|}~"""
        )

    def test__squeeze_whitespace(self):
        tests = [
            # (text, repl, expect)
            (None, None),
            ('', ''),
            ('a  b', 'a b'),
            ('a      b', 'a b'),
            ('  a  b  c  ', ' a b c '),
            ("Hélè   d'   Eñça", "Hélè d' Eñça"),
        ]
        for t in tests:
            self.assertEqual(squeeze_whitespace(t[0]), t[1])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
