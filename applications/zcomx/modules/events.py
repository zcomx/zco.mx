# -*- coding: utf-8 -*-

"""

Classes and functions related to events.
"""
import datetime
from gluon import *
from applications.zcomx.modules.books import update_rating
from applications.zcomx.modules.job_queuers import LogDownloadsQueuer
from applications.zcomx.modules.records import Record
from applications.zcomx.modules.user_agents import is_bot

LOG = current.app.logger
LOG_DOWNLOADS_LIMIT = 1000


class BookView(Record):
    """Class representing a book_view record."""
    db_table = 'book_view'


class Contribution(Record):
    """Class representing a contribution record."""
    db_table = 'contribution'


class Download(Record):
    """Class representing a download record."""
    db_table = 'download'


class DownloadClick(Record):
    """Class representing a download_click record."""
    db_table = 'download_click'


class PaypalLog(Record):
    """Class representing a paypal_log record."""
    db_table = 'paypal_log'


class Rating(Record):
    """Class representing a rating record."""
    db_table = 'rating'


class BaseEvent(object):
    """Base class representing a loggable event"""

    def __init__(self, user_id):
        """Constructor

        Args:
            user_id: integer, id of user triggering event.
        """
        self.user_id = user_id

    def _log(self, value=None):
        """Create a record representing a log of the event."""
        raise NotImplementedError

    def log(self, value=None):
        """Log event."""
        self._log(value=value)
        self._post_log()

    def _post_log(self):
        """Post log functionality."""
        raise NotImplementedError


class BookEvent(BaseEvent):
    """Class representing a loggable book event"""

    def __init__(self, book, user_id):
        """Constructor

        Args:
            book: Book instance
            user_id: integer, id of user triggering event.
        """
        super(BookEvent, self).__init__(user_id)
        self.book = book

    def _log(self, value=None):
        raise NotImplementedError

    def _post_log(self):
        raise NotImplementedError


class ContributionEvent(BookEvent):
    """Class representing a book contribution event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.contribution.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(self.book, rating='contribution')


class DownloadEvent(BookEvent):
    """Class representing a book download event."""

    def _log(self, value=None):
        if value is None:
            return
        # value is a download_click_entity
        db = current.app.db
        download_click = DownloadClick.from_id(value)
        if not download_click:
            LOG.error('download_click not found: %s', value)
            return

        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            download_click_id=download_click.id,
        )
        event_id = db.download.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        # download event ratings are updated en masse.
        pass


class RatingEvent(BookEvent):
    """Class representing a book rating event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.rating.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(self.book, rating='rating')


class ViewEvent(BookEvent):
    """Class representing a book view event."""

    def _log(self, value=None):
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=self.book.id,
            time_stamp=datetime.datetime.now()
        )
        event_id = db.book_view.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        db = current.app.db
        update_rating(self.book, rating='view')


class ZcoContributionEvent(BaseEvent):
    """Class representing a contribution to zco.mx event."""

    def _log(self, value=None):
        if value is None:
            return
        db = current.app.db
        data = dict(
            auth_user_id=self.user_id or 0,
            book_id=0,
            time_stamp=datetime.datetime.now(),
            amount=value
        )
        event_id = db.contribution.insert(**data)
        db.commit()
        return event_id

    def _post_log(self):
        pass


def is_loggable(download_click_id, interval_seconds=1800):
    """Determine if a download_click is loggable.

    Args:
        download_click_id: id of download_click record
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
    download_click = DownloadClick.from_id(download_click_id)

    if download_click.record_table == 'all':
        return False

    if download_click.is_bot:
        return False

    click_as_epoch = download_click.time_stamp.strftime('%s')

    # line-too-long (C0301): *Line too long (%%s/%%s)*
    # pylint: disable=C0301
    query = \
        (db.download_click.id != download_click.id) & \
        (db.download_click.ip_address == download_click.ip_address) & \
        (db.download_click.auth_user_id == download_click.auth_user_id) & \
        (db.download_click.record_table == download_click.record_table) & \
        (db.download_click.record_id == download_click.record_id) & \
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
        is_bot=is_bot()
    )
    click_id = db.download_click.insert(**data)
    db.commit()
    query = (db.download_click.id == click_id)
    click_record = db(query).select(limitby=(0, 1)).first()
    if is_loggable(click_id):
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
