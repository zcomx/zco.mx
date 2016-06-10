#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Book classes and functions.
"""
import datetime
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
    short_url as creator_short_url
from applications.zcomx.modules.images import \
    CachedImgTag, \
    ImageDescriptor
from applications.zcomx.modules.names import \
    BookName, \
    BookNumber, \
    BookTitle, \
    names as name_values
from applications.zcomx.modules.records import \
    Record, \
    Records
from applications.zcomx.modules.shell_utils import tthsum
from applications.zcomx.modules.zco import \
    BOOK_STATUSES, \
    BOOK_STATUS_ACTIVE, \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT, \
    SITE_NAME


DEFAULT_BOOK_TYPE = 'one-shot'
LOG = current.app.logger


class Book(Record):
    """Class representing a book record."""
    db_table = 'book'

    def page_count(self):
        """return the number of pages in the book.

        returns:
            integer, the number of pages
        """
        return len(self.pages())

    def pages(self, orderby=None, limitby=None):
        """Return a list of pages of the book.

        Args:
            orderby: orderby expression, see select()
                Default, [page_no, id]
            limitby: limitby expression, see seelct()

        Returns:
            list of BookPage instances
        """
        if orderby is None:
            db = current.app.db
            orderby = [db.book_page.page_no, db.book_page.id]
        return Records.from_key(
            BookPage, dict(book_id=self.id), orderby=orderby, limitby=limitby)


def book_name(book, use='file'):
    """Return the name of the book suitable for specified use.

    Args:
        book: Book instance
        use: one of 'file', 'search', 'url'

    Returns:
        string, name of file
    """
    if use == 'file':
        return names(book.as_dict())['name_for_file']
    elif use == 'search':
        return book.name_for_search
    elif use == 'url':
        return book.name_for_url
    return


def book_page_for_json(book_page):
    r"""Return the book_page formated as json suitable for jquery-file-upload.

    Args:
        book_page: BookPage instance

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
    filename = book_page.upload_image().original_name()
    size = ImageDescriptor(book_page.upload_image().fullname()).size_bytes()

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


def book_pages_as_json(book, book_page_ids=None):
    """Return the book pages formated as json suitable for jquery-file-upload.

    Args:
        book: Book instance
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
    for page in book.pages():
        if not book_page_ids or page.id in book_page_ids:
            pages.append(page)
    json_pages = [book_page_for_json(p) for p in pages]
    return dumps(dict(files=json_pages))


def book_pages_years(book):
    """Return a list of years for the pages of a book.

    The years can be used for copyright.

    Args:
        book: Book instance

    Returns:
        list of integers
    """
    return sorted(set([x.created_on.year for x in book.pages()]))


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


def calc_contributions_remaining(book):
    """Return the calculated contributions remaining for the book to reach
    its contributions target.

    Args:
        book: Book instance

    Returns:
        float, dollar amount of contributions remaining.
    """
    if not book:
        return 0.00

    db = current.app.db
    target = contributions_target(book)

    query = (db.contribution.book_id == book.id)
    total = db.contribution.amount.sum()
    rows = db(query).select(total)
    contributed_total = rows[0][total] if rows and rows[0][total] else 0.00

    remaining = target - contributed_total
    if remaining < 0:
        remaining = 0.00
    return remaining


def calc_status(book):
    """Determine the calculated status of the book.

    Args:
        book: Book instance

    Returns:
        string, the status of a book, eg BOOK_STATUS_ACTIVE
    """
    if book.status == BOOK_STATUS_DISABLED:
        return BOOK_STATUS_DISABLED
    return BOOK_STATUS_ACTIVE if book.page_count() > 0 else BOOK_STATUS_DRAFT


def cbz_comment(book):
    """ Return a comment suitable for the cbz file.

    Args:
        book: Book instance

    Returns:
        string, eg '2014|Cartoonist Name|Title of Book|64'
    """
    creator = Creator.from_id(book.creator_id)
    cc_licence = CCLicence.from_id(book.cc_licence_id)

    fields = []
    fields.append(str(book.publication_year))
    fields.append(creator.name)
    fields.append(book.name)
    fields.append(formatted_number(book))
    fields.append(cc_licence.code)
    fields.append(creator_short_url(creator))
    return '|'.join(fields)


def cbz_link(book, components=None, **attributes):
    """Return a link suitable for the cbz file of a book.

    Args:
        book: Book instance
        components: list, passed to A(*components), default [book.name_for_url]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')
    if not book:
        return empty

    link_url = cbz_url(book)
    if not link_url:
        return empty

    if not components:
        name = '{n}.cbz'.format(n=book_name(book, use='url').lower())
        components = [name]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def cbz_url(book, **url_kwargs):
    """Return the url to the cbz file for the book.

    Args:
        book: Book instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}

    Returns:
        string, url, eg
            http://zco.mx/FirstLast/MyBook-001.cbz
    """
    creator = Creator.from_id(book.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.cbz'.format(name=name),
        **kwargs
    )


