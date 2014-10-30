#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Search classes and functions.
"""
import collections
from gluon import *
from applications.zcomx.modules.books import \
    contribute_link as book_contribute_link, \
    formatted_name, \
    read_link as book_read_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    can_receive_contributions, \
    contribute_link as creator_contribute_link, \
    torrent_link as creator_torrent_link, \
    url as creator_url
from applications.zcomx.modules.stickon.sqlhtml import LocalSQLFORM


class Grid(object):
    """Class representing a grid for search results."""

    # The key element is the one displayed in bottom right corner of tiles.
    _attributes = {
        'table': None,                  # db table name of key element
        'field': None,                  # db field name of key element
        'label': None,                  # default label of key element
        'tab_label': None,              # label for tab on front page
                                        #     (defaults to label)
        'header_label': None,           # label for column header
                                        #     (defaults to label)
        'class': None,                  # class of div containing key element
        'order_field': None,            # field to use for sorting
                                        #     (default table.field)
        'order_dir': 'ASC',             # Sort order direction. 'ASC' or 'DESC'
    }

    _buttons = [
        'book_contribute',
        'download',
        'read',
    ]

    _default_paginate = 10

    def __init__(self, form_grid_args=None):
        """Constructor"""
        self.form_grid_args = form_grid_args
        self.db = current.app.db
        self.request = current.request
        self.form_grid = None
        self._paginate = None
        self._set()

    def _set(self):
        """Set the grid. """
        db = self.db
        request = self.request
        queries = []
        queries.append((db.book.status == True))
        queries.extend(self.filters())

        db.auth_user.name.represent = lambda v, row: A(
            v,
            _href=creator_url(row.creator.id, extension=False)
        )

        db.book.name.represent = lambda v, row: A(
            formatted_name(
                db,
                row.book,
                include_publication_year=False,
            ),
            _href=book_url(row.book.id, extension=False)
        )

        db.book_page.created_on.represent = lambda v, row: str(v.date()) \
            if v is not None else 'n/a'

        fields = [
            db.book.id,
            db.book.name,
            db.book.book_type_id,
            db.book.number,
            db.book.of_number,
            db.book_page.created_on,
            db.book.publication_year,
            db.book.release_date,
            db.book.views_year,
            db.book.downloads,
            db.book.contributions_remaining,
            db.book.created_on,
            db.creator.id,
            db.auth_user.name,
            db.creator.paypal_email,
            db.creator.contributions_remaining,
        ]

        visible = [str(x) for x in self.visible_fields()]
        for f in fields:
            if str(f) in visible:
                self.show(f)
            else:
                self.hide(f)

        headers = {
            'auth_user.name': 'Cartoonist',
            'book.name': 'Title',
            'book.publication_year': 'Year',
            'book.released_date': 'Released',
            'book.views_year': 'Views',
            'book.contributions_remaining': 'Remaining',
            'book_page.created_on': 'Added',
            'creator.contributions_remaining': 'Remaining',
        }

        links = []

        def add_link(body, header=''):
            """Add link to links list."""
            links.append({'header': header, 'body': body})

        if 'read' in self._buttons:
            add_link(read_link)

        if 'torrent' in self._buttons:
            add_link(torrent_link)

        if 'creator_contribute' in self._buttons:
            add_link(creator_contribute_button)

        if 'download' in self._buttons:
            add_link(download_link)

        if 'book_contribute' in self._buttons:
            add_link(book_contribute_button)

        page2 = db.book_page.with_alias('page2')

        sorter_icons = (
            SPAN(XML('&#x25B2;'), _class='grid_sort_marker'),
            SPAN(XML('&#x25BC;'), _class='grid_sort_marker')
        )

        if not queries:
            queries.append(db.book)
        query = reduce(lambda x, y: x & y, queries) if queries else None

        grid_class = 'web2py_grid grid_view_{v} grid_key_{o}'.format(
            v=request.vars.view or 'tile',
            o=self.__class__.__name__.replace('Grid', '').lower()
        )

        kwargs = dict(
            fields=fields,
            headers=headers,
            orderby=self.orderby(),
            groupby=self.groupby(),
            left=[
                db.creator.on(db.book.creator_id == db.creator.id),
                db.auth_user.on(
                    db.creator.auth_user_id == db.auth_user.id
                ),
                db.book_page.on(db.book_page.book_id == db.book.id),
                page2.on(
                    (page2.book_id == db.book.id) &
                    (page2.id != db.book_page.id) &
                    (page2.created_on < db.book_page.created_on)
                ),
            ],
            paginate=self._default_paginate,
            details=False,
            editable=False,
            deletable=False,
            create=False,
            csv=False,
            searchable=False,
            maxtextlengths={
                'book.name': 50,
                'auth_user.name': 50,
            },
            links=links,
            sorter_icons=sorter_icons,
            editargs={'deletable': False},
            _class=grid_class,
        )
        if self.form_grid_args:
            kwargs.update(self.form_grid_args)

        self.form_grid = LocalSQLFORM.grid(query, **kwargs)
        self._paginate = kwargs['paginate']
        # Remove 'None' record count if applicable.
        for count, div in enumerate(self.form_grid[0]):
            if str(div) == '<div class="web2py_counter">None</div>':
                del self.form_grid[0][count]

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return []

    def groupby(self):
        """Return groupby defining how report is grouped.

        Returns:
            gluon.dal.Field
        """
        db = self.db
        return db.book.id

    def hide(self, field):
        """Hide the field."""
        return self.set_field(field, visible=False)

    def items_per_page(self):
        """Return the number of items (rows) per page."""
        return self._paginate if self._paginate else 20

    @classmethod
    def label(cls, key):
        """Return a label for an order_field

        The first found of these is returned:
            order_field[key]
            order_field['label']
            orderby_key
        """
        keys = [key, 'label']
        for k in keys:
            if k in cls._attributes:
                return cls._attributes[k]
        return cls.__name__.replace('Grid', '').lower()

    def order_fields(self):
        """Return list of fields used in ordering.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [db[self._attributes['table']][self._attributes['field']]]

    def orderby(self):
        """Return orderby defining how report is sorted.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        fields = self.order_fields()
        if self._attributes['order_dir'] == 'DESC':
            fields[0] = ~fields[0]
        fields.append(db.book.number)
        fields.append(db.book.id)                # For consistent results
        return fields

    def rows(self):
        """Return the rows of the grid."""
        return self.form_grid.rows if self.form_grid else []

    @classmethod
    def set_field(cls, field, visible=True):
        """Set the status of a field."""
        field.readable = visible
        field.writable = visible

    def show(self, field):
        """Show the field."""
        return self.set_field(field, visible=True)

    def tile_class(self):
        """Return the class name of div in tile of key element."""
        return 'tile_key_{o}'.format(
            o=self.__class__.__name__.replace('Grid', '').lower()
        )

    def tile_label(self):
        """Return the label of the key element in tile view."""
        if not 'label' in self._attributes:
            return ''
        return self._attributes['label'] or ''

    def tile_value(self, row):
        """Return the value of the key element in tile view."""
        db = self.db
        fieldname = self._attributes['field']
        tablename = self._attributes['table']
        value = row[tablename][fieldname]
        if db[tablename][fieldname].represent:
            value = db[tablename][fieldname].represent(value, row)
        return value or ''

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return []


class CartoonistsGrid(Grid):
    """Class representing a grid for search results: cartoonist"""

    _attributes = {
        'table': 'creator',
        'field': 'contributions_remaining',
        'label': 'remaining',
        'tab_label': 'cartoonists',
        'order_field': 'auth_user.name',
        'order_dir': 'ASC',
    }

    _buttons = [
        'creator_contribute',
        'torrent',
    ]

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def groupby(self):
        """Return groupby defining how report is grouped.

        Returns:
            gluon.dal.Field
        """
        db = self.db
        return db.creator.id

    def order_fields(self):
        """Return list of fields used in ordering.
        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [db.auth_user.name]

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.auth_user.name,
            db.creator.contributions_remaining,
        ]


