#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_encoding.py

Test suite for zcomix/modules/encoding.py

"""

import unittest
from applications.zcomix.modules.encoding import \
        BaseLatin, \
        LatinDict, \
        LatinList, \
        LatinString, \
        latin_factory
from applications.zcomix.modules.test_runner import LocalTestCase

# pylint: disable=C0111,R0904

LATIN = u"¼ éíñ§ÐÌëÑ » ¼ ö ® © ’Èç"
LATIN_AS_ASCII = """1/4 einSDIeN >> 1/4 o R c 'Ec"""


class TestBaseLatin(LocalTestCase):

    def test____init__(self):
        base_latin = BaseLatin('abc')
        self.assertTrue(base_latin)

    def test__as_ascii(self):
        base_latin = BaseLatin('abc')
        self.assertEqual(base_latin.as_ascii(), 'abc')


class TestLatinDict(LocalTestCase):

    def test____init__(self):
        d = {'key1': 'value1', 'key2': 'value2'}
        latin_dict = LatinDict(d)
        self.assertTrue(latin_dict)

    def test__as_ascii(self):
        d = {
                'key1': 'value1',
                'key2': LATIN,
                'key3': {
                    'key4': ['value4', {'key6': 'value6'}, LATIN],
                    'key5': LATIN,
                    }
            }

        expect = {
                'key1': 'value1',
                'key2': LATIN_AS_ASCII,
                'key3': {
                    'key4': ['value4', {'key6': 'value6'}, LATIN_AS_ASCII],
                    'key5': LATIN_AS_ASCII,
                    }
                }

        latin_dict = LatinDict(d)
        self.assertEqual(latin_dict.as_ascii(), expect)


class TestLatinList(LocalTestCase):

    def test____init__(self):
        l = ['value1', 'value2']
        latin_list = LatinList(l)
        self.assertTrue(latin_list)

    def test__as_ascii(self):
        l = ['value1', LATIN, ['value2', LATIN],
                {'key1': 'value1', 'key2': LATIN}]
        expect = ['value1', LATIN_AS_ASCII, ['value2', LATIN_AS_ASCII],
                {'key1': 'value1', 'key2': LATIN_AS_ASCII}]
        latin_list = LatinList(l)
        self.assertEqual(latin_list.as_ascii(), expect)


class TestLatinString(LocalTestCase):

    def test____init__(self):
        latin_string = LatinString('abcdefg')
        self.assertTrue(latin_string)

    def test__as_ascii(self):
        latin_string = LatinString(LATIN)
        self.assertEqual(latin_string.as_ascii(), LATIN_AS_ASCII)


class TestFunctions(LocalTestCase):

    def test__latin2ascii(self):
        pass            # Not easy to test. Tested by LatinString.

    def test__latin_factory(self):
        self.assertIsInstance(latin_factory({}), LatinDict)
        self.assertIsInstance(latin_factory([]), LatinList)
        self.assertIsInstance(latin_factory(''), LatinString)
        self.assertIsInstance(latin_factory(bool()), BaseLatin)


if __name__ == '__main__':
    unittest.main()
