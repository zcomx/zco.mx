# -*- coding: utf-8 -*-
""" Search controller."""

import uuid
from BeautifulSoup import BeautifulSoup
from applications.zcomx.modules.search import classified


def box():
    """Controller for search box component"""
    return dict()


def index():
    """Default controller."""
    session.next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )
    return dict()


def list_grid():
    """Search results list grid."""
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

    grid = classified(request)(form_grid_args=grid_args)
    return dict(grid=grid)


def tile_grid():
    """Search results cover grid.

    request.vars.o: string, orderby field, one of Search.orderby_fields.keys()
    """
    response.view = 'search/creator_tile_grid.load' \
        if request.vars.o and request.vars.o == 'creators' \
        else 'search/tile_grid.load'

    grid_args = dict(
        paginate=12,
    )
    grid = classified(request)(form_grid_args=grid_args)

    # extract the paginator from the grid
    soup = BeautifulSoup(str(grid.form_grid))
    paginator = soup.find('div', {'class': 'web2py_paginator grid_header '})

    return dict(
        grid=grid,
        paginator=paginator,
    )
