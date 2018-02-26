# -*- coding: utf-8 -*-
"""Book controller functions"""
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.zco import Zco


def book():
    """Book page controller """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def index():
    """Books grid."""
    # This is no longer used
    redirect(URL(c='default', f='index'))


def reader():
    """Read a book. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def scroller():
    """Read a book using the scroller. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")


def set_book_mark():
    """Handler for ajax set book mark calls.

    request.vars.book_id: int, id of book
    request.vars.page_no: int, page_no

    """
    response.generic_patterns = ['json']

    def do_error(msg=None):
        """Error handler."""
        return {'status': 'error', 'msg': msg or 'Server request failed'}

    if request.vars.book_id is None:
        return do_error('No book_id provided')
    if request.vars.page_no is None:
        return do_error('No page_no provided')

    try:
        book_id = int(request.vars.book_id)
    except (TypeError, ValueError):
        return do_error('Invalid book_id: {i}'.format(i=request.vars.book_id))

    try:
        page_no = int(request.vars.page_no)
    except (TypeError, ValueError):
        return do_error('Invalid page_no: {i}'.format(i=request.vars.page_no))

    try:
        book_record = Book.from_id(book_id)
    except LookupError:
        book_record = None
    if not book_record:
        return do_error('Book not found, id: {i}.'.format(i=book_id))

    book_marks = Zco().book_marks
    book_marks[book_id] = page_no
    Zco().book_marks = book_marks

    return {'status': 'ok'}


def slider():
    """Read a book using the slider. """
    # The controller is deprecated. The page is handled by routing.
    raise HTTP(404, "Page not found")
