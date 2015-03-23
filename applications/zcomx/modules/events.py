#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to events.
"""
import logging
from gluon import *
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

LOG = logging.getLogger('app')


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
            ip_address, record_table, record_
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
