#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomix/modules/utils.py

"""
import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.storage import Storage
from applications.zcomix.modules.utils import \
    ItemDescription, \
    move_record, \
    profile_wells, \
    reorder
from applications.zcomix.modules.test_runner import LocalTestCase

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
        self.assertEqual(
            str(item.as_html()),
            '<div><div class="short_description" title="123456789 123456789 ">123456789 ... <a class="desc_more_link" data-w2p_disable_with="default" href="#">more</a></div><div class="full_description hidden">123456789 123456789 </div></div>'

        )

        # Test long item, break on word
        item = ItemDescription(self._description)
        item.truncate_length = 15
        self.assertEqual(
            str(item.as_html()),
            '<div><div class="short_description" title="123456789 123456789 ">123456789 ... <a class="desc_more_link" data-w2p_disable_with="default" href="#">more</a></div><div class="full_description hidden">123456789 123456789 </div></div>'
        )

        # Test attributes
        item = ItemDescription('123456789')
        self.assertEqual(
            str(item.as_html(**dict(_id='my_id'))),
            '<div id="my_id">123456789</div>'
        )


class TestFunctions(LocalTestCase):

    _fields = ['a', 'b', 'c']
    _by_name = {}

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

    def _reset(self):
        record_ids = [
            self._by_name['a'],
            self._by_name['b'],
            self._by_name['c'],
        ]
        reorder(db.test__reorder.order_no, record_ids=record_ids)

    def _ordered_values(self, field='name'):
        """Get the field values in order."""
        values = db().select(
            db.test__reorder[field],
            orderby=[db.test__reorder.order_no, db.test__reorder.id],
        )
        return [x[field] for x in values]

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

    def test__profile_wells(self):
        request = Storage()
        request.function = 'books'
        request.args = [99]

        tests = [
            #(request.function, expect)
            ('index', {
                'account': 'link',
                'creator': 'link',
                'books': 'link',
                'book_edit': None,
                'book_pages': None,
                'book_links': None,
                'book_link_edit': None,
                'book_release': None,
            }),
            ('creator', {
                'account': 'link',
                'creator': 'text',
                'books': 'link',
                'book_edit': None,
                'book_pages': None,
                'book_links': None,
                'book_link_edit': None,
                'book_release': None,
            }),
            ('books', {
                'account': 'link',
                'creator': 'link',
                'books': 'text',
                'book_edit': None,
                'book_pages': None,
                'book_links': None,
                'book_link_edit': None,
                'book_release': None,
            }),
            ('book_edit', {
                'account': 'link',
                'creator': 'link',
                'books': 'link',
                'book_edit': 'text',
                'book_pages': 'link',
                'book_links': 'link',
                'book_link_edit': None,
                'book_release': None,
            }),
            ('book_link_edit', {
                'account': 'link',
                'creator': 'link',
                'books': 'link',
                'book_edit': 'link',
                'book_pages': None,
                'book_links': 'link',
                'book_link_edit': 'text',
                'book_release': None,
            }),
        ]

        for t in tests:
            request = Storage()
            request.function = t[0]
            wells = profile_wells(request)
            statuses = {}
            for k, v in wells.items():
                statuses[k] = v['status']
            self.assertEqual(statuses, t[1])

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
        self.assertEqual(self._ordered_values(field='order_no'), [100, 101, 102])

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
