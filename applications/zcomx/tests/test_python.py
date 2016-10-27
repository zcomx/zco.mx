#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_python.py

Test suite for zcomx/modules/python.py

"""
import unittest
from applications.zcomx.modules.python import \
    List, \
    from_dict_by_keys
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=C0111,R0904


class TestList(LocalTestCase):

    def test_parent____init__(self):
        integers = List([1, 2, 3])
        self.assertEqual(len(integers), 3)

    def test__reshape(self):
        integers = List(range(0, 10))
        self.assertEqual(len(integers), 10)

        tests = [
            # (shape, expect)
            ((2, 5), [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]),
            ((None, None), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
            ((None, 5), [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]),
            ((None, 3), [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]),
            ((2, None), [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]),
            ((3, None), [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]),
            ((2, 4), [[0, 1, 2, 3], [4, 5, 6, 7]]),
            ((1, 5), [[0, 1, 2, 3, 4]]),
            ((3, 5), [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]),
            ((2, 6), [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9]]),
        ]

        for t in tests:
            self.assertEqual(integers.reshape(t[0]), t[1])


class TestFunctions(LocalTestCase):

    def test__from_dict_by_keys(self):
        data = {
            'a': {
                'aa': {
                    'aaa': 111,
                    'aab': 112,
                },
                'ab': {
                    'aba': 121,
                    'abb': 122,
                },
            },
            'b': {
                'ba': {
                    'baa': 211,
                    'bab': 212,
                },
                'bb': {
                    'bba': 221,
                    'bbb': 222,
                },
            },
        }

        tests = [
            # (map_list, expect)
            ([], data),
            (
                ['a'],
                {
                    'aa': {'aaa': 111, 'aab': 112},
                    'ab': {'aba': 121, 'abb': 122},
                }
            ),
            (['a', 'aa'], {'aaa': 111, 'aab': 112}),
            (['a', 'aa', 'aaa'], 111),
            (['b', 'bb', 'bbb'], 222),
            (['c'], KeyError),
            (['a', 'ac'], KeyError),
            (['a', 'aa', 'aac'], KeyError),
        ]
        for t in tests:
            if t[1] == KeyError:
                self.assertRaises(
                    t[1], from_dict_by_keys, data, t[0])
            else:
                self.assertEqual(
                    from_dict_by_keys(data, t[0]),
                    t[1]
                )


if __name__ == '__main__':
    unittest.main()
