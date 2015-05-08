#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book classes and functions.
"""
import datetime
import logging
import os
import urlparse
from gluon import *
from gluon.dal.objects import REGEX_STORE_PATTERN
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import \
    from_id as book_type_from_id
from applications.zcomx.modules.creators import \
    creator_name, \
    formatted_name as creator_formatted_name, \
    short_url as creator_short_url
from applications.zcomx.modules.images import \
    CachedImgTag, \
    ImageDescriptor
from applications.zcomx.modules.names import \
    BookName, \
    BookNumber, \
    BookTitle, \
    names as name_values
from applications.zcomx.modules.shell_utils import tthsum
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row
from applications.zcomx.modules.zco import \
    BOOK_STATUSES, \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT, \
    SITE_NAME


DEFAULT_BOOK_TYPE = 'one-shot'
LOG = logging.getLogger('app')

class BaseEvent(object):
    """Base class representing a loggable event"""

    def __init__(self, user_id):
        """Constructor

        Args:
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
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


class BookEvent(BaseEvent):
    """Class representing a loggable book event"""

    def __init__(self, book_entity, user_id):
        """Constructor

        Args:
            book_entity: Row instance or integer, if integer, this is the id of
                the book. The book record is read.
            user_id: integer, id of user triggering event.
        """
        super(BookEvent, self).__init__(user_id)
        db = current.app.db
        self.book_entity = book_entity
        self.book = entity_to_row(db.book, book_entity)

    def _log(self, value=None):
        raise NotImplementedError

    def _post_log(self):
        raise NotImplementedError


class ContributionEvent(BookEvent):
    """Class representing a book contribution event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.contribution.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(db, self.book, rating='contribution')


class DownloadEvent(BookEvent):
    """Class representing a book download event."""

    def _log(self, value=None):
        if value is None:
            return
        # value is a download_click_entity
        db = current.app.db
        download_click = entity_to_row(db.download_click, value)
        if not download_click:
            LOG.error('download_click not found: %s', value)
            return

        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            download_click_id=download_click.id,
        )
        event_id = db.download.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        # download event ratings are updated en masse.
        pass


class RatingEvent(BookEvent):
    """Class representing a book rating event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.rating.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(db, self.book, rating='rating')


class ViewEvent(BookEvent):
    """Class representing a book view event."""

    def _log(self, value=None):
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now()
        )
        event_id = db.book_view.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(db, self.book, rating='view')


class ZcoContributionEvent(BaseEvent):
    """Class representing a contribution to zco.mx event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=0,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.contribution.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        pass


def book_name(book_entity, use='file'):
    """Return the name of the book suitable for specified use.

    Args:
        book_entity: Row instance or integer representing a book.
        use: one of 'file', 'search', 'url'

    Returns:
        string, name of file
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))
    if use == 'file':
        return names(book.as_dict())['name_for_file']
    elif use == 'search':
        return book.name_for_search
    elif use == 'url':
        return book.name_for_url
    return


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
    size = ImageDescriptor(page.upload_image().fullname()).size_bytes()

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


def calc_status(book_entity):
    """Determine the calculated status of the book.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        string, the status of a book, eg BOOK_STATUS_ACTIVE
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    if book_record.status == BOOK_STATUS_DISABLED:
        return BOOK_STATUS_DISABLED

    page_count = db(db.book_page.book_id == book_record.id).count()
    return BOOK_STATUS_ACTIVE if page_count > 0 else BOOK_STATUS_DRAFT


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

    cc_licence = entity_to_row(db.cc_licence, book_record.cc_licence_id)
    if not cc_licence:
        raise NotFoundError('Cc licence not found, {e}'.format(
            e=book_record.cc_licence_id))

    fields = []
    fields.append(str(book_record.publication_year))
    fields.append(creator_formatted_name(creator_record))
    fields.append(book_record.name)
    fields.append(formatted_number(book_record))
    fields.append(cc_licence.code)
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
            (db.book.status == BOOK_STATUS_ACTIVE)

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

    if img_attributes:
        attributes.update(img_attributes)

    return CachedImgTag(image, size=size, attributes=attributes)()


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
    data['name'] = name

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
        data['number'] = 1
        data['of_number'] = 1
    data.update(names(data, fields=db.book.fields))
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
    book_type = book_type_from_id(book.book_type_id)
    return book_type.formatted_number(book.number, book.of_number)


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


def html_metadata(book_entity):
    """Return book attributes for HTML metadata.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        dict
    """
    if not book_entity:
        return {}

    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    creator_record = entity_to_row(db.creator, book_record.creator_id)
    if not creator_record:
        raise NotFoundError('Creator not found, {e}'.format(
            e=book_record.creator_id))

    try:
        first_page = get_page(book_entity, page_no='first')
    except NotFoundError:
        first_page = None

    image_url = None
    if first_page:
        image_url = URL(
            c='images',
            f='download',
            args=first_page.image,
            vars={'size': 'web'},
            host=True,
        )

    return {
        'creator_name': creator_formatted_name(creator_record),
        'creator_twitter': creator_record.twitter,
        'description': book_record.description,
        'image_url': image_url,
        'name': formatted_name(db, book_record, include_publication_year=True),
        'type': 'book',
        'url': url(book_record, host=True),
    }


def images(book_entity):
    """Return a list of image names associated with the book.

    This includes images associated with the book and any of the book
    pages.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        list of strings, list of image names. Eg of an image name:
            book_page.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    image_names = []

    for field in db.book.fields:
        if db.book[field].type != 'upload':
            continue
        if not book[field]:
            continue
        image_names.append(book[field])

    for page in book_pages(book):
        for field in db.book_page.fields:
            if db.book_page[field].type != 'upload':
                continue
            if not page.book_page[field]:
                continue
            image_names.append(page.book_page[field])

    return image_names


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
        name = '{n}.magnet'.format(
            n=book_name(book_entity, use='url').lower()
        )
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