def cc_licence_data(book):
    """Return data required for the cc licence for the book.

    Args:
        book: Book instance

    Returns:
        dict
    """
    creator = Creator.from_id(book.creator_id)

    year_list = book_pages_years(book)
    if not year_list:
        year_list = [datetime.date.today().year]
    if len(year_list) == 1:
        years = str(year_list[0])
    else:
        years = '{f}-{l}'.format(f=year_list[0], l=year_list[-1])

    return dict(
        owner=creator.name,
        owner_url=creator_short_url(creator),
        title=book.name,
        title_url=short_url(book),
        year=years,
        place=book.cc_licence_place,
    )


def complete_link(book, components=None, **attributes):
    """Return html code suitable for a 'set as complete' link/button/checkbox.

    Args:
        book: Book instance
        components: list, passed to A(*components)
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
    if not book:
        return empty

    if not components:
        components = [
            DIV(
                INPUT(_type='checkbox', _value='off'),
                _class="checkbox_wrapper"
            )
        ]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='login', f='book_complete', args=book.id, extension=False)

    return A(*components, **kwargs)


def contribute_link(book, components=None, **attributes):
    """Return html code suitable for a 'Contribute' link.

    Args:
        book: Book instance
        components: list, passed to A(*components),  default ['Contribute']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
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
    for book_row in books:
        book = Book.from_id(book_row.id)
        amount = calc_contributions_remaining(book)
        total = total + amount
    return total


def contributions_target(book):
    """Return the contributions target for the book.


    Args:
        book: Book instance

    Returns:
        float, dollar amount of contributions target.
    """
    rate_per_page = 10.00

    if not book:
        return 0.00

    amount = round(rate_per_page * book.page_count())
    return amount


def cover_image(book, size='original', img_attributes=None):
    """Return html code suitable for the cover image.

    Args:
        book: Book instance
        size: string, the size of the image. One of SIZES
        img_attributes: dict of attributes for IMG
    """
    image = None
    if book:
        try:
            first_page = get_page(book, page_no='first')
        except LookupError:
            first_page = None

        image = first_page.image if first_page else None

    attributes = {'_alt': ''}

    if img_attributes:
        attributes.update(img_attributes)

    return CachedImgTag(image, size=size, attributes=attributes)()


def default_contribute_amount(book):
    """Return the default amount for the contribute widget.

    Args:
        book: Book instance
    """
    minimum = 1
    maximum = 20
    rate_per_page = 1.0 / 20

    amount = round(rate_per_page * book.page_count())
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
        book_type = BookType.from_key(dict(name=DEFAULT_BOOK_TYPE))
        if book_type:
            data['book_type_id'] = book_type.id
        data['number'] = 1
        data['of_number'] = 1
    data.update(names(data, fields=db.book.fields))
    return data


