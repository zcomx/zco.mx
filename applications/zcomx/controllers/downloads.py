# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
import logging
from gluon.contrib.simplejson import dumps
from applications.zcomx.modules.events import is_loggable
from applications.zcomx.modules.job_queue import \
    LogDownloadsQueuer
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')

LOG_DOWNLOADS_LIMIT = 1000


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

    click_id = db.download_click.insert(
        ip_address=request.client,
        time_stamp=request.now,
        auth_user_id=auth.user_id or 0,
        record_table=request.vars.record_table,
        record_id=record_id,
    )
    db.commit()
    click_record = db(db.download_click.id == click_id).select().first()
    if is_loggable(click_record):
        click_data = {
            'loggable': True,
            'completed': False,
        }
        click_record.update_record(**click_data)
        db.commit()

        if not request.vars.no_queue:
            job = LogDownloadsQueuer(
                db.job,
                cli_options={'-r': True, '-l': str(LOG_DOWNLOADS_LIMIT)},
            ).queue()
            LOG.debug('Log downloads job id: %s', job.id)
    else:
        click_data = {
            'loggable': False,
            'completed': True,
        }
        click_record.update_record(**click_data)
        db.commit()
    return {
        'id': click_record.id,
        'status': 'ok',
    }


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

    return dict(book=book_record)
