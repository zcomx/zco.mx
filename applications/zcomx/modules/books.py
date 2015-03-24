#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book classes and functions.
"""
import datetime
import logging
import os
import re
import string
import urlparse
from gluon import *
from gluon.dal.objects import REGEX_STORE_PATTERN
from gluon.storage import Storage
from gluon.validators import urlify
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name, \
    short_url as creator_short_url, \
    url_name as creator_url_name
from applications.zcomx.modules.files import TitleFileName
from applications.zcomx.modules.images import \
    ImgTag, \
    is_optimized, \
    queue_optimize
from applications.zcomx.modules.shell_utils import tthsum
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row


DEFAULT_BOOK_TYPE = 'one-shot'
LOG = logging.getLogger('app')


class BookEvent(object):
    """Class representing a loggable book event"""

    def __init__(self, book_entity, user_id):
        """Constructor

        Args:
            book_entity: Row instance or integer, if integer, this is the id of
                the book. The book record is read.
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        self.book_entity = book_entity
        self.book = entity_to_row(db.book, book_entity)
        self.user_id = user_id

    def _log(self, value=None):
        """Create a record representing a log of the event."""
        raise NotImplementedError

    def log(self, value=None):
        """Log event."""
        self._log(value=value)
        self._post_log()

    def _post_log(self):
        """Post log functionality."""
        raise NotImplementedError


class ContributionEvent(BookEvent):
    """Class representing a book contribution event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        event_id = db.contribution.insert(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        db.commit()
        return event_id

    def _post_log(self):
        """Post log functionality."""
        db = current.app.db
        update_rating(db, self.book, rating='contribution')


class DownloadEvent(BookEvent):
    """Class representing a book download event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def _log(self, value=None):
        if value is None:
            return
        # value is a download_click_entity
        db = current.app.db
        download_click = entity_to_row(db.download_click, value)
        if not download_click:
            LOG.error('download_click not found: %s', value)
            return

        event_id = db.download.insert(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            download_click_id=download_click.id,
        )
        db.commit()
        return event_id

    def _post_log(self):
        """Post log functionality."""
        # download event ratings are updated en masse.
        pass


class RatingEvent(BookEvent):
    """Class representing a book rating event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        event_id = db.rating.insert(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        db.commit()
        return event_id

    def _post_log(self):
        """Post log functionality."""
        db = current.app.db
        update_rating(db, self.book, rating='rating')


class ViewEvent(BookEvent):
    """Class representing a book view event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def _log(self, value=None):
        db = current.app.db
        event_id = db.book_view.insert(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now()
        )
        db.commit()
        return event_id

    def _post_log(self):
        """Post log functionality."""
        db = current.app.db
        update_rating(db, self.book, rating='view')


def book_page_for_json(db, book_page_id):
    r"""Return the book_page formated as json suitable for jquery-file-upload.

    Args:
        db: gluon.dal.DAL instance
        book_page_id: integer, the id of the book_page record

    Returns:
        dict, containing book_page data suitable for jquery-file-upload
            {
                "name": "picture1.jpg",
                "size": 902604,
                "url": "http:\/\/dom.org\/files\/picture1.jpg",
                "thumbnailUrl": "http:\/\/dom.org\/files\/thumbnail\/pic1.jpg",
                "deleteUrl": "http:\/\/dom.org\/files\/picture1.jpg",
                "deleteType": "DELETE"
            },
    """
    try:
        page = BookPage(book_page_id)
    except NotFoundError:
        return

    filename = page.upload_image().original_name()
    size = page.upload_image().size()

    down_url = URL(
        c='images',
        f='download',
        args=page.book_page.image,
    )

    thumb = URL(
        c='images',
        f='download',
        args=page.book_page.image,
        vars={'size': 'web'},
    )

    delete_url = URL(
        c='login',
        f='book_pages_handler',
        args=page.book_page.book_id,
        vars={'book_page_id': page.book_page.id},
    )

    return dict(
        book_id=page.book_page.book_id,
        book_page_id=page.book_page.id,
        name=filename,
        size=size,
        url=down_url,
        thumbnailUrl=thumb,
        deleteUrl=delete_url,
        deleteType='DELETE',
    )


