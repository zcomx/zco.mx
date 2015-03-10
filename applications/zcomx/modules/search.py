#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Search classes and functions.
"""
import collections
import logging
from BeautifulSoup import BeautifulSoup
from gluon import *
from gluon.tools import prettydate
from gluon.validators import urlify
from applications.zcomx.modules.books import \
    contribute_link as book_contribute_link, \
    cover_image, \
    download_link as book_download_link, \
    formatted_name, \
    read_link as book_read_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    can_receive_contributions, \
    contribute_link as creator_contribute_link, \
    torrent_link as creator_torrent_link, \
    url as creator_url
from applications.zcomx.modules.images import CreatorImgTag
from applications.zcomx.modules.stickon.sqlhtml import LocalSQLFORM
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row, \
    replace_in_elements

LOG = logging.getLogger('app')


class Grid(object):
    """Class representing a grid for search results."""

    # The key element is the one displayed in bottom right corner of tile.
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

    _not_found_msg = None

    viewbys = {
        # name: items_per_page
        'list': {
            'items_per_page': 20,
            'icon': 'th-list',
        },
        'tile': {
            'items_per_page': 12,
            'icon': 'th-large',
        },
    }

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile'):
        """Constructor

        Args:
            form_grid_args: dict, parameters passed to form grid. Must be
                valid parameters fo SQLFORM.grid
            queries: list of gluon.dal.Expression, additional expressions used
                for filtering records in results.
            default_viewby: string, one of 'list', 'tile'. The default view to
                use.
        """
        self.form_grid_args = form_grid_args
        self.queries = queries
        self.default_viewby = default_viewby \
            if default_viewby in self.viewbys else 'tile'
        self.db = current.app.db
        self.request = current.request
        self.form_grid = None
        self._paginate = None
        self.viewby = self.request.vars.view \
            if self.request.vars.view \
            and self.request.vars.view in self.viewbys \
            else self.default_viewby
        self._set()

    def _set(self):
        """Set the grid. """
        db = self.db
        request = self.request
        queries = list(self.queries) if self.queries else []
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

        db.book_page.created_on.represent = lambda v, row: \
            str(prettydate(v, T=current.T)) if v is not None else 'n/a'

        fields = [
            db.book.id,
            db.book.name,
            db.book.book_type_id,
            db.book.number,
            db.book.of_number,
            db.book_page.created_on,
            db.book.publication_year,
            db.book.release_date,
            db.book.views,
            db.book.downloads,
            db.book.contributions_remaining,
            db.book.created_on,
            db.creator.id,
            db.auth_user.name,
            db.creator.paypal_email,
            db.creator.contributions_remaining,
            db.creator.torrent,
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
            'book.views': 'Views',
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
            SPAN(
                TAG.i(_class='icon zc-arrow-up size-08'),
                _class='grid_sort_marker'
            ),
            SPAN(
                TAG.i(_class='icon zc-arrow-down size-08'),
                _class='grid_sort_marker'
            ),
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
            paginate=self.viewbys[self.viewby]['items_per_page'],
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
        LOG.debug('self: %s', self)
        LOG.debug('db._lastsql: %s', db._lastsql)
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
        return self._paginate if self._paginate \
            else self.viewbys[self.viewby]['items_per_page']

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

    def render(self):
        """Render the grid."""
        db = self.db
        paginator = None
        if self.viewby == 'tile':
            # extract the paginator from the grid
            soup = BeautifulSoup(str(self.form_grid))
            paginator = soup.find(
                'div',
                {'class': 'web2py_paginator grid_header '}
            )

        if self.viewby == 'list':
            grid_div = DIV(
                self.form_grid,
                _class='grid_section row'
            )
        else:
            divs = []
            tiles = []
            rows = self.rows()
            for row in rows:
                value = self.tile_value(row)
                tile_class = BookTile
                if self.request.vars:
                    if self.request.vars.o \
                            and self.request.vars.o == 'creators':
                        tile_class = CartoonistTile
                    elif self.request.vars.monies:
                        tile_class = MoniesBookTile
                tile = tile_class(db, value, row)
                tiles.append(tile.render())

            if rows:
                divs.append(DIV(
                    tiles,
                    _class='row tile_view'
                ))
                if paginator:
                    divs.append(DIV(
                        XML(paginator)
                    ))
            else:
                divs.append(DIV(current.T('No records found')))

            grid_div = DIV(divs, _class='grid_section')

        if self._not_found_msg is not None:
            replace_in_elements(
                grid_div,
                'No records found',
                current.T(self._not_found_msg),
                callback=lambda x: x.add_class('not_found_msg')
            )

        return grid_div

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

    def tabs(self):
        """Return a div of clickable tabs used to select the orderby."""
        lis = []
        orderbys = [
            x for x in GRID_CLASSES.keys()
            if (self.request.vars.o == 'search'
                and x == self.request.vars.o)
            or (self.request.vars.o != 'search' and x != 'search')
        ]

        orderby = self.request.vars.o \
            if self.request.vars.o in orderbys else orderbys[0]
        for o in orderbys:
            active = 'active' if o == orderby else ''
            orderby_vars = dict(self.request.vars)
            orderby_vars.pop('contribute', None)    # Del contribute modal trig
            if 'page' in orderby_vars:
                # Each tab should reset to page 1.
                del orderby_vars['page']
            orderby_vars['o'] = o
            label = GRID_CLASSES[o].label('tab_label')
            lis.append(LI(
                A(
                    label,
                    _href=URL(r=self.request, vars=orderby_vars),
                ),
                _class='nav-tab {a}'.format(a=active),
            ))

        return UL(
            lis,
            _class='nav nav-tabs',
        )

    def tile_value(self, row):
        """Return the value of the key element in tile view."""
        db = self.db
        fieldname = self._attributes['field']
        tablename = self._attributes['table']
        value = row[tablename][fieldname]
        if db[tablename][fieldname].represent:
            value = db[tablename][fieldname].represent(value, row)
        return value or ''

    def viewby_buttons(self):
        """Return a div of buttons viewby options."""
        buttons = []
        for v in sorted(self.viewbys.keys()):
            args = list(self.request.args)
            viewby_vars = dict(self.request.vars)
            # Properly route the creator if applicable.
            # ?creator=First_Last => /First_Last
            creator = viewby_vars.pop('creator', None)
            if creator:
                args.append(creator)
            viewby_vars.pop('contribute', None)     # Del contribute modal trig
            viewby_vars['view'] = v
            disabled = 'disabled' if v == self.viewby else 'active'
            buttons.append(A(
                SPAN(
                    _class='glyphicon glyphicon-{icon}'.format(
                        icon=self.viewbys[v]['icon']
                    ),
                ),
                _href=URL(r=self.request, args=args, vars=viewby_vars),
                _class='btn btn-default btn-lg {d}'.format(d=disabled),
            ))
        return DIV(buttons, _class='btn-group')

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

    _not_found_msg = 'No cartoonists found'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='list'):
        """Constructor"""
        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

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
            # db.creator.contributions_remaining,
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

    _not_found_msg = 'No books found'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile'):
        """Constructor"""
        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

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


class CreatorMoniesGrid(Grid):
    """Class representing a grid for search results: creator_monies"""

    _attributes = dict(Grid._attributes)
    _attributes.update({
        'table': 'book',
        'field': 'name',
        'order_dir': 'ASC',
    })

    _not_found_msg = 'No books found'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile',
            creator_entity=None):
        """Constructor"""

        db = current.app.db
        self.creator = None
        if creator_entity is not None:
            self.creator = entity_to_row(db.creator, creator_entity)
            if not self.creator:
                raise NotFoundError('Creator not found: {e}'.format(
                    e=creator_entity))

        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        queries = []
        if self.creator:
            queries.append((db.book.creator_id == self.creator.id))
        return queries


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

    _not_found_msg = 'No ongoing series'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile'):
        """Constructor"""
        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

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
            db.book.views,
            # db.book.contributions_remaining,
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

    _not_found_msg = 'No books released'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile'):
        """Constructor"""
        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

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
            # db.book.contributions_remaining,
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

    _not_found_msg = 'No matches found'

    def __init__(
            self,
            form_grid_args=None,
            queries=None,
            default_viewby='tile'):
        """Constructor"""
        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        request = self.request
        queries = []
        if request.vars.kw:
            kw = urlify(request.vars.kw)
            queries.append(
                (db.book.urlify_name.contains(kw)) |
                (db.creator.urlify_name.contains(kw))
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
            db.book.views,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


GRID_CLASSES = collections.OrderedDict()
GRID_CLASSES['ongoing'] = OngoingGrid
GRID_CLASSES['releases'] = ReleasesGrid
# GRID_CLASSES['contributions'] = ContributionsGrid
GRID_CLASSES['creators'] = CartoonistsGrid
GRID_CLASSES['search'] = SearchGrid


class Tile(object):
    """Class representing a Tile"""

    class_name = 'tile'

    def __init__(self, db, value, row):
        """Constructor

        Args:
            db: gluon.dal.Dal instance
            value: string, value to display in footer right side.
            row: gluon.dal.Row representing row of grid
        """
        self.db = db
        self.value = value
        self.row = row

    def contribute_link(self):
        """Return the tile contribute link."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return

    def download_link(self):
        """Return the tile download link."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return

    def footer(self):
        """Return a div for the tile footer."""

        orderby_field_value = DIV(
            self.value,
            _class='orderby_field_value'
        )

        return DIV(
            self.footer_links(),
            orderby_field_value,
            _class='col-sm-12'
        )

    def footer_links(self):
        """Return a div for the tile footer links."""
        db = self.db
        row = self.row

        breadcrumb_lis = []
        append_li = lambda x: x and breadcrumb_lis.append(LI(x))

        if can_receive_contributions(db, row.creator):
            append_li(self.contribute_link())
        append_li(self.download_link())

        return UL(
            breadcrumb_lis,
            _class='breadcrumb pipe_delimiter'
        )

    def image(self):
        """Return a div for the tile image."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return

    def render(self):
        """Render the tile."""
        divs = []

        append_div = lambda x: x and divs.append(DIV(x, _class='row'))

        append_div(self.title())
        append_div(self.subtitle())
        append_div(self.image())
        append_div(self.footer())

        unique_class = '_'.join([self.class_name, 'item'])

        return DIV(
            *divs,
            _class='item_container {u}'.format(u=unique_class)
        )

    def subtitle(self):
        """Return div for the tile subtitle."""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return

    def title(self):
        """Return a div for the tile title"""
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return


