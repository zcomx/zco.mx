#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Zco: System globals, constants and session classes and functions.
"""
import logging
from gluon import *
from gluon.storage import Storage

LOG = logging.getLogger('app')

# Constants

BOOK_STATUS_ACTIVE = 'a'
BOOK_STATUS_DISABLED = 'x'
BOOK_STATUS_DRAFT = 'd'
BOOK_STATUSES = [
    BOOK_STATUS_ACTIVE,
    BOOK_STATUS_DISABLED,
    BOOK_STATUS_DRAFT,
]

NICES = {
    'resize': 11,
    'indicia': 13,
    'mktorrent': 14,
    'zip': 15,
    'zc-p2p': 18,
    'optimize': 19,         # max
}

SITE_NAME = 'zco.mx'


class Zco(object):
    """Class used for system globals and sessions

    Session variables are stored in web2py's globals session. Zco
    is used as a go-between so the variables can be documented in
    a single place and name collisions can be avoided.
    """
    # R0201: *Method could be a function*
    # pylint: disable=R0201

    def __init__(self):
        """Constructor """
        if current.session.zco is None:
            current.session.zco = Storage({})

    # Session variables
    # next_url
    #  Stores the next url to redirect to. Can be used whenever there
    #  is an intermediate redirect out of the control of the code.
    @property
    def next_url(self):
        """Getter."""
        return current.session.zco.next_url

    @next_url.setter
    def next_url(self, value):
        """Setter."""
        current.session.zco.next_url = value

    @next_url.deleter
    def next_url(self):
        """Deleter."""
        current.session.zco.next_url = None

    # paypal_in_progress
    #  Used to prevent endless loop on browser Back. When the contributions.py
    #  def paypal() controller is run it redirects automatically to
    #  paypal.com. If the user uses the browser Back button, it will redirect
    #  from paypal.com back to the paypal() controller, which then
    #  automatically redirects to paypal.com causing an endless loop. The
    #  paypal_in_progress session variable is set to prevent this looping.
    #  When the controller is first run, session.paypal_in_progress is set to
    #  True. When the controller is re-run on browser Back, the value is
    #  checked. If True, don't display the page, redirect to next_url.
    @property
    def paypal_in_progress(self):
        """Getter."""
        return current.session.zco.paypal_in_progress

    @paypal_in_progress.setter
    def paypal_in_progress(self, value):
        """Setter."""
        current.session.zco.paypal_in_progress = value

    @paypal_in_progress.deleter
    def paypal_in_progress(self):
        """Deleter."""
        current.session.zco.paypal_in_progress = None

    # Global variables
    @property
    def all_torrent_url(self):
        """FIXME"""
        return dict(c='zco.mx.torrent', f='index')


def html_metadata():
    """Return the HTML metadata for the site.

    Returns:
        dict
    """
    return {
        'name': SITE_NAME,
        'title': SITE_NAME,
        'description': (
            'zco.mx is a curated not-for-profit comic-sharing website'
            ' for self-publishing cartoonists and their readers.'
        ),
        'icon': URL(
            c='static',
            f='images/zco.mx-logo-small.png',
            host=True,
        ),
        'type': '',
        'twitter': '@zcomx_bot',
        'url': URL(host=True),
    }
