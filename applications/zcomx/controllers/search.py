# -*- coding: utf-8 -*-
""" Search controller."""
from gluon.validators import urlify
from applications.zcomx.modules.access import requires_login_if_configured
from applications.zcomx.modules.books import \
    formatted_name as formatted_book_name, \
    url as book_url
from applications.zcomx.modules.creators import \
    formatted_name as formatted_creator_name, \
    url as creator_url
from applications.zcomx.modules.search import classified
from applications.zcomx.modules.zco import \
    BOOK_STATUS_ACTIVE, \
    Zco

import logging
LOG = logging.getLogger('app')


def autocomplete_books():
    """Return autocomplete results of books for search input.

    request.vars.q: string, the query keywords.
        Returns all books if q is blank.

    """
    response.generic_patterns = ['json']

    items = []

    queries = []
    queries.append((db.book.status == BOOK_STATUS_ACTIVE))
    if request.vars.q:
        kw = urlify(request.vars.q)
        queries.append((db.book.name_for_search.contains(kw)))
    query = reduce(lambda x, y: x & y, queries) if queries else None
    rows = db(query).select(
        db.book.id,
        orderby=db.book.name,
        distinct=True,
    )

    for r in rows:
        items.append(
            {
                'id': r.id,
                'table': 'book',
                'value': formatted_book_name(
                    db, r.id, include_publication_year=False)
            }
        )

    return dict(results=items)


def autocomplete_creators():
    """Return autocomplete results of creators for search input.

    request.vars.q: string, the query keywords.
    """
    response.generic_patterns = ['json']

    items = []

    queries = []
    # Creators must have at least one book
    queries.append((db.book.id != None))
    if request.vars.q:
        kw = urlify(request.vars.q)
        queries.append((db.creator.name_for_search.contains(kw)))
    query = reduce(lambda x, y: x & y, queries) if queries else None
    rows = db(query).select(
        db.creator.id,
        left=[
            db.book.on(db.book.creator_id == db.creator.id)
        ],
        orderby=db.creator.name_for_search,
        distinct=True,
    )

    for r in rows:
        items.append(
            {
                'id': r.id,
                'table': 'creator',
                'value': formatted_creator_name(r.id),
            }
        )

    return dict(results=items)


def autocomplete_selected():
    """Handle a selected item from autocomplete options.

    request.args(0): string, name of table ('book' or 'creator')
    request.args(1): integer, id of record in table
    """
    def page_not_found():
        """Handle page not found."""
        redirect(URL(c='errors', f='page_not_found'))

    if not request.args(0) or not request.args(1):
        page_not_found()

    if request.args(0) not in ['book', 'creator']:
        page_not_found()

    try:
        record_id = int(request.args(1))
    except (TypeError, ValueError):
        page_not_found()

    if request.args(0) == 'book':
        url = book_url(record_id)
    elif request.args(0) == 'creator':
        url = creator_url(record_id)

    if not url:
        page_not_found()

    redirect(url)


def box():
    """Controller for search box component"""
    return dict()


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

    grid = classified(request)()

    return dict(
        grid=grid,
        grid_div=grid.render(),
        icons=icons,
    )
