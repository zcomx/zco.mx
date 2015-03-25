# -*- coding: utf-8 -*-
"""Torrent controller functions"""
import cgi
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
    """
    # Note: there is a bug in web2py Ver 2.9.11-stable where request.vars
    # is not set by routes.
    # Ticket: http://code.google.com/p/web2py/issues/detail?id=1990
    # If necessary, parse request.env.query_string for the values.
    def parse_get_vars():
        """Adapted from gluon/globals.py class Request"""
        query_string = request.env.get('query_string', '')
        dget = cgi.parse_qs(query_string, keep_blank_values=1)
        get_vars = Storage(dget)
        for (key, value) in get_vars.iteritems():
            if isinstance(value, list) and len(value) == 1:
                get_vars[key] = value[0]
        return get_vars

    request.vars.update(parse_get_vars())

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
                'url': URL(c='zco.mx.torrent', f='index', host=True),
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

    if not request.vars:
        return page_not_found()

    if not request.vars.torrent:
        return page_not_found()

    torrent_type = None
    torrent_name = None

    if request.vars.creator:
        creator_record = None

        # Test for request.vars.creator as creator.id
        try:
            int(request.vars.creator)
        except (TypeError, ValueError):
            pass
        else:
            creator_record = entity_to_row(
                db.creator,
                request.vars.creator
            )

        # Test for request.vars.creator as creator.name_for_url
        if not creator_record:
            name = request.vars.creator.replace('_', ' ')
            query = (db.creator.name_for_url == name)
            creator_record = db(query).select().first()

        if not creator_record:
            return page_not_found()

        if '{i:03d}'.format(i=creator_record.id) == request.vars.creator:
            # Redirect to name version
            c_url = creator_url(creator_record)
            redirect('/'.join([c_url, request.vars.torrent]))

        torrent_type = 'book'
        torrent_name = request.vars.torrent
    else:
        if request.vars.torrent == 'zco.mx.torrent':
            torrent_type = 'all'
        else:
            torrent_type = 'creator'
            torrent_name = request.vars.torrent

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
        book_name = torrent_name.rstrip('.torrent')
        query = (db.book.creator_id == creator_record.id) & \
            (db.book.name_for_url == book_name)
        book = db(query).select().first()
        if not book or not book.torrent:
            return page_not_found()
        if book:
            redirect(URL(download, args=['book', book.id]))
        else:
            return page_not_found()

    return page_not_found()
