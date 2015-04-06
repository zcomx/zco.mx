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


def requires_agreed_to_terms():
    """Decorator restricting access to function to only admin ips.

    Args:
        otherwise: callable, what to do if requires fails,
            or string, url to redirect to.

    Returns:
        decorated function
    """
    def _decorator(action):
        """Decorator"""
        def wrapper(*a, **b):
            """Wrapped function."""
            db = current.app.db
            auth = current.app.auth

            if not auth.is_impersonating():
                creator_record = db(
                    db.creator.auth_user_id == auth.user_id
                ).select(db.creator.ALL).first()
                if not creator_record or not creator_record.agreed_to_terms:
                    return redirect(URL(c='login', f='agree_to_terms'))

            return action(*a, **b)
        wrapper.__doc__ = action.__doc__
        wrapper.__name__ = action.__name__
        wrapper.__dict__.update(action.__dict__)
        return wrapper
    return _decorator
