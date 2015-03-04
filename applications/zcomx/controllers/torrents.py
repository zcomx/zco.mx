# -*- coding: utf-8 -*-
"""Torrent controller functions"""
import logging
from gluon.storage import Storage
from applications.zcomx.modules.books import \
    torrent_url as book_torrent_url
from applications.zcomx.modules.creators import \
    torrent_url as creator_torrent_url
from applications.zcomx.modules.downloaders import TorrentDownloader

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

    request.args(0): string name of torrent file.

        All:     /zco.mx.torrent
        Creator: /First Last (101.zco.mx).torrent
        Book:    /My Book 01 (of 01) (2015) (98.zco.mx).cbz.torrent
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
    if request.args(0) == 'zco.mx.torrent':
        torrent_type = 'all'
    elif request.args(0).endswith('.cbz.torrent'):
        torrent_type = 'book'
    else:
        torrent_type = 'creator'

    if torrent_type == 'all':
        redirect(URL(download, args='all'))

    if torrent_type == 'creator':
        query = (db.creator.torrent.like('%/{t}'.format(
            t=request.args(0))))
        creator = db(query).select().first()
        if creator:
            redirect(URL(download, args=['creator', creator.id]))
        else:
            return page_not_found()

    if torrent_type == 'book':
        query = (db.book.torrent.like('%/{t}'.format(t=request.args(0))))
        book = db(query).select().first()
        if book:
            redirect(URL(download, args=['book', book.id]))
        else:
            return page_not_found()

    return page_not_found()
