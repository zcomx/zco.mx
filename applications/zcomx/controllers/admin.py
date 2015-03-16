# -*- coding: utf-8 -*-
""" Admin controller."""

from applications.zcomx.modules.access import requires_admin_ip


@requires_admin_ip()
def index():
    """Default controller."""
    return dict()
