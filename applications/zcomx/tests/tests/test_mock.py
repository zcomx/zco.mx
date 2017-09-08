#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_mock.py

Test suite for zcomx/modules/tests/mock.py

"""
import datetime
import unittest
from applications.zcomx.modules.date_n_time import \
    str_to_date, \
    str_to_datetime
from applications.zcomx.modules.tests.mock import \
    DateMock, \
    DateTimeMock
from applications.zcomx.modules.tests.runner import LocalTestCase

# pylint: disable=missing-docstring


class TestDateMock(LocalTestCase):
    today_str = '2016-12-13 17:06:48'
    today = str_to_date(today_str)

    def test____init__(self):
        self.assertNotEqual(datetime.datetime.today(), self.today)

        with DateMock(self.today) as m:
            self.assertEqual(datetime.datetime.today(), self.today)
            self.assertTrue(isinstance(m, DateMock))

        self.assertNotEqual(datetime.datetime.today(), self.today)

    def test____enter__(self):
        pass        # tested in test____init__

    def test____exit__(self):
        pass        # tested in test____init__

    def test__mocked_class(self):
        mock = DateMock(self.today)
        got = mock.mocked_class()
        self.assertTrue(hasattr(got, 'today'))
        self.assertEqual(got.today(), self.today)


class TestDateTimeMock(LocalTestCase):
    now_str = '2016-12-13 17:06:48'
    now = str_to_datetime(now_str)

    def test____init__(self):
        self.assertNotEqual(datetime.datetime.now(), self.now)

        with DateTimeMock(self.now) as m:
            self.assertEqual(datetime.datetime.now(), self.now)
            self.assertTrue(isinstance(m, DateTimeMock))

        self.assertNotEqual(datetime.datetime.now(), self.now)

    def test____enter__(self):
        pass        # tested in test____init__

    def test____exit__(self):
        pass        # tested in test____init__

    def test__mocked_class(self):
        mock = DateTimeMock(self.now)
        got = mock.mocked_class()
        self.assertTrue(hasattr(got, 'now'))
        self.assertEqual(got.now(), self.now)


if __name__ == '__main__':
    unittest.main()
