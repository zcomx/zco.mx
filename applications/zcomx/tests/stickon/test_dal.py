#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for zcomx/modules/stickon/dal.py
"""
import unittest
from pydal.objects import Row
from applications.zcomx.modules.stickon.dal import RecordGenerator
from applications.zcomx.modules.tests.runner import LocalTestCase
# pylint: disable=missing-docstring


class TestRecordGenerator(LocalTestCase):

    def test____init__(self):
        query = (db.book_type)
        record_gen = RecordGenerator(query)
        self.assertTrue(record_gen)

    def test__generator(self):
        query = (db.book_type)
        record_gen = RecordGenerator(query)

        def test_book_type(record, expect_fields=None):
            self.assertTrue(isinstance(record, Row))
            fields = expect_fields if expect_fields is not None else \
                sorted(db.book_type.fields)
            self.assertEqual(
                sorted(record.as_dict().keys()),
                fields,
            )

        generator = record_gen.generator()
        record_1 = next(generator)
        test_book_type(record_1)
        record_2 = next(generator)
        test_book_type(record_2)
        record_3 = next(generator)
        test_book_type(record_3)
        self.assertEqual(
            sorted([x['name'] for x in [record_1, record_2, record_3]]),
            ['mini-series', 'one-shot', 'ongoing']
        )
        self.assertRaises(StopIteration, generator.__next__)

        # Test fields
        field_names = ['name', 'sequence']
        fields = [db.book_type[x] for x in field_names]
        record_gen = RecordGenerator(query, fields=fields)
        generator = record_gen.generator()
        record_1 = next(generator)
        test_book_type(record_1, field_names)
        record_2 = next(generator)
        test_book_type(record_2, field_names)
        record_3 = next(generator)
        test_book_type(record_3, field_names)

        # Test orderby
        orderby = [~db.book_type.name]
        record_gen = RecordGenerator(query, orderby=orderby)
        generator = record_gen.generator()
        record_1 = next(generator)
        record_2 = next(generator)
        record_3 = next(generator)
        self.assertEqual(
            [x['name'] for x in [record_1, record_2, record_3]],
            ['ongoing', 'one-shot', 'mini-series']
        )

        # Test limitby
        limitby = (0, 1)
        record_gen = RecordGenerator(query, limitby=limitby)
        generator = record_gen.generator()
        record_1 = next(generator)
        self.assertRaises(StopIteration, generator.__next__)


def setUpModule():
    """Set up web2py environment."""
    # pylint: disable=invalid-name
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
