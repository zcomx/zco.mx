# -*- coding: utf-8 -*-
"""Book controller functions"""

from applications.zcomx.modules.books import \
    ViewEvent, \
    cover_image, \
    read_link
from applications.zcomx.modules.links import CustomLinks


def book():
    """Book page controller

    request.args(0): id of book
    """
    if not request.args(0):
        redirect(URL(c='default', f='index'))

    book_record = db(db.book.id == request.args(0)).select(
        db.book.ALL).first()
    if not book_record:
        redirect(URL(c='default', f='index'))
    if not book_record.status:
        redirect(URL(c='default', f='index'))

    creator = db(db.creator.id == book_record.creator_id).select(
        db.creator.ALL).first()
    auth_user = db(db.auth_user.id == creator.auth_user_id).select(
        db.auth_user.ALL).first()

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

    pre_links = []
    if creator.tumblr:
        pre_links.append(A('tumblr', _href=creator.tumblr, _target='_blank'))
    if creator.wikipedia:
        pre_links.append(
            A('wikipedia', _href=creator.wikipedia, _target='_blank'))

    return dict(
        auth_user=auth_user,
        book=book_record,
        cover_image=cover,
        creator=creator,
        creator_links=CustomLinks(db.creator, creator.id).represent(
            pre_links=pre_links),
        links=CustomLinks(db.book, book_record.id).represent(),
        page_count=db(db.book_page.book_id == book_record.id).count(),
        read_button=read_button,
    )


def index():
    """Books grid."""
    # This is no longer used
    redirect(URL(c='default', f='index'))


def reader():
    """Read a book.

    request.args(0): id of book
    response.view should be assigned previous to calling this controller.
    """
    if not request.args(0):
        redirect(URL(c='default', f='index'))

    book_record = db(db.book.id == request.args(0)).select(
        db.book.ALL).first()
    if not book_record:
        redirect(URL(c='default', f='index'))
    if not book_record.status:
        redirect(URL(c='default', f='index'))

    creator_record = db(db.creator.id == book_record.creator_id).select(
        db.creator.ALL).first()
    auth_user = db(db.auth_user.id == creator_record.auth_user_id).select(
        db.auth_user.ALL).first()

    views = [
        'books/carousel.html',
        'books/gallery.html',
        'books/scroller.html',
        'books/slider.html',
    ]

    if response.view not in views:
        response.view = 'books/slider.html'

    page_images = db(db.book_page.book_id == request.args(0)).select(
        db.book_page.image,
        orderby=[db.book_page.page_no, db.book_page.id]
    )
    try:
        current_page = int(request.vars.page)
    except (TypeError, ValueError):
        current_page = 0
    next_page = current_page + 1 if current_page + 1 < len(page_images) else 0
    prev_page = current_page - 1 \
        if current_page - 1 >= 0 else len(page_images) - 1

    size = 'web'

    ViewEvent(book_record, auth.user_id).log()

    return dict(
        auth_user=auth_user,
        book=book_record,
        creator=creator_record,
        pages=page_images,
        current_page=current_page,
        next_page=next_page,
        prev_page=prev_page,
        size=size,
    )


def carousel():
    """Read a book using the carousel.

    request.args(0): id of book
    """
    response.view = 'books/carousel.html'
    return reader()


def gallery():
    """Read a book using the blueimp gallery.

    request.args(0): id of book
    """
    response.files.append(
        URL('static', 'blueimp/Gallery/css/blueimp-gallery.min.css')
    )
    response.view = 'books/gallery.html'
    return reader()


def scroller():
    """Read a book using the scroller.

    request.args(0): id of book
    """
    response.view = 'books/scroller.html'
    return reader()


def slider():
    """Read a book using the slider.

    request.args(0): id of book
    """
    response.view = 'books/slider.html'
    return reader()