def book_pages(book_entity):
    """Return a list of BookPage instances representing the pages in the book.

    Args:

    Returns:
        list of BookPage instances
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    pages = []
    query = (db.book_page.book_id == book_record.id)
    rows = db(query).select(orderby=[db.book_page.page_no, db.book_page.id])
    for page_entity in rows:
        pages.append(BookPage(page_entity))
    return pages


def book_pages_as_json(db, book_id, book_page_ids=None):
    """Return the book pages formated as json suitable for jquery-file-upload.

    Args:
        db: gluon.dal.DAL instance
        book_id: integer, the id of the book record
        book_page_ids: list of ids, integers of book_page records. By default
            all pages of book are returned. With this option only pages with
            ids in this list are returned.

    Returns:
        string, json formatted book_page data
            {'files': [
                {
                    ... see book_page_for_json ...
                },
            ]
            }

    """
    pages = []
    query = (db.book_page.book_id == book_id)
    if book_page_ids:
        query = query & (db.book_page.id.belongs(book_page_ids))
    records = db(query).select(db.book_page.id, orderby=db.book_page.page_no)
    for record in records:
        pages.append(book_page_for_json(db, record.id))
    return dumps(dict(files=pages))


def book_pages_years(book_entity):
    """Return a list of years for the pages of a book.

    The years can be used for copyright.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    query = (db.book_page.book_id == book_record.id)
    return sorted(set(
        [x.created_on.year for x in db(query).select(db.book_page.created_on)]
    ))


def book_tables():
    """Return a list of tables referencing books.

    Returns:
        list of strings, list of table names.
    """
    return [
        'book_page',
        'book_to_link',
        'book_view',
        'contribution',
        'derivative',
        'download',
        'publication_metadata',
        'publication_serial',
        'rating',
    ]


def book_types(db):
    """Return a XML instance representing book types suitable for
    an HTML radio button input.

    Args:
        db: gluon.dal.DAL instance
    """
    # {'value': record_id, 'text': description}, ...
    types = db(db.book_type).select(
        db.book_type.ALL,
        orderby=db.book_type.sequence
    )
    return XML(
        ','.join(
            [
                '{{"value":"{x.id}", "text":"{x.description}"}}'.format(x=x)
                for x in types
            ]
        )
    )


def by_attributes(attributes_list):
    """Return a Row instances representing a book matching the attributes.

    Args:
        attributes_list: list of dicts, dict of book attributes.

    Returns:
        Row instance representing a book.

    The book returned is the one that first matches a dict in the attributes
    list.
    """
    if not attributes_list:
        return
    for attributes in attributes_list:
        db = current.app.db
        queries = []
        for key, value in attributes.items():
            if value is not None:
                queries.append((db.book[key] == value))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        if not query:
            return
        book = db(query).select().first()
        if book:
            return book


def calc_contributions_remaining(db, book_entity):
    """Return the calculated contributions remaining for the book to reach
    its contributions target.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.

    Returns:
        float, dollar amount of contributions remaining.
    """
    book = entity_to_row(db.book, book_entity)
    if not book:
        return 0.00

    target = contributions_target(db, book)

    query = (db.contribution.book_id == book.id)
    total = db.contribution.amount.sum()
    rows = db(query).select(total)
    contributed_total = rows[0][total] if rows and rows[0][total] else 0.00

    remaining = target - contributed_total
    if remaining < 0:
        remaining = 0.00
    return remaining


def cbz_comment(book_entity):
    """ Return a comment suitable for the cbz file.


    Args:
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.

    Returns:
        string, eg '2014|Cartoonist Name|Title of Book|64'
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    creator_record = entity_to_row(db.creator, book_record.creator_id)
    if not creator_record:
        raise NotFoundError('Creator not found, {e}'.format(
            e=book_record.creator_id))

    fields = []
    fields.append(str(book_record.publication_year))
    fields.append(creator_formatted_name(creator_record))
    fields.append(book_record.name)
    fields.append(formatted_number(book_record))
    fields.append(creator_short_url(creator_record))
    return '|'.join(fields)


def cc_licence_data(book_entity):
    """Return data required for the cc licence for the book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    creator_record = entity_to_row(db.creator, book_record.creator_id)
    if not creator_record:
        raise NotFoundError('Creator not found, {e}'.format(
            e=book_record.creator_id))

    year_list = book_pages_years(book_record)
    if not year_list:
        year_list = [datetime.date.today().year]

    if len(year_list) == 1:
        years = str(year_list[0])
    else:
        years = '{f}-{l}'.format(f=year_list[0], l=year_list[-1])

    return dict(
        owner=creator_formatted_name(creator_record),
        owner_url=creator_short_url(creator_record),
        title=book_record.name,
        title_url=short_url(book_record),
        year=years,
        place=book_record.cc_licence_place,
    )


