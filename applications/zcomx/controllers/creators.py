# -*- coding: utf-8 -*-
"""Creator controller functions"""

import cgi
from gluon.storage import Storage
from applications.zcomx.modules.links import CustomLinks
from applications.zcomx.modules.routing import route


def books():
    """Creator books report controller.
    request.args(0): integer, id of creator.
    """
    return dict()


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
    view_dict, view = route(db, request, auth)
    if view:
        response.view = view
    if view_dict:
        return view_dict

    # If we get here, we don't have a valid creator
    raise HTTP(404, "Page not found")
