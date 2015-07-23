# -*- coding: utf-8 -*-
"""RSS controller functions"""
import cgi
import logging
import traceback
from gluon.storage import Storage
from applications.zcomx.modules.book_lists import OngoingBookList
from applications.zcomx.modules.books import \
    rss_url as book_rss_url
from applications.zcomx.modules.creators import \
    Creator, \
    rss_url as creator_rss_url, \
    url as creator_url
from applications.zcomx.modules.rss import channel_from_type
from applications.zcomx.modules.zco import Zco

LOG = logging.getLogger('app')


def modal():
    """Controller for rss modal.

    request.args(0): integer, optional, id of creator.
    """
    return dict()


def route():
    """Parse and route rss urls.

    Format #1:
        request.vars.rss: string name of rss file.
        Examples:

            All:     ?rss=zco.mx.rss
            Creator: ?rss=FirstLast.rss

    Format #2
        request.vars.creator: integer (creator id) or string (creator name)
        request.vars.rss: string 'name for url' of book.

        Examples:
            Book:    ?creator=123&rss=MyBook-01of01.rss
            Book:    ?creator=FirstLast&rss=MyBook-01of01.rss

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

        urls.suggestions = [
            {
                'label': 'All zco.mx rss:',
                'url': URL(host=True, **(Zco().all_rss_url)),
            },
        ]

        creator = db(db.creator).select(orderby='<random>').first()
        if creator:
            urls.suggestions.append({
                'label': 'Cartoonist rss:',
                'url': creator_rss_url(creator, host=True),
            })

        book = db(db.book).select(orderby='<random>').first()
        if book:
            urls.suggestions.append({
                'label': 'Book rss:',
                'url': book_rss_url(book, host=True),
            })

        response.view = 'errors/page_not_found.html'
        message = 'The requested rss feed was not found on this server.'
        return dict(urls=urls, message=message)

    if not request.vars:
        return page_not_found()

    if not request.vars.rss:
        return page_not_found()

    rss_type = None
    rss_name = None

    if request.vars.creator:
        creator_record = None

        # Test for request.vars.creator as creator.id
        try:
            int(request.vars.creator)
        except (TypeError, ValueError):
            pass
        else:
            creator_record = Creator.from_id(request.vars.creator)

        # Test for request.vars.creator as creator.name_for_url
        if not creator_record:
            name = request.vars.creator.replace('_', ' ')
            creator_record = Creator.from_key({'name_for_url': name})

        if not creator_record:
            return page_not_found()

        if '{i:03d}'.format(i=creator_record.id) == request.vars.creator:
            # Redirect to name version
            c_url = creator_url(creator_record)
            redirect_url = '/'.join([c_url, request.vars.rss])
            redirect(redirect_url)

        rss_type = 'book'
        rss_name = request.vars.rss
    else:
        if request.vars.rss == 'zco.mx.rss':
            rss_type = 'all'
        else:
            rss_type = 'creator'
            rss_name = request.vars.rss

    if rss_type == 'all':
        rss_channel = channel_from_type('all')
        response.view = 'rss/feed.rss'
        return rss_channel.feed()

    extension = '.rss'
    if rss_type == 'creator':
        creator_name = rss_name
        if rss_name.endswith(extension):
            creator_name = rss_name[:(-1 * len(extension))]
        query = (db.creator.name_for_url == creator_name)
        creator = db(query).select().first()
        if not creator:
            return page_not_found()

        rss_channel = channel_from_type('creator', record_id=creator.id)
        response.view = 'rss/feed.rss'
        return rss_channel.feed()

    if rss_type == 'book':
        if rss_name.endswith(extension):
            book_name = rss_name[:(-1 * len(extension))]
        query = (db.book.creator_id == creator_record.id) & \
            (db.book.name_for_url == book_name)
        book = db(query).select().first()
        if not book:
            return page_not_found()

        rss_channel = channel_from_type('book', record_id=book.id)
        response.view = 'rss/feed.rss'
        return rss_channel.feed()

    return page_not_found()


def widget():
    """Controller for rss widget (reader notifications)

    request.args(0): integer, optional, id of creator.
    """
    creator_record = None
    if request.args(0):
        creator_record = Creator.from_id(request.args(0))

    book_records = None
    if creator_record:
        book_list = OngoingBookList(creator_record)
        book_records = book_list.books()

    query = (db.book.id != None)     # Creators must have at least one book.
    creators = db(query).select(
        db.creator.id,
        db.auth_user.name,
        left=[
            db.auth_user.on(db.auth_user.id == db.creator.auth_user_id),
            db.book.on(db.book.creator_id == db.creator.id),
        ],
        groupby=db.creator.id,
        orderby=db.auth_user.name,
    )

    names = [x.creator.id for x in creators]
    labels = [x.auth_user.name for x in creators]

    fields = [
        Field(
            'creator_id',
            type='integer',
            default=creator_record.id if creator_record else 0,
            requires=IS_EMPTY_OR(
                IS_IN_SET(
                    names,
                    labels=labels,
                    zero='- - -',
                )
            )
        ),
    ]

    form = SQLFORM.factory(
        *fields,
        submit_button='Submit'
    )

    form.custom.widget.creator_id['_class'] += ' form-control'

    if form.process(keepvalues=True, message_onsuccess='').accepted:
        redirect(URL(r=request, args=form.vars.creator_id))

    return dict(
        books=book_records,
        creator=creator_record,
        form=form
    )
