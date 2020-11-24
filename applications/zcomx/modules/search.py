#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Search classes and functions.
"""
import string
from bs4 import BeautifulSoup
from gluon import *
from gluon.tools import prettydate
from pydal.validators import urlify
from applications.zcomx.modules.books import \
    Book, \
    contribute_link as book_contribute_link, \
    cover_image, \
    download_link as book_download_link, \
    follow_link as book_follow_link, \
    formatted_name, \
    is_followable, \
    read_link as book_read_link, \
    show_download_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    Creator, \
    can_receive_contributions, \
    contribute_link as creator_contribute_link, \
    follow_link as creator_follow_link, \
    torrent_link as creator_torrent_link, \
    torrent_url as creator_torrent_url, \
    url as creator_url
from applications.zcomx.modules.images import CreatorImgTag
from applications.zcomx.modules.stickon.sqlhtml import make_grid_class
from applications.zcomx.modules.utils import \
    ClassFactory, \
    replace_in_elements
from applications.zcomx.modules.zco import BOOK_STATUS_ACTIVE
from functools import reduce

LOG = current.app.logger


class AlphaPaginator(object):
    """Class representing a AlphaPaginator"""

    def __init__(self, request):
        """Initializer

        Args:
            request: Request instance represent the page the paginator is
                displayed on.
        """
        self.request = request

    def get_url(self, letter):
        """Get the url for the paginator element for the given letter.

        Args:
            letter: str, a letter of the alphabet.

        Returns:
            URL() instance
        """
        work_vars = self.request.vars
        work_vars['alpha'] = letter.lower()
        return URL(
            r=self.request,
            args=self.request.args,
            vars=work_vars
        )

    def render(self, container_additional_classes=None):
        """Render the alpha paginator.

        Args:
            container_additional_classes: list, additional classes to add to
                container div.
        """
        url_divs = []

        def spacer_div(fraction):
            # <div class="alpha_paginator_spacer quarter"></div>
            return DIV(
                _class='alpha_paginator_spacer {f}'.format(f=fraction)
            )

        spacers = {
            # letter: [ list of spacers that follow it ]
            'F': ['quarter'],
            'I': ['third'],
            'L': ['quarter'],
            'M': ['half'],
            'R': ['third', 'quarter'],
            'X': ['quarter'],
        }

        current_letter = None
        if self.request.vars and self.request.vars.alpha:
            current_letter = self.request.vars.alpha.upper()

        for letter in string.ascii_uppercase:
            url = self.get_url(letter)
            a_classes = ['alpha_paginator_link']
            if current_letter and current_letter == letter:
                a_classes.append('current')

            div = DIV(
                A(
                    letter.upper(),
                    _href=url,
                ),
                _class=' '.join(a_classes),
            )
            url_divs.append(div)
            if letter in spacers:
                for fraction in spacers[letter]:
                    url_divs.append(spacer_div(fraction))

        container_classes = ['web2py_paginator', 'alpha_paginator_container']
        if container_additional_classes:
            container_classes.extend(container_additional_classes)

        return DIV(
            url_divs,
            _class=' '.join(container_classes)
        )


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

    _buttons = []
    _include_alpha_paginator = False    # If True include alpha paginator
    _not_found_msg = None

    class_factory = ClassFactory('class_factory_id')
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

        self.has_numeric_paginator = False

        # Search engines are making requests with invalid 'order' values.
        # Eg order=123
        # Scrub them.
        if self.request.vars.order and '.' not in self.request.vars.order:
            self.request.vars.order = None

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
        queries.append((db.book.status == BOOK_STATUS_ACTIVE))
        queries.extend(self.filters())

        db.auth_user.name.represent = lambda v, row: A(
            v,
            _href=creator_url(row.creator, extension=False)
        )

        def book_name_rep(value, row):
            """db.book.name.represent."""
            # unused-argument (W0613): *Unused argument %%r*
            # pylint: disable=W0613
            book = Book.from_id(row.book.id)
            return A(
                formatted_name(book, include_publication_year=False),
                _href=book_url(book, extension=False)
            )
        db.book.name.represent = book_name_rep

        db.book.page_added_on.represent = lambda v, row: \
            str(prettydate(v, T=current.T)) if v is not None else 'n/a'

        fields = [
            db.book.id,
            db.book.name,
            db.book.book_type_id,
            db.book.number,
            db.book.of_number,
            db.book.publication_year,
            db.book.release_date,
            db.book.views,
            db.book.downloads,
            db.book.contributions_remaining,
            db.book.name_for_url,
            db.book.page_added_on,
            db.book.created_on,
            db.creator.id,
            db.auth_user.name,
            db.creator.paypal_email,
            db.creator.contributions_remaining,
            db.creator.torrent,
            db.creator.name_for_url,
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
            'book.released_date': 'Completed',
            'book.views': 'Views',
            'book.contributions_remaining': 'Remaining',
            'book.page_added_on': 'Added',
            'creator.contributions_remaining': 'Remaining',
        }

        links = []

        def add_link(body, header=''):
            """Add link to links list."""
            links.append({'header': header, 'body': body})

        if 'read' in self._buttons:
            add_link(read_link)

        if 'creator_torrent' in self._buttons:
            add_link(link_for_creator_torrent)

        if 'creator_contribute' in self._buttons:
            add_link(creator_contribute_button)

        if 'download' in self._buttons:
            add_link(download_link)

        if 'creator_follow' in self._buttons:
            add_link(link_for_creator_follow)

        if 'book_follow' in self._buttons:
            add_link(follow_link)

        if 'book_contribute' in self._buttons:
            add_link(book_contribute_button)

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
            field_id=db[self._attributes['table']].id,
            headers=headers,
            orderby=self.orderby(),
            groupby=self.groupby(),
            left=[
                db.creator.on(db.book.creator_id == db.creator.id),
                db.auth_user.on(
                    db.creator.auth_user_id == db.auth_user.id
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

        grid_class = make_grid_class(
            export='none', search='none', ui='glyphicon')
        self.form_grid = grid_class.grid(query, **kwargs)
        self._paginate = kwargs['paginate']
        # Remove 'None' record count if applicable.
        for count, div in enumerate(self.form_grid[0]):
            if str(div) == '<div class="web2py_counter">None</div>':
                del self.form_grid[0][count]

    def alpha_paginator(self):
        return AlphaPaginator(self.request)

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
        fields.append(db.book.number)
        fields.append(db.book.id)                # For consistent results
        if self._attributes['order_dir'] == 'DESC':
            fields = [~x for x in fields]
        return fields

    def render(self):
        """Render the grid."""
        db = self.db

        # extract the paginator from the grid
        soup = BeautifulSoup(str(self.form_grid), 'html.parser')
        paginator = soup.find(
            'div',
            {'class': 'web2py_paginator grid_header '}
        )

        if paginator:
            self.has_numeric_paginator = True

        if self.viewby == 'list':
            grid_div = DIV(
                self.form_grid,
                _class='grid_section row'
            )
        else:
            divs = []
            tiles = []
            rows = self.rows()
            if rows:
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

        orderbys = ['search'] \
            if self.request.vars.o == 'search' \
            else ['completed', 'ongoing', 'creators']

        orderby = self.request.vars.o \
            if self.request.vars.o in orderbys else orderbys[0]
        for o in orderbys:
            active = 'active' if o == orderby else ''
            request_vars = dict(self.request.vars)
            request_vars.pop('o', None)    # The url takes care of this
            request_vars.pop('contribute', None)    # Del contribute modal trig
            if 'page' in request_vars:
                # Each tab should reset to page 1.
                del request_vars['page']
            if self._include_alpha_paginator:
                request_vars['alpha'] = 'a'
            label = self.class_factory(o).label('tab_label')
            lis.append(LI(
                A(
                    label,
                    _href=URL(c='z', f=label, vars=request_vars),
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
            viewby_vars.pop('o', None)     # Urls contain this
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
        """Return list of visible fields.

        Returns:
            list of gluon.dal.Field instances
        """
        # no-self-use (R0201): *Method could be a function*
        # pylint: disable=R0201
        return []


@Grid.class_factory.register
class CartoonistsGrid(Grid):
    """Class representing a grid for search results: cartoonist"""
    class_factory_id = 'creators'

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
        'creator_follow',
        'creator_torrent',
    ]

    _include_alpha_paginator = True
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

    def filters(self):
        """Define query filters.

        Returns:
            list of gluon.dal.Expression instances
        """
        db = self.db
        request = self.request
        queries = []
        if request.vars.alpha:
            queries.append(
                (db.creator.name_for_search.startswith(request.vars.alpha))
            )
        return queries

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
        """Return list of visible fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.auth_user.name,
            # db.creator.contributions_remaining,
        ]


