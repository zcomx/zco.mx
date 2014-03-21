#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Search classes and functions.
"""
from gluon import *
from applications.zcomix.modules.books import read_link
from applications.zcomix.modules.stickon.sqlhtml import LocalSQLFORM


class Search(object):
    """Class representing a search grid"""

    order_fields = {
            'contributions': {
                'table': 'book',
                'field': 'contributions',
                'fmt': lambda x: '${v:0.0f}'.format(v=x),
                'label': 'contributions',
                'periods': True,
                },
            'newest': {
                'table': 'book',
                'field': 'created_on',
                'fmt': lambda x: str(x.date()),
                'label': 'added',
                'periods': False,
                },
            'views': {
                'table': 'book',
                'field': 'views',
                'fmt': lambda x: '{v}'.format(v=x),
                'label': 'views',
                'periods': True,
                },
            'rating': {
                'table': 'book',
                'field': 'rating',
                'fmt': lambda x: '{v:0.1f}'.format(v=x),
                'label': 'rating',
                'periods': True,
                },
            }

    def __init__(self):
        """Constructor"""
        self.grid = None
        self.orderby_field = None
        self.paginate = 0

    def set(self, db, request, grid_args=None):
        """Set the grid.

        Args:
            db: gluon.dal.DAL instance
            request: gluon.globals.Request instance.
            grid_args: dict of SQLFORM.grid arguments.
        """
        # C0103: *Invalid name "%%s" (should match %%s)*
        # pylint: disable=C0103

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

        if request.vars.released == '0':
            queries.append((db.book.release_date == None))
        if request.vars.released == '1':
            queries.append((db.book.release_date != None))

        if request.vars.kw:
            queries.append(
                (db.book.name.contains(request.vars.kw)) | \
                (db.auth_user.name.contains(request.vars.kw))
                )

        if not queries:
            queries.append(db.book)

        query = reduce(lambda x, y: x & y, queries) if queries else None

        period = 'month' if request.vars.period == 'month' else 'year'

        if request.vars.o and request.vars.o in self.order_fields.keys():
            orderby_field = self.order_fields[request.vars.o]
        else:
            orderby_field = self.order_fields['views']

        self.orderby_field = orderby_field

        if orderby_field['periods']:
            orderby_fieldname = '{f}_{p}'.format(
                    f=orderby_field['field'], p=period)
        else:
            orderby_fieldname = orderby_field['field']

        orderby = [~db[orderby_field['table']][orderby_fieldname]]
        orderby.append(db.book.id)              # Ensure consistent results

        db.book.id.readable = False
        db.book.id.writable = False
        db.book.name.represent = lambda v, row: A(v, _href=URL(c='books', f='book', args=row.book.id, extension=False))
        db.creator.id.readable = False
        db.creator.id.writable = False
        db.auth_user.name.represent = lambda v, row: A(v, _href=URL(c='creators', f='creator', args=row.creator.id, extension=False))

        fields = [
            db.book.id,
            db.book.name,
            db.book.release_date,
            db.book.contributions_year,
            db.book.contributions_month,
            db.book.rating_year,
            db.book.rating_month,
            db.book.views_year,
            db.book.views_month,
            db.book.created_on,
            db.creator.id,
            ]

        def link_book_id(row):
            book_id = 0
            if 'book' in row:
                # grid
                book_id = row.book.id
            elif 'id' in row:
                # editing
                book_id = row.id
            return book_id

        def contribute_link(row):
            book_id = link_book_id(row)
            if not book_id:
                return ''

            return A('contribute',
                _href=URL(c='books', f='book', args=book_id, extension=False),
                )

        def download_link(row):
            book_id = link_book_id(row)
            return A(
                'Download',
                _href=URL(c='books', f='download', args=book_id, extension=False),
                _class='btn btn-default fixme',
                _type='button',
                )

        def edit_link(row):
            book_id = link_book_id(row)
            if not book_id:
                return ''

            return A(
                SPAN(_class="glyphicon glyphicon-pencil"),
                'Edit',
                _href=URL(c='profile', f='book_edit', args=book_id, anchor='book_edit', extension=False),
                _class='btn btn-default',
                _type='button',
                )

        def read_link_func(row):
            book_id = link_book_id(row)
            if not book_id:
                return ''
            return read_link(db, book_id, **dict(_class='btn btn-default', _type='button'))

        def release_link(row):
            book_id = link_book_id(row)
            if not book_id:
                return ''

            return A('Release',
                _href=URL(c='profile', f='book_release', args=book_id, extension=False),
                _class='btn btn-default',
                _type='button',
                )

        links = [
                {
                    'header': '',
                    'body': read_link_func,
                },
                ]

        if editable:
            if request.vars.released == '0':
                links.append(
                    {
                        'header': '',
                        'body': release_link,
                    }
                    )
            links.append(
                {
                    'header': '',
                    'body': edit_link,
                }
                )
        else:
            links.append(
                {
                    'header': '',
                    'body': download_link,
                },
                )
            links.append(
                {
                    'header': '',
                    'body': contribute_link,
                }
                )

        if request.vars.view != 'list' or not creator:
            fields.append(db.auth_user.name)

        oncreate = None
        if editable and creator:
            def update_book_creator(form):
                db(db.book.id == form.vars.id).update(creator_id=creator.id)
                db.commit()
            oncreate = update_book_creator

        def ondelete(table, record_id):
            """Callback for ondelete."""
            # Delete all records associated with the book.
            for t in ['book_page', 'book_view', 'contribution', 'rating']:
                db(db[t].book_id == record_id).delete()
            db.commit()
            # Delete all links associated with the book.
            for row in db(db.book_to_link.book_id == record_id).select(db.book_to_link.link_id):
                db(db.link.id == row['link_id']).delete()
            db(db.book_to_link.book_id == record_id).delete()
            db.commit()

        kwargs = dict(
                fields=fields,
                headers={
                    'book.name': 'Title',
                    'auth_user.name': 'Creator',
                    },
                orderby=orderby,
                left=[
                    db.creator.on(db.book.creator_id == db.creator.id),
                    db.auth_user.on(db.creator.auth_user_id == db.auth_user.id),
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
                editargs={'deletable': False},
                )
        if grid_args:
            kwargs.update(grid_args)

        self.grid = LocalSQLFORM.grid(query, **kwargs)
        self.paginate = kwargs['paginate']       # Make paginate accessible.
        # Remove 'None' record count if applicable.
        for count, div in enumerate(self.grid[0]):
            if str(div) == '<div class="web2py_counter">None</div>':
                del self.grid[0][count]