def download_link(book, components=None, **attributes):
    """Return html code suitable for a 'Download' link.

    Args:
        book: Book instance
        components: list, passed to A(*components),  default ['Download']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
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


def fileshare_link(book, components=None, **attributes):
    """Return html code suitable for a 'release for filesharing'
    link/button/checkbox.

    Args:
        book: Book instance
        components: list, passed to A(*components)
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
    if not book:
        return empty

    if not components:
        components = [
            DIV(
                INPUT(_type='checkbox', _value='off'),
                _class="checkbox_wrapper"
            )
        ]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = URL(
            c='login', f='book_fileshare', args=book.id, extension=False)

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


def formatted_name(book, include_publication_year=True):
    """Return the formatted name of the book

    Args:
        book: Book instance
        include_publication_year: If True, the publication year is included in
            the name.
    """
    if not book:
        return ''

    fmt = '{name}'
    data = {
        'name': book.name,
    }

    number = formatted_number(book)
    if number:
        fmt = '{name} {num}'
        data['num'] = number

    if include_publication_year:
        fmt = ' '.join([fmt, '({year})'])
        data['year'] = book.publication_year
    return fmt.format(**data)


def formatted_number(book):
    """Return the number of the book formatted.

    Args:
        book: Book instance
    """
    if not book:
        return ''
    book_type = BookType.classified_from_id(book.book_type_id)
    return book_type.formatted_number(book.number, book.of_number)


def get_page(book, page_no=1):
    """Return a page of a book.

    Args:
        book: Book instance
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
        BookPage instance

    Raises:
        LookupError, if book doesn't have a page associated with the provided
            page_no value.
    """
    db = current.app.db

    want_page_no = None
    if page_no == 'first':
        want_page_no = 1
    elif page_no in ['last', 'indicia']:
        page_max = db.book_page.page_no.max()
        query = (db.book_page.book_id == book.id)
        want_page_no = db(query).select(page_max)[0][page_max]
    else:
        try:
            want_page_no = int(page_no)
        except (TypeError, ValueError):
            want_page_no = None
    if want_page_no is None:
        raise LookupError('Book id {b}, page not found, {p}'.format(
            b=book.id, p=page_no))

    key = {
        'book_id': book.id,
        'page_no': want_page_no,
    }
    book_page = BookPage.from_key(key)

    if page_no == 'indicia':
        book_page.id = None
        book_page.image = None
        book_page.page_no = book_page.page_no + 1

    return book_page


def html_metadata(book):
    """Return book attributes for HTML metadata.

    Args:
        book: Book instance

    Returns:
        dict
    """
    if not book:
        return {}

    creator = Creator.from_id(book.creator_id)

    try:
        first_page = get_page(book, page_no='first')
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
        'creator_name': creator.name,
        'creator_twitter': creator.twitter,
        'description': book.description,
        'image_url': image_url,
        'name': formatted_name(book, include_publication_year=True),
        'type': 'book',
        'url': url(book, host=True),
    }


def images(book):
    """Return a list of image names associated with the book.

    This includes images associated with the book and any of the book
    pages.

    Args:
        book: Book instance

    Returns:
        list of strings, list of image names. Eg of an image name:
            book_page.image.801685b627e099e.300332e6a7067.jpg
    """
    db = current.app.db

    image_names = []

    for field in db.book.fields:
        if db.book[field].type != 'upload':
            continue
        if not book[field]:
            continue
        image_names.append(book[field])

    for page in book.pages():
        for field in db.book_page.fields:
            if db.book_page[field].type != 'upload':
                continue
            if not page[field]:
                continue
            image_names.append(page[field])

    return image_names


def is_completed(book):
    """Determine if the book is completed.

    Args:
        book: Row instance representing a book.
    """
    return True if book.status == BOOK_STATUS_ACTIVE \
        and not book.complete_in_progress \
        and book.release_date \
        else False


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
        and not is_completed(book) \
        else False


