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
from pydal.helpers.regex import REGEX_STORE_PATTERN
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.book_types import BookType
from applications.zcomx.modules.cc_licences import CCLicence
from applications.zcomx.modules.creators import \
    Creator, \
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
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.shell_utils import tthsum
from applications.zcomx.modules.utils import entity_to_row
from applications.zcomx.modules.zco import \
    BOOK_STATUSES, \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT, \
    SITE_NAME


DEFAULT_BOOK_TYPE = 'one-shot'
LOG = logging.getLogger('app')


class Book(Record):
    """Class representing a book record."""
    db_table = 'book'


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
        raise LookupError('Book not found, {e}'.format(e=book_entity))
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
        page = BookPage.from_id(book_page_id)
    except LookupError:
        return

    filename = page.upload_image().original_name()
    size = ImageDescriptor(page.upload_image().fullname()).size_bytes()

    down_url = URL(
        c='images',
        f='download',
        args=page.image,
    )

    thumb = URL(
        c='images',
        f='download',
        args=page.image,
        vars={'size': 'web'},
    )

    delete_url = URL(
        c='login',
        f='book_pages_handler',
        args=page.book_id,
        vars={'book_page_id': page.id},
    )

    return dict(
        book_id=page.book_id,
        book_page_id=page.id,
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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    pages = []
    query = (db.book_page.book_id == book_record.id)
    ids = db(query).select(
        db.book_page.id,
        orderby=[db.book_page.page_no, db.book_page.id]
    )
    for page_id in ids:
        pages.append(BookPage.from_id(page_id))
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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

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
        'activity_log',
        'tentative_activity_log',
        'book_page',
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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    creator = Creator.from_id(book_record.creator_id)
    cc_licence = CCLicence.from_id(book_record.cc_licence_id)

    fields = []
    fields.append(str(book_record.publication_year))
    fields.append(creator_formatted_name(creator))
    fields.append(book_record.name)
    fields.append(formatted_number(book_record))
    fields.append(cc_licence.code)
    fields.append(creator_short_url(creator))
    return '|'.join(fields)


def cbz_link(book_entity, components=None, **attributes):
    """Return a link suitable for the cbz file of a book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        components: list, passed to A(*components), default [book.name_for_url]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise LookupError('Book not found, id: {e}'.format(
            e=book_entity))

    link_url = cbz_url(book)
    if not link_url:
        return empty

    if not components:
        name = '{n}.cbz'.format(
            n=book_name(book_entity, use='url').lower()
        )
        components = [name]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def cbz_url(book_entity, **url_kwargs):
    """Return the url to the cbz file for the book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast/MyBook-001.cbz
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Creator not found, id: {e}'.format(
            e=book_entity))

    creator = Creator.from_id(book_record.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book_record, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.cbz'.format(name=name),
        **kwargs
    )


def cc_licence_data(book_entity):
    """Return data required for the cc licence for the book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    creator = Creator.from_id(book_record.creator_id)

    year_list = book_pages_years(book_record)
    if not year_list:
        year_list = [datetime.date.today().year]

    if len(year_list) == 1:
        years = str(year_list[0])
    else:
        years = '{f}-{l}'.format(f=year_list[0], l=year_list[-1])

    return dict(
        owner=creator_formatted_name(creator),
        owner_url=creator_short_url(creator),
        title=book_record.name,
        title_url=short_url(book_record),
        year=years,
        place=book_record.cc_licence_place,
    )


def complete_link(book_entity, components=None, **attributes):
    """Return html code suitable for a 'set as complete' link/button/checkbox.

    Args:
        book_entity: Row instance or integer representing a book record.
        components: list, passed to A(*components)
        attributes: dict of attributes for A()
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        return empty

    if not components:
        components = [
            DIV(
                INPUT(_type='checkbox', _value='off'),
                _class="completed_checkbox_wrapper"
            )
        ]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='login', f='book_release', args=book.id, extension=False)

    return A(*components, **kwargs)


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


def contributions_remaining_by_creator(creator):
    """Return the calculated contributions remaining for all books of the
    creator.

    Args:
        creator: Creator instance

    Returns:
        float, dollar amount of contributions remaining.
    """
    # invalid-name (C0103): *Invalid %%s name "%%s"%%s*
    # pylint: disable=C0103
    if not creator:
        return 0.00

    db = current.app.db
    query = (db.book.creator_id == creator.id) & \
            (db.book.status == BOOK_STATUS_ACTIVE)

    total = 0
    books = db(query).select()
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
    except LookupError:
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


def defaults(name, creator):
    """Return a dict representing default values for a book.

    Args:
        name: string, name of book
        creator: Creator instance

    Returns:
        dict: representing book fields and values.
    """
    if not creator:
        return {}

    data = {}
    data['name'] = name

    db = current.app.db
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


