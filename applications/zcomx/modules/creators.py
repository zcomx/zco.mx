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
from applications.zcomx.modules.images import \
    is_optimized, \
    queue_optimize
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
        )
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

    update_data = names(
        CreatorName(formatted_name(creator)), fields=db.creator.fields)

    if update_data:
        db(db.creator.id == creator.id).update(**update_data)
        db.commit()


def optimize_images(
        creator_entity,
        priority='optimize_img',
        job_options=None,
        cli_options=None):
    """Optimize all images related to a creator.

    Args:
        creator_entity: Row instance or integer representing a creator.
        priority: string, priority key, one of PROIRITIES
        job_options: dict, job record attributes used for JobQueuer property
        cli_options: dict, options for job command
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Book not found, {e}'.format(e=creator_entity))

    jobs = []

    for field in db.creator.fields:
        if db.creator[field].type != 'upload' or not creator[field]:
            continue
        jobs.append(
            queue_optimize(
                creator[field],
                priority=priority,
                job_options=job_options,
                cli_options=cli_options
            )
        )

    return jobs


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

    kwargs = {
        '_data-record_table': 'creator',
        '_data-record_id': str(creator.id),
        '_class': 'log_download_link',
    }
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
            http://zco.mx/torrents/route/First_Last_(123.zco.mx).torrent
            routes_out should convert it to
                http://zco.mx/First_Last_(123.zco.mx).torrent)
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


def unoptimized_images(creator_entity):
    """Return a list of unoptimized images related to a creator.

    Images are deemed unoptimized if there is no optimize_img_log record
    indicating it has been optimized.

    Args:
        creator_entity: Row instance or integer representing a creator.

    Returns:
        list of strings, [image_name_1, image_name_2, ...]
            eg image name: creator.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        raise NotFoundError('Creator not found, {e}'.format(e=creator_entity))

    unoptimals = []

    for field in db.creator.fields:
        if db.creator[field].type != 'upload':
            continue
        if not creator[field]:
            continue
        if not is_optimized(creator[field]):
            unoptimals.append(creator[field])

    return unoptimals


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
