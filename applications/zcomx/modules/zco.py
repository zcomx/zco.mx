#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Zco: System globals, constants and session classes and functions.
"""
from gluon import *
from gluon.storage import Storage
from applications.zcomx.modules.stickon.tools import ModelDb

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

IN_PROGRESS = '__in_progress__'
SITE_NAME = 'zco.mx'
TUMBLR_USERNAME = 'zcomx'
TWITTER_BOT_HANDLE = '@zcomx_bot'


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
    def get_next_url(self):
        """Getter."""
        return current.session.zco.next_url

    def set_next_url(self, value):
        """Setter."""
        current.session.zco.next_url = value

    def del_next_url(self):
        """Deleter."""
        current.session.zco.next_url = None

    next_url = property(
        get_next_url, set_next_url, del_next_url, 'Next url to redirect to')

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
    def get_paypal_in_progress(self):
        """Getter."""
        return current.session.zco.paypal_in_progress

    def set_paypal_in_progress(self, value):
        """Setter."""
        current.session.zco.paypal_in_progress = value

    def del_paypal_in_progress(self):
        """Deleter."""
        current.session.zco.paypal_in_progress = None

    paypal_in_progress = property(
        get_paypal_in_progress,
        set_paypal_in_progress,
        del_paypal_in_progress,
        'Indicates if a paypal payment is in progress'
    )

    # Global variables
    @property
    def all_rss_url(self):
        """Url for all rss feed."""
        return dict(c='zco.mx.rss', f='index')

    @property
    def all_torrent_url(self):
        """Url for all-torrent."""
        return dict(c='zco.mx.torrent', f='index')


class ZcoModelDb(ModelDb):
    """ModelDb with Zco customizations."""

    def _auth_post_hook(self, auth):
        if not self.local_settings.disable_authentication:
            auth.settings.extra_fields['auth_user'] = [Field('name')]


class ZcoMigratedModelDb(ZcoModelDb):
    """Class representing the db.py model with migration enabled."""
    migrate = True


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
        'twitter': TWITTER_BOT_HANDLE,
        'url': URL(host=True),
    }
