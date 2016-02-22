# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.books import Book
from applications.zcomx.modules.events import log_download_click


def download_click_handler():
    """Ajax callback for logging a download click.

    request.vars.record_table: string, name of table to record download for
    request.vars.record_id: integer, id of record.
    request.vars.no_queue: boolean, if set, don't queue a logs_download job
    """
    def do_error(msg):
        """Error handler."""
        return dumps({'status': 'error', 'msg': msg})

    if not request.vars.record_table \
            or request.vars.record_table not in ['all', 'book', 'creator']:
        return do_error('Invalid data provided')

    record_id = 0
    if request.vars.record_table in ['book', 'creator']:
        try:
            record_id = int(request.vars.record_id)
        except (TypeError, ValueError):
            return do_error('Invalid data provided')

    queue_log_downloads = True if not request.vars.no_queue else False

    click_id = log_download_click(
        request.vars.record_table,
        record_id,
        queue_log_downloads=queue_log_downloads,
    )

    return dumps({
        'id': click_id,
        'status': 'ok',
    })


def index():
    """Contributions grid."""
    redirect(URL(c='default', f='index'))


def modal():
    """Downloads input controller for modal view.

    request.args(0): integer, id of book (required)
    """
    do_error = lambda msg: redirect(
        URL(c='z', f='modal_error', vars={'message': msg}))

    book = None
    if request.args(0):
        try:
            book = Book.from_id(request.args(0))
        except LookupError:
            do_error('Invalid data provided')

    if not book:
        do_error('Invalid data provided')
    if not book.cbz:
        do_error('This book is not available for download.')

    return dict(book=book)