def contribute_link(db, book_entity, components=None, **attributes):
    """Return html code suitable for a 'Contribute' link.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
        components: list, passed to A(*components),  default ['Contribute']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    book = entity_to_row(db.book, book_entity)
    if not book:
        return empty

    if not components:
        components = ['Contribute']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='contributions',
            f='modal',
            vars=dict(book_id=book.id),
            extension=False
        )

    return A(*components, **kwargs)


def contributions_remaining_by_creator(db, creator_entity):
    """Return the calculated contributions remaining for all books of the
    creator.

    Args:
        db: gluon.dal.DAL instance
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator. The creator record is read.

    Returns:
        float, dollar amount of contributions remaining.
    """
    # invalid-name (C0103): *Invalid %%s name "%%s"*
    # pylint: disable=C0103
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        return 0.00

    query = (db.book.creator_id == creator.id) & \
            (db.book.status == True)

    total = 0
    books = db(query).select(db.book.ALL)
    for book in books:
        amount = calc_contributions_remaining(db, book)
        total = total + amount
    return total


def contributions_target(db, book_entity):
    """Return the contributions target for the book.


    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.

    Returns:
        float, dollar amount of contributions target.
    """
    rate_per_page = 10.00

    book = entity_to_row(db.book, book_entity)
    if not book:
        return 0.00

    page_count = db(db.book_page.book_id == book.id).count()
    amount = round(rate_per_page * page_count)
    return amount


def cover_image(db, book_entity, size='original', img_attributes=None):
    """Return html code suitable for the cover image.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        size: string, the size of the image. One of SIZES
        img_attributes: dict of attributes for IMG
    """
    try:
        first_page = get_page(book_entity, page_no='first')
    except NotFoundError:
        first_page = None

    image = first_page.image if first_page else None

    attributes = {'_alt': ''}

    if size == 'tbn':
        thumb_w = thumb_h = 170
        if not first_page:
            # Create a dummy book_page record
            first_page = Storage(
                thumb_w=thumb_w,
                thumb_h=thumb_h,
            )

        fmt = ' '.join([
            'width: {w}px;',
            'height: {h}px;',
            'margin: {pv}px {pr}px {pv}px {pl}px;',
        ])
        width = first_page.thumb_w
        height = first_page.thumb_h
        padding_vertical = (thumb_h - height) / 2
        if padding_vertical < 0:
            padding_vertical = 0
        attributes['_style'] = fmt.format(
            w=width,
            h=height,
            pl=0,
            pr=0,
            pv=padding_vertical,
        )

    if img_attributes:
        attributes.update(img_attributes)

    return ImgTag(image, size=size, attributes=attributes)()


def default_contribute_amount(db, book_entity):
    """Return the default amount for the contribute widget.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    minimum = 1
    maximum = 20
    rate_per_page = 1.0 / 20

    book = entity_to_row(db.book, book_entity)

    page_count = db(db.book_page.book_id == book.id).count()
    amount = round(rate_per_page * page_count)
    if amount < minimum:
        amount = minimum
    if amount > maximum:
        amount = maximum
    return amount


def defaults(db, name, creator_entity):
    """Return a dict representing default values for a book.

    Args:
        db: gluon.dal.DAL instance
        name: string, name of book
        creator_entity: Row instance or integer, if integer, this is the id of
            the creator record.

    Returns:
        dict: representing book fields and values.
    """
    data = {}
    creator = entity_to_row(db.creator, creator_entity)
    if not creator:
        return {}

    data['creator_id'] = creator.id

    # Check if a book with the same name exists.
    query = (db.book.creator_id == creator.id) & (db.book.name == name)
    orderby = ~db.book.number
    book = db(query).select(db.book.ALL, orderby=orderby).first()
    if book:
        data['book_type_id'] = book.book_type_id
        data['number'] = book.number + 1                # Must be unique
        data['of_number'] = book.of_number
    else:
        book_type_record = db(db.book_type.name == DEFAULT_BOOK_TYPE).select(
            db.book_type.ALL).first()
        if book_type_record:
            data['book_type_id'] = book_type_record.id
    data['urlify_name'] = urlify(name, maxlen=99999)
    return data