def name_fields():
    """Return a list of book fields associated with book names.

    When these fields change, book names need to be updated.

    Returns:
        list of strings, field names
    """
    return [
        'name',
        'book_type_id',
        'number',
        'of_number',
    ]


def names(book, fields=None):
    """Return a dict of name variations suitable for the book db record.

    Args:
        book: dict representing book with mininum keys
            'name', 'book_type_id', 'number', 'of_number'
        fields: list, passed to names(..., fields=fields)

    Returns:
        dict. See names.py names.

    Usage:
        names(book_record.as_dict(), db.book.fields)
    """
    book_type = book_type_from_id(book['book_type_id'])
    number = book_type.formatted_number(book['number'], book['of_number'])
    return name_values(
        BookTitle(
            BookName(book['name']),
            BookNumber(number)
        ),
        fields=fields
    )


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

    return ImageDescriptor(page.upload_image().fullname()).orientation()


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

    name_of_creator = creator_name(book_record.creator_id, use='url')
    if not name_of_creator:
        return

    books_name = book_name(book_record, use='url')
    if not books_name:
        return

    page_name = '{p:03d}'.format(p=page_record.page_no)

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c='creators',
        f='index',
        args=[name_of_creator, books_name, page_name],
        vars={'reader': reader} if reader else None,
        **kwargs
    )


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


def set_status(book_entity, status):
    """Set the status of a book.

    Args:
        book_entity: Row instance or integer representing a book.
        status: string, the status of a book.

    Raises:
        NotFoundError, if book_entity doesn't represent a book on file.
        ValueError, if the status is invalid.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    if status not in BOOK_STATUSES:
        raise ValueError('Invalid status {s}'.format(s=status))

    if book_record.status != status:
        book_record.update_record(status=status)
        db.commit()


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
    if not book_record:
        return

    name = book_name(book_entity, use='url')
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

    fmt = '{name} ({year}) ({cid}.zco.mx).cbz.torrent'
    return fmt.format(
        name=book_name(book_record, use='file'),
        year=str(book_record.publication_year),
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
        name = '{n}.torrent'.format(
            n=book_name(book_entity, use='url').lower()
        )
        components = [name]

    kwargs = {}
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

    name_of_creator = creator_name(book_record.creator_id, use='url')
    if not name_of_creator:
        return

    name = book_name(book_record, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.torrent'.format(name=name),
        **kwargs
    )


def tumblr_data(book_entity):
    """Return book attributes for tumblr data.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        dict
    """
    if not book_entity:
        return {}

    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise NotFoundError('Book not found, {e}'.format(e=book_entity))

    try:
        first_page = get_page(book_entity, page_no='first')
    except NotFoundError:
        first_page = None

    first_page_image = first_page.image if first_page else None

    download_url = None
    if first_page:
        download_url = URL(
            c='images',
            f='download',
            args=first_page.image,
            vars={'size': 'web'},
            host=SITE_NAME,
        )

    return {
        'cover_image_name': first_page_image,
        'description': book_record.description,
        'download_url': download_url,
        'formatted_name': formatted_name(
            db, book_record, include_publication_year=True),
        'formatted_name_no_year': formatted_name(
            db, book_record, include_publication_year=False),
        'formatted_number': formatted_number(book_record),
        'name': book_record.name,
        'name_camelcase': BookName(book_record.name).for_url(),
        'name_for_search': book_name(book_record, use='search'),
        'short_url': short_url(book_record),
        'url': url(book_record, host=SITE_NAME),
    }


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
        creator_record.update_record(contributions_remaining=total)
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

    name_of_creator = creator_name(book_record.creator_id, use='url')
    if not name_of_creator:
        return

    name = book_name(book_record, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name_of_creator, name], **kwargs)
