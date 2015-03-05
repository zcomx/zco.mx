# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
import logging
from applications.zcomx.modules.books import DownloadEvent
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')


def index():
    """Contributions grid."""
    redirect(URL(c='default', f='index'))


def modal():
    """Downloads input controller for modal view.

    request.args(0): integer, id of book (required)
    """
    do_error = lambda msg: redirect(
        URL(c='default', f='modal_error', vars={'message': msg}))

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record:
        do_error('Invalid data provided')
    if not book_record.cbz:
        do_error('This book is not available for download.')

    # Use a web2py form to log download events. The form is not actually
    # displayed on the page. It is submitted with ajax in downloads.js.
    # The formkey checking will permit only a single download per view of the
    # page.
    fields = [
        Field(
            'book_id',
            type='string',
            default=book_record.id,
        ),
    ]

    form = SQLFORM.factory(
        *fields,
        formstyle='table2cols',
        submit_button='Submit'
    )

    formname = 'download_modal_check'
    if form.process(
            keepvalues=True, message_onsuccess='', formname=formname).accepted:
        DownloadEvent(book_record, auth.user_id).log()

    return dict(book=book_record, form=form)
