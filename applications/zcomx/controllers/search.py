# -*- coding: utf-8 -*-
""" Search controller."""

import uuid
from BeautifulSoup import BeautifulSoup
from applications.zcomx.modules.search import Search


def box():
    """Controller for search box component"""
    return dict()


def cover_grid():
    """Search results cover grid.

    request.vars.o: string, orderby field, one of:
            'newest' (default) 'views', 'rating', 'contributions'
    """
    search = Search()
    search.set(db, request)

    # extract the paginator from the grid
    soup = BeautifulSoup(str(search.grid))
    paginator = soup.find('div', {'class': 'web2py_paginator grid_header '})
    return dict(
            grid=search.grid,
            items_per_page=search.paginate,
            orderby_field=search.orderby_field,
            paginator=paginator,
            )


def index():
    """Default controller."""
    return dict()


def list_grid():
    """Search results list grid."""
    db.book.contributions_year.readable = False
    db.book.contributions_month.readable = False
    db.book.rating_year.readable = False
    db.book.rating_month.readable = False
    db.book.views_year.readable = False
    db.book.views_month.readable = False

    # Two forms can be placed on the same page. Make sure the formname is
    # unique.

    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    formname = request.vars._formname or str(uuid.uuid4())

    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212

    grid_args = dict(
             paginate=20,
             formname=formname,
             )

    search = Search()
    search.set(db, request, grid_args=grid_args)

    return dict(grid=search.grid)
