#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Test suite for zcomx/modules/search.py

"""
import unittest
import urllib
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.storage import Storage
from gluon.tools import prettydate
from applications.zcomx.modules.books import \
    book_name, \
    get_page, \
    formatted_name, \
    page_url
from applications.zcomx.modules.creators import \
    can_receive_contributions, \
    creator_name, \
    formatted_name as formatted_creator_name
from applications.zcomx.modules.search import \
    BookTile, \
    CartoonistTile, \
    CartoonistsGrid, \
    ContributionsGrid, \
    CreatorMoniesGrid, \
    GRID_CLASSES, \
    Grid, \
    MoniesBookTile, \
    OngoingGrid, \
    ReleasesGrid, \
    SearchGrid, \
    Tile, \
    book_contribute_button, \
    creator_contribute_button, \
    classified, \
    download_link, \
    link_book_id, \
    read_link, \
    torrent_link
from applications.zcomx.modules.tests.runner import LocalTestCase
from applications.zcomx.modules.utils import entity_to_row
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE

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
        query = (db.book.status == BOOK_STATUS_ACTIVE)
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
        self.assertEqual(grid._paginate, 12)
        self.assertEqual(grid.items_per_page(), 12)

        for t in [10, 20, 9999]:
            args = {'paginate': t}
            grid = SubGrid(form_grid_args=args)
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

    def test__render(self):
        grid = SubGrid()
        grid_div = grid.render()
        soup = BeautifulSoup(str(grid_div))
        # <div class="grid_section"><div class="row tile_view">
        #    ...
        div = soup.div
        self.assertEqual(div['class'], 'grid_section')
        div_2 = div.div
        self.assertEqual(div_2['class'], 'row tile_view')

    def test__rows(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = SubGrid()
        rows = grid.rows()
        self.assertEqual(len(rows), grid._paginate)
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

    def test__tabs(self):
        grid = SubGrid()
        # Default as per front page
        for key in grid.request.vars.keys():
            del grid.request.vars[key]
        tabs = grid.tabs()
        soup = BeautifulSoup(str(tabs))
        # <ul class="nav nav-tabs">
        #   <li class="nav-tab active">
        #     <a href="/?o=ongoing">ongoing</a>
        #   </li>
        #   <li class="nav-tab ">
        #     <a href="/?o=releases">releases</a>
        #   </li>
        #   <li class="nav-tab ">
        #     <a href="/?o=contributions">contributions</a>
        #   </li>
        #   <li class="nav-tab ">
        #     <a href="/?o=creators">cartoonists</a>
        #   </li>
        # </ul>

        ul = soup.ul
        self.assertEqual(ul['class'], 'nav nav-tabs')
        li_1 = ul.li
        self.assertEqual(li_1['class'], 'nav-tab active')
        anchor_1 = li_1.a
        self.assertEqual(anchor_1['href'], '/?o=ongoing')
        self.assertEqual(anchor_1.string, 'ongoing')

        li_2 = li_1.nextSibling
        anchor_2 = li_2.a
        self.assertEqual(anchor_2['href'], '/?o=releases')
        self.assertEqual(anchor_2.string, 'releases')

        # li_2 = li_1.nextSibling
        # anchor_2 = li_2.a
        # self.assertEqual(anchor_2['href'], '/?o=contributions')
        # self.assertEqual(anchor_2.string, 'contributions')

        li_3 = li_2.nextSibling
        self.assertEqual(li_3['class'], 'nav-tab ')
        anchor_3 = li_3.a
        self.assertEqual(anchor_3['href'], '/?o=creators')
        self.assertEqual(anchor_3.string, 'cartoonists')

        # Test removal of request.vars.contribute
        grid.request.vars.contribute = '1'
        tabs = grid.tabs()
        soup = BeautifulSoup(str(tabs))
        anchor_1 = soup.ul.li.a
        self.assertEqual(anchor_1['href'], '/?o=ongoing')
        anchor_2 = soup.ul.li.nextSibling.a
        self.assertEqual(anchor_2['href'], '/?o=releases')
        # anchor_2 = soup.ul.li.nextSibling.a
        # self.assertEqual(anchor_2['href'], '/?o=contributions')
        anchor_3 = soup.ul.li.nextSibling.nextSibling.a
        self.assertEqual(anchor_3['href'], '/?o=creators')

    def test__tile_value(self):
        creator = self.add(db.creator, dict(
            email='test__tile_value@email.com'
        ))
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

    def test__viewby_buttons(self):
        grid = SubGrid()
        # Default as per front page
        for key in grid.request.vars.keys():
            del grid.request.vars[key]
        buttons = grid.viewby_buttons()
        soup = BeautifulSoup(str(buttons))
        # <div class="btn-group">
        #   <a class="btn btn-default btn-lg active" href="/?view=list">
        #     <span class="glyphicon glyphicon-th-list"></span>
        #   </a>
        #   <a class="btn btn-default btn-lg disabled" href="/?view=tile">
        #     <span class="glyphicon glyphicon-th-large"></span>
        #   </a>
        # </div>
        div = soup.div
        self.assertEqual(div['class'], 'btn-group')
        anchor_1 = div.a
        self.assertEqual(anchor_1['class'], 'btn btn-default btn-lg active')
        self.assertEqual(anchor_1['href'], '/?view=list')
        span_1 = anchor_1.span
        self.assertEqual(span_1['class'], 'glyphicon glyphicon-th-list')

        anchor_2 = anchor_1.nextSibling
        self.assertEqual(anchor_2['class'], 'btn btn-default btn-lg disabled')
        self.assertEqual(anchor_2['href'], '/?view=tile')
        span_2 = anchor_2.span
        self.assertEqual(span_2['class'], 'glyphicon glyphicon-th-large')

        # Test removal of request.vars.contribute
        grid.request.vars.contribute = '1'
        buttons = grid.viewby_buttons()
        soup = BeautifulSoup(str(buttons))
        anchor_1 = soup.div.a
        self.assertEqual(anchor_1['href'], '/?view=list')
        anchor_2 = soup.div.a.nextSibling
        self.assertEqual(anchor_2['href'], '/?view=tile')

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
            # [db.auth_user.name, db.creator.contributions_remaining]
            [db.auth_user.name]
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


class TestCreatorMoniesGrid(LocalTestCase):

    def test____init__(self):
        # protected-access (W0212): *Access to a protected member %%s
        # pylint: disable=W0212
        grid = CreatorMoniesGrid()
        self.assertTrue(grid)
        self.assertEqual(grid._attributes['table'], 'book')
        self.assertEqual(grid._attributes['field'], 'name')

    def test__filters(self):
        # creator not set
        grid = CreatorMoniesGrid()
        self.assertEqual(len(grid.filters()), 0)

        # creator is set
        creator = self.add(db.creator, dict(email='test__filters@email.com'))
        grid = CreatorMoniesGrid(creator_entity=creator)
        self.assertEqual(len(grid.filters()), 1)


class TestMoniesBookTile(LocalTestCase):

    _grid = None
    _row = None
    _value = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._grid = OngoingGrid()
        cls._row = cls._grid.rows()[0]
        cls._value = cls._grid.tile_value(cls._row)
        cls._creator = entity_to_row(db.creator, cls._row.creator.id)

    def test____init__(self):
        tile = MoniesBookTile(db, self._value, self._row)
        self.assertTrue(tile)

    def test__contribute_link(self):
        tile = MoniesBookTile(db, self._value, self._row)
        self.assertEqual(tile.contribute_link(), None)

    def test__download_link(self):
        tile = MoniesBookTile(db, self._value, self._row)
        self.assertEqual(tile.contribute_link(), None)

    def test__footer(self):
        save_paypal = self._row.creator.paypal_email

        # Test: can contribute = True
        self._row.creator.paypal_email = 'testing@paypal.com'
        self.assertTrue(can_receive_contributions(db, self._row.creator))

        tile = MoniesBookTile(db, self._value, self._row)
        footer = tile.footer()
        soup = BeautifulSoup(str(footer))
        # <div class="col-sm-12 name">
        #    <a class="contribute_button"
        #      href="/contributions/modal?book_id=64">
        #         Test Do Not Delete 01 (of 01)</a>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 name')

        anchor = div.a
        self.assertEqual(anchor['class'], 'contribute_button no_rclick_menu')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id={id}'.format(
                id=self._row.book.id)
        )

        # Test: can contribute = False
        self._row.creator.paypal_email = None
        self.assertFalse(can_receive_contributions(db, self._row.creator))
        tile = MoniesBookTile(db, self._value, self._row)
        footer = tile.footer()
        soup = BeautifulSoup(str(footer))
        # <div class="col-sm-12 name">Test Do Not Delete 01 (of 01)</div>
        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 name')
        self.assertEqual(
            div.string,
            formatted_name(
                db, self._row.book.id, include_publication_year=False)
        )

        # Restore
        self._row.creator.paypal_email = save_paypal

    def test__image(self):
        save_paypal = self._row.creator.paypal_email

        # Test: can contribute = True
        self._row.creator.paypal_email = 'testing@paypal.com'
        self.assertTrue(can_receive_contributions(db, self._row.creator))

        tile = MoniesBookTile(db, self._value, self._row)
        image_div = tile.image()
        soup = BeautifulSoup(str(image_div))
        # <div class="col-sm-12 image_container">
        #   <a class="contribute_button"
        #           href="/contributions/modal?book_id=64">
        #       <img alt=""
        #       src="/images/download/book_page.image.aaa.000.png?size=web" />
        #   </a>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 image_container')
        anchor = div.a
        self.assertEqual(anchor['class'], 'contribute_button no_rclick_menu')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id={id}'.format(
                id=self._row.book.id)
        )

        img = anchor.img
        self.assertEqual(img['alt'], '')
        first = get_page(self._row.book, page_no='first')
        self.assertEqual(img['src'], '/images/download/{i}?size=web'.format(
            i=first.image))

        # Test: can contribute = False
        self._row.creator.paypal_email = None
        self.assertFalse(can_receive_contributions(db, self._row.creator))
        tile = MoniesBookTile(db, self._value, self._row)
        image_div = tile.image()
        soup = BeautifulSoup(str(image_div))
        #  <div class="col-sm-12 image_container">
        #    <img alt=""
        #       src="/images/download/book_page.image.aaa.000.png?size=web" />
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 image_container')

        img = div.img
        self.assertEqual(img['alt'], '')
        first = get_page(self._row.book, page_no='first')
        self.assertEqual(img['src'], '/images/download/{i}?size=web'.format(
            i=first.image))

        # Restore
        self._row.creator.paypal_email = save_paypal

    def test_render(self):
        tile = MoniesBookTile(db, self._value, self._row)
        div = tile.render()
        soup = BeautifulSoup(str(div))

        div = soup.div
        self.assertEqual(div['class'], 'item_container monies_book_tile_item')

        div_1 = div.div
        self.assertEqual(div_1['class'], 'row')
        self.assertEqual(str(div_1.div), str(tile.image()))

        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'row')
        self.assertEqual(str(div_2.div), str(tile.footer()))

    def test__subtitle(self):
        tile = MoniesBookTile(db, self._value, self._row)
        self.assertEqual(tile.contribute_link(), None)

    def test__title(self):
        tile = MoniesBookTile(db, self._value, self._row)
        self.assertEqual(tile.contribute_link(), None)


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
                # db.book.contributions_remaining,
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
                # db.book.contributions_remaining,
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


class TestTile(LocalTestCase):

    _grid = None
    _row = None
    _value = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._grid = OngoingGrid()
        cls._row = cls._grid.rows()[0]
        cls._value = cls._grid.tile_value(cls._row)

    def test____init__(self):
        tile = Tile(db, self._value, self._row)
        self.assertTrue(tile)

    def test__contribute_link(self):
        tile = Tile(db, self._value, self._row)
        self.assertEqual(tile.contribute_link(), None)

    def test__download_link(self):
        tile = Tile(db, self._value, self._row)
        self.assertEqual(tile.download_link(), None)

    def test__footer(self):
        tile = Tile(db, self._value, self._row)
        footer = tile.footer()
        soup = BeautifulSoup(str(footer))
        # <div class="col-sm-12">
        # <ul class="breadcrumb pipe_delimiter"></ul>
        # <div class="orderby_field_value">1 week ago</div>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12')

        ul = div.ul
        self.assertEqual(ul['class'], 'breadcrumb pipe_delimiter')
        self.assertEqual(ul.string, None)

        div_2 = div.div
        self.assertEqual(div_2['class'], 'orderby_field_value')

        self.assertEqual(
            div_2.string,
            str(prettydate(self._row.book_page.created_on))
        )

    def test__footer_links(self):
        tile = Tile(db, self._value, self._row)
        links = tile.footer_links()
        soup = BeautifulSoup(str(links))
        # <ul class="breadcrumb pipe_delimiter"></ul>

        ul = soup.ul
        self.assertEqual(ul['class'], 'breadcrumb pipe_delimiter')
        self.assertEqual(ul.string, None)

    def test__image(self):
        tile = Tile(db, self._value, self._row)
        self.assertEqual(tile.image(), None)

    def test__render(self):
        tile = Tile(db, self._value, self._row)
        div = tile.render()
        soup = BeautifulSoup(str(div))
        #  <div class="item_container">
        #    <div class="row">
        #      <div class="col-sm-12">
        #        <ul class="breadcrumb pipe_delimiter"></ul>
        #        <div class="orderby_field_value">1 week ago</div>
        #      </div>
        #    </div>
        #  </div>

        div = soup.div
        self.assertEqual(div['class'], 'item_container tile_item')

        div_2 = div.div
        self.assertEqual(div_2['class'], 'row')

        div_3 = div_2.div
        self.assertEqual(div_3['class'], 'col-sm-12')

        ul = div_3.ul
        self.assertEqual(ul['class'], 'breadcrumb pipe_delimiter')
        self.assertEqual(ul.string, None)

        div_4 = div_3.div
        self.assertEqual(div_4['class'], 'orderby_field_value')

    def test__subtitle(self):
        tile = Tile(db, self._value, self._row)
        self.assertEqual(tile.subtitle(), None)

    def test__title(self):
        tile = Tile(db, self._value, self._row)
        self.assertEqual(tile.title(), None)


class TestBookTile(LocalTestCase):

    _grid = None
    _row = None
    _value = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._grid = ReleasesGrid()
        cls._row = cls._grid.rows()[0]
        cls._value = cls._grid.tile_value(cls._row)
        cls._creator = entity_to_row(db.creator, cls._row.creator.id)

    def test____init__(self):
        tile = BookTile(db, self._value, self._row)
        self.assertTrue(tile)

    def test__contribute_link(self):
        tile = BookTile(db, self._value, self._row)
        link = tile.contribute_link()
        soup = BeautifulSoup(str(link))
        # <a class="contribute_button"
        #    href="/contributions/modal?book_id=98">contribute</a>
        anchor = soup.a
        self.assertEqual(anchor['class'], 'contribute_button no_rclick_menu')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?book_id={i}'.format(i=self._row.book.id)
        )

    def test__download_link(self):
        save_book_id = self._row.book.id
        book = db(db.book.id == self._row.book.id).select().first()

        # Test book with cbz
        if not book.cbz:
            book_with_cbz_id = db(db.book.cbz != None).select().first()
            self._row.book.id = book_with_cbz_id.id

        tile = BookTile(db, self._value, self._row)
        link = tile.download_link()
        soup = BeautifulSoup(str(link))
        # <a class="download_button no_rclick_menu"
        #       href="/downloads/modal/93">download</a>
        anchor = soup.a
        self.assertEqual(anchor['class'], 'download_button no_rclick_menu')
        self.assertEqual(anchor['href'], '/downloads/modal/{i}'.format(
            i=self._row.book.id))
        self.assertEqual(anchor.string, 'download')

        # Test without cbz
        self._row.book.id = save_book_id
        if book.cbz:
            book_no_cbz_id = db(db.book.cbz == None).select().first()
            self._row.book.id = book_no_cbz_id.id

        tile = BookTile(db, self._value, self._row)
        link = tile.download_link()
        soup = BeautifulSoup(str(link))
        self.assertEqual(str(soup), '<span></span>')

        # Reset
        self._row.book.id = save_book_id

    def test_footer(self):
        tile = BookTile(db, self._value, self._row)
        footer = tile.footer()
        soup = BeautifulSoup(str(footer))
        # <div class="col-sm-12">
        #   <ul class="breadcrumb pipe_delimiter">
        #     <li><a class="download_button no_rclick_menu"
        #       href="/downloads/modal/2208">download</a>
        #     </li>
        #   </ul>
        #   <div class="orderby_field_value">2015-03-04</div>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12')

        ul = div.ul
        self.assertEqual(ul['class'], 'breadcrumb pipe_delimiter')
        lis = ul.findAll('li')
        dl_li = None
        if can_receive_contributions(db, self._creator):
            self.assertEqual(len(lis), 2)
            li = lis[0]
            anchor = li.a
            self.assertEqual(
                anchor['class'], 'contribute_button no_rclick_menu')
            self.assertEqual(
                anchor['href'],
                '/contributions/modal?book_id={id}'.format(
                    id=self._row.book.id)
            )
            self.assertEqual(anchor.string, 'contribute')
            dl_li = li.nextSibling
        else:
            self.assertEqual(len(lis), 1)
            dl_li = lis[0]

        anchor = dl_li.a
        self.assertEqual(anchor['class'], 'download_button no_rclick_menu')
        self.assertEqual(anchor['href'], '/downloads/modal/{i}'.format(
            i=self._row.book.id))
        self.assertEqual(anchor.string, 'download')

        div_2 = div.div
        self.assertEqual(div_2['class'], 'orderby_field_value')
        self.assertEqual(
            div_2.string,
            str(self._row.book.release_date)
        )

    def test__image(self):
        tile = BookTile(db, self._value, self._row)
        image_div = tile.image()
        soup = BeautifulSoup(str(image_div))
        # <div class="col-sm-12 image_container">
        #   <a class="book_page_image"
        #       href="/Jim_Karsten/Test_Do_Not_Delete_001/001" title="">
        #   <img alt=""
        #       src="/images/download/book_page.image.aaa.00.jpg?size=web" />
        #   </a>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 image_container')
        anchor = div.a
        self.assertEqual(anchor['class'], 'book_page_image')
        first = get_page(self._row.book, page_no='first')
        self.assertEqual(anchor['href'], page_url(first))
        self.assertEqual(anchor['title'], '')

        img = anchor.img
        self.assertEqual(img['alt'], '')
        self.assertEqual(img['src'], '/images/download/{i}?size=web'.format(
            i=first.image))

    def test_render(self):
        tile = BookTile(db, self._value, self._row)
        div = tile.render()
        soup = BeautifulSoup(str(div))

        div = soup.div
        self.assertEqual(div['class'], 'item_container book_tile_item')

        div_1 = div.div
        self.assertEqual(div_1['class'], 'row')
        self.assertEqual(str(div_1.div), str(tile.title()))

        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'row')
        self.assertEqual(str(div_2.div), str(tile.subtitle()))

        div_3 = div_2.nextSibling
        self.assertEqual(div_3['class'], 'row')
        self.assertEqual(str(div_3.div), str(tile.image()))

        div_4 = div_3.nextSibling
        self.assertEqual(div_4['class'], 'row')
        self.assertEqual(str(div_4.div), str(tile.footer()))

    def test__subtitle(self):
        tile = BookTile(db, self._value, self._row)
        subtitle_div = tile.subtitle()
        soup = BeautifulSoup(str(subtitle_div))
        # <div class="col-sm-12 creator">
        #   <a href="/Jim_Karsten" title="Jim Karsten">Jim Karsten</a>
        # </div>
        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 creator')
        anchor = div.a
        self.assertEqual(
            anchor['href'],
            '/{name}'.format(
                name=creator_name(self._row.creator.id, use='url'))
        )
        self.assertEqual(anchor['title'], self._row.auth_user.name)
        self.assertEqual(anchor.string, self._row.auth_user.name)

    def test__title(self):
        tile = BookTile(db, self._value, self._row)
        title_div = tile.title()
        soup = BeautifulSoup(str(title_div))
        # <div class="col-sm-12 name">
        #   <a href="/Jim_Karsten/Test_Do_Not_Delete_001"
        #       title="Test Do Not Delete 001">Test Do Not Delete 001</a>
        # </div>
        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 name')
        anchor = div.a
        self.assertEqual(anchor['href'], '/{c}/{b}'.format(
            c=creator_name(self._row.creator.id, use='url'),
            b=urllib.quote(book_name(self._row.book.id, use='url'))
        ))
        book_formatted = formatted_name(
            db, self._row.book.id, include_publication_year=True)
        self.assertEqual(anchor['title'], book_formatted)
        self.assertEqual(anchor.string, book_formatted)


class TestCartoonistTile(LocalTestCase):

    _grid = None
    _row = None
    _value = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUpClass(cls):
        cls._grid = CartoonistsGrid()
        cls._row = cls._grid.rows()[0]
        cls._value = cls._grid.tile_value(cls._row)
        cls._creator = entity_to_row(db.creator, cls._row.creator.id)

    def test____init__(self):
        tile = CartoonistTile(db, self._value, self._row)
        self.assertTrue(tile)

    def test__contribute_link(self):
        tile = CartoonistTile(db, self._value, self._row)
        link = tile.contribute_link()
        soup = BeautifulSoup(str(link))
        # <a class="contribute_button"
        #    href="/contributions/modal?creator_id=98">contribute</a>
        anchor = soup.a
        self.assertEqual(anchor['class'], 'contribute_button no_rclick_menu')
        self.assertEqual(
            anchor['href'],
            '/contributions/modal?creator_id={i}'.format(
                i=self._row.creator.id)
        )

    def test__download_link(self):
        tile = CartoonistTile(db, self._value, self._row)
        link = tile.download_link()
        soup = BeautifulSoup(str(link))
        # <a href="/Jim_Karsten">download</a>
        anchor = soup.a
        self.assertEqual(
            anchor['href'],
            '/{name}'.format(
                name=creator_name(self._row.creator.id, use='url'))
        )

    def test__footer(self):
        tile = CartoonistTile(db, self._value, self._row)
        footer = tile.footer()
        soup = BeautifulSoup(str(footer))
        # <div class="col-sm-12">
        #   <ul class="breadcrumb pipe_delimiter">
        #     <li><a class="contribute_button"
        #       href="/contributions/modal?creator_id=101">contribute</a></li>
        #     <li><a href="/Jim_Karsten">download</a></li>
        #   </ul>
        #   <div class="orderby_field_value">1 week ago</div>
        # </div>
        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12')

        ul = div.ul
        self.assertEqual(ul['class'], 'breadcrumb pipe_delimiter')
        lis = ul.findAll('li')
        dl_li = None
        if can_receive_contributions(db, self._creator):
            self.assertEqual(len(lis), 2)
            li = lis[0]
            anchor = li.a
            self.assertEqual(
                anchor['class'], 'contribute_button no_rclick_menu')
            self.assertEqual(
                anchor['href'],
                '/contributions/modal?creator_id={id}'.format(
                    id=self._row.creator.id)
            )
            self.assertEqual(anchor.string, 'contribute')
            dl_li = li.nextSibling
        else:
            self.assertEqual(len(lis), 1)
            dl_li = lis[0]

        anchor = dl_li.a
        self.assertEqual(
            anchor['href'],
            '/{name}'.format(
                name=creator_name(self._row.creator.id, use='url'))
        )
        self.assertEqual(anchor.string, 'download')

        div_2 = div.div
        self.assertEqual(div_2['class'], 'orderby_field_value')
        self.assertEqual(
            div_2.string,
            None
            # db.creator.contributions_remaining.represent(
            #    self._row.creator.contributions_remaining, self._row)
        )

    def test__image(self):
        tile = CartoonistTile(db, self._value, self._row)
        image_div = tile.image()
        soup = BeautifulSoup(str(image_div))
        if self._creator.image:
            # <div class="col-sm-12 image_container">
            #   <a href="/Charles_Forsman" title="">
            #     <img alt="Charles Forsman"
            #      src="/images/download/creator.image.aaa.000.jpg?size=web" />
            #   </a>
            # </div
            div = soup.div
            self.assertEqual(div['class'], 'col-sm-12 image_container')
            anchor = div.a
            self.assertEqual(
                anchor['href'],
                '/{name}'.format(
                    name=creator_name(self._row.creator.id, use='url'))
            )
            self.assertEqual(anchor['title'], '')
            img = anchor.img
            self.assertEqual(img['alt'], formatted_creator_name(self._creator))
            self.assertTrue('/images/download/creator.image' in img['src'])

        else:
            # <div class="col-sm-12 image_container">
            #   <a href="/Jim_Karsten" title="">
            #   <div alt="Jim Karsten" class="preview placeholder_torso">
            #     <i class="icon zc-torso"></i>
            #   </div>
            #   </a>
            # </div>
            div = soup.div
            self.assertEqual(div['class'], 'col-sm-12 image_container')
            anchor = div.a
            self.assertEqual(
                anchor['href'],
                '/{name}'.format(
                    name=creator_name(self._row.creator.id, use='url'))
            )
            self.assertEqual(anchor['title'], '')
            div_2 = div.div
            self.assertEqual(div_2['class'], 'preview placeholder_torso')
            icon = div_2.i
            self.assertEqual(icon['class'], 'icon zc-torso')

    def test_render(self):
        tile = CartoonistTile(db, self._value, self._row)
        div = tile.render()
        soup = BeautifulSoup(str(div))

        # <div class="item_container">
        #   <div class="row">
        #     <div class="col-sm-12 name">
        #       <a href="/Jim_Karsten" title="Jim Karsten">Jim Karsten</a>
        #     </div>
        #   </div>
        #   <div class="row">
        #     <div class="col-sm-12 image_container">
        #       <a href="/Jim_Karsten" title="">
        #       <div alt="Jim Karsten" class="preview placeholder_torso">
        #         <i class="icon zc-torso"></i>
        #       </div>
        #       </a>
        #     </div>
        #   </div>
        #   <div class="row">
        #     <div class="col-sm-12">
        #       <ul class="breadcrumb pipe_delimiter">
        #         <li><a href="/Jim_Karsten">download</a></li>
        #       </ul>
        #       <div class="orderby_field_value">1 week ago</div>
        #     </div>
        #   </div>
        # </div>

        div = soup.div
        self.assertEqual(div['class'], 'item_container cartoonist_tile_item')

        div_1 = div.div
        self.assertEqual(div_1['class'], 'row')
        self.assertEqual(str(div_1.div), str(tile.title()))

        div_2 = div_1.nextSibling
        self.assertEqual(div_2['class'], 'row')
        self.assertEqual(str(div_2.div), str(tile.image()))

        div_3 = div_2.nextSibling
        self.assertEqual(div_3['class'], 'row')
        self.assertEqual(str(div_3.div), str(tile.footer()))

    def test__title(self):
        tile = CartoonistTile(db, self._value, self._row)
        title_div = tile.title()
        soup = BeautifulSoup(str(title_div))
        # <div class="col-sm-12 name">
        #   <a href="/Jim_Karsten" title="Jim Karsten">Jim Karsten</a>
        # </div>
        div = soup.div
        self.assertEqual(div['class'], 'col-sm-12 name')
        anchor = div.a
        self.assertEqual(
            anchor['href'],
            '/{name}'.format(
                name=creator_name(self._row.creator.id, use='url'))
        )
        self.assertEqual(anchor['title'], self._row.auth_user.name)
        self.assertEqual(anchor.string, self._row.auth_user.name)


class TestFunctions(LocalTestCase):
    _auth_user = None
    _book = None
    _creator = None

    # C0103: *Invalid name "%s" (should match %s)*
    # pylint: disable=C0103
    @classmethod
    def setUp(cls):
        cls._auth_user = cls.add(db.auth_user, dict(
            name='First Last',
        ))
        cls._creator = cls.add(db.creator, dict(
            auth_user_id=cls._auth_user.id,
            name_for_url='FirstLast',
        ))
        name = '_My Functions Book_'
        book_type_id = db(db.book_type).select().first().id
        cls._book = cls.add(db.book, dict(
            name=name,
            creator_id=cls._creator.id,
            book_type_id=book_type_id,
            cbz='_fake_cbz_',
            torrent='_fake_torrent_',
            name_for_url='MyFunctionsBook',
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
        if anchor:
            data['string'] = anchor.string
            for attr in ['href', 'class', 'type']:
                try:
                    data[attr] = anchor[attr]
                except KeyError:
                    data[attr] = None
        return data

    def test_constants(self):
        self.assertEqual(
            GRID_CLASSES.keys(),
            ['ongoing', 'releases', 'creators', 'search']
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
            # (request.vars.o, expect)
            (None, OngoingGrid),
            ('_fake_', OngoingGrid),
            ('ongoing', OngoingGrid),
            ('releases', ReleasesGrid),
            # ('contributions', ContributionsGrid),
            ('creators', CartoonistsGrid),
        ]
        for t in tests:
            request.vars.o = t[0]
            self.assertEqual(classified(request), t[1])

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
        row = self._row()
        data = self._parse_link(download_link(row))
        self.assertEqual(data['string'], 'Download')
        self.assertEqual(data['href'], '/downloads/modal/{i}'.format(
            i=row.book.id))
        self.assertEqual(
            data['class'],
            'btn btn-default download_button no_rclick_menu'
        )

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
            '/FirstLast/MyFunctionsBook/001' in data['href'])
        self.assertTrue('btn' in data['class'])

    def test__torrent_link(self):
        self.assertEqual(torrent_link({}), '')

        data = self._parse_link(torrent_link(self._row()))
        self.assertEqual(data['string'], 'FirstLast.torrent')
        self.assertEqual(
            data['href'],
            '/FirstLast_({i}.zco.mx).torrent'.format(i=self._creator.id)
        )
        self.assertEqual(data['class'], 'log_download_link')
        self.assertEqual(data['type'], None)


def setUpModule():
    """Set up web2py environment."""
    # C0103: *Invalid name "%%s" (should match %%s)*
    # pylint: disable=C0103
    LocalTestCase.set_env(globals())


if __name__ == '__main__':
    unittest.main()
