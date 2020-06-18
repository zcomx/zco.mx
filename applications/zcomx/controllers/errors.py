# -*- coding: utf-8 -*-
"""
Controller for error handling.
"""
from gluon.storage import Storage
from applications.zcomx.modules.stickon.restricted import log_ticket
from applications.zcomx.modules.zco import Zco


def index():
    """Default controller."""
    title = 'Server error'
    message = 'The server was not able to display the requested page.'
    return dict(message=message, title=title)


def handler():
    """Error handler controller.

    The redirect with client_side handles errors occuring within components
    without repeated page reloads.
    """
    log_ticket(request.vars.ticket)
    error_page = response.render('errors/index.html', dict())
    # In routes.py, 406 should redirect to def index
    raise HTTP(406, error_page)


def page_not_found():
    """Page not found. Used if an invalid url is provided.

    request.vars.invalid_url: string, optional, url user used.
    """
    deprecated_default_functions = [
        'about',
        'contribute',
        'copyright_claim',
        'expenses',
        'faq',
        'faqc',
        'files',
        'logos',
        'modal_error',
        'monies',
        'overview',
        'terms',
        'todo',
    ]

    title = 'Page not found'

    urls = None
    message = None

    session_pnf = Zco().page_not_found
    if session_pnf:
        if 'urls' in session_pnf:
            urls = session_pnf['urls']
        if 'message' in session_pnf:
            message = session_pnf['message']
        del Zco().page_not_found

    if not urls:
        urls = Storage({})
        urls.suggestions = []
        if request.vars.request_url \
                and request.vars.request_url.startswith('/zcomx/default'):
            parts = request.vars.request_url.split('/')
            if len(parts) >= 3:
                func_name = parts[3]
                if func_name in deprecated_default_functions:
                    urls.suggestions.append({
                        'label': func_name + ':',
                        'url': URL(c='z', f=func_name, host=True)
                    })
        urls.invalid = request.vars.request_url

    if not message:
        message = 'The server was not able to display the requested page.'

    return dict(urls=urls, message=message, title=title)


def test_exception():
    """Controller for testing exception handling."""
    raise SyntaxError('Exception raised from test_exception.')
