#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
test_date_n_time.py

Test suite for zcomx/modules/date_n_time.py

"""

import datetime
import unittest
from applications.zcomx.modules.date_n_time import \
        age, \
        english_delta, \
        english_seconds, \
        enumerate_month_dates, \
        enumerate_year_dates, \
        str_to_date, \
        str_to_datetime
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__age(self):
        tests = [
                #(timestamp, units, rounded, today, age),
                ('', 'years', True, '2013-01-22', 0),
                (None, 'years', True, '2013-01-22', 0),
                (datetime.datetime(2013, 1, 22, 0, 0, 0), 'seconds', True,
                    datetime.datetime(2013, 1, 22, 0, 0, 1), 1),
                (datetime.datetime(2013, 1, 22, 0, 0, 0), 'seconds', True,
                    datetime.datetime(2013, 1, 22, 1, 0, 0), 3600),
                (datetime.datetime(2013, 1, 21, 0, 0, 0), 'days', True,
                    datetime.datetime(2013, 1, 22, 1, 0, 0), 1),
                (datetime.datetime(2012, 1, 22, 0, 0, 0), 'years', True,
                    datetime.datetime(2013, 1, 22, 1, 0, 0), 1),
                (datetime.date(2013, 1, 21), 'seconds', True,
                    datetime.date(2013, 1, 22), 86400),
                (datetime.date(2013, 1, 21), 'seconds', False,
                    datetime.date(2013, 1, 22), 86400),
                (datetime.date(2013, 1, 21), 'days', True,
                    datetime.date(2013, 1, 22), 1),
                (datetime.date(2012, 12, 31), 'days', True,
                    datetime.date(2013, 1, 22), 22),
                (datetime.date(2012, 12, 31), 'days', False,
                    datetime.date(2013, 1, 22), 22),
                (datetime.date(2012, 1, 22), 'years', True,
                    datetime.date(2013, 1, 22), 1),
                (datetime.date(1964, 8, 30), 'years', True,
                    datetime.date(2013, 1, 22), 48),
                (datetime.date(1964, 8, 30), 'years', False,
                    datetime.date(2013, 1, 22), 48.39798216253585),
                ('2013-01-22 00:00:00', 'seconds', True,
                    '2013-01-22 00:00:01', 1),
                ('2013-01-21 00:00:00', 'days', True,
                    '2013-01-22 00:00:01', 1),
                ('2012-01-22 00:00:00', 'years', True,
                    '2013-01-22 00:00:01', 1),
                ('2013-01-21', 'seconds', True, '2013-01-22', 86400),
                ('2013-01-21', 'days', True, '2013-01-22', 1),
                ('2012-01-22', 'years', True, '2013-01-22', 1),
                ]

        for t in tests:
            self.assertEqual(age(t[0], units=t[1], rounded=t[2], today=t[3]),
                    t[4])

        # Test without any args
        no_kwargs_age = age(datetime.date(1964, 8, 30))
        self.assertTrue(no_kwargs_age > 40)
        self.assertTrue(no_kwargs_age < 100)

        # Test invalid args
        invalids = [
                #(timestamp, units, rounded, today, age),
                ('_invalid_', 'years', True, '2013-01-22'),
                ('2013-01-22', '_invalid_', True, '2013-01-22'),
                ('2013-01-22', 'years', True, '_invalid_'),
                ('None', 'years', True, '2013-07-02'),
                ('0000-00-00', 'years', True, '2013-07-02'),
                ('2013-01-22', 'years', True, '0000-00-00'),
                ]

        for t in invalids:
            self.assertRaises(SyntaxError, age, t[0], units=t[1], rounded=t[2],
                    today=t[3])

    def test__english_delta(self):
        tests = [
                #(datetime1, datetime2, zeroes, max_attributes, expect)
                (
                    '2012-02-11 15:55:18',
                    '2012-02-10 14:54:17',
                    True,
                    0,
                    '1 day, 1 hour, 1 minute, 1 second',
                ),
                (
                    '2012-02-12 17:58:25',
                    '2012-02-10 14:54:17',
                    True,
                    0,
                    '2 days, 3 hours, 4 minutes, 8 seconds',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-10 14:54:17',
                    True,
                    0,
                    '2 days, 1 hour, 4 minutes, 1 second',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-12 15:58:18',
                    True,
                    0,
                    '0 days, 0 hours, 0 minutes, 0 seconds',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-12 15:58:18',
                    False,
                    0,
                    '0 seconds',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-12 15:50:14',
                    True,
                    0,
                    '0 days, 0 hours, 8 minutes, 4 seconds',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-12 15:50:14',
                    False,
                    0,
                    '8 minutes, 4 seconds',
                ),
                (
                    '2012-02-12 15:50:18',
                    '2012-02-12 14:50:14',
                    True,
                    0,
                    '0 days, 1 hour, 0 minutes, 4 seconds',
                ),
                (
                    '2012-02-12 15:50:18',
                    '2012-02-12 14:50:14',
                    False,
                    0,
                    '1 hour, 4 seconds',
                ),
                (
                    '2012-02-12 17:58:25',
                    '2012-02-10 14:54:17',
                    True,
                    4,
                    '2 days, 3 hours, 4 minutes, 8 seconds',
                ),
                (
                    '2012-02-12 17:58:25',
                    '2012-02-10 14:54:17',
                    True,
                    3,
                    '2 days, 3 hours, 4 minutes',
                ),
                (
                    '2012-02-12 17:58:25',
                    '2012-02-10 14:54:17',
                    True,
                    2,
                    '2 days, 3 hours',
                ),
                (
                    '2012-02-12 17:58:25',
                    '2012-02-10 14:54:17',
                    True,
                    1,
                    '2 days',
                ),
                (
                    '2012-02-12 15:58:18',
                    '2012-02-12 15:58:18',
                    False,
                    1,
                    '0 seconds',
                ),
                ]

        for t in tests:
            self.assertEqual(english_delta(str_to_datetime(t[0]),
                str_to_datetime(t[1]), zeros=t[2], max_attributes=t[3]), t[4])

    def test__english_seconds(self):
        # The seconds in these tests are the deltas of timestamps in
        # english_delta tests.
        tests = [
                #(seconds, zeroes, max_attributes, expect)
                (
                    90061,
                    True,
                    0,
                    '1 day, 1 hour, 1 minute, 1 second',
                ),
                (
                    183848,
                    True,
                    0,
                    '2 days, 3 hours, 4 minutes, 8 seconds',
                ),
                (
                    176641,
                    True,
                    0,
                    '2 days, 1 hour, 4 minutes, 1 second',
                ),
                (
                    0,
                    True,
                    0,
                    '0 days, 0 hours, 0 minutes, 0 seconds',
                ),
                (
                    0,
                    False,
                    0,
                    '0 seconds',
                ),
                (
                    484,
                    True,
                    0,
                    '0 days, 0 hours, 8 minutes, 4 seconds',
                ),
                (
                    484,
                    False,
                    0,
                    '8 minutes, 4 seconds',
                ),
                (
                    3604,
                    True,
                    0,
                    '0 days, 1 hour, 0 minutes, 4 seconds',
                ),
                (
                    3604,
                    False,
                    0,
                    '1 hour, 4 seconds',
                ),
                (
                    183848,
                    True,
                    4,
                    '2 days, 3 hours, 4 minutes, 8 seconds',
                ),
                (
                    183848,
                    True,
                    3,
                    '2 days, 3 hours, 4 minutes',
                ),
                (
                    183848,
                    True,
                    2,
                    '2 days, 3 hours',
                ),
                (
                    183848,
                    True,
                    1,
                    '2 days',
                ),
                (
                    0,
                    False,
                    1,
                    '0 seconds',
                ),
                ]

        for t in tests:
            self.assertEqual(english_seconds(t[0], zeros=t[1],
                max_attributes=t[2]), t[3])

    def test__enumerate_month_dates(self):
        tests = [
                #(start, end, expect)
                ('2012-01-01', '2012-12-31', [
                    ('2012-01-01', '2012-01-31'),
                    ('2012-02-01', '2012-02-29'),
                    ('2012-03-01', '2012-03-31'),
                    ('2012-04-01', '2012-04-30'),
                    ('2012-05-01', '2012-05-31'),
                    ('2012-06-01', '2012-06-30'),
                    ('2012-07-01', '2012-07-31'),
                    ('2012-08-01', '2012-08-31'),
                    ('2012-09-01', '2012-09-30'),
                    ('2012-10-01', '2012-10-31'),
                    ('2012-11-01', '2012-11-30'),
                    ('2012-12-01', '2012-12-31'),
                    ]),
                ('2012-01-02', '2012-01-01', []),
                ('2011-11-11', '2012-02-02', [
                    ('2011-11-11', '2011-11-30'),
                    ('2011-12-01', '2011-12-31'),
                    ('2012-01-01', '2012-01-31'),
                    ('2012-02-01', '2012-02-02'),
                    ]),
                ]
        for t in tests:
            results = []
            for s, e in enumerate_month_dates(str_to_date(t[0]),
                    str_to_date(t[1])):
                results.append((str(s), str(e)))
            self.assertEqual(results, t[2])

    def test__enumerate_year_dates(self):
        tests = [
                #(start, end, expect)
                ('2012-01-01', '2012-12-31', [
                    ('2012-01-01', '2012-12-31'),
                    ]),
                ('2012-01-02', '2012-01-01', []),
                ('2011-11-11', '2012-02-02', [
                    ('2011-11-11', '2011-12-31'),
                    ('2012-01-01', '2012-02-02'),
                    ]),
                ]
        for t in tests:
            results = []
            for s, e in enumerate_year_dates(str_to_date(t[0]),
                    str_to_date(t[1])):
                results.append((str(s), str(e)))
            self.assertEqual(results, t[2])

    def test__str_to_date(self):
        date = str_to_date('2011-04-14')
        self.assertTrue(isinstance(date, datetime.date))
        self.assertEqual(str(date), '2011-04-14')

        # Invalid dates
        self.assertEqual(str_to_date('2011-06-31'), None)
        self.assertEqual(str_to_date('abc'), None)
        self.assertEqual(str_to_date(''), None)

    def test__str_to_datetime(self):
        date = str_to_datetime('2011-04-14 12:29:59')
        self.assertTrue(isinstance(date, datetime.date))
        self.assertEqual(str(date), '2011-04-14 12:29:59')

        # Invalid datetimes
        self.assertEqual(str_to_datetime('2011-06-31 12:29:59'), None)
        self.assertEqual(str_to_datetime('2011-06-30 24:59:59'), None)
        self.assertEqual(str_to_datetime('abc'), None)
        self.assertEqual(str_to_datetime(''), None)


if __name__ == '__main__':
    unittest.main()