def magnet_link(book, components=None, **attributes):
    """Return a link suitable for the magnet for a book.

    Args:
        book: Book instance
        components: list, passed to A(*components),  default [torrent_name()]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')
    if not book:
        return empty

    link_url = magnet_uri(book)
    if not link_url:
        return empty

    if not components:
        name = '{n}.magnet'.format(
            n=book_name(book, use='url').lower()
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


def magnet_uri(book):
    """Create a magnet uri for a book.

    Args:
        book: Book instance

    Returns:
        str, the magnet uri,
        eg: 'magnet:?xt=urn:tree:tiger:UY...SD&xl=2604758&dn=My+Book+(2013).cbz
    """
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
        names(book.as_dict(), db.book.fields)
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


def next_book_in_series(book):
    """Return the next book in the series.

    Args:
        book: Book instance

    Returns:
        Book instance representing next book.
    """
    if not book:
        return

    book_type = BookType.classified_from_id(book.book_type_id)
    if not book_type.is_series():
        return

    db = current.app.db
    query = (db.book.creator_id == book.creator_id) & \
        (db.book.name == book.name) & \
        (db.book.number > book.number)
    next_book = db(query).select(
        db.book.id,
        orderby=db.book.number,
        limitby=(0, 1)
    ).first()
    if not next_book:
        return
    return Book.from_id(next_book.id)


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
    book = Book.from_id(book_page.book_id)

    creator = Creator.from_id(book.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    books_name = book_name(book, use='url')
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


def publication_months(format_directive='%b'):
    """Return a list of dicts representing months of the year suitable for a
    drop down menu.

    Args:
        format_directive: str, directive to use for strftime when determining
            the text of months.
                format_directive            Results
                %b                          Jan, Feb, ..., Dec
                %B                          January, February, ..., December

    Returns:
        list of dicts, Example:
            [{'value': 1, 'text': 'Jan'}, {'value': 2, 'text': 'Feb'},...]
    """
    values = []
    for x in range(1, 13):
        date = datetime.date(1970, x, 1)
        values.append({'value': x, 'text': date.strftime(format_directive)})
    return values


def publication_year_range():
    """Return a tuple representing the start and end range of publication years
    """
    return (1970, datetime.date.today().year + 5)


def read_link(book, components=None, **attributes):
    """Return html code suitable for a 'Read' link.

    Args:
        book: Book instance
        components: list, passed to A(*components),  default ['Read']
        attributes: dict of attributes for A()
    """
    empty = SPAN('')
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


def rss_url(book, **url_kwargs):
    """Return the url to the rss feed for the book.

    Args:
        book: Book instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast/MyBook-001.rss
    """
    if not book:
        return

    creator = Creator.from_id(book.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.rss'.format(name=name),
        **kwargs
    )


def set_status(book, status):
    """Set the status of a book.

    Args:
        book: Book instance
        status: string, the status of a book.

    Raises:
        ValueError, if the status is invalid.

    Returns
        Book instance
    """
    if status not in BOOK_STATUSES:
        raise ValueError('Invalid status {s}'.format(s=status))

    if book.status != status:
        book = Book.from_updated(book, dict(status=status))
    return book


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
    book = Book.from_id(book_page.book_id)
    book_url = short_url(book)
    if not book_url:
        return
    page_name = '{p:03d}'.format(p=book_page.page_no)
    return '/'.join([book_url.rstrip('/'), page_name])


def short_url(book):
    """Return a short url for the book webpage.

    Args:
        book: Book instance

    Returns:
        string, url, eg http://101.zco.mx/My_Book_(2014)
    """
    if not book:
        return

    name = book_name(book, use='url')
    if not name:
        return

    try:
        creator = Creator.from_id(book.creator_id)
    except LookupError:
        return

    url_for_creator = creator_short_url(creator)
    if not url_for_creator:
        return

    return urlparse.urljoin(url_for_creator, name)


def social_media_data(book):
    """Return book attributes for social media.

    Args:
        book: Book instance

    Returns:
        dict
    """
    if not book:
        return {}

    try:
        first_page = get_page(book, page_no='first')
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
        'description': book.description,
        'download_url': download_url,
        'formatted_name': formatted_name(book, include_publication_year=True),
        'formatted_name_no_year': formatted_name(
            book, include_publication_year=False),
        'formatted_number': formatted_number(book),
        'name': book.name,
        'name_camelcase': BookName(book.name).for_url(),
        'name_for_search': book_name(book, use='search'),
        'short_url': short_url(book),
        'url': url(book, host=SITE_NAME),
    }


def torrent_file_name(book):
    """Return the name of the torrent file for the book.

    Args:
        book: Book instance

    Returns:
        string, the file name.
    """
    if not book:
        return

    fmt = '{name} ({year}) ({cid}.zco.mx).cbz.torrent'
    return fmt.format(
        name=book_name(book, use='file'),
        year=str(book.publication_year),
        cid=book.creator_id,
    )


def torrent_link(book, components=None, **attributes):
    """Return a link suitable for the torrent file of a book.

    Args:
        book: Book instance
        components: list, passed to A(*components), default [book.name_for_url]
        attributes: dict of attributes for A()
    Returns:
        A instance
    """
    empty = SPAN('')
    if not book:
        return empty

    link_url = torrent_url(book)
    if not link_url:
        return empty

    if not components:
        name = '{n}.torrent'.format(
            n=book_name(book, use='url').lower()
        )
        components = [name]

    kwargs = {}
    kwargs.update(attributes)

    if '_href' not in attributes:
        kwargs['_href'] = link_url

    return A(*components, **kwargs)


def torrent_url(book, **url_kwargs):
    """Return the url to the torrent file for the book.

    Args:
        book: Book instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg
            http://zco.mx/FirstLast/MyBook-001.torrent
    """
    if not book:
        return

    creator = Creator.from_id(book.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(
        c=name_of_creator,
        f='{name}.torrent'.format(name=name),
        **kwargs
    )


def update_contributions_remaining(book):
    """Update the contributions_remaining for the creator of the book.

    Args
        book: Book instance
    """
    if not book:
        return

    data = dict(
        contributions_remaining=calc_contributions_remaining(book)
    )
    updated_book = Book.from_updated(book, data)

    if not updated_book.creator_id:
        return

    creator = Creator.from_id(updated_book.creator_id)
    if not creator:
        return

    total = contributions_remaining_by_creator(creator)
    if creator.contributions_remaining != total:
        data = dict(contributions_remaining=total)
        creator = Creator.from_updated(creator, data)


def update_rating(book, rating=None):
    """Update an accumulated rating for a book.

    Args
        book: Book instance
        rating: string, one of 'contribution', 'rating', 'view'. If None,
                all ratings are updated.
    """
    db = current.app.db
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
        book = Book.from_updated(book, {field.name: value})

    if rating is None or rating == 'contribution':
        update_contributions_remaining(book)


def url(book, **url_kwargs):
    """Return a url suitable for the book webpage.

    Args:
        book: Bow instance
        url_kwargs: dict of kwargs for URL(). Eg {'extension': False}
    Returns:
        string, url, eg http://zco.mx/creators/index/First_Last/My_Book_(2014)
            (routes_out should convert it to
            http://zco.mx/First_Last/My_Book_(2014))
    """
    if not book or not book.name:
        return

    creator = Creator.from_id(book.creator_id)
    name_of_creator = creator_name(creator, use='url')
    if not name_of_creator:
        return

    name = book_name(book, use='url')
    if not name:
        return

    kwargs = {}
    kwargs.update(url_kwargs)
    return URL(c='creators', f='index', args=[name_of_creator, name], **kwargs)