@Grid.class_factory.register
class CompletedGrid(Grid):
    """Class representing a grid for search results: completed"""
    class_factory_id = 'completed'

    _attributes = {
        'table': 'book',
        'field': 'release_date',
        'label': 'release date',
        'tab_label': 'completed',
        'header_label': 'completed',
        'class': 'orderby_completed',
        'order_dir': 'DESC',
    }

    _buttons = [
        'book_contribute',
        'download',
        'read',
    ]

    _not_found_msg = 'No completed books'

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
        """Return list of visible fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.publication_year,
            db.book.release_date,
            db.book.downloads,
            db.book.views,
            # db.book.contributions_remaining,
            db.auth_user.name,
        ]


@Grid.class_factory.register
class CreatorMoniesGrid(Grid):
    """Class representing a grid for search results: creator_monies"""
    class_factory_id = 'creator_monies'

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
            creator=None):
        """Constructor"""
        self.creator = creator

        Grid.__init__(
            self,
            form_grid_args=form_grid_args,
            queries=queries,
            default_viewby=default_viewby
        )
        self.viewby = 'tile'        # This grid is tile only.

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


@Grid.class_factory.register
class OngoingGrid(Grid):
    """Class representing a grid for search results: ongoing"""
    class_factory_id = 'ongoing'

    _attributes = {
        'table': 'book',
        'field': 'page_added_on',
        'label': 'page added',
        'tab_label': 'ongoing',
        'header_label': 'added',
        'class': 'orderby_ongoing',
        'order_dir': 'DESC',
    }

    _buttons = [
        'book_contribute',
        'book_follow',
        'read',
    ]

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
        """Return list of visible fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.page_added_on,
            db.book.views,
            # db.book.contributions_remaining,
            db.auth_user.name,
        ]


