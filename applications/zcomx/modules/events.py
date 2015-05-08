#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to events.
"""
import logging
from gluon import *
from applications.zcomx.modules.job_queue import \
    LogDownloadsQueuer
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

LOG = logging.getLogger('app')
LOG_DOWNLOADS_LIMIT = 1000


def is_loggable(download_click_entity, interval_seconds=1800):
    """Determine if a download_click is loggable.

    Args:
        download_click_entity: Row instance or integer representing a
            download_click record.
        interval_seconds: minimum number of seconds that must pass before
            a second click from same user is logged.

    Returns:
        True if download_click should be logged.

    Loggable if:
        There is no previous loggable download click with the same
            ip_address, record_table, record_id within the last
            interval_seconds seconds.
    """
    db = current.app.db
    click = entity_to_row(db.download_click, download_click_entity)
    if not click:
        raise NotFoundError('Download click not found, {e}'.format(
            e=download_click_entity))

    click_as_epoch = click.time_stamp.strftime('%s')

    query = \
        (db.download_click.id != click.id) & \
        (db.download_click.ip_address == click.ip_address) & \
        (db.download_click.auth_user_id == click.auth_user_id) & \
        (db.download_click.record_table == click.record_table) & \
        (db.download_click.record_id == click.record_id) & \
        (db.download_click.loggable == True) & \
        (db.download_click.time_stamp.epoch() - click_as_epoch > -1 * interval_seconds)
    rows = db(query).select(db.download_click.id)
    return len(rows) == 0


def log_download_click(record_table, record_id, queue_log_downloads=True):
    """Log a download click.

    Args:
        record_table: string, name of table for download_click, one of
            ['all', 'book', 'creator']
        record_id: integer, id of record if record_table 'book' or 'creator'
            should be 0 if record_table is 'all'
        queue_log_downloads: If True, queue a job to log all downloads, ie
            convert download_click records to download records.

    Returns:
        integer, id of download_click record.
    """
    db = current.app.db
    request = current.request
    auth = current.app.auth

    data = dict(
        ip_address=request.client,
        time_stamp=request.now,
        auth_user_id=auth.user_id or 0,
        record_table=record_table,
        record_id=record_id,
    )
    click_id = db.download_click.insert(**data)
    db.commit()
    click_record = db(db.download_click.id == click_id).select().first()
    if is_loggable(click_record):
        click_data = {
            'loggable': True,
            'completed': False,
        }
        click_record.update_record(**click_data)
        db.commit()

        if queue_log_downloads:
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
    return click_id