def download_link(db, book_entity, components=None, **attributes):
    """Return html code suitable for a 'Download' link.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
        components: list, passed to A(*components),  default ['Download']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    book = entity_to_row(db.book, book_entity)
    if not book:
        return empty
    if not book.cbz or not book.torrent:
        return empty

    if not components:
        components = ['Download']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='downloads',
            f='modal',
            args=[book.id],
            extension=False
        )

    return A(*components, **kwargs)


def formatted_name(db, book_entity, include_publication_year=True):
    """Return the formatted name of the book

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
        include_publication_year: If True, the publication year is included in
            the name.
    """
    book = entity_to_row(db.book, book_entity)
    if not book:
        return ''

    fmt = '{name}'
    data = {
        'name': book.name,
    }

    number = formatted_number(book_entity)
    if number:
        fmt = '{name} {num}'
        data['num'] = number

    if include_publication_year:
        fmt = ' '.join([fmt, '({year})'])
        data['year'] = book.publication_year
    return fmt.format(**data)


def formatted_number(book_entity):
    """Return the number of the book formatted.

    Args:
        book_entity: Row instance or integer representing a book.
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        return ''
    book_type = entity_to_row(db.book_type, book.book_type_id)
    if not book_type:
        return ''

    if book_type.name == 'one-shot':
        return ''
    elif book_type.name == 'ongoing':
        return '{num:03d}'.format(num=book.number)
    elif book_type.name == 'mini-series':
        return '{num:02d} (of {of:02d})'.format(
            num=book.number,
            of=book.of_number,
        )
    return ''


def get_page(book_entity, page_no=1):
    """Return a page of a book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        page_no: integer or string, if integer, the book_page record with
            page_no matching is returned.
            The following strings are acceptable.
            'first': equivalent to page_no=1
            'last': returns the last page in book (excluding indicia)
            'indicia': returns a dummy page representing the indicia
                    id: None
                    book_id: id of book
                    page_no: last page page_no + 1
                    image: None

    Returns:
        Row instance representing a book_page.
    Raises:
        NotFoundError, if book_entity doesn't match a book, or book doesn't
            have a page associated with the provided page_no value.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    want_page_no = None
    if page_no == 'first':
        want_page_no = 1
    elif page_no in ['last', 'indicia']:
        page_max = db.book_page.page_no.max()
        query = (db.book_page.book_id == book_record.id)
        want_page_no = db(query).select(page_max)[0][page_max]
    else:
        try:
            want_page_no = int(page_no)
        except (TypeError, ValueError):
            want_page_no = None
    if want_page_no is None:
        raise NotFoundError('Book id {b}, page not found, {p}'.format(
            b=book_record.id, p=page_no))

    query = (db.book_page.book_id == book_record.id) & \
            (db.book_page.page_no == want_page_no)
    book_page = db(query).select(db.book_page.ALL, limitby=(0, 1)).first()
    if not book_page:
        raise NotFoundError('Book id {b}, page not found, {p}'.format(
            b=book_record.id, p=page_no))

    if page_no == 'indicia':
        book_page.id = None
        book_page.image = None
        book_page.page_no = book_page.page_no + 1

    return book_page


def magnet_link(book_entity, components=None, **attributes):
    """Return a link suitable for the magnet for a book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        components: list, passed to A(*components),  default [torrent_name()]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, id: {e}'.format(
            e=book_entity))

    link_url = magnet_uri(book)
    if not link_url:
        return empty

    if not components:
        u_name = url_name(book_entity)
        if not u_name:
            return
        name = '{n}.magnet'.format(n=u_name).lower()
        components = [name]

    kwargs = {
        '_data-record_table': 'book',
        '_data-record_id': str(book.id),
        '_class': 'log_download_link',
    }
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def magnet_uri(book_entity):
    """Create a magnet uri for a book.

    Args:
        book_entity: Row instance or integer representing a book record.

    Returns:
        str, the magnet uri,
        eg: 'magnet:?xt=urn:tree:tiger:UY...SD&xl=2604758&dn=My+Book+(2013).cbz
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book or not book.cbz:
        return

    tthsum_hash = tthsum(book.cbz)
    filename = os.path.basename(book.cbz)
    filesize = os.stat(book.cbz).st_size
    fmt = 'magnet:?xt=urn:tree:tiger:{tthsum}&xl={size}&dn={name}'
    return fmt.format(
        name=filename,
        size=filesize,
        tthsum=tthsum_hash,
    )


def numbers_for_book_type(db, book_type_id):
    """Return a dict for the number settings for a book_type_id.

    Args:
        db: gluon.dal.DAL instance
        book_type_id: integer, id of book_type record
    """
    default = {'number': False, 'of_number': False}
    query = (db.book_type.id == book_type_id)
    book_type = db(query).select(db.book_type.ALL).first()
    if not book_type:
        return default
    elif book_type.name == 'ongoing':
        return {'number': True, 'of_number': False}
    elif book_type.name == 'mini-series':
        return {'number': True, 'of_number': True}
    else:
        return default


def optimize_images(
        book_entity,
        priority='optimize_img',
        job_options=None,
        cli_options=None):
    """Optimize all images related to a book.

    Args:
        book_entity: Row instance or integer representing a book.
        priority: string, priority key, one of PROIRITIES
        job_options: dict, job record attributes used for JobQueuer property
        cli_options: dict, options for job command
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    jobs = []

    for field in db.book.fields:
        if db.book[field].type != 'upload' or not book[field]:
            continue
        jobs.append(
            queue_optimize(
                book[field],
                priority=priority,
                job_options=job_options,
                cli_options=cli_options
            )
        )

    query = (db.book_page.book_id == book.id)
    for book_page in db(query).select():
        for field in db.book_page.fields:
            if db.book_page[field].type != 'upload' or not book_page[field]:
                continue
            jobs.append(
                queue_optimize(
                    book_page[field],
                    priority=priority,
                    job_options=job_options,
                    cli_options=cli_options
                )
            )

    return jobs


