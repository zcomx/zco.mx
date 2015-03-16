#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Access classes and functions.
"""
from gluon import *


def requires_admin_ip(requires_login=True, otherwise=None):
    """Decorator restricting access to function to only admin ips.

    Args:
        otherwise: callable, what to do if requires fails.

    Returns:
        decorated function
    """
    def _is_admin_ip():
        """auth.requires() condition"""
        # To be safe, return False on any errors/exceptions
        admin_ips = current.app.local_settings.admin_ips
        if not admin_ips:
            return False

        if current.request.client != admin_ips:
            return False
        return True
    return current.app.auth.requires(
        _is_admin_ip, requires_login=requires_login, otherwise=otherwise)
