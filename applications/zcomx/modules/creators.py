#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
import logging
import os
from gluon import *
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.files import for_file
from applications.zcomx.modules.job_queue import \
    UpdateIndiciaQueuer
from applications.zcomx.modules.names import \
    CreatorName, \
    names
from applications.zcomx.modules.strings import \
    camelcase, \
    replace_punctuation, \
    squeeze_whitespace
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row
from applications.zcomx.modules.zco import SITE_NAME

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
        data = dict(
            auth_user_id=auth_user.id,
            email=auth_user.email,
        )
        creator_id = db.creator.insert(**data)
        db.commit()
        on_change_name(creator_id)

        # Create the default indicia for the creator
        queue_update_indicia(creator_id)


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


def creator_name(creator_entity, use='file'):
    """Return the name of the creator for the specific use.

    Args:
        creator_entity: Row instance or integer representing a creator.
        use: one of 'file', 'search', 'url'

    Returns:
        string, name of file
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, {e}'.format(e=creator_entity))
    if use == 'file':
        return CreatorName(formatted_name(creator)).for_file()
    elif use == 'search':
        return creator.name_for_search
    elif use == 'url':
        return creator.name_for_url
    return


def for_path(name):
    """Scrub name so it is suitable for use in a file path or url.

    Args:
        name: string, creator name to be scrubbed.
    Returns:
        string, scrubbed name
    """
    # Remove apostrophes
    # Otherwise "Fred's Smith" becomes 'FredSSmith' not 'FredsSmith'
    name = replace_punctuation(name, repl='', punctuation="""'""")
    # Replace punctuation with space
    name = replace_punctuation(name)
    name = squeeze_whitespace(name)
    name = camelcase(name)
    return for_file(name)


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


def html_metadata(creator_entity):
    """Return creator attributes for HTML metadata.

    Args:
        creator_entity: Row instance or integer representing a creator.

    Returns:
        dict
    """
    if not creator_entity:
        return {}

    db = current.app.db
    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record:
        raise NotFoundError('Creator not found, {e}'.format(e=creator_entity))

    image_url = None
    if creator_record.image:
        image_url = URL(
            c='images',
            f='download',
            args=creator_record.image,
            vars={'size': 'web'},
            host=True
        )

    return {
        'description': creator_record.bio,
        'image_url': image_url,
        'name': formatted_name(creator_record),
        'twitter': creator_record.twitter,
        'type': 'profile',
        'url': url(creator_record, host=True),
    }


def image_as_json(db, creator_entity, field='image'):
    """Return the creator image as json.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        field: string, the name of the creator field to get the image from.
    """
    image_attributes = []
    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record:
        return dumps(dict(files=image_attributes))

    if field not in db.creator.fields:
        LOG.error('Invalid creator image field: %s', field)
        return dumps(dict(files=image_attributes))

    if not creator_record[field]:
        return dumps(dict(files=image_attributes))

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

    image_attributes.append(
        dict(
            name=filename,
            size=size,
            url=image_url,
            thumbnailUrl=thumb,
            deleteUrl=delete_url,
            deleteType='DELETE',
        )
    )

    return dumps(dict(files=image_attributes))


def images(creator_entity):
    """Return a list of image names associated with the creator.

    Args:
        creator_entity: Row instance or integer representing a creator record.

    Returns:
        list of strings, list of image names. Eg of an image name:
            creator.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, {e}'.format(e=creator_entity))

    image_names = []
    for field in db.creator.fields:
        if db.creator[field].type != 'upload':
            continue
        if not creator[field]:
            continue
        image_names.append(creator[field])
    return image_names


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

    update_data = names(
        CreatorName(formatted_name(creator)), fields=db.creator.fields)

    if update_data:
        db(db.creator.id == creator.id).update(**update_data)
        db.commit()


def profile_onaccept(form):
    """Additional processing when profile is accepted.

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


def queue_update_indicia(creator_entity):
    """Queue a job to update the indicia images for a creator.

    Args:
        creator_entity: Row instance or integer representing a creator.

    Returns:
        Row instance representing the job created.
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=creator_entity))

    job = UpdateIndiciaQueuer(
        db.job,
        cli_args=[str(creator.id)],
    ).queue()

    if not job:
        # This isn't critical, just log a message.
        LOG.error(
            'Failed to create job to update indicia: %s',
            creator.id
        )

    return job


def rss_url(creator_entity, **url_kwargs):
    """Return the url to the rss feed for all of creator's books.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast.rss
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=creator_entity))

    controller = '{name}.rss'.format(name=creator_name(creator, use='url'))

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=controller,
        f='index',
        **kwargs
    )



def short_url(creator_entity):
    """Return a shortened url suitable for the creator page.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
    Returns:
        string, url, eg http://101.zco.mx
    """
    if not creator_entity:
        return

    db = current.app.db

    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record:
        return

    # Until SSL certs are available for subdomains, don't use SSL.
    return '{scheme}://{cid}.zco.mx'.format(
        # scheme=current.request.env.wsgi_url_scheme or 'https',
        scheme='http',
        cid=creator_record.id,
    )


def torrent_file_name(creator_entity):
    """Return the name of the torrent file for the creator.

    Args:
        creator_entity: Row instance or integer representing a creator.

    Returns:
        string, the file name.
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=creator_entity))

    fmt = '{name} ({url}).torrent'
    return fmt.format(
        name=creator_name(creator, use='file'),
        url='{cid}.zco.mx'.format(cid=creator.id),
    )


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

    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=creator_entity))

    link_url = torrent_url(creator)
    if not link_url:
        return empty

    if not components:
        name = '{n}.torrent'.format(n=creator_name(creator, use='url'))
        components = [name]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def torrent_url(creator_entity, **url_kwargs):
    """Return the url to the torrent file for all of creator's books.

    Args:
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast_(123.zco.mx).torrent
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=creator_entity))

    controller = '{name} ({i}.zco.mx).torrent'.format(
        name=creator_name(creator, use='file'),
        i=creator.id,
    ).replace(' ', '_')

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=controller,
        f='index',
        **kwargs
    )


def tumblr_data(creator_entity):
    """Return creator attributes for tumblr data.

    Args:
        creator_entity: Row instance or integer representing a creator.

    Returns:
        dict
    """
    if not creator_entity:
        return {}

    db = current.app.db
    creator_record = entity_to_row(db.creator, creator_entity)
    if not creator_record:
        raise NotFoundError('Creator not found, {e}'.format(e=creator_entity))

    social_media = []           # (field, url) tuples
    social_media_fields = [
        'website',
        'twitter',
        'shop',
        'tumblr',
        'facebook',
    ]

    for field in social_media_fields:
        if creator_record[field]:
            anchor = db.creator[field].represent(
                creator_record[field], creator_record)
            value = anchor.attributes['_href']
            social_media.append((field, value))

    return {
        'name': formatted_name(creator_record),
        'name_for_search': creator_name(creator_entity, use='search'),
        'name_for_url': creator_name(creator_entity, use='url'),
        'short_url': short_url(creator_record),
        'social_media': social_media,
        'twitter': creator_record.twitter,
        'url': url(creator_record, host=SITE_NAME),
    }


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
    name = creator_name(creator_entity, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name], **kwargs)
