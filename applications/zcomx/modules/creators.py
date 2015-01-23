#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
import logging
import os
from gluon import *
from gluon.contrib.simplejson import dumps
from gluon.validators import urlify
from applications.zcomx.modules.files import FileName
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')


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
        creator_id = db.creator.insert(
            auth_user_id=auth_user.id,
            email=auth_user.email,
            indicia_modified=current.request.now,     # Trigger update of
                                                      # indicia_* fields
        )
        db.commit()
        on_change_name(creator_id)


def book_for_contributions(db, creator_entity):
    """Return the book contributions to the creator will be applied to.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the record. The creator record is read.

    Returns:
        Row instance representing book.
    """
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        return
    query = (db.book.creator_id == creator.id)
    return db(query).select(
        db.book.ALL,
        orderby=~db.book.contributions_remaining,
        limitby=(0, 1),
    ).first()


def can_receive_contributions(db, creator_entity):
    """Return whether a creator can receive contributions.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the record. The creator record is read.

    Returns:
        boolean, True if creator can receive contributions.
    """
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        return False

    # Must have paypal email
    if not creator.paypal_email:
        return False

    # Must have a book for contributions.
    book = book_for_contributions(db, creator_entity)
    if not book:
        return False
    return True


def contribute_link(db, creator_entity, components=None, **attributes):
    """Return html code suitable for a 'Contribute' link.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the record. The creator record is read.
        components: list, passed to A(*components),  default ['Contribute']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        return empty

    if not components:
        components = ['Contribute']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='contributions',
            f='modal',
            vars=dict(creator_id=creator.id),
            extension=False
        )

    return A(*components, **kwargs)


def for_path(name):
    """Scrub name so it is suitable for use in a file path or url.

    Args:
        name: string, creator name to be scrubbed.
    Returns:
        string, scrubbed name
    """
    return FileName(name).scrubbed()


def formatted_name(creator_entity):
    """Return the formatted name of the creator.

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

    return auth_user.name


def image_as_json(db, creator_entity, field='image'):
    """Return the creator image as json.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        field: string, the name of the creator field to get the image from.
    """
    images = []
    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record:
        return dumps(dict(files=images))

    if field not in db.creator.fields:
        LOG.error('Invalid creator image field: %s', field)
        return dumps(dict(files=images))

    if not creator_record[field]:
        return dumps(dict(files=images))

    filename, original_fullname = db.creator[field].retrieve(
        creator_record[field],
        nameonly=True,
    )

    try:
        size = os.stat(original_fullname).st_size
    except (KeyError, OSError):
        size = 0

    image_url = URL(
        c='images',
        f='download',
        args=creator_record[field],
    )

    thumb = URL(
        c='images',
        f='download',
        args=creator_record[field],
        vars={'size': 'web'},
    )

    delete_url = URL(
        c='login',
        f='creator_img_handler',
        args=[field]
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


def on_change_name(creator_entity):
    """Update creator record when name is changed.

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

    update_data = {}

    name = formatted_name(creator)
    if creator.path_name != name:
        update_data['path_name'] = name

    urlify_name = urlify(name)
    if creator.urlify_name != urlify_name:
        update_data['urlify_name'] = urlify_name

    if update_data:
        db(db.creator.id == creator.id).update(**update_data)
        db.commit()


def profile_onaccept(form):
    """Set the creator.path_name field associated with the user.

    Args:
        form: form with form.vars values. form.vars.id is expected to be the
            id of the auth_user record for the creator.

    Usage:
        onaccept = [creator_profile_onaccept, ...]
    """
    if not form.vars.id:
        return
    db = current.app.db
    creator = db(db.creator.auth_user_id == form.vars.id).select(
        db.creator.ALL).first()
    on_change_name(creator)


def torrent_link(creator_entity, components=None, **attributes):
    """Return a link suitable for the torrent file of all of creator's books.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        components: list, passed to A(*components),  default [torrent_name()]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

    name = torrent_name(creator_entity)
    if not name:
        return empty

    link_url = torrent_url(creator_entity)
    if not link_url:
        return empty

    if not components:
        components = [name]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def torrent_name(creator_entity):
    """Return the name of the torrent file of all of creator's books.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
    Returns:
        string, eg 'all-first_last.torrent'
    """
    name = url_name(creator_entity)
    if not name:
        return
    return 'all-{n}.torrent'.format(n=name).lower()


def torrent_url(creator_entity, **url_kwargs):
    """Return the url to the torrent file for all of creator's books.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, eg /path/to/all-first_last.torrent
    """
    name = torrent_name(creator_entity)
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c='FIXME',
        f='{dir}/{file}'.format(dir='FIXME', file=name),
        **kwargs
    )


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
