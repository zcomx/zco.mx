# -*- coding: utf-8 -*-
"""Torrent controller functions"""
import traceback
from gluon.storage import Storage
from applications.zcomx.modules.books import \
    Book, \
    cbz_url
from applications.zcomx.modules.creators import \
    Creator, \
    url as creator_url
from applications.zcomx.modules.downloaders import CBZDownloader
from applications.zcomx.modules.events import log_download_click


def download():
    """Download cbz file.

    request.args(0): integer, id of book record
    request.vars.no_queue: boolean, if set, don't queue a logs_download job
    """
    if request.args:
        record_table = 'book'
        record_id = request.args(0)
        queue_log_downloads = True if not request.vars.no_queue else False
        log_download_click(
            record_table,
            record_id,
            queue_log_downloads=queue_log_downloads
        )

    return CBZDownloader().download(request, db)


def route():
    """Parse and route cbz urls.

    request.vars.creator: integer (creator id) or string (creator name)
    request.vars.cbz: string name of cbz file

    Examples:
        ?creator=123&cbz=My_Book_01_(of 01).cbz
        ?creator=First_Last&cbz=My_Book_01_(of 01).cbz

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
        except Exception:
            for line in traceback.format_exc().split("\n"):
                LOG.error(line)
            raise HTTP(404, "Page not found")

    def formatted_page_not_found():
        """Page not found formatter."""
        urls = Storage({})
        urls.invalid = '{scheme}://{host}{uri}'.format(
            scheme=request.env.wsgi_url_scheme or 'https',
            host=request.env.http_host,
            uri=request.env.web2py_original_uri or request.env.request_uri
        )

        urls.suggestions = []

        query = (db.book.cbz != None)
        book_row = db(query).select(
            db.book.id, orderby='<random>', limitby=(0, 1)).first()
        book = Book.from_id(book_row.id)
        if book:
            urls.suggestions.append({
                'label': 'CBZ file:',
                'url': cbz_url(book, host=True),
            })

        response.view = 'errors/page_not_found.html'
        message = 'The requested CBZ file was not found on this server.'
        return dict(urls=urls, message=message)

    if not request.vars:
        return page_not_found()

    if not request.vars.creator:
        return page_not_found()

    if not request.vars.cbz:
        return page_not_found()

    cbz_name = request.vars.cbz

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
        name = request.vars.creator.replace('_', ' ')
        try:
            creator = Creator.from_key({'name_for_url': name})
        except LookupError:
            creator = None

    if not creator:
        return page_not_found()

    if '{i:03d}'.format(i=creator.id) == request.vars.creator:
        # Redirect to name version
        c_url = creator_url(creator)
        redirect_url = '/'.join([c_url, request.vars.cbz])
        if request.vars.no_queue:
            redirect_url += '?no_queue=' + str(request.vars.no_queue)
        redirect(redirect_url)

    download_vars = {'no_queue': request.vars.no_queue} \
        if request.vars.no_queue else {}

    extension = '.cbz'
    if cbz_name.endswith(extension):
        book_name = cbz_name[:(-1 * len(extension))]
    query = (db.book.creator_id == creator.id) & \
        (db.book.name_for_url == book_name)
    book = db(query).select(limitby=(0, 1)).first()
    if not book or not book.cbz:
        return page_not_found()
    redirect(URL(
        c='cbz',
        f='download',
        args=[book.id],
        vars=download_vars
    ))

    return page_not_found()