class ContributionsGrid(Grid):
    """Class representing a grid for search results: contributions"""

    _attributes = {
        'table': 'book',
        'field': 'contributions_remaining',
        'label': 'remaining',
        'tab_label': 'contributions',
        'class': 'orderby_contributions',
        'order_dir': 'ASC',
    }

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        queries = []
        queries.append(db.book.contributions_remaining > 0)
        queries.append(db.creator.paypal_email != '')
        return queries

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.publication_year,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


class CreatorGrid(ContributionsGrid):
    """Class representing a grid for search results: creator"""

    def __init__(self, form_grid_args=None):
        """Constructor"""
        ContributionsGrid.__init__(self, form_grid_args=form_grid_args)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        request = self.request
        queries = []
        creator = None
        if request.vars.creator_id:
            query = (db.creator.id == request.vars.creator_id)
            creator = db(query).select(db.creator.ALL).first()

        if creator:
            queries.append((db.book.creator_id == creator.id))

        if request.vars.released == '0':
            queries.append((db.book.release_date == None))
        if request.vars.released == '1':
            queries.append((db.book.release_date != None))
        return queries

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.contributions_remaining,
        ]


class OngoingGrid(Grid):
    """Class representing a grid for search results: ongoing"""

    _attributes = {
        'table': 'book_page',
        'field': 'created_on',
        'label': 'page added',
        'tab_label': 'ongoing',
        'header_label': 'added',
        'class': 'orderby_ongoing',
        'order_dir': 'DESC',
    }

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        queries = []
        queries.append((db.book.release_date == None))
        return queries

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book_page.created_on,
            db.book.views_year,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


