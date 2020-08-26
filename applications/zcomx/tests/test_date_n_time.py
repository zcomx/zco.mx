#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_date_n_time.py

Test suite for zcomx/modules/date_n_time.py

"""

import datetime
import unittest
from applications.zcomx.modules.date_n_time import (
    age,
    english_delta,
    english_seconds,
    enumerate_month_dates,
    enumerate_year_dates,
    is_day_of_week,
    month_first_last,
    str_to_date,
    str_to_datetime,
    utc_to_localtime,
)
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=C0111,R0904


class TestFunctions(LocalTestCase):

    def test__age(self):
        tests = [
            # (timestamp, units, rounded, today, age),
            ('', 'years', True, '2013-01-22', 0),
            (None, 'years', True, '2013-01-22', 0),
            (
                datetime.datetime(2013, 1, 22, 0, 0, 0),
                'seconds',
                True,
                datetime.datetime(2013, 1, 22, 0, 0, 1),
                1
            ),
            (
                datetime.datetime(2013, 1, 22, 0, 0, 0),
                'seconds',
                True,
                datetime.datetime(2013, 1, 22, 1, 0, 0),
                3600
            ),
            (
                datetime.datetime(2013, 1, 21, 0, 0, 0),
                'days',
                True,
                datetime.datetime(2013, 1, 22, 1, 0, 0),
                1
            ),
            (
                datetime.datetime(2012, 1, 22, 0, 0, 0),
                'years',
                True,
                datetime.datetime(2013, 1, 22, 1, 0, 0),
                1
            ),
            (
                datetime.date(2013, 1, 21),
                'seconds',
                True,
                datetime.date(2013, 1, 22),
                86400
            ),
            (
                datetime.date(2013, 1, 21),
                'seconds',
                False,
                datetime.date(2013, 1, 22),
                86400
            ),
            (
                datetime.date(2013, 1, 21),
                'days',
                True,
                datetime.date(2013, 1, 22),
                1
            ),
            (
                datetime.date(2012, 12, 31),
                'days',
                True,
                datetime.date(2013, 1, 22),
                22
            ),
            (
                datetime.date(2012, 12, 31),
                'days',
                False,
                datetime.date(2013, 1, 22),
                22
            ),
            (
                datetime.date(2012, 1, 22),
                'years',
                True,
                datetime.date(2013, 1, 22),
                1
            ),
            (
                datetime.date(1964, 8, 30),
                'years',
                True,
                datetime.date(2013, 1, 22),
                48
            ),
            (
                datetime.date(1964, 8, 30),
                'years', False,
                datetime.date(2013, 1, 22),
                48.39798216253585
            ),
            ('2013-01-22 00:00:00', 'seconds', True, '2013-01-22 00:00:01', 1),
            ('2013-01-21 00:00:00', 'days', True, '2013-01-22 00:00:01', 1),
            ('2012-01-22 00:00:00', 'years', True, '2013-01-22 00:00:01', 1),
            ('2013-01-21', 'seconds', True, '2013-01-22', 86400),
            ('2013-01-21', 'days', True, '2013-01-22', 1),
            ('2012-01-22', 'years', True, '2013-01-22', 1),
        ]

        for t in tests:
            self.assertEqual(
                age(t[0], units=t[1], rounded=t[2], today=t[3]),
                t[4]
            )

        # Test without any args
        no_kwargs_age = age(datetime.date(1964, 8, 30))
        self.assertTrue(no_kwargs_age > 40)
        self.assertTrue(no_kwargs_age < 100)

        # Test invalid args
        invalids = [
            # (timestamp, units, rounded, today, age),
            ('_invalid_', 'years', True, '2013-01-22'),
            ('2013-01-22', '_invalid_', True, '2013-01-22'),
            ('2013-01-22', 'years', True, '_invalid_'),
            ('None', 'years', True, '2013-07-02'),
            ('0000-00-00', 'years', True, '2013-07-02'),
            ('2013-01-22', 'years', True, '0000-00-00'),
        ]

        for t in invalids:
            self.assertRaises(
                SyntaxError, age, t[0], units=t[1], rounded=t[2], today=t[3])

    def test__english_delta(self):
        tests = [
            # (datetime1, datetime2, zeroes, max_attributes, expect)
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
            self.assertEqual(
                english_delta(
                    str_to_datetime(t[0]),
                    str_to_datetime(t[1]),
                    zeros=t[2],
                    max_attributes=t[3]
                ),
                t[4]
            )

    def test__english_seconds(self):
        # The seconds in these tests are the deltas of timestamps in
        # english_delta tests.
        tests = [
            # (seconds, zeroes, max_attributes, expect)
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
            self.assertEqual(
                english_seconds(
                    t[0],
                    zeros=t[1],
                    max_attributes=t[2]
                ),
                t[3]
            )

    def test__enumerate_month_dates(self):
        tests = [
            # (start, end, expect)
            (
                '2012-01-01',
                '2012-12-31',
                [
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
                ]
            ),
            ('2012-01-02', '2012-01-01', []),
            (
                '2011-11-11',
                '2012-02-02',
                [
                    ('2011-11-11', '2011-11-30'),
                    ('2011-12-01', '2011-12-31'),
                    ('2012-01-01', '2012-01-31'),
                    ('2012-02-01', '2012-02-02'),
                ]
            ),
        ]
        for t in tests:
            results = []
            for start, end in enumerate_month_dates(
                    str_to_date(t[0]), str_to_date(t[1])):
                results.append((str(start), str(end)))
            self.assertEqual(results, t[2])

    def test__enumerate_year_dates(self):
        tests = [
            # (start, end, expect)
            ('2012-01-01', '2012-12-31', [('2012-01-01', '2012-12-31')]),
            ('2012-01-02', '2012-01-01', []),
            (
                '2011-11-11',
                '2012-02-02',
                [
                    ('2011-11-11', '2011-12-31'),
                    ('2012-01-01', '2012-02-02'),
                ]
            ),
        ]
        for t in tests:
            results = []
            d_1 = str_to_date(t[0])
            d_2 = str_to_date(t[1])
            for start, end in enumerate_year_dates(d_1, d_2):
                results.append((str(start), str(end)))
            self.assertEqual(results, t[2])

    def test__is_day_of_week(self):
        tests = [
            # (date, day_of_week, expect)
            ('2017-01-01', 'Sun', True),
            ('2017-01-01', 'Mon', False),
            ('2017-01-01', 'Tue', False),
            ('2017-01-01', 'Wed', False),
            ('2017-01-01', 'Thu', False),
            ('2017-01-01', 'Fri', False),
            ('2017-01-01', 'Sat', False),
            ('2017-01-01', 'Sunday', True),
            ('2017-01-01', 'Monday', False),
            ('2017-01-01', 'Tuesday', False),
            ('2017-01-01', 'Wednesday', False),
            ('2017-01-01', 'Thursday', False),
            ('2017-01-01', 'Friday', False),
            ('2017-01-01', 'Saturday', False),
            ('2017-01-01', 'Sun', True),
            ('2017-01-02', 'Mon', True),
            ('2017-01-03', 'Tue', True),
            ('2017-01-04', 'Wed', True),
            ('2017-01-05', 'Thu', True),
            ('2017-01-06', 'Fri', True),
            ('2017-01-07', 'Sat', True),
            ('2017-01-01', 'Sunday', True),
            ('2017-01-02', 'Monday', True),
            ('2017-01-03', 'Tuesday', True),
            ('2017-01-04', 'Wednesday', True),
            ('2017-01-05', 'Thursday', True),
            ('2017-01-06', 'Friday', True),
            ('2017-01-07', 'Saturday', True),
            ('2017-01-01', 'Fake', False),
            ('2017-01-01', 'xxx', False),
        ]

        for t in tests:
            date = str_to_date(t[0])
            self.assertEqual(is_day_of_week(date, t[1]), t[2])

    def test__month_first_last(self):
        tests = [
            # (date, expect first, expect last)
            ('2018-01-01', '2018-01-01', '2018-01-31'),
            ('2018-01-15', '2018-01-01', '2018-01-31'),
            ('2018-01-31', '2018-01-01', '2018-01-31'),
            ('2018-02-01', '2018-02-01', '2018-02-28'),
            ('2018-02-15', '2018-02-01', '2018-02-28'),
            ('2018-02-28', '2018-02-01', '2018-02-28'),
            ('2018-12-01', '2018-12-01', '2018-12-31'),
            ('2018-12-15', '2018-12-01', '2018-12-31'),
            ('2018-12-28', '2018-12-01', '2018-12-31'),
            # leap year
            ('2000-02-01', '2000-02-01', '2000-02-29'),
            ('2000-02-15', '2000-02-01', '2000-02-29'),
            ('2000-02-28', '2000-02-01', '2000-02-29'),
            ('2000-02-29', '2000-02-01', '2000-02-29'),
        ]
        for t in tests:
            date = str_to_date(t[0])
            expect = (
                str_to_date(t[1]),
                str_to_date(t[2])
            )
            self.assertEqual(month_first_last(date), expect)

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

    def test__utc_to_localtime(self):
        tests = [
            # (utc, zone, expect)
            ('2018-07-31 12:00:00', None, '2018-07-31 08:00:00'),
            ('2018-12-31 12:00:00', None, '2018-12-31 07:00:00'),
            # Second Sunday in March, switch from EST to DST at 2am
            ('2018-03-11 06:59:59', None, '2018-03-11 01:59:59'),
            ('2018-03-11 07:00:00', None, '2018-03-11 03:00:00'),
            # ('2018-03-11 05:00:00', None, '2018-03-11 02:00:00'),
            # First Sunday in November, switch from DST to EST at 2am
            ('2018-11-04 06:59:59', None, '2018-11-04 01:59:59'),
            ('2018-11-04 06:00:00', None, '2018-11-04 01:00:00'),
            ('2018-07-31 12:00:00', 'Europe/Amsterdam', '2018-07-31 14:00:00'),
            ('2018-12-31 12:00:00', 'Europe/Amsterdam', '2018-12-31 13:00:00'),
            # Last Sunday in March, switch from CET to DST at 1am
            ('2018-03-25 00:59:59', 'Europe/Amsterdam', '2018-03-25 01:59:59'),
            ('2018-03-25 01:00:00', 'Europe/Amsterdam', '2018-03-25 03:00:00'),
            # Last Sunday in October, switch from DST to CET at 1am
            ('2018-10-28 00:59:59', 'Europe/Amsterdam', '2018-10-28 02:59:59'),
            ('2018-10-28 01:00:00', 'Europe/Amsterdam', '2018-10-28 02:00:00'),
        ]
        for t in tests:
            utc = str_to_datetime(t[0])
            zone = t[1]
            expect = str_to_datetime(t[2])

            if zone:
                got = utc_to_localtime(utc, zone=zone)
            else:
                got = utc_to_localtime(utc)
            self.assertEqual(got, expect)


if __name__ == '__main__':
    unittest.main()