def follow_link(book, components=None, **attributes):
    """Return html code suitable for a 'Follow' link.

    Args:
        book: Row instance representing the book
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
            args=[book.creator_id],
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
    book_type = BookType.classified_from_id(book.book_type_id)
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
        LookupError, if book_entity doesn't match a book, or book doesn't
            have a page associated with the provided page_no value.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Book not found, {e}'.format(e=book_entity))

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
        raise LookupError('Book id {b}, page not found, {p}'.format(
            b=book_record.id, p=page_no))

    key = {
        'book_id': book_record.id,
        'page_no': want_page_no,
    }
    book_page = BookPage.from_key(key)
    if not book_page:
        raise LookupError('Book id {b}, page not found, {p}'.format(
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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    creator = Creator.from_id(book_record.creator_id)

    try:
        first_page = get_page(book_entity, page_no='first')
    except LookupError:
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
        'creator_name': creator_formatted_name(creator),
        'creator_twitter': creator.twitter,
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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

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
            if not page[field]:
                continue
            image_names.append(page[field])

    return image_names


def is_downloadable(book):
    """Determine if the book can be downloaded.

    Args:
        book: Row instance representing a book.
    """
    return True if book.status == BOOK_STATUS_ACTIVE \
        and book.cbz \
        and book.torrent \
        else False


def is_followable(book):
    """Determine if the book can be followed.

    Args:
        book: Row instance representing a book.
    """
    return True if book.status == BOOK_STATUS_ACTIVE \
        and not is_released(book) \
        else False


def is_released(book):
    """Determine if the book is released.

    Args:
        book: Row instance representing a book.
    """
    return True if book.status == BOOK_STATUS_ACTIVE \
        and not book.releasing \
        and book.release_date \
        else False


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
        raise LookupError('Book not found, id: {e}'.format(
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
    book_type = BookType.classified_from_id(book['book_type_id'])
    number = book_type.formatted_number(book['number'], book['of_number'])
    return name_values(
        BookTitle(
            BookName(book['name']),
            BookNumber(number)
        ),
        fields=fields
    )


def next_book_in_series(book_entity):
    """Return the next book in the series.

    Args:
        book_entity: Row instance or integer representing a book.

    Returns:
        Row instance representing next book.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    book_type = BookType.classified_from_id(book_record.book_type_id)
    if not book_type.is_series():
        return

    query = (db.book.creator_id == book_record.creator_id) & \
        (db.book.name == book_record.name) & \
        (db.book.number > book_record.number)
    return db(query).select(orderby=db.book.number).first()


def page_url(book_page, reader=None, **url_kwargs):
    """Return a url suitable for the reader webpage of a book page.

    Args:
        book_page: BookPage instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url,
            eg http://zco.mx/creators/index/First_Last/My_Book_(2014)/002
            (routes_out should convert it to
            http://zco.mx/First_Last/My_Book_(2014))/002
    """
    db = current.app.db

    book_record = entity_to_row(db.book, book_page.book_id)
    if not book_record:
        return

    creator = Creator.from_id(book_record.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    books_name = book_name(book_record, use='url')
    if not books_name:
        return

    page_name = '{p:03d}'.format(p=book_page.page_no)

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
    except LookupError:
        return empty

    if not components:
        components = ['Read']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = page_url(first_page, extension=False)

    return A(*components, **kwargs)


def rss_url(book_entity, **url_kwargs):
    """Return the url to the rss feed for the book.

    Args:
        book_entity: Row instance or integer, if integer, this is the id of
            the book. The book record is read.
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast/MyBook-001.rss
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Creator not found, id: {e}'.format(
            e=book_entity))

    creator = Creator.from_id(book_record.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book_record, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.rss'.format(name=name),
        **kwargs
    )


def set_status(book_entity, status):
    """Set the status of a book.

    Args:
        book_entity: Row instance or integer representing a book.
        status: string, the status of a book.

    Raises:
        LookupError, if book_entity doesn't represent a book on file.
        ValueError, if the status is invalid.
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    if status not in BOOK_STATUSES:
        raise ValueError('Invalid status {s}'.format(s=status))

    if book_record.status != status:
        book_record.update_record(status=status)
        db.commit()


def short_page_img_url(book_page):
    """Return a short url for the book page image.

    Args:
        book_page: BookPage instance

    Returns:
        string, url, eg http://101.zco.mx/My_Book/001.jpg
    """
    book_page_url = short_page_url(book_page)
    if not book_page_url:
        return

    m = REGEX_STORE_PATTERN.search(book_page.image or '')
    extension = m and m.group('e') or ''
    if not extension:
        return book_page_url
    return '.'.join([book_page_url, extension])


def short_page_url(book_page):
    """Return a short url for the book page.

    Args:
        book_page: BookPage instance
    Returns:
        string, url, eg http://101.zco.mx/My_Book/001
    """
    book_url = short_url(book_page.book_id)
    if not book_url:
        return
    page_name = '{p:03d}'.format(p=book_page.page_no)
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

    try:
        creator = Creator.from_id(book_record.creator_id)
    except LookupError:
        return

    url_for_creator = creator_short_url(creator)
    if not url_for_creator:
        return

    return urlparse.urljoin(url_for_creator, name)


def social_media_data(book_entity):
    """Return book attributes for social media.

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
        raise LookupError('Book not found, {e}'.format(e=book_entity))

    try:
        first_page = get_page(book_entity, page_no='first')
    except LookupError:
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
        raise LookupError('Creator not found, id: {e}'.format(
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
        components: list, passed to A(*components), default [book.name_for_url]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')

    db = current.app.db
    book = entity_to_row(db.book, book_entity)
    if not book:
        raise LookupError('Book not found, id: {e}'.format(
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
            http://zco.mx/FirstLast/MyBook-001.torrent
    """
    db = current.app.db
    book_record = entity_to_row(db.book, book_entity)
    if not book_record:
        raise LookupError('Creator not found, id: {e}'.format(
            e=book_entity))

    creator = Creator.from_id(book_record.creator_id)
    name_of_creator = creator_name(creator, use='url')
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

    creator = Creator.from_id(book_record.creator_id)
    if not creator:
        return

    total = contributions_remaining_by_creator(creator)
    if creator.contributions_remaining != total:
        db(db.creator.id == creator.id).update(contributions_remaining=total)
        db.commit()


def update_rating(db, book, rating=None):
    """Update an accumulated rating for a book.

    Args
        db: gluon.dal.DAL instance
        book: Book instance
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
        db(query).update(**{field.name: value})
    db.commit()

    if rating is None or rating == 'contribution':
        update_contributions_remaining(db, book.id)


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

    creator = Creator.from_id(book_record.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book_record, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name_of_creator, name], **kwargs)
