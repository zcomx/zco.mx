# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
import logging
from applications.zcomx.modules.books import \
    ContributionEvent, \
    default_contribute_amount
from applications.zcomx.modules.creators import \
    book_for_contributions, \
    formatted_name
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

LOG = logging.getLogger('app')


def modal():
    """Downloads input controller for modal view.

    request.args(0): integer, id of book (required)
    """
    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record:
        redirect(
            URL('modal_error', vars={'message': 'Invalid data provided'}))

    if not book_record.cbz:
        redirect(
            URL('modal_error', vars={'message': 'This book is not available for download.'}))

    return dict(book=book_record)


def index():
    """Contributions grid."""
    redirect(URL(c='default', f='index'))
