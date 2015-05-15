# -*- coding: utf-8 -*-
"""
Default controller.
"""
import logging
import os
from applications.zcomx.modules.books import \
    page_url, \
    url as book_url
from applications.zcomx.modules.creators import \
    url as creator_url
from applications.zcomx.modules.search import classified
from applications.zcomx.modules.stickon.tools import ExposeImproved
from applications.zcomx.modules.utils import \
    faq_tabs, \
    markmin
from applications.zcomx.modules.zco import Zco

LOG = logging.getLogger('app')


def _search_results(request, response, orderby):
    """Helper function for search results."""
    response.view = 'search/index.html'

    Zco().next_url = URL(
        c=request.controller,
        f=request.function,
        args=request.args,
        vars=request.vars
    )

    request.vars.o = orderby

    icons = {'list': 'th-list', 'tile': 'th-large'}

    grid = classified(request)()

    return dict(
        grid=grid,
        grid_div=grid.render(),
        icons=icons,
    )


def about():
    """About page"""
    return markmin('about')


def cartoonists():
    """Front page 'cartoonists' tab."""
    return _search_results(request, response, 'creators')


def completed():
    """Front page 'completed' tab."""
    return _search_results(request, response, 'completed')


def contribute():
    """Contribute to zcomx admin controller"""
    Zco().paypal_in_progress = None
    redirect(URL(c='contributions', f='paypal', extension=False))


def copyright_claim():
    """Copyright claim page"""
    return markmin('copyright_claim')


def expenses():
    """Expenses page"""
    return markmin('expenses')


def faq():
    """FAQ page"""
    # Set up for 'donations' contributions to paypal handling.
    layout = 'login/layout.html' if auth and auth.user_id \
        else 'layout_main.html'
    extra = dict(
        tabs=faq_tabs(active='faq'),
        layout=layout,
    )
    return markmin('faq', extra=extra)


def faqc():
    """Creator FAQ page"""
    extra = dict(
        tabs=faq_tabs(active='faqc'),
    )

    return markmin('faqc', extra=extra)


@auth.requires_login()
def files():
    """Logos page"""
    base_path = os.path.join(request.folder, 'static', 'files')
    expose = ExposeImproved(base=base_path, display_breadcrumbs=False)
    return dict(expose=expose)


def index():
    """Default controller."""
    redirect(URL(c='default', f='index'))


def logos():
    """Logos page"""
    base_path = os.path.join(request.folder, 'static', 'images', 'logos')
    expose = ExposeImproved(base=base_path, display_breadcrumbs=False)
    return dict(expose=expose)


def modal_error():
    """Controller for displaying error messages within modal.

    request.vars.message: string, error message
    """
    return dict(message=request.vars.message)


def monies():
    """Controller for front page with contribute modal open."""
    redirect(URL(c='search', f='index', vars={'contribute': 1}))


def ongoing():
    """Front page 'ongoing' tab."""
    return _search_results(request, response, 'ongoing')


def overview():
    """Overview page"""
    return markmin('overview')


def search():
    """Front page 'search' input post controller."""
    return _search_results(request, response, 'search')


def terms():
    """Terms page"""
    is_creator = auth and auth.user_id
    layout = 'login/layout.html' if is_creator else 'layout_main.html'

    summary_sections = []
    if is_creator:
        summary_sections = [
            'terms-key_points',
        ]

    sections = [
        'terms-terms_of_use',
        'terms-content_guidelines',
        'terms-privacy_policy',
    ]

    return dict(
        layout=layout,
        sections=sections,
        summary_sections=summary_sections,
    )


def todo():
    """Todo page"""
    return markmin('todo')


def top():
    """Controller for top header component

    request.args(0): name of page, optional. Set to None for home page.
    """
    left_links = []
    right_links = []
    delimiter_class = 'pipe_delimiter'

    home = A(
        'home',
        _href=URL(c='default', f='index', extension=False)
    )
    left_links.append(LI(home))

    def li_link(label, url, **kwargs):
        """Return a LI(A(...)) structure."""
        if url is not None:
            li_text = A(label, _href=url)
        else:
            li_text = label
        return LI(li_text, **kwargs)

    def book_link(book_id, text_only=False):
        """Return a book link."""
        label = 'book'
        url = book_url(book_id, extension=False) \
            if book_id and not text_only else None
        return li_link(label, url)

    def creator_link(creator_id, text_only=False):
        """Return a creator link."""
        label = 'cartoonist'
        url = creator_url(creator_id, extension=False) \
            if creator_id and not text_only else None
        return li_link(label, url)

    def login_link(label):
        """Return a link suitable for a login label"""
        return li_link(
            label,
            URL(c='login', f=label, extension=False),
            _class='active' if request.args(1) == label else '',
        )

    def page_link(page_id, text_only=False):
        """Return a read (book page) link."""
        label = 'read'
        url = page_url(page_id, extension=False) \
            if page_id and not text_only else None
        return li_link(label, url)

    def search_link(request):
        """Return a search results link."""
        label = 'search'
        url = URL(c='search', f='index', vars=request.vars)
        return li_link(label, url)

    if request.args(0):
        if request.args(0) == 'reader':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(request.vars.creator_id))
            left_links.append(book_link(request.vars.book_id))
            left_links.append(page_link(
                request.vars.book_page_id,
                text_only=True
            ))
        elif request.args(0) == 'book':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(request.vars.creator_id))
            left_links.append(book_link(
                request.vars.book_id,
                text_only=True
            ))
        elif request.args(0) == 'creator':
            delimiter_class = 'gt_delimiter'
            left_links.append(creator_link(
                request.vars.creator_id,
                text_only=True
            ))
        elif request.args(0) == 'login':
            delimiter_class = 'pipe_delimiter'
            left_links.append(login_link('books'))
            left_links.append(login_link('indicia'))
            left_links.append(login_link('profile'))
            left_links.append(login_link('account'))
    else:
        if request.vars.o == 'search':
            delimiter_class = 'gt_delimiter'
            left_links.append(search_link(request))

    breadcrumbs = {}
    breadcrumbs['left'] = OL(
        left_links,
        _class='breadcrumb left {d}'.format(d=delimiter_class),
    )

    if right_links:
        breadcrumbs['right'] = OL(
            right_links,
            _class='breadcrumb right',
        )

    return dict(breadcrumbs=breadcrumbs)
