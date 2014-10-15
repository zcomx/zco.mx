# -*- coding: utf-8 -*-
""" Search controller."""

import uuid
from BeautifulSoup import BeautifulSoup
from applications.zcomx.modules.search import Search


def box():
    """Controller for search box component"""
    return dict()


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


def tile_grid():
    """Search results cover grid.

    request.vars.o: string, orderby field, one of:
            'newest' (default) 'views', 'rating', 'contributions'
    """
    response.view = 'search/creator_tile_grid.load' \
        if request.vars.o and request.vars.o == 'creators' \
        else 'search/tile_grid.load'
    search = Search()
    search.set(db, request)

    soup = BeautifulSoup(str(search.grid))

    # extract the paginator from the grid
    paginator = soup.find('div', {'class': 'web2py_paginator grid_header '})

    contributions_by_id = {}
    if request.vars.o == 'creators':
        # extract the contributions_remaining
        # This is stored in a link that isn't made available in the grid
        # properties.
        table = soup.find('table')
        if table:
            for tr in table.findAll('tr'):
                try:
                    creator_id = int(tr['id'])
                except (KeyError, TypeError, ValueError):
                    continue
                tds = tr.findAll('td')
                if len(tds) < 2:
                    continue
                try:
                    amount = float(tds[1].span.string.strip())
                except (KeyError, TypeError, ValueError):
                    continue
                contributions_by_id[creator_id] = amount

    return dict(
        contributions_by_id=contributions_by_id,
        grid=search.grid,
        items_per_page=search.paginate,
        orderby_field=search.orderby_field,
        paginator=paginator,
    )