def orientation(book_page_entity):
    """Return the orientation of the book page.

    Args:
        book_page_entity: Row instance or integer, if integer, this is the id
            of the book_page. The book_page record is read.
    """
    page = BookPage(book_page_entity)
    if not page.book_page.image:
        raise NotFoundError('Book page has no image, book_page.id {i}'.format(
            i=page.book_page.id))

    return page.upload_image().orientation()


def page_url(book_page_entity, reader=None, **url_kwargs):
    """Return a url suitable for the reader webpage of a book page.

    Args:
        book_page_entity: Row instance or integer, if integer, this is the id
            of the book_page. The book_page record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url,
            eg http://zco.mx/creators/index/First_Last/My_Book_(2014)/002
            (routes_out should convert it to
            http://zco.mx/First_Last/My_Book_(2014))/002
    """
    db = current.app.db
    page_record = entity_to_row(db.book_page, book_page_entity)
    if not page_record:
        return

    book_record = entity_to_row(db.book, page_record.book_id)
    if not book_record:
        return

    creator_name = creator_url_name(book_record.creator_id)
    if not creator_name:
        return

    book_name = url_name(book_record)
    if not book_name:
        return

    page_name = '{p:03d}'.format(p=page_record.page_no)

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c='creators',
        f='index',
        args=[creator_name, book_name, page_name],
        vars={'reader': reader} if reader else None,
        **kwargs
    )


def parse_url_name(name, default=None):
    """Parse a book url name and return book attributes.

    Args:
        name: string, name of book used in url (ie what is returned by
                def url_name()
        default: dict of default values for attrubutes in returned dicts

    Returns
        list of dict of book attributes.
            eg [{
                    name: Name
                    book_type_id: 1,
                    number: 1,
                    of_number: 4,
                }]
    """
    if not name:
        return

    books = []

    start = dict(
        name=None,
        number=None,
        of_number=None,
        book_type_id=None,
    )

    if default:
        start.update(default)

    db = current.app.db

    type_id_by_name = {}
    for t in db(db.book_type).select():
        type_id_by_name[t.name] = t.id

    # line-too-long (C0301): *Line too long (%%s/%%s)*
    # pylint: disable=C0301
    type_res = {
        'mini-series': re.compile(r'(?P<name>.*)_(?P<number>[0-9]+)_\(of_(?P<of_number>[0-9]+)\)$'),
        'one-shot': re.compile(r'(?P<name>.*?)$'),
        'ongoing': re.compile(r'(?P<name>.*)_(?P<number>[0-9]+)$'),
    }

    # Test in order most-complex to least.
    for book_type in ['mini-series', 'ongoing', 'one-shot']:
        book = dict(start)
        m = type_res[book_type].match(name)
        if not m:
            continue
        book.update(m.groupdict())
        book['book_type_id'] = type_id_by_name[book_type]
        if book['name']:
            book['name'] = book['name'].replace('_', ' ')
        for field in ['number', 'of_number']:
            if book[field]:
                try:
                    book[field] = int(book[field])
                except (TypeError, ValueError):
                    book[field] = None
        books.append(book)
    return books


def publication_year_range():
    """Return a tuple representing the start and end range of publication years
    """
    return (1970, datetime.date.today().year + 5)


def publication_years():
    """Return a XML instance representing publication years suitable for
    drop down menu.
    """
    # {'value': '1970', 'text': '1970'}, ...
    return XML(
        ','.join(
            [
                '{{"value":"{x}", "text":"{x}"}}'.format(x=x)
                for x in range(*publication_year_range())
            ]
        )
    )


