#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book classes and functions.
"""
import datetime
import os
import re
from gluon import *
from gluon.storage import Storage
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.creators import url_name as creator_url_name
from applications.zcomx.modules.images import ImgTag
from applications.zcomx.modules.utils import entity_to_row


DEFAULT_BOOK_TYPE = 'one-shot'


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
        vars={'size': 'tbn'},
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
            ["{{'value':'{x.id}', 'text':'{x.description}'}}".format(x=x)
                for x in types])
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


def cover_image(db, book_id, size='original', img_attributes=None):
    """Return html code suitable for the cover image.

    Args:
        db: gluon.dal.DAL instance
        book_id: integer, the id of the book
        size: string, the size of the image. One of SIZES
        img_attributes: dict of attributes for IMG
    """
    page = first_page(db, book_id)
    image = page.image if page else None

    attributes = {}

    if size == 'tbn':
        thumb_w = thumb_h = 170
        if not page:
            # Create a dummy book_page record
            page = Storage(
                thumb_w=thumb_w,
                thumb_h=thumb_h,
            )

        fmt = ' '.join([
            'width: {w}px;',
            'height: {h}px;',
            'margin: {pv}px {pr}px {pv}px {pl}px;',
        ])
        width = page.thumb_w
        height = page.thumb_h
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
    return data


def first_page(db, book_id, orderby=None):
    """Return the first page for the book.

    Args
        db: gluon.dal.DAL instance
        book_id: integer, the id of the book
        orderby: gluon.dal.Field used to order pages.
                Default db.book_page.page_no
    """
    order_by = orderby or db.book_page.page_no
    query = (db.book_page.book_id == book_id)
    return db(query).select(db.book_page.ALL, orderby=order_by).first()


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
    page_record = entity_to_row(db.book, book_page_entity)
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
    return (1900, datetime.date.today().year + 5)


def publication_years():
    """Return a XML instance representing publication years suitable for
    drop down menu.
    """
    # {'value': '1900', 'text': '1900'}, ...
    return XML(
        ','.join(
            ["{{'value':'{x}', 'text':'{x}'}}".format(x=x)
                for x in range(*publication_year_range())])
    )


def read_link(db, book_entity, components=None, **attributes):
    """Return html code suitable for the cover image.

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

    page = first_page(db, book.id)
    if not page:
        return empty

    if not components:
        components = ['Read']

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = page_url(page, extension=False)

    return A(*components, **kwargs)


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
            # (book field, data field, period, function, format)
            (db.book.contributions_year, db.contribution.amount, 'year',
                'sum'),
            (db.book.contributions_month, db.contribution.amount, 'month',
                'sum'),
        ],
        'rating': [
            (db.book.rating_year, db.rating.amount, 'year', 'avg'),
            (db.book.rating_month, db.rating.amount, 'month', 'avg'),
        ],
        'view': [
            (db.book.views_year, db.book_view.id, 'year', 'count'),
            (db.book.views_month, db.book_view.id, 'month', 'count'),
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

    periods = {
        # name: days
        'month': 30,
        'year': 365,
    }

    book_query = (db.book.id == book.id)
    for field, data_field, period, func in rating_data:
        data_table = data_field.table
        days = periods[period]
        min_date = datetime.datetime.now() - datetime.timedelta(days=days)
        time_query = (data_table.time_stamp >= min_date)
        if func == 'sum':
            tally = data_field.sum()
        elif func == 'avg':
            tally = data_field.avg()
        elif func == 'count':
            tally = data_field.count()
        query = book_query & time_query
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
        string, eg Firstname_Lastname
    """
    if not book_entity:
        return

    db = current.app.db

    book_record = entity_to_row(db.book, book_entity)
    if not book_record or not book_record.name:
        return
    return formatted_name(
        db, book_record, include_publication_year=False).replace(' ', '_')
