# -*- coding: utf-8 -*-
"""Book controller functions"""


def book():
    """Book page controller """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def index():
    """Books grid."""
    # This is no longer used
    redirect(URL(c='default', f='index'))


def reader():
    """Read a book. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def scroller():
    """Read a book using the scroller. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def slider():
    """Read a book using the slider. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")
