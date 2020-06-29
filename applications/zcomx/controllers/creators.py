# -*- coding: utf-8 -*-
"""Creator controller functions"""

import traceback
from applications.zcomx.modules.access import requires_login_if_configured
from applications.zcomx.modules.routing import \
    Router, \
    SpareCreatorError
from applications.zcomx.modules.zco import Zco


def creator():
    """Creator page."""
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


@requires_login_if_configured(local_settings)
def index():
    """Creators default controller.

    This controller is used to route creator related requests.
    """
    router = Router(db, request, auth)

    try:
        router.route()
    except SpareCreatorError as err:
        LOG.info(err)
        raise HTTP(404, "Page not found")
    except HTTP:
        # These don't need to be logged as they provide no useful info.
        raise
    except Exception:
        # Ensure that during the page_not_found formatting if any exceptions
        # happen a 404 is returned. Then search bots, for example, see they
        # have an invalid page, and also fail2ban can catch them.
        raise HTTP(404, "Page not found")

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
        Zco().next_url = request.env.web2py_original_uri
        return router.view_dict

    # If we get here, we don't have a valid creator
    raise HTTP(404, "Page not found")


def monies():
    """Creator page."""
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")
