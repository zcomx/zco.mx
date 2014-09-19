#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Routing classes and functions.
"""
from gluon.html import A, SPAN
from applications.zcomx.modules.books import \
    ViewEvent, \
    by_attributes, \
    cover_image, \
    page_url, \
    parse_url_name, \
    read_link
from applications.zcomx.modules.links import CustomLinks


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
        return (None, None)

    if not creator_record:
        creator_record = db(db.creator.id == creator_id).select(
            db.creator.ALL
        ).first()
        if not creator_record:
            return (None, None)

    auth_user = db(db.auth_user.id == creator_record.auth_user_id).select(
        db.auth_user.ALL
    ).first()
    if not auth_user:
        return (None, None)

    if request.vars.book:
        attrs = parse_url_name(request.vars.book)
        attrs['creator_id'] = creator_record.id
        book_record = by_attributes(attrs)
        if book_record:
            book_id = book_record.id
        else:
            return (None, None)

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
                return (None, None)

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
