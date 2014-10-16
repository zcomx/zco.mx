#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/utils.py

"""
import os
import shutil
import unittest
from gluon import *
from gluon.dal import Reference
from applications.zcomx.modules.test_runner import LocalTestCase
from applications.zcomx.modules.utils import \
    ItemDescription, \
    entity_to_row, \
    markmin_content, \
    move_record, \
    reorder

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class TestItemDescription(LocalTestCase):

    _description = '123456789 123456789 '

    def test____init__(self):
        item = ItemDescription(self._description)
        self.assertTrue(item)
        self.assertEqual(item.description, self._description)
        self.assertEqual(item.truncate_length, 200)

    def test__as_html(self):
        item = ItemDescription(None)
        self.assertEqual(
            str(item.as_html()),
            '<div></div>'
        )

        item = ItemDescription('')
        self.assertEqual(
            str(item.as_html()),
            '<div></div>'
        )

        # Test short item
        item = ItemDescription('123456789')
        self.assertEqual(
            str(item.as_html()),
            '<div>123456789</div>'
        )

        # Test long item, break on space
        item = ItemDescription(self._description)
        item.truncate_length = 10
        # C0301 (line-too-long): *Line too long (%%s/%%s)*
        # pylint: disable=C0301
        self.assertEqual(
            str(item.as_html()),
            '<div><div class="short_description" title="123456789 123456789 ">123456789 ... <a class="desc_more_link" href="#">more</a></div><div class="full_description hidden">123456789 123456789 </div></div>'

        )

        # Test long item, break on word
        item = ItemDescription(self._description)
        item.truncate_length = 15
        self.assertEqual(
            str(item.as_html()),
            '<div><div class="short_description" title="123456789 123456789 ">123456789 ... <a class="desc_more_link" href="#">more</a></div><div class="full_description hidden">123456789 123456789 </div></div>'
        )

        # Test attributes
        item = ItemDescription('123456789')
        self.assertEqual(
            str(item.as_html(**dict(_id='my_id'))),
            '<div id="my_id">123456789</div>'
        )


class TestFunctions(LocalTestCase):

    _by_name = {}
    _fields = ['a', 'b', 'c']
    _tmp_backup = None
    _tmp_dir = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        db.define_table(
            'test__reorder',
            Field('name'),
            Field('order_no', 'integer'),
            migrate=True,
        )

        db.test__reorder.truncate()

        for f in cls._fields:
            record_id = db.test__reorder.insert(
                name=f,
                order_no=0,
            )
            db.commit()
            cls._by_name[f] = record_id

        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        if cls._tmp_backup is None:
            cls._tmp_backup = os.path.join(
                db._adapter.folder,
                '..',
                'uploads',
                'tmp_bak'
            )
        if cls._tmp_dir is None:
            cls._tmp_dir = os.path.join(
                db._adapter.folder,
                '..',
                'uploads',
                'tmp'
            )

    @classmethod
    def tearDown(cls):
        if cls._tmp_backup and os.path.exists(cls._tmp_backup):
            if os.path.exists(cls._tmp_dir):
                shutil.rmtree(cls._tmp_dir)
            os.rename(cls._tmp_backup, cls._tmp_dir)

    def _reset(self):
        record_ids = [
            self._by_name['a'],
            self._by_name['b'],
            self._by_name['c'],
        ]
        reorder(db.test__reorder.order_no, record_ids=record_ids)

    def _ordered_values(self, field='name'):
        """Get the field values in order."""
        # R0201 (no-self-use): *Method could be a function*
        # pylint: disable=R0201
        values = db().select(
            db.test__reorder[field],
            orderby=[db.test__reorder.order_no, db.test__reorder.id],
        )
        return [x[field] for x in values]

    def test__entity_to_row(self):
        book = self.add(db.book, dict(name='test__entity_to_row'))

        # Test Row, Reference, id
        for entity in [book, Reference(book.id), book.id]:
            got = entity_to_row(db.book, entity)
            self.assertEqual(book.as_dict(), got.as_dict())

    def test__markmin_content(self):
        faq = markmin_content('faq.mkd')
        self.assertTrue('#### What is zco.mx?' in faq)

    def test__move_record(self):
        self._reset()
        reorder(db.test__reorder.order_no)
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c'])

        def test_move(name, direction, expect, query=None):
            move_record(
                db.test__reorder.order_no,
                self._by_name[name],
                direction=direction,
                query=query,
            )
            self.assertEqual(self._ordered_values(), expect)

        test_move('a', 'up', ['a', 'b', 'c'])
        test_move('a', 'down', ['b', 'a', 'c'])
        test_move('a', 'down', ['b', 'c', 'a'])
        test_move('a', 'down', ['b', 'c', 'a'])
        test_move('a', 'up', ['b', 'a', 'c'])
        test_move('a', 'up', ['a', 'b', 'c'])
        test_move('a', 'up', ['a', 'b', 'c'])
        test_move('b', '_fake_', ['b', 'a', 'c'])

        # Test non-existent id
        self._reset()
        move_record(
            db.test__reorder.order_no,
            99999,              # Non-existent id
            direction='down'
        )
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c'])

        # Test query
        query = (db.test__reorder.id.belongs(
            [self._by_name['a'], self._by_name['b']])
        )
        test_move('a', 'down', ['b', 'a', 'c'], query=query)
        # 'c' is not included in query so it doesn't move.
        test_move('a', 'down', ['b', 'a', 'c'], query=query)

    def test__reorder(self):
        self._reset()

        reorder(db.test__reorder.order_no)
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c'])

        # Test record_ids param
        self._reset()
        record_ids = [
            self._by_name['b'],
            self._by_name['c'],
            self._by_name['a'],
        ]
        reorder(db.test__reorder.order_no, record_ids=record_ids)
        self.assertEqual(self._ordered_values(), ['b', 'c', 'a'])

        # Test query param
        self._reset()
        query = (db.test__reorder.id > 0)
        reorder(db.test__reorder.order_no, query=query)
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c'])

        # Test start param
        self._reset()
        reorder(db.test__reorder.order_no, start=100)
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c'])
        self.assertEqual(
            self._ordered_values(field='order_no'),
            [100, 101, 102]
        )

        # Add record to table
        self._reset()
        db.test__reorder.insert(
            name='d',
            order_no=9999,
        )
        db.commit()
        reorder(db.test__reorder.order_no)
        self.assertEqual(self._ordered_values(), ['a', 'b', 'c', 'd'])

        # Delete record from table
        self._reset()
        db(db.test__reorder.name == 'b').delete()
        db.commit()
        reorder(db.test__reorder.order_no)
        self.assertEqual(self._ordered_values(), ['a', 'c', 'd'])
        self.assertEqual(self._ordered_values(field='order_no'), [1, 2, 3])


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
