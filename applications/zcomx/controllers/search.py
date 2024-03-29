# -*- coding: utf-8 -*-
""" Search controller."""
from applications.zcomx.modules.access import requires_login_if_configured
from applications.zcomx.modules.autocomplete import autocompleter_class
from applications.zcomx.modules.books import (
    Book,
    url as book_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    url as creator_url,
)
from applications.zcomx.modules.search import (
    Grid,
)
from applications.zcomx.modules.zco import Zco


def autocomplete():
    """Return autocomplete results for search input.

    request.args(0): string, table, one of 'book' or 'creator'
    request.vars.q: string, the query keywords.
        Returns all records if q is Falsy.
    """
    response.generic_patterns = ['json']
    completer_class = autocompleter_class(request.args(0))
    if not completer_class:
        return dict(results=[])
    completer = completer_class(keyword=request.vars.q)
    return dict(results=completer.search())


def autocomplete_selected():
    """Handle a selected item from autocomplete options.

    request.args(0): string, name of table ('book' or 'creator')
    request.args(1): integer, id of record in table
    """
    def page_not_found():
        """Handle page not found."""
        raise HTTP(404, "Page not found")

    if not request.args(0) or not request.args(1):
        page_not_found()

    if request.args(0) not in ['book', 'creator']:
        page_not_found()

    try:
        record_id = int(request.args(1))
    except (TypeError, ValueError):
        page_not_found()

    if request.args(0) == 'book':
        try:
            book = Book.from_id(record_id)
        except LookupError:
            url = None
        else:
            url = book_url(book)
    elif request.args(0) == 'creator':
        try:
            creator = Creator.from_id(record_id)
        except LookupError:
            url = None
        else:
            url = creator_url(creator)

    if not url:
        page_not_found()

    redirect(url)


def box():
    """Controller for search box component"""
    return {}


@requires_login_if_configured(local_settings)
def index():
    """Default controller."""
    Zco().next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )

    icons = {'list': 'th-list', 'tile': 'th-large'}

    try:
        grid = Grid.class_factory(request.vars.o or 'completed')
    except KeyError as exc:
        # 'releases' is deprecated, logging errors for it creates too much
        # noise.
        log_func = LOG.info if request.vars.o == 'releases' else LOG.error
        log_func('Invalid front view requested: o=%s', request.vars.o)
        raise HTTP(404, "Page not found") from exc

    return dict(
        grid=grid,
        grid_div=grid.render(),
        icons=icons,
    )
