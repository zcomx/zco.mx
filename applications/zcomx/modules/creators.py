#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
import os
from gluon import *
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.utils import entity_to_row


def add_creator(form):
    """Create a creator record.

    Args:
        form: form with form.vars values. form.vars.email is expected to be
            set to the email of the auth_user record.

    Usage:
        onaccept = [add_creator, ...]
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
            path_name=for_path(auth_user.name),
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
    creator_record = entity_to_row(db.creator, creator_id)
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

    image_url = URL(
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
        c='login',
        f='creator_img_handler',
    )

    images.append(
        dict(
            name=filename,
            size=size,
            url=image_url,
            thumbnailUrl=thumb,
            deleteUrl=delete_url,
            deleteType='DELETE',
        )
    )

    return dumps(dict(files=images))


def set_creator_path_name(form):
    """Set the creator.path_name field associated with the user.

    Args:
        form: form with form.vars values. form.vars.id is expected to be the
            id of the auth_user record for the creator.

    Usage:
        onaccept = [set_creator_path_name, ...]
    """
    if not form.vars.id:
        return
    db = current.app.db
    creator = db(db.creator.auth_user_id == form.vars.id).select(
        db.creator.ALL).first()
    set_path_name(creator)


def set_path_name(creator_entity):
    """Set the path_name field on a creator record.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
    """
    if not creator_entity:
        return

    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
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


def url(creator_entity, **url_kwargs):
    """Return a url suitable for the creator page.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg http://zco.mx/creators/index/Firstname_Lastname
            (routes_out should convert it to http://zco.mx/Firstname_Lastname)
    """
    name = url_name(creator_entity)
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name], **kwargs)


def url_name(creator_entity):
    """Return the name used for the creator in the url.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
    Returns:
        string, eg Firstname_Lastname
    """
    if not creator_entity:
        return

    db = current.app.db

    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record or not creator_record.path_name:
        return

    return creator_record.path_name.decode(
        'utf-8'
    ).encode('utf-8').replace(' ', '_')
