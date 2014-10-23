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
    read_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    can_receive_contributions, \
    contribute_link as creator_contribute_link, \
    torrent_link as creator_torrent_link, \
    url as creator_url
from applications.zcomx.modules.stickon.sqlhtml import LocalSQLFORM


class Search(object):
    """Class representing a search grid"""

    order_fields = collections.OrderedDict()
    # Items are displayed on front page in order.
    order_fields['contributions'] = {
        'table': 'book',
        'field': 'contributions_remaining',
        'fmt': lambda x: '${v:0.0f}'.format(v=x),
        'label': 'remaining',
        'tab_label': 'contributions',
        'class': 'orderby_contributions',
        'order_dir': 'ASC',
    }
    order_fields['newest'] = {
        'table': 'book_page',
        'field': 'created_on',
        'fmt': lambda x: str(x.date()) if x is not None else 'n/a',
        'label': 'page added',
        'tab_label': 'newest pages',
        'header_label': 'added',
        'class': 'orderby_newest_pages',
        'order_dir': 'DESC',
    }
    order_fields['views'] = {
        'table': 'book',
        'field': 'views_year',
        'fmt': lambda x: '{v}'.format(v=x),
        'label': 'views',
        'class': 'orderby_views',
        'order_dir': 'DESC',
    }
    order_fields['creators'] = {
        'table': 'creator',
        'field': 'contributions_remaining',
        'fmt': lambda v: '${v:0,.2f}'.format(v=v),
        'label': 'remaining',
        'tab_label': 'cartoonists',
        'class': 'orderby_creators',
        'order_dir': 'ASC',
    }

    def __init__(self):
        """Constructor"""
        self.grid = None
        self.orderby_field = None
        self.paginate = 0

    @classmethod
    def label(cls, orderby_key, key):
        """Return a label for an order_field

        The first found of these is returned:
            order_field[key]
            order_field['label']
            orderby_key
        """
        if orderby_key not in cls.order_fields:
            return orderby_key
        keys = [key, 'label']
        for k in keys:
            if k in cls.order_fields[orderby_key]:
                return cls.order_fields[orderby_key][k]
        return orderby_key

    def set(self, db, request, grid_args=None):
        """Set the grid.

        Args:
            db: gluon.dal.DAL instance
            request: gluon.globals.Request instance.
            grid_args: dict of SQLFORM.grid arguments.
        """
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103
        orderby_key = request.vars.o \
            if request.vars.o and request.vars.o in self.order_fields.keys() \
            else 'contributions'
        orderby_field = self.order_fields[orderby_key]
        self.orderby_field = orderby_field
        orderby_table = orderby_field['table']
        orderby_fieldname = orderby_field['field']

        queries = []

        editable = False
        creator = None
        auth = current.app.auth
        if request.vars.rw:
            creator = db(db.creator.auth_user_id == auth.user_id).select(
                db.creator.ALL).first()
            if creator:
                editable = True

        if not creator and request.vars.creator_id:
            query = (db.creator.id == request.vars.creator_id)
            creator = db(query).select(db.creator.ALL).first()

        if creator:
            queries.append((db.book.creator_id == creator.id))

        if not editable:
            queries.append((db.book.status == True))

        if request.vars.released == '0':
            queries.append((db.book.release_date == None))
        if request.vars.released == '1':
            queries.append((db.book.release_date != None))

        if request.vars.kw:
            queries.append(
                (db.book.name.contains(request.vars.kw)) |
                (db.auth_user.name.contains(request.vars.kw))
            )

        if orderby_key == 'contributions' and not creator:
            queries.append(db.book.contributions_remaining > 0)
            queries.append(db.creator.paypal_email != '')

        orderby = [db[orderby_field['table']][orderby_fieldname]]
        if orderby_field['order_dir'] == 'DESC':
            orderby[0] = ~orderby[0]
        orderby.append(db.book.number)
        orderby.append(db.book.id)                # For consistent results

        groupby = db.creator.id if orderby_key == 'creators' else db.book.id

        def set_field(field, visible=True):
            """Set the status of a field."""
            field.readable = visible
            field.writable = visible

        hide = lambda f: set_field(f, visible=False)
        show = lambda f: set_field(f, visible=True)

        hide(db.book.id)
        db.book.name.represent = lambda v, row: A(
            formatted_name(
                db,
                row.book,
                include_publication_year=(row.book.release_date != None)
            ),
            _href=book_url(row.book.id, extension=False)
        )
        if orderby_key == 'creators':
            hide(db.book.name)
        hide(db.book.book_type_id)
        hide(db.book.number)
        hide(db.book.of_number)
        if request.vars.released == '0' or orderby_key == 'creators':
            # Ongoing books won't be published.
            hide(db.book.publication_year)
        hide(db.book.release_date)
        hide(db.creator.id)
        if request.vars.view != 'list' or not creator:
            show(db.auth_user.name)
        db.auth_user.name.represent = lambda v, row: A(
            v,
            _href=creator_url(row.creator.id, extension=False)
        )
        hide(db.creator.paypal_email)
        if orderby_key == 'newest':
            db.book_page.created_on.represent = lambda v, row: str(v.date()) \
                if v is not None else 'n/a'

        for k, v in self.order_fields.items():
            if orderby_key == k:
                show(db[v['table']][v['field']])
            else:
                hide(db[v['table']][v['field']])

        if request.vars.creator_id:
            hide(db.auth_user.name)

        db[orderby_table][orderby_fieldname].represent = \
            lambda v, row: orderby_field['fmt'](v)

        fields = [
            db.book.id,
            db.book.name,
            db.book.book_type_id,
            db.book.number,
            db.book.of_number,
            db.book.publication_year,
            db.book.release_date,
            db.book.contributions_remaining,
            db.book.views_year,
            db.book.created_on,
            db.creator.id,
            db.auth_user.name,
            db.creator.paypal_email,
            db.creator.contributions_remaining,
            db.book_page.created_on,
        ]

        headers = {
            'book.name': 'Title',
            'auth_user.name': 'Cartoonist',
        }
        for k, v in self.order_fields.items():
            key = '{t}.{f}'.format(t=v['table'], f=v['field'])
            headers[key] = self.label(k, 'header_label').title()

        def link_book_id(row):
            """Return id of book associated with row."""
            book_id = 0
            if 'book' in row:
                # grid
                book_id = row.book.id
            elif 'id' in row:
                # editing
                book_id = row.id
            return book_id

        def creator_contribute_button(row):
            """Return a creator 'contribute' button suitable for grid row."""
            # Only display if creator has a paypal address.
            if not 'creator' in row or not row.creator.id:
                return ''
            if not can_receive_contributions(db, row.creator):
                return ''
            return creator_contribute_link(
                db,
                row.creator.id,
                **dict(_class='btn btn-default', _type='button')
            )

        def book_contribute_button(row):
            """Return a 'contribute' button suitable for grid row."""
            book_id = link_book_id(row)
            if not book_id:
                return ''

            # Only display if creator has a paypal address.
            if not 'creator' in row or not row.creator.paypal_email:
                return ''

            return book_contribute_link(
                db,
                book_id,
                **dict(_class='btn btn-default', _type='button')
            )

        def download_link(row):
            """Return a 'Download' link suitable for grid row."""
            book_id = link_book_id(row)
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

        def edit_link(row):
            """Return an 'Edit' link suitable for grid row."""
            book_id = link_book_id(row)
            if not book_id:
                return ''

            return A(
                SPAN(_class="glyphicon glyphicon-pencil"),
                'Edit',
                _href=URL(
                    c='login',
                    f='book_edit',
                    args=book_id,
                    anchor='book_edit',
                    extension=False
                ),
                _class='btn btn-default',
                _type='button',
            )

        def read_link_func(row):
            """Return an 'Read' link suitable for grid row."""
            book_id = link_book_id(row)
            if not book_id:
                return ''
            return read_link(
                db,
                book_id,
                **dict(_class='btn btn-default', _type='button')
            )

        def release_link(row):
            """Return an 'Release' link suitable for grid row."""
            book_id = link_book_id(row)
            if not book_id:
                return ''

            return A(
                'Release',
                _href=URL(
                    c='login',
                    f='book_release',
                    args=book_id,
                    extension=False
                ),
                _class='btn btn-default',
                _type='button',
            )

        def torrent_link(row):
            """Return a torrent link suitable for grid row."""
            if 'creator' not in row or not row.creator.id:
                return ''
            return creator_torrent_link(
                row.creator.id,
                _class='fixme',
            )

        links = []

        def add_link(body, header=''):
            """Add link to links list."""
            links.append({'header': header, 'body': body})

        if orderby_key != 'creators':
            add_link(read_link_func)

        if editable:
            if request.vars.released == '0':
                add_link(release_link)
            add_link(edit_link)
        else:
            if orderby_key == 'creators':
                add_link(torrent_link)
                add_link(creator_contribute_button)
            else:
                add_link(download_link)
                add_link(book_contribute_button)

        oncreate = None
        if editable and creator:
            def update_book_creator(form):
                """Update creator_id field of book record."""
                db(db.book.id == form.vars.id).update(creator_id=creator.id)
                db.commit()
            oncreate = update_book_creator

        def ondelete(unused_table, record_id):
            """Callback for ondelete."""
            # Delete all records associated with the book.
            for t in ['book_page', 'book_view', 'contribution', 'rating']:
                db(db[t].book_id == record_id).delete()
            db.commit()
            # Delete all links associated with the book.
            query = (db.book_to_link.book_id == record_id)
            for row in db(query).select(db.book_to_link.link_id):
                db(db.link.id == row['link_id']).delete()
            db(db.book_to_link.book_id == record_id).delete()
            db.commit()

        page2 = db.book_page.with_alias('page2')

        sorter_icons = (
            SPAN(XML('&#x25B2;'), _class='grid_sort_marker'),
            SPAN(XML('&#x25BC;'), _class='grid_sort_marker')
        )

        if not queries:
            queries.append(db.book)
        query = reduce(lambda x, y: x & y, queries) if queries else None

        grid_class = 'web2py_grid grid_view_{v} grid_key_{o}'.format(
            v=request.vars.view or 'tile', o=orderby_key)

        kwargs = dict(
            fields=fields,
            headers=headers,
            orderby=orderby,
            groupby=groupby,
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
            paginate=10,
            details=False,
            editable=False,
            deletable=editable,
            create=False,
            csv=False,
            searchable=False,
            maxtextlengths={
                'book.name': 50,
                'auth_user.name': 50,
            },
            links=links,
            oncreate=oncreate,
            ondelete=ondelete,
            sorter_icons=sorter_icons,
            editargs={'deletable': False},
            _class=grid_class,
        )
        if grid_args:
            kwargs.update(grid_args)

        self.grid = LocalSQLFORM.grid(query, **kwargs)
        self.paginate = kwargs['paginate']       # Make paginate accessible.
        # Remove 'None' record count if applicable.
        for count, div in enumerate(self.grid[0]):
            if str(div) == '<div class="web2py_counter">None</div>':
                del self.grid[0][count]
