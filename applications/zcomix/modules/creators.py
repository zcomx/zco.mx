#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
import os
from gluon import *
from gluon.contrib.simplejson import dumps


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
        db.auth_user.ALL
    ).first()
    if not auth_user:
        # Nothing we can do if there is no auth_user record
        return

    creator = db(db.creator.auth_user_id == auth_user.id).select(
        db.creator.ALL
    ).first()

    if not creator:
        db.creator.insert(
            auth_user_id=auth_user.id,
            email=auth_user.email,
        )
        db.commit()


def image_as_json(db, creator_id):
    """Return the creator image as json.

    Args:
        db: gluon.dal.DAL instance
        creator_id: integer, id of creator record.
    """
    images = []
    creator_record = db(db.creator.id == creator_id).select(
        db.creator.ALL
    ).first()

    if not creator_record or not creator_record.image:
        return dumps(dict(files=images))

    filename, original_fullname = db.creator.image.retrieve(
        creator_record.image,
        nameonly=True,
    )

    try:
        size = os.stat(original_fullname).st_size
    except (KeyError, OSError):
        size = 0

    url = URL(
        c='images',
        f='download',
        args=creator_record.image,
    )

    thumb = URL(
        c='images',
        f='download',
        args=creator_record.image,
        vars={'size': 'thumb'},
    )

    delete_url = URL(
        c='profile',
        f='creator_img_handler',
    )

    images.append(
        dict(
            name=filename,
            size=size,
            url=url,
            thumbnailUrl=thumb,
            deleteUrl=delete_url,
            deleteType='DELETE',
        )
    )

    return dumps(dict(files=images))
