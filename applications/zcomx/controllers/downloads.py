# -*- coding: utf-8 -*-
"""
Controllers related to downloads.
"""
import functools
import json
from applications.zcomx.modules.books import (
    Book,
    cbz_url,
    downloadable as downable_books,
    formatted_name,
    magnet_uri,
    torrent_url as book_torrent_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    downloadable as downable_creators,
    torrent_url as creator_torrent_url,
)
from applications.zcomx.modules.records import Records
from applications.zcomx.modules.events import log_download_click


def download_click_handler():
    """Ajax callback for logging a download click.

    request.vars.record_table: string, name of table to record download for
    request.vars.record_id: integer, id of record.
    request.vars.no_queue: boolean, if set, don't queue a logs_download job
    """
    def do_error(msg):
        """Error handler."""
        return json.dumps({'status': 'error', 'msg': msg})

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

    return json.dumps({
        'id': click_id,
        'status': 'ok',
    })


def downloadable_books():
    """Ajax callback to get downloadable books.

    request.args(0): int, id of creator.
    """

    def do_error(msg):
        """Error handler."""
        return json.dumps({'status': 'error', 'msg': msg})

    creator = None
    if request.args:
        try:
            creator = Creator.from_id(int(request.args[0]))
        except LookupError:
            LOG.error('Creator not found, id: %s', request.args[0])

    if not creator:
        return do_error('Unable to get list of books.')

    book_data = []
    for book in downable_books(creator_id=creator.id, orderby=db.book.name):
        try:
            book_data.append(
                {
                    'id': book.id,
                    'title': formatted_name(
                        book,
                        include_publication_year=(book.release_date != None)
                    ),
                    'torrent_url': book_torrent_url(book, extension=False),
                    'magnet_uri': magnet_uri(book),
                    'cbz_url': cbz_url(book, extension=False),
                }
            )
        except Exception:
            continue

    if not book_data:
        return do_error('Unable to get list of books.')

    return json.dumps({
        'books': book_data,
        'status': 'ok',
    })


def downloadable_creators():
    """Ajax callback to get downloadable creators."""

    def do_error(msg):
        """Error handler."""
        return json.dumps({'status': 'error', 'msg': msg})

    creator_data = []
    for creator in downable_creators(orderby=db.creator.name_for_search):
        creator_data.append(
            {
                'id': creator.id,
                'name': creator.name,
                'torrent_url': creator_torrent_url(creator, extension=False),
            }
        )

    if not creator_data:
        return do_error('Unable to get list of creators.')

    return json.dumps({
        'creators': creator_data,
        'status': 'ok',
    })


def index():
    """Contributions grid."""
    redirect(URL(c='default', f='index'))


def modal():
    """Downloads input controller for modal view.

    request.args(0): str, table name, eg 'book' or 'creator', optional
    request.args(1): integer, id of record, optional
    """
    book_id = 0
    creator_id = 0

    if request.args(0) and request.args(1):
        if request.args(0) == 'book':
            book = None
            try:
                book = Book.from_id(request.args(1))
            except LookupError:
                pass
            if book:
                book_id = book.id
                creator_id = book.creator_id
        elif request.args(0) == 'creator':
            creator = None
            try:
                creator = Creator.from_id(request.args(1))
            except LookupError:
                pass
            if creator:
                creator_id = creator.id

    if not creator_id:
        creators = downable_creators(
            orderby=db.creator.name_for_search,
            limitby=(0, 1)
        )
        if creators:
            creator_id = creators[0].id

    if not book_id and creator_id:
        books = downable_books(
            creator_id=creator_id,
            orderby=db.book.name,
            limitby=(0, 1)
        )
        if books:
            book_id = books[0].id

    return dict(
        book_id=book_id,
        creator_id=creator_id,
    )