def read_link(db, book_entity, components=None, **attributes):
    """Return html code suitable for a 'Read' link.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
        components: list, passed to A(*components),  default ['Read']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    book = entity_to_row(db.book, book_entity)
    if not book:
        return empty

    try:
        first_page = get_page(book, page_no='first')
    except NotFoundError:
        return empty

    if not components:
        components = ['Read']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = page_url(first_page, extension=False)

    return A(*components, **kwargs)


def release_barriers(book_entity):
    """Return a list of barriers preventing the release of a book.

    Args:
        book_entity: Row instance or integer representing a book record.

    Returns:
        list of dicts (barriers). A barrier dict has the following format.
            {
                'code': 'reason_code',
                'reason': 'The reason the book cannot be released.',
                'description': 'A longer description of the reason.',
                'fixes': [
                    'Step 1 to fix problem',
                    'Step 2 to fix problem',
                    ...
                ]
            }
        The description is optional.
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    barriers = []

    pages = book_pages(book_entity)

    # Book has no name
    if not book.name:
        barriers.append({
            'code': 'no_name',
            'reason': 'The book has no name.',
            'description': (
                'Cbz and torrent files are named after the book name. '
                'Without a name these files cannot be created.'
            ),
            'fixes': [
                'Edit the book and set the name.',
            ]
        })

    # Book has no pages
    if len(pages) == 0:
        barriers.append({
            'code': 'no_pages',
            'reason': 'The book has no pages.',
            'fixes': [
                'Upload images to create pages for the book.',
            ]
        })

    # Another book already exists with same name
    query = (db.book.creator_id == book.creator_id) & \
            (db.book.name == book.name) & \
            (db.book.book_type_id != book.book_type_id) & \
            (db.book.release_date != None) & \
            (db.book.id != book.id)
    if db(query).count() > 0:
        barriers.append({
            'code': 'dupe_name',
            'reason': 'You already released a book with the same name.',
            'description': (
                'Cbz and torrent files are named after the book name. '
                'The name of the book must be unique.'
            ),
            'fixes': [
                'Modify the name of the book to make it unique.',
                'If this is a duplicate, delete the book.',
            ]
        })

    # Another book already exists with same name/number
    query = (db.book.creator_id == book.creator_id) & \
            (db.book.name == book.name) & \
            (db.book.book_type_id == book.book_type_id) & \
            (db.book.number == book.number) & \
            (db.book.release_date != None) & \
            (db.book.id != book.id)
    if db(query).count() > 0:
        barriers.append({
            'code': 'dupe_number',
            'reason':
                'You already released a book with the same name and number.',
            'description': (
                'Cbz and torrent files are named after the book name. '
                'The name/number of the book must be unique.'
            ),
            'fixes': [
                (
                    'Verify the number of the book is correct. '
                    'Possibly it needs to be incremented.'
                ),
                'If this is a duplicate, delete the book.',
            ]
        })

    # Licence is not set
    if not book.cc_licence_id:
        barriers.append({
            'code': 'no_licence',
            'reason': 'No licence has been selected for the book.',
            'description': (
                'Books released on zco.mx '
                'are published on public file sharing networks. '
                'A licence must be set indicating permission to do this.'
            ),
            'fixes': [
                'Edit the book and set the licence.',
            ]
        })

    # Licence is 'All Rights Reserved'
    arr = db(db.cc_licence.code == 'All Rights Reserved').select().first()
    if arr and arr.id and book.cc_licence_id == arr.id:
        barriers.append({
            'code': 'licence_arr',
            'reason':
                "The licence on the book is set to 'All Rights Reserved'.",
            'description': (
                'Books released on zco.mx '
                'are published on public file sharing networks. '
                'This is not permitted if the licence is '
                '"All Rights Reserved".'
            ),
            'fixes': [
                'Edit the book and change the licence.',
            ]
        })

    # Publication metadata is not set
    metadata = db(db.publication_metadata.book_id == book.id).select().first()
    if not metadata:
        barriers.append({
            'code': 'no_metadata',
            'reason':
                "The publication metadata has not been set for the book.",
            'description': (
                'Books released on zco.mx include an indicia page. '
                'The page has a paragraph outlining '
                'the publication history of the book.'
                'The publication metadata has to be set '
                'to create this paragraph.'
            ),
            'fixes': [
                'Edit the book and set the publication metadata.',
            ]
        })

    # Images are wide enough.
    if pages:
        small_images = []
        min_width = BookPage.min_cbz_width
        for page in pages:
            dims = page.upload_image().dimensions(size='cbz')
            if not dims:
                dims = page.upload_image().dimensions(size='original')
            width, unused_h = dims
            if width < min_width:
                original_name = page.upload_image().original_name()
                small_images.append(
                    '{n} (width: {w} px)'.format(n=original_name, w=width)
                )
        if small_images:
            fixes = [
                'Replace the following images with larger copies.',
            ]
            fixes.extend(small_images)
            barriers.append({
                'code': 'images_too_narrow',
                'reason':
                'Some images are not large enough. Min width: {w} px'.format(
                    w=min_width),
                'description': (
                    'Released books are packaged for CBZ viewers.'
                    'In order for book page images to display '
                    'at a reasonable resolution, images must be '
                    'a minimum pixels wide.'
                ),
                'fixes': fixes
            })

    return barriers


