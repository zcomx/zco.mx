# -*- coding: utf-8 -*-
"""Creator controller functions"""

import cgi
from gluon.storage import Storage
from applications.zcomx.modules.routing import Router


def creator():
    """Creator page."""
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def index():
    """Creators default controller.

    This controller is used to route creator related requests.
    """
    # Note: there is a bug in web2py Ver 2.9.11-stable where request.vars
    # is not set by routes.
    # Ticket: http://code.google.com/p/web2py/issues/detail?id=1990
    # If necessary, parse request.env.query_string for the values.
    def parse_get_vars():
        """Adapted from gluon/globals.py class Request"""
        query_string = request.env.get('query_string', '')
        dget = cgi.parse_qs(query_string, keep_blank_values=1)
        get_vars = Storage(dget)
        for (key, value) in get_vars.iteritems():
            if isinstance(value, list) and len(value) == 1:
                get_vars[key] = value[0]
        return get_vars

    request.vars.update(parse_get_vars())

    router = Router(db, request, auth)
    router.route()
    if router.redirect:
        redirect(router.redirect)
    if router.view:
        if router.view == 'creators/monies.html' \
                or router.view == 'books/scroller.html' \
                or router.view == 'books/slider.html':
            response.files.append(
                URL('static', 'fonts/sf_cartoonist/stylesheet.css')
            )
            response.files.append(
                URL('static', 'fonts/brushy_cre/stylesheet.css')
            )
        response.view = router.view
    if router.view_dict:
        # Set next_url. Used in contributions.py def paypal()
        session.next_url = request.env.web2py_original_uri
        return router.view_dict

    # If we get here, we don't have a valid creator
    raise HTTP(404, "Page not found")


def monies():
    """Creator page."""
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")
