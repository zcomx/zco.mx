#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book classes and functions.
"""
import datetime
import logging
import os
import re
import urlparse
from gluon import *
from gluon.dal.objects import REGEX_STORE_PATTERN
from gluon.storage import Storage
from gluon.validators import urlify
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.creators import \
    formatted_name as creator_formatted_name, \
    short_url as creator_short_url, \
    url_name as creator_url_name
from applications.zcomx.modules.images import \
    ImgTag, \
    UploadImage, \
    queue_optimize
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

    def log(self, value=None):
        """Create a record representing a log of the event."""
        raise NotImplementedError


class ContributionEvent(BookEvent):
    """Class representing a book contribution event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def log(self, value=None):
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
        update_rating(db, self.book, rating='contribution')
        return event_id


class RatingEvent(BookEvent):
    """Class representing a book rating event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def log(self, value=None):
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
        update_rating(db, self.book, rating='rating')
        return event_id


class ViewEvent(BookEvent):
    """Class representing a book view event."""

    def __init__(self, book_entity, user_id):
        BookEvent.__init__(self, book_entity, user_id)

    def log(self, value=None):
        db = current.app.db
        event_id = db.book_view.insert(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now()
        )
        db.commit()
        update_rating(db, self.book, rating='view')
        return event_id


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
    query = (db.book_page.id == book_page_id)
    book_page = db(query).select(db.book_page.ALL).first()
    if not book_page:
        return

    filename, original_fullname = db.book_page.image.retrieve(
        book_page.image,
        nameonly=True,
    )

    try:
        size = os.stat(original_fullname).st_size
    except (KeyError, OSError):
        size = 0

    down_url = URL(
        c='images',
        f='download',
        args=book_page.image,
    )

    thumb = URL(
        c='images',
        f='download',
        args=book_page.image,
        vars={'size': 'web'},
    )

    delete_url = URL(
        c='login',
        f='book_pages_handler',
        args=book_page.book_id,
        vars={'book_page_id': book_page.id},
    )

    return dict(
        book_id=book_page.book_id,
        book_page_id=book_page.id,
        name=filename,
        size=size,
        url=down_url,
        thumbnailUrl=thumb,
        deleteUrl=delete_url,
        deleteType='DELETE',
    )


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


def by_attributes(attributes):
    """Return a Row instances representing a book matching the attributes.

    Args:
        attributes: dict of book attributes.

    Returns:
        Row instance representing a book.
    """
    if not attributes:
        return
    db = current.app.db
    queries = []
    for key, value in attributes.items():
        if value is not None:
            queries.append((db.book[key] == value))
    query = reduce(lambda x, y: x & y, queries) if queries else None
    if not query:
        return
    return db(query).select().first()


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
    book_type = entity_to_row(db.book_type, book.book_type_id)

    fmt = '{name}'
    data = {
        'name': book.name,
    }

    if book_type.name == 'ongoing':
        fmt = '{name} {num:03d}'
        data['num'] = book.number
    elif book_type.name == 'mini-series':
        fmt = '{name} {num:02d} (of {of:02d})'
        data['num'] = book.number
        data['of'] = book.of_number

    if include_publication_year:
        fmt = ' '.join([fmt, '({year})'])
        data['year'] = book.publication_year
    return fmt.format(**data)


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


def is_releasable(db, book_entity):
    """Return whether the book can be released.

    Args:
        db: gluon.dal.DAL instance
        book_entity: Row instance or integer, if integer, this is the id of the
            book. The book record is read.
    """
    book = entity_to_row(db.book, book_entity)
    if not book:
        return False
    if not book.name:
        return False
    page_count = db(db.book_page.book_id == book.id).count()
    return True if page_count > 0 else False


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


def optimize_book_images(
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
    query = (db.book_page.book_id == book.id)
    page_ids = [x.id for x in db(query).select(db.book_page.id)]

    for table in ['book', 'book_page']:
        for field in db[table].fields:
            if db[table][field].type == 'upload':
                if table == 'book':
                    record_ids = [book.id]
                else:
                    record_ids = list(page_ids)
                for record_id in record_ids:
                    jobs.append(
                        queue_optimize(
                            str(db[table][field]),
                            record_id,
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
    db = current.app.db
    book_page = entity_to_row(db.book_page, book_page_entity)
    if not book_page:
        raise NotFoundError('book page not found, {e}'.format(
            e=book_page_entity))
    if not book_page.image:
        raise NotFoundError('Book page has no image, book_page.id {i}'.format(
            i=book_page.id))

    up_image = UploadImage(db.book_page.image, book_page.image)
    width, height = up_image.dimensions()
    if width == height:
        return 'square'
    elif width > height:
        return 'landscape'
    else:
        return 'portrait'


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


def parse_url_name(name):
    """Parse a book url name and return book attributes.

    Args:
        name: string, name of book used in url (ie what is returned by
                def url_name()

    Returns
        dict of book attributes.
            eg {
                    name: Name
                    book_type_id: 1,
                    number: 1,
                    of_number: 4,
                }
    """
    if not name:
        return

    book = dict(
        name=None,
        number=None,
        of_number=None,
        book_type_id=None,
    )

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
        m = type_res[book_type].match(name)
        if m:
            book.update(m.groupdict())
            book['book_type_id'] = type_id_by_name[book_type]
            break
    if book['name']:
        book['name'] = book['name'].replace('_', ' ')
    for field in ['number', 'of_number']:
        if book[field]:
            try:
                book[field] = int(book[field])
            except (TypeError, ValueError):
                book[field] = None
    return book


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

    name = url_name(book_entity)
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
        string, eg My_Book_(2014)
    """
    if not book_entity:
        return

    db = current.app.db

    book_record = entity_to_row(db.book, book_entity)
    if not book_record or not book_record.name:
        return
    return formatted_name(
        db, book_record, include_publication_year=False).replace(' ', '_')