@Grid.class_factory.register
class SearchGrid(Grid):
    """Class representing a grid for search results."""
    class_factory_id = 'search'

    _attributes = {
        'table': 'book',
        'field': 'page_added_on',
        'label': 'page added',
        'tab_label': 'search',
        'header_label': 'added',
        'order_dir': 'DESC',
    }

    _buttons = [
        'book_contribute',
        'download',
        'book_follow',
        'read',
    ]

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
                (db.book.name_for_search.contains(kw)) |
                (db.creator.name_for_search.contains(kw))
            )
        return queries

    def visible_fields(self):
        """Return list of visible fields.

        Returns:
            list of gluon.dal.Field instances
        """
        db = self.db
        return [
            db.book.name,
            db.book.page_added_on,
            db.book.views,
            db.book.contributions_remaining,
            db.auth_user.name,
        ]


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

    def follow_link(self):
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
        row = self.row

        breadcrumb_lis = []
        append_li = lambda x: x and breadcrumb_lis.append(LI(x))

        if can_receive_contributions(row.creator):
            append_li(self.contribute_link())

        dl_link = self.download_link()
        if dl_link and str(dl_link) != str(SPAN('')):
            append_li(dl_link)

        follow = self.follow_link()
        if follow and str(follow) != str(SPAN('')):
            append_li(follow)

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
        self.book = Book.from_id(self.row.book.id)

    def contribute_link(self):
        """Return the tile contribute link."""
        return book_contribute_link(
            self.book,
            components=['contribute'],
            **dict(_class='contribute_button no_rclick_menu')
        )

    def download_link(self):
        """Return the tile download link."""
        if not show_download_link(self.book):
            return SPAN('')

        return book_download_link(
            self.book,
            components=['download'],
            **dict(_class='download_button no_rclick_menu')
        )

    def follow_link(self):
        """Return the tile download link."""
        row = self.row

        book = Book.from_id(row.book.id)
        if not is_followable(book):
            return SPAN('')

        creator = Creator.from_id(row.creator.id)
        return creator_follow_link(
            creator,
            components=['follow'],
            **dict(_class='rss_button no_rclick_menu')
        )

    def image(self):
        """Return a div for the tile image."""
        return DIV(
            DIV(
                book_read_link(
                    self.book,
                    components=[cover_image(self.book, size='web')],
                    **dict(
                        _class='book_page_image zco_book_reader',
                        _title=''
                    )
                ),
                _class='image_container_wrapper',
            ),
            _class='col-sm-12 image_container',
        )

    def subtitle(self):
        """Return div for the tile subtitle."""
        row = self.row
        creator = Creator.from_id(row.creator.id)
        creator_href = creator_url(creator, extension=False)

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
        row = self.row
        book_name = formatted_name(
            self.book,
            include_publication_year=(row.book.release_date != None)
        )
        book_link = A(
            book_name,
            _href=book_url(self.book, extension=False),
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
        self.creator = Creator.from_id(self.row.creator.id)
        self.creator_href = creator_url(self.creator, extension=False)

    def contribute_link(self):
        """Return the tile contribute link."""
        return creator_contribute_link(
            self.creator,
            components=['contribute'],
            **dict(_class='contribute_button no_rclick_menu')
        )

    def download_link(self):
        """Return the tile download link."""
        empty = SPAN('')
        row = self.row
        if not row.creator or not row.creator.id or not row.creator.torrent:
            return empty
        url = creator_torrent_url(self.creator)
        return A(
            'download',
            _href=url
        )

    def follow_link(self):
        """Return the tile follow link."""
        row = self.row
        return creator_follow_link(
            row.creator,
            components=['follow'],
            **dict(_class='rss_button no_rclick_menu')
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
        row = self.row
        creator_image = A(
            CreatorImgTag(
                self.creator.image,
                size='web',
                attributes={'_alt': row.auth_user.name}
            )(),
            _href=self.creator_href,
            _title=''
        )
        return DIV(
            DIV(
                creator_image,
                _class='image_container_wrapper',
            ),
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

    def follow_link(self):
        """Return the tile download link."""
        return

    def footer(self):
        """Return a div for the tile footer."""
        row = self.row
        book_name = formatted_name(
            self.book,
            include_publication_year=(row.book.release_date != None)
        )

        if can_receive_contributions(row.creator):
            inner = book_contribute_link(
                self.book,
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
        row = self.row
        img = cover_image(self.book, size='web')
        if can_receive_contributions(row.creator):
            inner = book_contribute_link(
                self.book,
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

    book = Book.from_id(book_id)
    return book_contribute_link(
        book,
        **dict(_class='btn btn-default contribute_button no_rclick_menu')
    )


def creator_contribute_button(row):
    """Return a creator 'contribute' button suitable for grid row."""
    # Only display if creator has a paypal address.
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id:
        return ''
    creator = Creator.from_id(row.creator.id)
    if not can_receive_contributions(creator):
        return ''
    return creator_contribute_link(
        creator,
        **dict(_class='btn btn-default contribute_button no_rclick_menu')
    )


def download_link(row):
    """Return a 'Download' link suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''

    book = Book.from_id(book_id)
    if not show_download_link(book):
        return ''

    return book_download_link(
        book,
        **dict(_class='btn btn-default download_button no_rclick_menu')
    )


def follow_link(row):
    """Return a 'Follow' link suitable for grid row."""

    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''

    book = Book.from_id(row.book.id)
    if not is_followable(book):
        return ''

    return book_follow_link(
        book,
        **dict(_class='btn btn-default rss_button no_rclick_menu')
    )


def link_book_id(row):
    """Return id of book associated with row."""
    try:
        book_id = row['book']['id']
    except (KeyError, TypeError):
        book_id = 0
    return book_id


def link_for_creator_follow(row):
    """Return a 'Follow' link suitable for grid row."""
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id:
        return ''
    creator = Creator.from_id(row.creator.id)
    return creator_follow_link(
        creator,
        **dict(_class='btn btn-default rss_button no_rclick_menu')
    )


def link_for_creator_torrent(row):
    """Return a creator torrent link suitable for grid row."""
    if not row:
        return ''
    if 'creator' not in row or not row.creator.id or not row.creator.torrent:
        return ''
    creator = Creator.from_id(row.creator.id)
    return creator_torrent_link(creator)


def read_link(row):
    """Return an 'Read' link suitable for grid row."""
    if not row:
        return ''
    book_id = link_book_id(row)
    if not book_id:
        return ''
    book = Book.from_id(book_id)
    return book_read_link(
        book,
        **dict(_class='btn btn-default zco_book_reader')
    )
