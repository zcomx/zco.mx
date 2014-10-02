#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Routing classes and functions.
"""
import urllib
from gluon.html import A, SPAN
from gluon.storage import Storage
from applications.zcomx.modules.books import \
    ViewEvent, \
    by_attributes, \
    cover_image, \
    page_url, \
    parse_url_name, \
    read_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    url as creator_url
from applications.zcomx.modules.links import CustomLinks
from applications.zcomx.modules.utils import entity_to_row


def route(db, request, auth):
    """Return vars dict and view for route.

    Args:
        db: gluon.dal.DAL instance
        request: gluon.globals.Request instance.
        auth: gluon.tools.Auth instance.

    Returns:
        tuple (view_dict, view)
    """
    # too-many-return-statements (R0911): *Too many return statements
    # pylint: disable=R0911
    view_dict = None
    view = None

    creator_id = None
    creator_record = None
    book_id = None
    book_record = None
    page_id = None
    book_page = None

    if not request.vars.creator:
        return (None, None)

    # Test for request.vars.creator as integer, assume creator.id
    try:
        int(request.vars.creator)
    except (TypeError, ValueError):
        pass
    else:
        creator_id = request.vars.creator

    if not creator_id:
        # Test for request.vars.creator as creator.name
        name = request.vars.creator.replace('_', ' ')
        creator_record = db(db.creator.path_name == name).select().first()
        if creator_record:
            creator_id = creator_record.id

    if not creator_id:
        return page_not_found(db, request, creator_id, book_id, page_id)

    if not creator_record:
        creator_record = entity_to_row(db.creator, creator_id)
        if not creator_record:
            return page_not_found(db, request, creator_id, book_id, page_id)

    auth_user = entity_to_row(db.auth_user, creator_record.auth_user_id)
    if not auth_user:
        return page_not_found(db, request, creator_id, book_id, page_id)

    if request.vars.book:
        attrs = parse_url_name(request.vars.book)
        attrs['creator_id'] = creator_record.id
        book_record = by_attributes(attrs)
        if book_record:
            book_id = book_record.id
        else:
            return page_not_found(db, request, creator_id, book_id, page_id)

    page_no = None

    if book_id and request.vars.page:
        # Strip off extension
        parts = request.vars.page.split('.')
        raw_page_no = parts[0]
        try:
            page_no = int(raw_page_no)
        except (TypeError, ValueError):
            page_no = None
        if page_no:
            query = (db.book_page.book_id == book_id) & \
                    (db.book_page.page_no == page_no)
            book_page = db(query).select().first()
            if book_page:
                page_id = book_page.id
            else:
                return page_not_found(
                    db, request, creator_id, book_id, page_id)

    if page_id:
        reader = request.vars.reader or book_record.reader

        page_images = db(db.book_page.book_id == book_record.id).select(
            db.book_page.image,
            db.book_page.page_no,
            orderby=[db.book_page.page_no, db.book_page.id]
        )

        ViewEvent(book_record, auth.user_id).log()

        query = (db.book_page.book_id == book_record.id)
        first_page = db(query).select(
            db.book_page.ALL,
            orderby=db.book_page.page_no
        ).first()

        scroll_link = A(
            SPAN('scroll'),
            _href=page_url(first_page, reader='scroller'),
            _class='btn btn-default {st}'.format(
                st='disabled' if reader == 'scroller' else 'active'),
            _type='button',
            cid=request.cid
        )

        slider_data = dict(
            _href=page_url(first_page, reader='slider'),
            _class='btn btn-default active',
            _type='button',
            cid=request.cid
        )

        if reader == 'slider':
            slider_data['_id'] = 'vertical_align_button'
            slider_data['_title'] = 'Center book page in window.'

        slider_link = A(
            SPAN('slider'),
            **slider_data
        )

        default_start_page_no = 1

        try:
            start_page_no = int(book_page.page_no)
        except (TypeError, ValueError):
            start_page_no = default_start_page_no

        if start_page_no < 1:
            start_page_no = default_start_page_no
        if start_page_no > len(page_images):
            start_page_no = len(page_images)

        view_dict = dict(
            auth_user=auth_user,
            book=book_record,
            creator=creator_record,
            links=[scroll_link, slider_link],
            pages=page_images,
            reader=reader,
            size='web',
            start_page_no=start_page_no,
        )

        view = 'books/slider.html' if reader == 'slider' else \
            'books/scroller.html'
        return (view_dict, view)

    pre_links = []
    if creator_record.tumblr:
        pre_links.append(
            A('tumblr', _href=creator_record.tumblr, _target='_blank'))
    if creator_record.wikipedia:
        pre_links.append(
            A('wikipedia', _href=creator_record.wikipedia, _target='_blank'))

    if book_record and book_record.status:

        cover = read_link(
            db,
            book_record,
            [cover_image(
                db,
                book_record.id,
                size='web',
                img_attributes={'_class': 'img-responsive'}
            )]
        )

        read_button = read_link(
            db,
            book_record,
            **dict(
                _class='btn btn-default',
                _type='button',
            )
        )

        view_dict = dict(
            auth_user=auth_user,
            book=book_record,
            cover_image=cover,
            creator=creator_record,
            creator_links=CustomLinks(db.creator, creator_record.id).represent(
                pre_links=pre_links),
            links=CustomLinks(db.book, book_record.id).represent(),
            page_count=db(db.book_page.book_id == book_record.id).count(),
            read_button=read_button,
        )

        view = 'books/book.html'
        return (view_dict, view)

    view_dict = dict(
        auth_user=auth_user,
        creator=creator_record,
        links=CustomLinks(
            db.creator, creator_record.id).represent(pre_links=pre_links),
    )

    view = 'creators/creator.html'

    return (view_dict, view)


def page_not_found(db, request, creator_id, book_id, page_id):
    """Redirect to the page not found.

    Args:
        db: gluon.dal.DAL instance
        request: gluon.globals.Request instance.
        creator_id: integer, id of creator record
        book_id: integer, id of book record
        page_id: integer, id of book_page record
    """
    urls = Storage({})
    urls.invalid = '{scheme}://{host}{uri}'.format(
        scheme=request.env.wsgi_url_scheme,
        host=request.env.http_host,
        uri=request.env.web2py_original_uri or request.env.request_uri
    )

    creator_record = None
    book_record = None
    page_record = None

    # Get an existing book page and use it for examples
    # Logic:
    #   if page_id: use that book_page
    #   elif book_id: use first page of that book
    #   elif creator_id: use first page of first book with pages from creator
    #   else : use first page of first book with pages from first creator

    query_wants = []
    if page_id:
        query_wants.append((db.book_page.id == page_id))
    if book_id:
        query_wants.append((db.book.id == book_id))
    if creator_id:
        query_wants.append((db.creator.id == creator_id))
    query_wants.append(None)

    for query_want in query_wants:
        queries = []
        if query_want:
            queries.append(query_want)
        queries.append((db.book_page.id is not None))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        rows = db(query).select(
            db.book_page.id,
            db.book.id,
            db.creator.id,
            left=[
                db.book.on(db.book_page.book_id == db.book.id),
                db.creator.on(db.book.creator_id == db.creator.id),
            ],
            orderby=[db.creator.path_name, db.book_page.page_no],
            limitby=(0, 1),
        )
        if rows:
            page_record = entity_to_row(db.book_page, rows[0].book_page.id)
            book_record = entity_to_row(db.book, rows[0].book.id)
            creator_record = entity_to_row(db.creator, rows[0].creator.id)
            break

    urls.page = urllib.unquote(page_url(page_record, host=True)) \
        if page_record else None
    urls.book = urllib.unquote(book_url(book_record, host=True)) \
        if book_record else None
    urls.creator = urllib.unquote(creator_url(creator_record, host=True)) \
        if creator_record else None
    message = 'The requested page was not found on this server.'

    view_dict = dict(urls=urls, message=message)
    view = 'default/page_not_found.html'
    return (view_dict, view)