class BookTile(Tile):
    """Class representing a Tile for a book"""

    class_name = 'book_tile'

    def __init__(self, db, value, row):
        """Constructor

        Args:
            db: gluon.dal.Dal instance
            value: string, value to display in footer right side.
            row: gluon.dal.Row representing row of grid
        """
        Tile.__init__(self, db, value, row)

    def contribute_link(self):
        """Return the tile contribute link."""
        db = self.db
        row = self.row
        return book_contribute_link(
            db,
            row.book.id,
            components=['contribute'],
            **dict(_class='contribute_button no_rclick_menu')
        )

    def download_link(self):
        """Return the tile download link."""
        db = self.db
        row = self.row
        return book_download_link(
            db,
            row.book.id,
            components=['download'],
            **dict(_class='download_button no_rclick_menu')
        )

    def image(self):
        """Return a div for the tile image."""
        db = self.db
        row = self.row
        return DIV(
            book_read_link(
                db,
                row.book.id,
                components=[cover_image(db, row.book, size='web')],
                **dict(_class='book_page_image', _title='')
            ),
            _class='col-sm-12 image_container',
        )

    def subtitle(self):
        """Return div for the tile subtitle."""
        row = self.row
        creator_href = creator_url(row.creator.id, extension=False)

        return DIV(
            A(
                row.auth_user.name,
                _href=creator_href,
                _title=row.auth_user.name,
            ),
            _class='col-sm-12 creator',
        )

    def title(self):
        """Return a div for the tile title"""
        db = self.db
        row = self.row
        book_name = formatted_name(
            db,
            row.book,
            include_publication_year=(row.book.release_date != None)
        )
        book_link = A(
            book_name,
            _href=book_url(row.book.id, extension=False),
            _title=book_name,
        )
        return DIV(
            book_link,
            _class='col-sm-12 name',
        )


