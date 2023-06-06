# -*- coding: utf-8 -*-
"""Torrent controller functions"""
import traceback
from gluon.storage import Storage
from applications.zcomx.modules.books import (
    Book,
    torrent_url as book_torrent_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    torrent_url as creator_torrent_url,
    url as creator_url,
)
from applications.zcomx.modules.downloaders import TorrentDownloader
from applications.zcomx.modules.events import log_download_click
from applications.zcomx.modules.zco import Zco


def download():
    """Download torrent

    request.args(0): one of 'all', 'book', 'creator',
    request.args(1): integer, id of record
        if request.args(0) is 'book' or 'creator'.
        Not used if request.args(0) is 'all'.
    request.vars.no_queue: boolean, if set, don't queue a logs_download job
    """
    if request.args:
        record_table = request.args(0)
        record_id = request.args(1) or 0
        queue_log_downloads = not bool(request.vars.no_queue)
        log_download_click(
            record_table,
            record_id,
            queue_log_downloads=queue_log_downloads,
        )

    return TorrentDownloader().download(request, db)


def route():
    """Parse and route torrent urls.

    Format #1:
        request.vars.torrent: string name of torrent file.
        Examples:

            All:     ?torrent=zco.mx.torrent
            Creator: ?torrent=First_Last_(101.zco.mx).torrent

    Format #2
        request.vars.creator: integer (creator id) or string (creator name)
        request.vars.torrent: string name of torrent file (book).

        Examples:
            Book:    ?creator=123&torrent=My_Book_01_(of 01).torrent
            Book:    ?creator=First_Last&torrent=My_Book_01_(of 01).torrent

        If request.vars.creator is an integer (creator id) the page is
            redirected to the string (creator name) page.

    request.vars.no_queue: boolean, if set, don't queue a logs_download job
    """
    def page_not_found():
        """Handle page not found.

        Ensures that during the page_not_found formatting if any
        exceptions happen they are logged, and a 404 is returned.
        (Then search bots, for example, see they have an invalid page)
        """
        try:
            return formatted_page_not_found()
        except HTTP:
            # These don't need to be logged as they provide no useful info.
            raise
        except Exception as exc:
            for line in traceback.format_exc().split("\n"):
                LOG.error(line)
            raise HTTP(404, "Page not found") from exc

    def formatted_page_not_found():
        """Page not found formatter."""
        urls = Storage({})
        urls.invalid = '{scheme}://{host}{uri}'.format(
            scheme=request.env.wsgi_url_scheme or 'https',
            host=request.env.http_host,
            uri=request.env.web2py_original_uri or request.env.request_uri
        )

        urls.suggestions = [
            {
                'label': 'All torrent:',
                'url': URL(host=True, **(Zco().all_torrent_url)),
            },
        ]

        creator_row = db(db.creator.torrent != None).select(
            orderby='<random>', limitby=(0, 1)).first()
        try:
            creator = Creator.from_id(creator_row.id)
        except LookupError:
            pass
        else:
            urls.suggestions.append({
                'label': 'Cartoonist torrent:',
                'url': creator_torrent_url(creator, host=True),
            })

        book_row = db(db.book.torrent != None).select(
            orderby='<random>', limitby=(0, 1)).first()
        try:
            book = Book.from_id(book_row.id)
        except LookupError:
            pass
        else:
            urls.suggestions.append({
                'label': 'Book torrent:',
                'url': book_torrent_url(book, host=True),
            })

        message = 'The requested torrent was not found on this server.'

        Zco().page_not_found = {
            'message': message,
            'urls': urls,
        }
        raise HTTP(404, 'Page not found')

    if not request.vars:
        return page_not_found()

    if not request.vars.torrent:
        return page_not_found()

    torrent_type = None
    torrent_name = None

    if request.vars.creator:
        creator = None

        # Test for request.vars.creator as creator.id
        try:
            int(request.vars.creator)
        except (TypeError, ValueError):
            pass
        else:
            try:
                creator = Creator.from_id(request.vars.creator)
            except LookupError:
                creator = None

        # Test for request.vars.creator as creator.name_for_url
        if not creator:
            encoded_name = \
                request.vars.creator.encode('latin-1').decode('utf-8')
            name = encoded_name.replace('_', ' ')
            try:
                creator = Creator.from_key({'name_for_url': name})
            except LookupError:
                creator = None

        if not creator:
            return page_not_found()

        if '{i:03d}'.format(i=creator.id) == request.vars.creator:
            # Redirect to name version
            c_url = creator_url(creator)
            redirect_url = '/'.join([c_url, request.vars.torrent])
            if request.vars.no_queue:
                redirect_url += '?no_queue=' + str(request.vars.no_queue)
            redirect(redirect_url)

        torrent_type = 'book'
        torrent_name = request.vars.torrent
    else:
        if request.vars.torrent == 'zco.mx.torrent':
            torrent_type = 'all'
        else:
            torrent_type = 'creator'
            torrent_name = request.vars.torrent

    download_vars = {'no_queue': request.vars.no_queue} \
        if request.vars.no_queue else {}

    if torrent_type == 'all':
        redirect(
            URL(c='torrents', f='download', args='all', vars=download_vars))

    if torrent_type == 'creator':
        query = (db.creator.torrent.like('%/{t}'.format(
            t=torrent_name)))
        creator = db(query).select(limitby=(0, 1)).first()
        if not creator:
            return page_not_found()
        redirect(URL(
            c='torrents',
            f='download',
            args=['creator', creator.id],
            vars=download_vars
        ))

    if torrent_type == 'book':
        extension = '.torrent'
        if torrent_name.endswith(extension):
            book_name = torrent_name[:(-1 * len(extension))]
        encoded_name = book_name.encode('latin-1').decode('utf-8')
        query = (db.book.creator_id == creator.id) & \
            (db.book.name_for_url == encoded_name)
        book = db(query).select(limitby=(0, 1)).first()
        if not book or not book.torrent:
            return page_not_found()
        redirect(URL(
            c='torrents',
            f='download',
            args=['book', book.id],
            vars=download_vars
        ))

    return page_not_found()
