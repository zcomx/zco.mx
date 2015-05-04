# -*- coding: utf-8 -*-
"""
Controller for error handling.
"""
import logging
from gluon.storage import Storage

LOG = logging.getLogger('app')


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
    redirect(URL('index'), client_side=True)


def page_not_found():
    """Page not found. Used if an invalid url is provided.

    request.vars.invalid_url: string, optional, url user used.
    request.vars.creator_id: integer, optional, id of creator to use in
        examples. This is ignored if request.vars.book_id is set.
    request.vars.book_id: integer, optional, id of book to use in examples.
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
    title = 'Page not found'
    message = 'The server was not able to display the requested page.'
    return dict(urls=urls, message=message, title=title)