class CartoonistTile(Tile):
    """Class representing a Tile for a cartoonist"""

    class_name = 'cartoonist_tile'

    def __init__(self, db, value, row):
        """Constructor

        Args:
            db: gluon.dal.Dal instance
            value: string, value to display in footer right side.
            row: gluon.dal.Row representing row of grid
        """
        Tile.__init__(self, db, value, row)
        self.creator_href = creator_url(self.row.creator.id, extension=False)

    def contribute_link(self):
        """Return the tile contribute link."""
        db = self.db
        row = self.row
        return creator_contribute_link(
            db,
            row.creator,
            components=['contribute'],
            **dict(_class='contribute_button no_rclick_menu')
        )

    def download_link(self):
        """Return the tile download link."""
        return A(
            'download',
            _href=self.creator_href
        )

    def footer(self):
        """Return a div for the tile footer."""
        # When crowdfunding feature is restored, this method isn't necessary,
        # just use the base class method. See mod 12727.

        orderby_field_value = DIV(
            '',
            _class='orderby_field_value'
        )

        return DIV(
            self.footer_links(),
            orderby_field_value,
            _class='col-sm-12'
        )

    def image(self):
        """Return a div for the tile image."""
        db = self.db
        row = self.row
        creator = entity_to_row(db.creator, row.creator.id)
        creator_image = A(
            CreatorImgTag(
                creator.image,
                size='tbn',
                attributes={'_alt': row.auth_user.name}
            )(),
            _href=self.creator_href,
            _title=''
        )
        return DIV(
            creator_image,
            _class='col-sm-12 image_container',
        )

    def title(self):
        """Return a div for the tile title"""
        row = self.row
        creator_link = A(
            row.auth_user.name,
            _href=self.creator_href,
            _title=row.auth_user.name,
        )
        return DIV(
            creator_link,
            _class='col-sm-12 name',
        )