def release_link(book_entity, components=None, **attributes):
    """Return html code suitable for a 'Release' link or button.

    Args:
        book_entity: Row instance or integer representing a book record.
        components: list, passed to A(*components),  default ['Release']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        return empty

    if not components:
        if book.releasing:
            components = ['Release (in progress)']
        else:
            components = ['Release']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='login', f='book_release', args=book.id, extension=False)

    if book.releasing:
        if '_class' not in attributes:
            kwargs['_class'] = 'disabled'
        else:
            kwargs['_class'] = ' '.join([kwargs['_class'], 'disabled'])

    return A(*components, **kwargs)


def short_page_img_url(book_page_entity):
    """Return a short url for the book page image.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
    Returns:
        string, url, eg http://101.zco.mx/My_Book/001.jpg
    """
    db = current.app.db
    page_record = entity_to_row(db.book_page, book_page_entity)
    if not page_record:
        return

    book_page_url = short_page_url(page_record)
    if not book_page_url:
        return

    m = REGEX_STORE_PATTERN.search(page_record.image or '')
    extension = m and m.group('e') or ''
    if not extension:
        return book_page_url
    return '.'.join([book_page_url, extension])


def short_page_url(book_page_entity):
    """Return a short url for the book page.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
    Returns:
        string, url, eg http://101.zco.mx/My_Book/001
    """
    db = current.app.db
    page_record = entity_to_row(db.book_page, book_page_entity)
    if not page_record:
        return

    book_url = short_url(page_record.book_id)
    if not book_url:
        return
    page_name = '{p:03d}'.format(p=page_record.page_no)
    return '/'.join([book_url.rstrip('/'), page_name])


def short_url(book_entity):
    """Return a short url for the book webpage.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
    Returns:
        string, url, eg http://101.zco.mx/My_Book_(2014)
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record or not book_record.name:
        return

    name = url_name(book_entity)
    if not name:
        return

    url_for_creator = creator_short_url(book_record.creator_id)
    if not url_for_creator:
        return

    return urlparse.urljoin(url_for_creator, name)


def torrent_file_name(book_entity):
    """Return the name of the torrent file for the book.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        string, the file name.
    """
    db = current.app.db

    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=book_entity))

    fmt = '{name} ({cid}.zco.mx).cbz.torrent'
    return fmt.format(
        name=TitleFileName(formatted_name(db, book_record)).scrubbed(),
        cid=book_record.creator_id,
    )


def torrent_link(book_entity, components=None, **attributes):
    """Return a link suitable for the torrent file of a book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        components: list, passed to A(*components),  default [torrent_name()]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, id: {e}'.format(
            e=book_entity))

    link_url = torrent_url(book)
    if not link_url:
        return empty

    if not components:
        u_name = url_name(book_entity)
        if not u_name:
            return
        name = '{n}.torrent'.format(n=u_name).lower()
        components = [name]

    kwargs = {
        '_data-record_table': 'book',
        '_data-record_id': str(book.id),
        '_class': 'log_download_link',
    }
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def torrent_url(book_entity, **url_kwargs):
    """Return the url to the torrent file for the book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/torrents/route/My Book 001 (123.zco.mx).torrent
            routes_out should convert it to
                http://zco.mx/My Book 001 (123.zco.mx).torrent)
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Creator not found, id: {e}'.format(
            e=book_entity))

    creator_name = creator_url_name(book_record.creator_id)
    if not creator_name:
        return

    name = url_name(book_record)
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=creator_name,
        f='{name}.torrent'.format(name=name),
        **kwargs
    )


