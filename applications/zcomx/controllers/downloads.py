# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
import logging
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.events import log_download_click
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')


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

    book_record = None
    if request.args(0):
        book_record = entity_to_row(db.book, request.args(0))
    if not book_record:
        do_error('Invalid data provided')
    if not book_record.cbz:
        do_error('This book is not available for download.')

    return dict(book=book_record)
