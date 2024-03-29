#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creator classes and functions.
"""
import functools
import json
import os
import shutil
from pydal.helpers.methods import delete_uploaded_files
from gluon import *
from applications.zcomx.modules.files import for_file
from applications.zcomx.modules.images import (
    SIZES,
    filename_for_size,
    square_image,
)
from applications.zcomx.modules.job_queuers import (
    UpdateIndiciaQueuer,
    queue_create_sitemap,
    queue_search_prefetch,
)
from applications.zcomx.modules.names import (
    CreatorName,
    names,
)
from applications.zcomx.modules.records import (
    Record,
    Records,
)
from applications.zcomx.modules.shell_utils import set_owner
from applications.zcomx.modules.strings import (
    camelcase,
    replace_punctuation,
    squeeze_whitespace,
)
from applications.zcomx.modules.zco import SITE_NAME

LOG = current.app.logger


class AuthUser(Record):
    """Class representing a auth_user record"""
    db_table = 'auth_user'


class Creator(Record):
    """Class representing a creator record"""
    db_table = 'creator'

    @classmethod
    def by_email(cls, email):
        """Return a Creator instance by an email.

        Args:
            email: str, email address (auth_user.email)

        Returns:
            Creator instance
        """
        auth_user = AuthUser.from_key(dict(email=email))
        return Creator.from_key(dict(auth_user_id=auth_user.id))

    def clear_image_tmp(self):
        """Clear the image_tmp field.

        Returns:
            Creator instance with image field updated
        """
        db = current.app.db

        if not self.image_tmp:
            return self

        return Creator.from_updated(
            self,
            {'image_tmp': None},
            validate=False,
        )

    def copy_image_from_tmp(self):
        """Copy the creator image from image_tmp to the image field.

        Returns:
            Creator instance with image field updated
        """
        db = current.app.db

        if self.image:
            dbset = db(db.creator.id == self.id)
            upload_fields = {'image': self.image}
            delete_uploaded_files(dbset, upload_fields=upload_fields)

        data = {}
        data['image'] = self.image_tmp.replace(
            'creator.image_tmp',
            'creator.image'
        )

        creator = Creator.from_updated(
            self,
            data,
            validate=False,
        )

        unused_original, full_name = db.creator.image_tmp.retrieve(
            creator.image_tmp,
            nameonly=True,
        )

        for size in SIZES:
            sized_fullname = filename_for_size(full_name, size)
            new_fullname = sized_fullname.replace(
                'creator.image_tmp',
                'creator.image'
            )
            dirname = os.path.dirname(new_fullname)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
                set_owner(dirname)
            if os.path.exists(sized_fullname):
                shutil.copy(sized_fullname, new_fullname)
                set_owner(new_fullname)

        return creator

    @property
    def name(self):
        """Return the name of the creator.

        Returns:
            str, the name of the creator
        """
        auth_user = self.as_one(AuthUser)
        return auth_user.name

    def square_image_tmp(self, offset=None):
        """Square the image stored in creator.image_tmp.

        Args:
            offset: str, see images.py def square_image
        """
        db = current.app.db
        if not self.image_tmp:
            return      # nothing to do

        unused_original, full_name = db.creator.image_tmp.retrieve(
            self.image_tmp,
            nameonly=True,
        )

        for size in SIZES:
            sized_fullname = filename_for_size(full_name, size)
            if os.path.exists(sized_fullname):
                square_image(sized_fullname, offset=offset)


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

    try:
        auth_user = AuthUser.from_key(dict(email=email))
    except LookupError:
        # Nothing we can do if there is no auth_user record
        return

    try:
        creator = Creator.from_key(dict(auth_user_id=auth_user.id))
    except LookupError:
        creator = None

    if not creator:
        data = dict(
            auth_user_id=auth_user.id,
            email=auth_user.email,
        )
        creator_id = db.creator.insert(**data)
        db.commit()

        creator = Creator.from_id(creator_id)
        on_change_name(creator)
        queue_update_indicia(creator)     # Create default indicia

    queue_create_sitemap()


def book_for_contributions(creator):
    """Return the book contributions to the creator will be applied to.

    Args:
        creator: Creator instance

    Returns:
        Row instance representing book.
    """
    if not creator:
        return
    db = current.app.db
    query = (db.book.creator_id == creator.id)
    return db(query).select(
        db.book.ALL,
        orderby=~db.book.contributions_remaining,
        limitby=(0, 1),
    ).first()


def can_receive_contributions(creator):
    """Return whether a creator can receive contributions.

    Args:
        creator: Creator instance

    Returns:
        boolean, True if creator can receive contributions.
    """
    if not creator:
        return False

    # Must have paypal email
    if not creator.paypal_email:
        return False

    # Must have a book for contributions.
    book = book_for_contributions(creator)
    if not book:
        return False
    return True


def contribute_link(creator, components=None, **attributes):
    """Return html code suitable for a 'Contribute' link.

    Args:
        creator: Creator instance
        components: list, passed to A(*components),  default ['Contribute']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

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


