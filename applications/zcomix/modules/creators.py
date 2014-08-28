#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
import os
from gluon import *
from gluon.contrib.simplejson import dumps
from applications.zcomix.modules.files import FileName


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


def for_path(name):
    """Scrub name so it is suitable for use in a file path or url.

    Args:
        name: string, creator name to be scrubbed.
    Returns:
        string, scrubbed name
    """
    return FileName(name).scrubbed()


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
        vars={'size': 'tbn'},
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


def set_path_name(creator_entity):
    """Set the path_name field on a creator record.

    Args:
        creator: Row instance or integer, Row instance represents creator,
                or integer representing id of creator record.
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
    """
    if not creator_entity:
        return

    db = current.app.db

    creator = None
    if hasattr(creator_entity, 'id'):
        creator = creator_entity
    else:
        # Assume creator is an id
        creator = db(db.creator.id == creator_entity).select().first()

    if not creator or not creator.auth_user_id:
        return

    # Read the auth_user record
    query = (db.auth_user.id == creator.auth_user_id)
    auth_user = db(query).select(db.auth_user.ALL).first()
    if not auth_user:
        return

    name = for_path(auth_user.name)
    if creator.path_name != name:
        db(db.creator.id == creator.id).update(path_name=name)
        db.commit()
