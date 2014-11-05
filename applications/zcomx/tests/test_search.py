#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/search.py

"""

import unittest
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.search import \
    Grid, \
    CartoonistsGrid, \
    ContributionsGrid, \
    CreatorGrid, \
    OngoingGrid, \
    ReleasesGrid, \
    SearchGrid, \
    GRID_CLASSES, \
    book_contribute_button, \
    creator_contribute_button, \
    classified, \
    download_link, \
    link_book_id, \
    read_link, \
    torrent_link
from applications.zcomx.modules.test_runner import LocalTestCase

# C0111: Missing docstring
# R0904: Too many public methods
# pylint: disable=C0111,R0904


class SubGrid(Grid):
    """SubClass for testing."""

    _attributes = {
        'table': 'book',
        'field': 'name',
        'label': 'name',
        'tab_label': 'book titles',
        'header_label': 'title',
        'order_field': 'book.name',
        'order_dir': 'DESC',
    }

    _buttons = [
        'read',
        'book_contribute',
    ]

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def visible_fields(self):
        db = self.db
        return [db.book.name]


class TestGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        args = {'paginate': 999999}
        grid = SubGrid(form_grid_args=args)
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book')
        self.assertEqual(grid._attributes['field'], 'name')
        self.assertTrue('header_label' in grid._attributes)

        self.assertTrue(grid.form_grid)
        query = (db.book.status == True)
        rows = db(query).select(
            db.book.id,
            left=[
                db.creator.on(db.book.creator_id == db.creator.id)
            ]
        )
        self.assertEqual(len(grid.form_grid.rows), len(rows))

    def test__filters(self):
        grid = SubGrid()
        self.assertEqual(grid.filters(), [])

    def test__groupby(self):
        grid = SubGrid()
        self.assertEqual(grid.groupby(), db.book.id)

    def test__hide(self):
        grid = SubGrid()
        self.assertEqual(db.book.name.readable, True)
        self.assertEqual(db.book.name.writable, True)
        grid.hide(db.book.name)
        self.assertEqual(db.book.name.readable, False)
        self.assertEqual(db.book.name.writable, False)
        grid.show(db.book.name)
        self.assertEqual(db.book.name.readable, True)
        self.assertEqual(db.book.name.writable, True)

    def test__items_per_page(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        self.assertEqual(grid._default_paginate, 10)
        self.assertEqual(grid._paginate, 10)
        self.assertEqual(grid.items_per_page(), 10)

        for t in [10, 20, 9999]:
            args = {'paginate': t}
            grid = SubGrid(form_grid_args=args)
            self.assertEqual(grid._default_paginate, 10)
            self.assertEqual(grid._paginate, t)
            self.assertEqual(grid.items_per_page(), t)

    def test__label(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        default = 'sub'     # from class name 'SubGrid'

        save_attributes = dict(SubGrid._attributes)

        # No 'label' key
        SubGrid._attributes = {}
        self.assertEqual(grid.label('tab_label'), default)

        # No 'tab_label' or 'header_label' keys
        SubGrid._attributes['label'] = '_label_'
        self.assertEqual(grid.label('tab_label'), '_label_')
        self.assertEqual(grid.label('header_label'), '_label_')

        # Has 'tab_label', no 'header_label' keys
        SubGrid._attributes['tab_label'] = '_tab_label_'
        self.assertEqual(grid.label('tab_label'), '_tab_label_')
        self.assertEqual(grid.label('header_label'), '_label_')

        # Has 'tab_label' and 'header_label' keys
        SubGrid._attributes['header_label'] = '_header_label_'
        self.assertEqual(grid.label('tab_label'), '_tab_label_')
        self.assertEqual(grid.label('header_label'), '_header_label_')

        SubGrid._attributes = save_attributes

    def test__order_fields(self):
        grid = SubGrid()
        order_fields = grid.order_fields()
        self.assertEqual(len(order_fields), 1)
        self.assertEqual(str(order_fields[0]), 'book.name')

    def test__orderby(self):
        grid = SubGrid()
        orderby = grid.orderby()
        self.assertEqual(len(orderby), 3)
        self.assertEqual(
            [str(x) for x in orderby],
            ['book.name DESC', 'book.number', 'book.id']
        )

    def test__rows(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        rows = grid.rows()
        self.assertEqual(len(rows), grid._default_paginate)
        self.assertEqual(
            sorted(rows[0].keys()),
            ['auth_user', 'book', 'book_page', 'creator']
        )

    def test__set_field(self):
        grid = SubGrid()
        self.assertEqual(db.book.name.readable, True)
        self.assertEqual(db.book.name.writable, True)
        grid.set_field(db.book.name, visible=False)
        self.assertEqual(db.book.name.readable, False)
        self.assertEqual(db.book.name.writable, False)
        grid.set_field(db.book.name, visible=True)
        self.assertEqual(db.book.name.readable, True)
        self.assertEqual(db.book.name.writable, True)
        grid.set_field(db.book.name, visible=False)
        self.assertEqual(db.book.name.readable, False)
        self.assertEqual(db.book.name.writable, False)
        grid.set_field(db.book.name)
        self.assertEqual(db.book.name.readable, True)
        self.assertEqual(db.book.name.writable, True)

    def test__show(self):
        pass        # Tested by test__hide

    def test__tile_class(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        self.assertEqual(grid.tile_class(), 'tile_key_sub')

    def test__tile_label(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        self.assertEqual(grid.tile_label(), 'name')
        grid._attributes['label'] = None
        self.assertEqual(grid.tile_label(), '')
        del grid._attributes['label']
        self.assertEqual(grid.tile_label(), '')
        grid._attributes['label'] = 'name'

    def test__tile_value(self):
        creator = self.add(db.creator, dict(path_name='test__tile_value'))
        name = '_My Book_'
        book_type_id = db(db.book_type).select().first().id
        book = self.add(db.book, dict(
            name=name,
            creator_id=creator.id,
            book_type_id=book_type_id,
        ))

        grid = SubGrid()
        row = db(db.book.id == book.id).select(
            db.book.ALL,
            db.creator.ALL,
            left=[db.creator.on(db.book.creator_id == db.creator.id)],
            orderby=db.book.id,
            limitby=(0, 1)
        ).first()
        self.assertEqual(row['book']['name'], '_My Book_')
        db.book.name.represent = None
        self.assertEqual(grid.tile_value(row), '_My Book_')

        db.book.name.represent = lambda v, r: v.upper()
        self.assertEqual(grid.tile_value(row), '_MY BOOK_')

    def test__visible_fields(self):
        grid = SubGrid()
        self.assertEqual(grid.visible_fields(), [db.book.name])


class TestCartoonistsGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = CartoonistsGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'creator')
        self.assertEqual(grid._attributes['field'], 'contributions_remaining')

    def test__groupby(self):
        grid = CartoonistsGrid()
        self.assertEqual(grid.groupby(), db.creator.id)

    def test__order_fields(self):
        grid = CartoonistsGrid()
        order_fields = grid.order_fields()
        self.assertEqual(len(order_fields), 1)
        self.assertEqual(str(order_fields[0]), 'auth_user.name')

    def test__visible_fields(self):
        grid = CartoonistsGrid()
        self.assertEqual(
            grid.visible_fields(),
            [db.auth_user.name, db.creator.contributions_remaining]
        )


class TestContributionsGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = ContributionsGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book')
        self.assertEqual(grid._attributes['field'], 'contributions_remaining')

    def test__filters(self):
        grid = ContributionsGrid()
        self.assertEqual(len(grid.filters()), 2)

    def test__visible_fields(self):
        grid = ContributionsGrid()
        self.assertEqual(
            grid.visible_fields(),
            [
                db.book.name,
                db.book.publication_year,
                db.book.contributions_remaining,
                db.auth_user.name,
            ]
        )


class TestCreatorGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = CreatorGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book')
        self.assertEqual(grid._attributes['field'], 'contributions_remaining')

    def test__filters(self):
        grid = CreatorGrid()
        self.assertEqual(len(grid.filters()), 0)

        creator = self.add(db.creator, dict(path_name='test__filters'))
        env = globals()
        request = env['request']
        request.vars.creator_id = creator.id
        self.assertEqual(len(grid.filters()), 1)
        request.vars.released = '0'
        self.assertEqual(len(grid.filters()), 2)
        request.vars.released = '1'
        self.assertEqual(len(grid.filters()), 2)

    def test__visible_fields(self):
        grid = CreatorGrid()
        self.assertEqual(
            grid.visible_fields(),
            [
                db.book.name,
                db.book.contributions_remaining,
            ]
        )


class TestOngoingGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = OngoingGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book_page')
        self.assertEqual(grid._attributes['field'], 'created_on')

    def test__filters(self):
        grid = OngoingGrid()
        self.assertEqual(len(grid.filters()), 1)

    def test__visible_fields(self):
        grid = OngoingGrid()
        self.assertEqual(
            grid.visible_fields(),
            [
                db.book.name,
                db.book_page.created_on,
                db.book.views,
                db.book.contributions_remaining,
                db.auth_user.name,
            ]
        )


class TestReleasesGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = ReleasesGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book')
        self.assertEqual(grid._attributes['field'], 'release_date')

    def test__filters(self):
        grid = ReleasesGrid()
        self.assertEqual(len(grid.filters()), 1)

    def test__visible_fields(self):
        grid = ReleasesGrid()
        self.assertEqual(
            grid.visible_fields(),
            [
                db.book.name,
                db.book.publication_year,
                db.book.release_date,
                db.book.downloads,
                db.book.contributions_remaining,
                db.auth_user.name,
            ]
        )


class TestSearchGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SearchGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book_page')
        self.assertEqual(grid._attributes['field'], 'created_on')

    def test__filters(self):
        grid = SearchGrid()
        self.assertEqual(len(grid.filters()), 0)
        env = globals()
        request = env['request']
        request.vars.kw = 'keyword'
        self.assertEqual(len(grid.filters()), 1)

    def test__visible_fields(self):
        grid = SearchGrid()
        self.assertEqual(
            grid.visible_fields(),
            [
                db.book.name,
                db.book_page.created_on,
                db.book.views,
                db.book.contributions_remaining,
                db.auth_user.name,
            ]
        )


class TestFunctions(LocalTestCase):
    _book = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._creator = cls.add(db.creator, dict(path_name='test__functions'))
        name = '_My Functions Book_'
        book_type_id = db(db.book_type).select().first().id
        cls._book = cls.add(db.book, dict(
            name=name,
            creator_id=cls._creator.id,
            book_type_id=book_type_id,
        ))

        cls.add(db.book_page, dict(
            book_id=cls._book.id,
            page_no=1,
        ))

    @classmethod
    def _row(cls):
        return db(db.book.id == cls._book.id).select(
            db.book.ALL,
            db.creator.ALL,
            left=[db.creator.on(db.book.creator_id == db.creator.id)],
            orderby=db.book.id,
            limitby=(0, 1)
        ).first()

    def _parse_link(self, link):
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        data = {}
        soup = BeautifulSoup(str(link))
        anchor = soup.find('a')
        data['string'] = anchor.string
        data['href'] = anchor['href']
        data['class'] = anchor['class']
        try:
            data['type'] = anchor['type']
        except KeyError:
            data['type'] = None
        return data

    def test_constants(self):
        self.assertEqual(
            GRID_CLASSES.keys(),
            ['ongoing', 'contributions', 'creators', 'search']
        )

    def test__book_contribute_button(self):
        self.assertEqual(book_contribute_button({}), '')

        self._book.update_record(creator_id=-1)
        db.commit()
        self.assertEqual(book_contribute_button(self._row()), '')

        self._book.update_record(creator_id=self._creator.id)
        self._creator.update_record(paypal_email='')
        db.commit()
        self.assertEqual(book_contribute_button(self._row()), '')

        self._creator.update_record(paypal_email='paypal@email.com')
        db.commit()

        data = self._parse_link(book_contribute_button(self._row()))
        self.assertEqual(data['string'], 'Contribute')
        self.assertTrue('/contributions/modal?book_id=' in data['href'])
        self.assertTrue('contribute_button' in data['class'])

    def test__classified(self):
        env = globals()
        request = env['request']

        tests = [
            #(request.vars.o, request.vars.creator_id, expect)
            (None, None, OngoingGrid),
            ('_fake_', None, OngoingGrid),
            ('ongoing', None, OngoingGrid),
            # ('releases', None, ReleasesGrid),
            ('contributions', None, ContributionsGrid),
            ('creators', None, CartoonistsGrid),
            ('contributions', 1, CreatorGrid),
        ]
        for t in tests:
            request.vars.o = t[0]
            request.vars.creator_id = t[1]
            self.assertEqual(classified(request), t[2])

    def test__creator_contribute_button(self):
        self.assertEqual(creator_contribute_button({}), '')

        self._creator.update_record(paypal_email='')
        db.commit()
        self.assertEqual(creator_contribute_button(self._row()), '')

        self._creator.update_record(paypal_email='paypal@email.com')
        db.commit()

        data = self._parse_link(creator_contribute_button(self._row()))
        self.assertEqual(data['string'], 'Contribute')
        self.assertTrue('/contributions/modal?creator_id=' in data['href'])
        self.assertTrue('contribute_button' in data['class'])

    def test__download_link(self):
        self.assertEqual(download_link({}), '')

        data = self._parse_link(download_link(self._row()))
        self.assertEqual(data['string'], 'Download')
        self.assertTrue('/books/download/' in data['href'])
        self.assertTrue('fixme' in data['class'])

    def test__link_book_id(self):
        self.assertEqual(link_book_id({}), 0)

        row = Storage(self._row())
        self.assertEqual(link_book_id(row), self._book.id)
        row.book = None
        self.assertEqual(link_book_id(row), 0)

    def test__read_link(self):
        self.assertEqual(read_link({}), '')

        data = self._parse_link(read_link(self._row()))
        self.assertEqual(data['string'], 'Read')
        self.assertTrue(
            '/test__functions/_My_Functions_Book__001/001' in data['href'])
        self.assertTrue('btn' in data['class'])

    def test__torrent_link(self):
        self.assertEqual(torrent_link({}), '')

        data = self._parse_link(torrent_link(self._row()))
        self.assertEqual(data['string'], 'all-test__functions.torrent')
        self.assertTrue(
            '/zcomx/FIXME/FIXME/all-test__functions.torrent' in data['href'])
        self.assertTrue('fixme' in data['class'])
        self.assertEqual(data['type'], None)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