def unoptimized_images(book_entity):
    """Return a list of unoptimized images related to a book.

    Images are deemed unoptimized if there is no optimize_img_log record
    indicating it has been optimized.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        list of strings, [image_name_1, image_name_2, ...]
            eg image name: book_page.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    unoptimals = []

    for field in db.book.fields:
        if db.book[field].type != 'upload':
            continue
        if not book[field]:
            continue
        if not is_optimized(book[field]):
            unoptimals.append(book[field])

    query = (db.book_page.book_id == book.id)
    for book_page in db(query).select():
        for field in db.book_page.fields:
            if db.book_page[field].type != 'upload':
                continue
            if not book_page[field]:
                continue
            if not is_optimized(book_page[field]):
                unoptimals.append(book_page[field])

    return unoptimals


def update_contributions_remaining(db, book_entity):
    """Update the contributions_remaining for the creator of the book.

    Args
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        return

    db(db.book.id == book_record.id).update(
        contributions_remaining=calc_contributions_remaining(db, book_record)
    )
    db.commit()

    if not book_record.creator_id:
        return

    creator_record = entity_to_row(db.creator, book_record.creator_id)
    if not creator_record:
        return

    total = contributions_remaining_by_creator(db, creator_record)
    if creator_record.contributions_remaining != total:
        creator_record.update_record(
            contributions_remaining=total
        )
        db.commit()


def update_rating(db, book_entity, rating=None):
    """Update an accumulated rating for a book.

    Args
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
        rating: string, one of 'contribution', 'rating', 'view'. If None,
                all ratings are updated.
    """
    ratings_data = {
        'contribution': [
            # (book field, data field, function, format)
            (db.book.contributions, db.contribution.amount, 'sum'),
        ],
        'download': [
            (db.book.downloads, db.download.id, 'count'),
        ],
        'rating': [
            (db.book.rating, db.rating.amount, 'avg'),
        ],
        'view': [
            (db.book.views, db.book_view.id, 'count'),
        ],
    }

    if rating is not None and rating not in ratings_data.keys():
        raise SyntaxError('Invalid rating: {r}'.format(r=rating))

    ratings = [rating] if rating is not None else ratings_data.keys()

    rating_data = []
    for r in ratings:
        rating_data.extend(ratings_data[r])

    book = entity_to_row(db.book, book_entity)
    if not book:
        return

    query = (db.book.id == book.id)
    for field, data_field, func in rating_data:
        data_table = data_field.table
        if func == 'sum':
            tally = data_field.sum()
        elif func == 'avg':
            tally = data_field.avg()
        elif func == 'count':
            tally = data_field.count()
        rows = db(query).select(
            tally,
            left=[data_table.on(data_table.book_id == db.book.id)],
            groupby=data_table.book_id
        ).first()
        value = rows[tally] or 0 if rows else 0
        db(db.book.id == book.id).update(**{field.name: value})
    db.commit()

    if rating is None or rating == 'contribution':
        update_contributions_remaining(db, book)


def url(book_entity, **url_kwargs):
    """Return a url suitable for the book webpage.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg http://zco.mx/creators/index/First_Last/My_Book_(2014)
            (routes_out should convert it to
            http://zco.mx/First_Last/My_Book_(2014))
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record or not book_record.name:
        return

    creator_name = creator_url_name(book_record.creator_id)
    if not creator_name:
        return

    name = url_name(book_record)
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[creator_name, name], **kwargs)


def url_name(book_entity):
    """Return the name used for the book in the url.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
    Returns:
        string, eg My_Book
    """
    if not book_entity:
        return

    db = current.app.db

    book_record = entity_to_row(db.book, book_entity)
    if not book_record or not book_record.name:
        return

    def as_camelcase(text):
        """Convert text to camelcase."""
        # Replace punctuation with space
        # Uppercase first letter of each word.
        # Join with no spaces.
        # Scrub for file use.
        replace_punctuation = string.maketrans(
            string.punctuation, ' ' * len(string.punctuation))
        text = text.translate(replace_punctuation)
        words = [x[0].upper() + x[1:] for x in text.split() if x]
        return TitleFileName(''.join(words)).scrubbed()

    # Strategy.
    # Goal: CamelCase with punctuation removed, separate number with hyphen
    fmt = '{name}'
    data = {
        'name': as_camelcase(str(book_record.name))
    }

    number = formatted_number(book_record)
    if number:
        fmt = '{name}-{num}'
        data['num'] = as_camelcase(number).lower()
    return fmt.format(**data)
