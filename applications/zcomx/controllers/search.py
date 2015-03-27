# -*- coding: utf-8 -*-
""" Search controller."""

from applications.zcomx.modules.search import classified
from applications.zcomx.modules.zco import Zco


def box():
    """Controller for search box component"""
    return dict()


def index():
    """Default controller."""
    Zco().next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )

    icons = {'list': 'th-list', 'tile': 'th-large'}

    grid = classified(request)()

    return dict(
        grid=grid,
        grid_div=grid.render(),
        icons=icons,
    )