def creator_name(creator, use='file'):
    """Return the name of the creator for the specific use.

    Args:
        creator: Creator instance
        use: one of 'file', 'search', 'url'

    Returns:
        string, name of file
    """
    if use == 'file':
        return CreatorName(creator.name).for_file()

    if use == 'search':
        return creator.name_for_search

    if use == 'url':
        return creator.name_for_url


def download_link(creator, components=None, **attributes):
    """Return html code suitable for a 'Download' link.

    Args:
        creator: Book instance
        components: list, passed to A(*components),  default ['Download']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
    if not creator:
        return empty

    if not components:
        components = ['Download']

    kwargs = {}
    kwargs.update(attributes)

    if creator.torrent:
        if '_href' not in attributes:
            kwargs['_href'] = URL(
                c='downloads',
                f='modal',
                args=['creator', creator.id],
                extension=False,
            )
        class_attr = attributes['_class'] if '_class' in attributes else ''
        kwargs['_class'] = (class_attr + ' enabled').strip()
        tag = A
    else:
        kwargs['_href'] = None
        if '_title' not in attributes:
            kwargs['_title'] = \
                'This creator has not released any books for file sharing.'
        class_attr = attributes['_class'] if '_class' in attributes else ''
        kwargs['_class'] = (class_attr + ' disabled').strip()
        tag = SPAN

    return tag(*components, **kwargs)


def downloadable(orderby=None, limitby=None):
    """Return list of downloadable books.

    Args:
        orderby: orderby expression, see select()
        limitby: limitby expression, see seelct()

    Returns:
        Records instance representing list of Creator instances.
    """
    db = current.app.db
    queries = []
    queries.append((db.creator.torrent != ''))
    query = functools.reduce(lambda x, y: x & y, queries) if queries else None

    return Records.from_query(Creator, query, orderby=orderby, limitby=limitby)


def follow_link(creator, components=None, **attributes):
    """Return html code suitable for a 'Follow' link.

    Args:
        creator: Creator instance
        components: list, passed to A(*components),  default ['Download']
        attributes: dict of attributes for A()
    """
    if not components:
        components = ['Follow']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='rss',
            f='modal',
            args=[creator.id],
            extension=False
        )

    return A(*components, **kwargs)


def for_auth_user(name):
    """Scrub name so it is suitable for auth_user.name

    Args:
        name: string, creator name to be scrubbed.
    Returns:
        string, scrubbed name
    """
    # remove underscores
    name = replace_punctuation(name, repl='', punctuation='_')
    name = squeeze_whitespace(name)
    return for_file(name)


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


def generator(query, orderby=None):
    """Generate creator records.

    Args:
        query: gluon.dal.Expr query.
        orderby: pydal.objects.Field instance or list of Field instance.

    Yields:
        Creator instance
    """
    db = current.app.db
    if orderby is None:
        orderby = [db.creator.id]

    ids = [x.id for x in db(query).select(db.creator.id, orderby=orderby)]
    for creator_id in ids:
        creator = Creator.from_id(creator_id)
        yield creator


def html_metadata(creator):
    """Return creator attributes for HTML metadata.

    Args:
        creator: Creator instance

    Returns:
        dict
    """
    if not creator:
        return {}

    image_url = None
    if creator.image:
        image_url = URL(
            c='images',
            f='download',
            args=creator.image,
            vars={'size': 'web'},
            host=True
        )

    return {
        'description': creator.bio,
        'image_url': image_url,
        'name': creator.name,
        'twitter': creator.twitter,
        'type': 'profile',
        'url': url(creator, host=True),
    }


def image_as_json(creator, field='image'):
    """Return the creator image as json.

    Args:
        creator: Creator instance
        field: string, the name of the creator field to get the image from.
    """
    image_attributes = []
    if not creator:
        return json.dumps(dict(files=image_attributes))

    db = current.app.db
    if field not in db.creator.fields:
        LOG.error('Invalid creator image field: %s', field)
        return json.dumps(dict(files=image_attributes))

    if not creator[field]:
        return json.dumps(dict(files=image_attributes))

    filename, original_fullname = db.creator[field].retrieve(
        creator[field],
        nameonly=True,
    )

    try:
        size = os.stat(original_fullname).st_size
    except (KeyError, OSError):
        size = 0

    image_url = URL(
        c='images',
        f='download',
        args=creator[field],
    )

    thumb = URL(
        c='images',
        f='download',
        args=creator[field],
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

    return json.dumps(dict(files=image_attributes))


def images(creator):
    """Return a list of image names associated with the creator.

    Args:
        creator: Creator instance

    Returns:
        list of strings, list of image names. Eg of an image name:
            creator.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    image_names = []
    for field in db.creator.fields:
        if not hasattr(creator, field):
            continue
        if db.creator[field].type != 'upload':
            continue
        if not creator[field]:
            continue
        image_names.append(creator[field])
    return image_names


