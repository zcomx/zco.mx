#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Access classes and functions.
"""
from gluon import *
from applications.zcomx.modules.creators import Creator


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
        admin_ips = current.app.local_settings.admin_ips.split(',')
        if not admin_ips:
            return False

        if current.request.client not in admin_ips:
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
            auth = current.app.auth

            if not auth.is_impersonating():
                redirect_url = URL(c='login', f='agree_to_terms')
                try:
                    creator = Creator.from_key(dict(auth_user_id=auth.user_id))
                except LookupError:
                    return redirect(redirect_url)
                else:
                    if not creator.agreed_to_terms:
                        return redirect(redirect_url)

            return action(*a, **b)
        wrapper.__doc__ = action.__doc__
        wrapper.__name__ = action.__name__
        wrapper.__dict__.update(action.__dict__)
        return wrapper
    return _decorator


def requires_login_if_configured(local_settings, otherwise=None):
    """Decorator restricting access to a function if the configuration
    settings prescribe login is required.

    private/settings.conf
        require_login = True            # Only allow access if logged in
        require_login = False           # Allow access to everyone

    Args:
        otherwise: callable, what to do if requires fails.

    Returns:
        decorated function
    """
    return current.app.auth.requires(
        True,
        requires_login=local_settings.require_login,
        otherwise=otherwise
    )
