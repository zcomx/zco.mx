# -*- coding: utf-8 -*-
"""RSS controller functions"""
import functools
import traceback
from gluon.storage import Storage
from applications.zcomx.modules.books import (
    Book,
    rss_url as book_rss_url,
)
from applications.zcomx.modules.creators import (
    Creator,
    rss_url as creator_rss_url,
    url as creator_url,
)
from applications.zcomx.modules.rss import channel_from_type
from applications.zcomx.modules.zco import (
    BOOK_STATUS_ACTIVE,
    Zco,
)


def modal():
    """Controller for rss modal.

    request.args(0): integer, optional, id of creator.
    """
    return {}


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
    # pylint: disable=too-many-return-statements
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
                'label': 'All zco.mx rss:',
                'url': URL(host=True, **(Zco().all_rss_url)),
            },
        ]

        creator_row = db(db.creator).select(
            orderby='<random>', limitby=(0, 1)).first()
        try:
            creator = Creator.from_id(creator_row.id)
        except LookupError:
            pass
        else:
            urls.suggestions.append({
                'label': 'Cartoonist rss:',
                'url': creator_rss_url(creator, host=True),
            })

        book_row = db(db.book).select(
            orderby='<random>', limitby=(0, 1)).first()
        try:
            book = Book.from_id(book_row.id)
        except LookupError:
            pass
        else:
            urls.suggestions.append({
                'label': 'Book rss:',
                'url': book_rss_url(book, host=True),
            })

        message = 'The requested rss feed was not found on this server.'
        Zco().page_not_found = {
            'message': message,
            'urls': urls,
        }
        raise HTTP(404, 'Page not found')

    if not request.vars:
        return page_not_found()

    if not request.vars.rss:
        return page_not_found()

    rss_type = None
    rss_name = None

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
        encoded_name = creator_name.encode('latin-1').decode('utf-8')
        query = (db.creator.name_for_url == encoded_name)
        creator = db(query).select(limitby=(0, 1)).first()
        if not creator:
            return page_not_found()

        rss_channel = channel_from_type('creator', record_id=creator.id)
        response.view = 'rss/feed.rss'
        return rss_channel.feed()

    if rss_type == 'book':
        if rss_name.endswith(extension):
            book_name = rss_name[:(-1 * len(extension))]
        encoded_name = book_name.encode('latin-1').decode('utf-8')
        query = (db.book.creator_id == creator.id) & \
            (db.book.name_for_url == encoded_name)
        book = db(query).select(limitby=(0, 1)).first()
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
    creator = None
    if request.args(0):
        creator = Creator.from_id(request.args(0))

    books = None
    if creator:
        queries = []
        queries.append((db.book.creator_id == creator.id))
        queries.append((db.book.status == BOOK_STATUS_ACTIVE))
        queries.append((db.book.release_date == None))
        queries.append((db.book.complete_in_progress != True))
        query = functools.reduce(lambda x, y: x & y, queries)
        books = db(query).select(
            db.book.ALL, orderby=[db.book.name, db.book.number])

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
            default=creator.id if creator else 0,
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
        books=books,
        creator=creator,
        form=form
    )
