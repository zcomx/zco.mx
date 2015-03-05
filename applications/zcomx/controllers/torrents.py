# -*- coding: utf-8 -*-
"""Torrent controller functions"""
import logging
from gluon.storage import Storage
from applications.zcomx.modules.books import \
    torrent_url as book_torrent_url
from applications.zcomx.modules.creators import \
    torrent_url as creator_torrent_url, \
    url as creator_url
from applications.zcomx.modules.downloaders import TorrentDownloader
from applications.zcomx.modules.utils import entity_to_row

LOG = logging.getLogger('app')


def download():
    """Download torrent

    request.args(0): one of 'all', 'book', 'creator',
    request.args(1): integer, id of record
        if request.args(0) is 'book' or 'creator'.
        Not used if request.args(0) is 'all'.
    """
    return TorrentDownloader().download(request, db)


def route():
    """Parse and route torrent urls.

    Format #1:
        request.args(0): string name of torrent file.
        Examples:

            All:     /zco.mx.torrent
            Creator: /First Last (101.zco.mx).torrent
            Book:    /My Book 01 (of 01) (2015) (123.zco.mx).cbz.torrent

    Format #2
        request.args(0): integer (creator id) or string (creator name)
        request.args(1): string name of torrent file.

        Examples:
            Book:    123/My Book 01 (of 01) (2015) (123.zco.mx).torrent
            Book:    First_Last/My Book 01 (of 01) (2015) (123.zco.mx).torrent

        Note: the '.cbz' is not included.
        If request.args(0) is an integer (creator id) the page is redirected to
            the string (creator name) page.
    """

    def page_not_found():
        """Handle page not found."""
        urls = Storage({})
        urls.invalid = '{scheme}://{host}{uri}'.format(
            scheme=request.env.wsgi_url_scheme or 'https',
            host=request.env.http_host,
            uri=request.env.web2py_original_uri or request.env.request_uri
        )

        urls.suggestions = [
            {
                'label': 'All torrent:',
                'url': URL(
                    c='torrents', f='route', args='zco.mx.torrent', host=True),
            },
        ]

        creator = db(db.creator.torrent != None).select(
            orderby=db.creator.id).first()
        if creator:
            urls.suggestions.append({
                'label': 'Creator torrent:',
                'url': creator_torrent_url(creator, host=True),
            })

        book = db(db.book.torrent != None).select(orderby=db.book.id).first()
        if book:
            urls.suggestions.append({
                'label': 'Book torrent:',
                'url': book_torrent_url(book, host=True),
            })

        response.view = 'errors/page_not_found.html'
        message = 'The requested torrent was not found on this server.'
        return dict(urls=urls, message=message)

    if not request.args:
        return page_not_found()

    torrent_type = None
    torrent_name = None

    if len(request.args) == 2:
        creator_record = None

        # Test for request.args(0) as creator.id
        try:
            int(request.args(0))
        except (TypeError, ValueError):
            pass
        else:
            creator_record = entity_to_row(
                db.creator,
                request.args(0)
            )

        # Test for request.vars.creator as creator.path_name
        if not creator_record:
            name = request.args(0).replace('_', ' ')
            query = (db.creator.path_name == name)
            creator_record = db(query).select().first()

        if not creator_record:
            return page_not_found()

        if '{i:03d}'.format(i=creator_record.id) == request.args(0):
            # Redirect to name version
            c_url = creator_url(creator_record)
            redirect('/'.join([c_url, request.args(1)]))

        torrent_type = 'book'
        torrent_name = request.args(1)
        if torrent_name.endswith('.torrent') \
                and not torrent_name.endswith('.cbz.torrent'):
            torrent_name = ''.join(
                [torrent_name.rstrip('.torrent'), '.cbz.torrent'])
    else:
        if request.args(0) == 'zco.mx.torrent':
            torrent_type = 'all'
        elif request.args(0).endswith('.cbz.torrent'):
            torrent_type = 'book'
            torrent_name = request.args(0)
        else:
            torrent_type = 'creator'
            torrent_name = request.args(0)

    if torrent_type == 'all':
        redirect(URL(download, args='all'))

    if torrent_type == 'creator':
        query = (db.creator.torrent.like('%/{t}'.format(
            t=torrent_name)))
        creator = db(query).select().first()
        if creator:
            redirect(URL(download, args=['creator', creator.id]))
        else:
            return page_not_found()

    if torrent_type == 'book':
        query = (db.book.torrent.like('%/{t}'.format(t=torrent_name)))
        book = db(query).select().first()
        if book:
            redirect(URL(download, args=['book', book.id]))
        else:
            return page_not_found()

    return page_not_found()