class ReleasesGrid(Grid):
    """Class representing a grid for search results: releases"""

    _attributes = {
        'table': 'book',
        'field': 'release_date',
        'label': 'release date',
        'tab_label': 'releases',
        'header_label': 'released',
        'class': 'orderby_releases',
        'order_dir': 'DESC',
    }

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        queries = []
        queries.append((db.book.release_date != None))
        return queries

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.publication_year,
            db.book.release_date,
            db.book.downloads,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


class SearchGrid(Grid):
    """Class representing a grid for search results."""

    _attributes = {
        'table': 'book_page',
        'field': 'created_on',
        'label': 'page added',
        'tab_label': 'search',
        'header_label': 'added',
        'order_dir': 'DESC',
    }

    def __init__(self, form_grid_args=None):
        """Constructor"""
        Grid.__init__(self, form_grid_args=form_grid_args)

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        request = self.request
        queries = []
        if request.vars.kw:
            queries.append(
                (db.book.name.contains(request.vars.kw)) |
                (db.auth_user.name.contains(request.vars.kw))
            )
        return queries

    def visible_fields(self):
        """Return list of visisble fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book_page.created_on,
            db.book.views_year,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


GRID_CLASSES = collections.OrderedDict()
GRID_CLASSES['ongoing'] = OngoingGrid
#GRID_CLASSES['releases'] = ReleasesGrid
GRID_CLASSES['contributions'] = ContributionsGrid
GRID_CLASSES['creators'] = CartoonistsGrid
GRID_CLASSES['search'] = SearchGrid


def book_contribute_button(row):
    """Return a 'contribute' button suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''

    # Only display if creator has a paypal address.
    if not 'creator' in row or not row.creator.paypal_email:
        return ''

    db = current.app.db
    return book_contribute_link(
        db,
        book_id,
        **dict(
            _class='btn btn-default contribute_button',
            _type='button'
        )
    )


def classified(request):
    """Return the appropriate Grid class for request.

    Args:
        request: gluon.global.Request instance

    Returns:
        Grid class or subclass
    """
    grid_class = OngoingGrid
    if request.vars.o:
        if request.vars.o in GRID_CLASSES:
            grid_class = GRID_CLASSES[request.vars.o]

        if request.vars.o == 'contributions' and request.vars.creator_id:
            grid_class = CreatorGrid

    return grid_class


def creator_contribute_button(row):
    """Return a creator 'contribute' button suitable for grid row."""
    # Only display if creator has a paypal address.
    if not row:
        return ''
    if not 'creator' in row or not row.creator.id:
        return ''
    db = current.app.db
    if not can_receive_contributions(db, row.creator):
        return ''
    return creator_contribute_link(
        db,
        row.creator.id,
        **dict(
            _class='btn btn-default contribute_button',
            _type='button'
        )
    )


def download_link(row):
    """Return a 'Download' link suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''
    return A(
        'Download',
        _href=URL(
            c='books',
            f='download',
            args=book_id,
            extension=False
        ),
        _class='btn btn-default fixme',
        _type='button',
    )


def link_book_id(row):
    """Return id of book associated with row."""
    try:
        book_id = row['book']['id']
    except (KeyError, TypeError):
        book_id = 0
    return book_id


def read_link(row):
    """Return an 'Read' link suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''
    db = current.app.db
    return book_read_link(
        db,
        book_id,
        **dict(_class='btn btn-default', _type='button')
    )


def torrent_link(row):
    """Return a torrent link suitable for grid row."""
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id:
        return ''
    return creator_torrent_link(
        row.creator.id,
        _class='fixme',
    )
