#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""

from gluon import *


def add_creator(form):
    """Create a creator record.

    Args:
        form: form with form.vars values.

    Usage:
        auth.settings.login_onaccept = lambda f: add_creator(f)
    """
    email = form.vars.email
    if not email:
        return

    db = current.app.db

    auth_user = db(db.auth_user.email == email).select(
            db.auth_user.ALL).first()
    if not auth_user:
        # Nothing we can do if there is no auth_user record
        return

    creator = db(db.creator.auth_user_id == auth_user.id).select(
            db.creator.ALL).first()

    if not creator:
        db.creator.insert(
            auth_user_id=auth_user.id,
            email=auth_user.email,
            )
        db.commit()