class MoniesBookTile(BookTile):
    """Class representing a Tile for a book in Monies format"""

    class_name = 'monies_book_tile'

    def __init__(self, db, value, row):
        """Constructor

        Args:
            db: gluon.dal.Dal instance
            value: string, value to display in footer right side.
            row: gluon.dal.Row representing row of grid
        """
        BookTile.__init__(self, db, value, row)

    def contribute_link(self):
        """Return the tile contribute link."""
        return

    def download_link(self):
        """Return the tile download link."""
        return

    def footer(self):
        """Return a div for the tile footer."""

        db = self.db
        row = self.row
        book_name = formatted_name(
            db,
            row.book,
            include_publication_year=(row.book.release_date != None)
        )

        if can_receive_contributions(db, row.creator):
            inner = book_contribute_link(
                db,
                row.book.id,
                components=[book_name],
                **dict(_class='contribute_button no_rclick_menu')
            )
        else:
            inner = book_name

        return DIV(
            inner,
            _class='col-sm-12 name',
        )

    def image(self):
        """Return a div for the tile image."""
        db = self.db
        row = self.row
        img = cover_image(db, row.book, size='web')
        if can_receive_contributions(db, row.creator):
            inner = book_contribute_link(
                db,
                row.book.id,
                components=[img],
                **dict(_class='contribute_button no_rclick_menu')
            ),
        else:
            inner = img

        return DIV(
            inner,
            _class='col-sm-12 image_container',
        )

    def subtitle(self):
        """Return div for the tile subtitle."""
        return

    def title(self):
        """Return a div for the tile title"""
        return


def book_contribute_button(row):
    """Return a 'contribute' button suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''

    # Only display if creator has a paypal address.
    if 'creator' not in row or not row.creator.paypal_email:
        return ''

    db = current.app.db
    return book_contribute_link(
        db,
        book_id,
        **dict(_class='btn btn-default contribute_button no_rclick_menu')
    )


def classified(request):
    """Return the appropriate Grid class for request.

    Args:
        request: gluon.global.Request instance

    Returns:
        Grid class or subclass
    """
    grid_class = OngoingGrid
    LOG.debug('request.vars.o: %s', request.vars.o)
    if request.vars.o:
        if request.vars.o in GRID_CLASSES:
            grid_class = GRID_CLASSES[request.vars.o]
    return grid_class


def creator_contribute_button(row):
    """Return a creator 'contribute' button suitable for grid row."""
    # Only display if creator has a paypal address.
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id:
        return ''
    db = current.app.db
    if not can_receive_contributions(db, row.creator):
        return ''
    return creator_contribute_link(
        db,
        row.creator.id,
        **dict(_class='btn btn-default contribute_button no_rclick_menu')
    )


def download_link(row):
    """Return a 'Download' link suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''

    db = current.app.db
    return book_download_link(
        db,
        book_id,
        **dict(_class='btn btn-default download_button no_rclick_menu')
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
        **dict(_class='btn btn-default')
    )


def torrent_link(row):
    """Return a torrent link suitable for grid row."""
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id:
        return ''
    return creator_torrent_link(row.creator.id)