def on_change_name(creator):
    """Update creator record when name is changed.

    Args:
        creator: Creator instance
            the creator. The creator record is read.
    """
    if not creator:
        return

    db = current.app.db
    update_data = names(CreatorName(creator.name), fields=db.creator.fields)

    updated_creator = Creator.from_updated(creator, update_data)
    queue_search_prefetch()
    queue_create_sitemap()
    return updated_creator


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
    try:
        creator = Creator.from_key(dict(auth_user_id=form.vars.id))
    except LookupError:
        return

    on_change_name(creator)


def queue_update_indicia(creator):
    """Queue a job to update the indicia images for a creator.

    Args:
        creator: Creator instance

    Returns:
        Row instance representing the job created.
    """
    db = current.app.db
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


def rss_url(creator, **url_kwargs):
    """Return the url to the rss feed for all of creator's books.

    Args:
        creator: Creator instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast.rss
    """
    controller = '{name}.rss'.format(name=creator_name(creator, use='url'))

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=controller,
        f='index',
        **kwargs
    )


def short_url(creator):
    """Return a shortened url suitable for the creator page.

    Args:
        creator: Creator instance

    Returns:
        string, url, eg http://101.zco.mx
    """
    if not creator:
        return

    # Until SSL certs are available for subdomains, don't use SSL.
    return '{scheme}://{cid}.zco.mx'.format(
        # scheme=current.request.env.wsgi_url_scheme or 'https',
        scheme='http',
        cid=creator.id,
    )


def social_media_data(creator):
    """Return creator attributes for social media.

    Args:
        creator: Creator instance

    Returns:
        dict
    """
    if not creator:
        return {}

    db = current.app.db

    social_media = []           # (field, url) tuples
    social_media_fields = [
        'website',
        'twitter',
        'shop',
        'tumblr',
        'facebook',
    ]

    for field in social_media_fields:
        if creator[field]:
            anchor = db.creator[field].represent(
                creator[field], creator)
            value = anchor.attributes['_href']
            social_media.append((field, value))

    return {
        'name': creator.name,
        'name_for_search': creator_name(creator, use='search'),
        'name_for_url': creator_name(creator, use='url'),
        'short_url': short_url(creator),
        'social_media': social_media,
        'twitter': creator.twitter,
        'url': url(creator, host=SITE_NAME),
    }


def torrent_file_name(creator):
    """Return the name of the torrent file for the creator.

    Args:
        creator: Creator instance

    Returns:
        string, the file name.
    """
    fmt = '{name} ({url}).torrent'
    return fmt.format(
        name=creator_name(creator, use='file'),
        url='{cid}.zco.mx'.format(cid=creator.id),
    )


def torrent_link(creator, components=None, **attributes):
    """Return a link suitable for the torrent file of all of creator's books.

    Args:
        components: list, passed to A(*components),  default [torrent_name()]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

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


def torrent_url(creator, **url_kwargs):
    """Return the url to the torrent file for all of creator's books.

    Args:
        creator: Creator instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast_(123.zco.mx).torrent
    """
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


def url(creator, **url_kwargs):
    """Return a url suitable for the creator page.

    Args:
        creator: Creator instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}

    Returns:
        string, url, eg http://zco.mx/creators/index/Firstname_Lastname
            (routes_out should convert it to http://zco.mx/Firstname_Lastname)
    """
    name = creator_name(creator, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name], **kwargs)
