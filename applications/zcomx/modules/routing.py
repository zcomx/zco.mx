#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Routing classes and functions.
"""
import os
import re
from gluon import *
from gluon.html import A, SPAN
from gluon.storage import Storage
from applications.zcomx.modules.book_pages import BookPage
from applications.zcomx.modules.books import \
    Book, \
    cover_image, \
    get_page, \
    page_url, \
    read_link, \
    url as book_url
from applications.zcomx.modules.creators import \
    Creator, \
    url as creator_url
from applications.zcomx.modules.events import ViewEvent
from applications.zcomx.modules.html.meta import \
    MetadataFactory, \
    html_metadata_from_records
from applications.zcomx.modules.indicias import BookIndiciaPage
from applications.zcomx.modules.links import \
    BookReviewLinkSet, \
    BuyBookLinkSet, \
    CreatorArticleLinkSet, \
    CreatorPageLinkSet
from applications.zcomx.modules.search import \
    CompletedGrid, \
    CreatorMoniesGrid, \
    OngoingGrid
from applications.zcomx.modules.user_agents import is_bot
from applications.zcomx.modules.zco import \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT, \
    Zco

LOG = current.app.logger


class SpareCreatorError(Exception):
    """Exception class for creator errors."""
    pass


class Router(object):
    """Class representing a Router"""
    not_found_msg = 'The requested page was not found on this server.'

    def __init__(self, db, request, auth):
        """Constructor

        Args:
            db: gluon.dal.DAL instance
            request: gluon.globals.Request instance.
            auth: gluon.tools.Auth instance.
        """
        self.db = db
        self.request = request
        self.auth = auth
        self.view = None
        self.redirect = None
        self.view_dict = {}
        self.creator = None
        self.auth_user_record = None
        self.book = None
        self.book_page_record = None
        self.embed = None
        self.zbr_origin = None

    def get_book(self):
        """Get the record of the book based on request.vars.book.

        Returns:
            gluon.dal.Row representing book record
        """
        db = self.db
        request = self.request
        if not self.book:
            if request.vars.book:
                creator = self.get_creator()
                if creator:
                    match = request.vars.book.lower()
                    query = (db.book.creator_id == creator.id) & \
                        (db.book.name_for_url.lower() == match)
                    book_row = db(query).select(limitby=(0, 1)).first()
                    if book_row:
                        self.book = Book(book_row.as_dict())
        return self.book

    def get_creator(self):
        """Get the record of the creator based on request.vars.creator.

        Returns:
            gluon.dal.Row representing creator record
        """
        db = self.db
        request = self.request
        if not self.creator:
            request_vars_creator = None
            if request.vars.creator:
                # A url like the following can make request.vars.creator a
                # list: https://zco.mx/123?creator=FirstLast
                # This should never happen, but some search bots make such
                # requests.
                if isinstance(request.vars.creator, (list, tuple)):
                    request_vars_creator = request.vars.creator[0]
                else:
                    request_vars_creator = request.vars.creator

            if request_vars_creator:
                # Test for request_vars_creator as creator.id
                try:
                    int(request_vars_creator)
                except (TypeError, ValueError):
                    pass
                else:
                    try:
                        self.creator = Creator.from_id(
                            request_vars_creator)
                    except LookupError:
                        pass

                # Test for request_vars_creator as creator.name_for_url
                if not self.creator:
                    name = request_vars_creator.replace('_', ' ')
                    query = (db.creator.name_for_url.lower() == name.lower())
                    creator_row = db(query).select(limitby=(0, 1)).first()
                    if creator_row:
                        self.creator = Creator(creator_row.as_dict())

                # Raise exception on 'SpareNN' records so 404 is returned.
                if self.creator:
                    re_spare = re.compile(r'Spare\d+')
                    if re_spare.match(self.creator.name_for_url):
                        fmt = 'Spare creator requested: {c}'
                        raise SpareCreatorError(fmt.format(
                            c=self.creator.name_for_url))

        return self.creator

    def _get_book_page(self):
        """Get the record of the book page based on request.vars.page.

        This is a helper function for get_book_page(). It makes it possible
        to return early and reduce nesting.

        Returns:
            gluon.dal.Row representing book_page record
        """
        request = self.request
        if not request.vars.page:
            return

        book = self.get_book()
        if not book:
            return

        # Strip off extension
        parts = request.vars.page.split('.')
        raw_page_no = parts[0]
        try:
            page_no = int(raw_page_no)
        except (TypeError, ValueError):
            page_no = None
        if not page_no:
            return

        record = None
        try:
            record = get_page(book, page_no=page_no)
        except LookupError:
            pass
        if record:
            return record

        # Check if indicia page is requested.
        last_page = None
        try:
            last_page = get_page(book, page_no='last')
        except LookupError:
            pass

        if not last_page or page_no != last_page.page_no + 1:
            return

        try:
            record = get_page(book, page_no='indicia')
        except LookupError:
            record = None
        return record

    def get_book_page(self):
        """Get the record of the book page based on request.vars.page.

        Returns:
            gluon.dal.Row representing book_page record
        """
        if not self.book_page_record:
            self.book_page_record = self._get_book_page()
        return self.book_page_record

    def get_reader(self):
        """Get the reader type.

        Returns:
            string, one of 'scroller', 'slider' or 'draft'
        """
        unreadable_statuses = [BOOK_STATUS_DRAFT, BOOK_STATUS_DISABLED]
        if self.book and self.book.status in unreadable_statuses:
            return 'draft'
        request = self.request
        if request.vars.reader \
                and request.vars.reader in ['scroller', 'slider']:
            return request.vars.reader
        if self.book:
            return self.book.reader

    def page_not_found(self):
        """Set for redirect to the page not found."""
        db = self.db
        request = self.request

        urls = Storage({})
        urls.invalid = '{scheme}://{host}{uri}'.format(
            scheme=request.env.wsgi_url_scheme or 'https',
            host=request.env.http_host,
            uri=request.env.web2py_original_uri or request.env.request_uri
        )

        # Get an existing book page and use it for examples
        # Logic:
        #   if page_record: use that book_page
        #   elif book: use first page of that book
        #   elif creator: use first page of first book with pages from
        #       creator
        #   else: use first page of random released book
        creator = self.get_creator()
        book = self.get_book()
        page_record = self.get_book_page()

        query_wants = []
        if page_record and page_record.id:
            query_wants.append((db.book_page.id == page_record.id))
        if book and book.id:
            query_wants.append((db.book.id == book.id))
        if creator and creator.id:
            query_wants.append((db.creator.id == creator.id))

        # random released book
        random_book = db(db.book.release_date != None).select(
            db.book.id,
            orderby='<random>',
            limitby=(0, 1),
        ).first()
        if random_book:
            query_wants.append((db.book.id == random_book.id))

        url_book_page = None
        url_book = None
        url_creator = None

        for query_want in query_wants:
            queries = []
            if query_want is not None:
                queries.append(query_want)
            queries.append((db.book_page.id != None))
            query = reduce(lambda x, y: x & y, queries) if queries else None
            rows = db(query).select(
                db.book_page.id,
                db.book.id,
                db.creator.id,
                left=[
                    db.book.on(db.book_page.book_id == db.book.id),
                    db.creator.on(db.book.creator_id == db.creator.id),
                ],
                orderby=[
                    db.creator.name_for_url,
                    ~db.book.release_date,
                    db.book_page.page_no
                ],
                limitby=(0, 1),
            )
            if rows:
                if rows[0].book_page.id:
                    url_book_page = BookPage.from_id(rows[0].book_page.id)
                if rows[0].book.id:
                    url_book = Book.from_id(rows[0].book.id)
                if rows[0].creator.id:
                    url_creator = Creator.from_id(rows[0].creator.id)
                break

        urls.suggestions = []
        urls.suggestions.append({
            'label': 'Cartoonist page:',
            'url': creator_url(url_creator, host=True),
        })
        urls.suggestions.append({
            'label': 'Book page:',
            'url': book_url(url_book, host=True),
        })
        urls.suggestions.append({
            'label': 'Read:',
            'url': page_url(url_book_page, host=True),
        })

        Zco().page_not_found = {
            'message': self.not_found_msg,
            'urls': urls,
        }
        raise HTTP(404, 'Page not found')

    def preset_links(self):
        """Return a list of preset links for the creator.

        Returns:
            list of A() instances representing links.
        """
        pre_links = []
        creator = self.get_creator()
        if not creator:
            return []
        for preset in ['shop', 'tumblr', 'facebook']:
            if creator[preset]:
                pre_links.append(
                    A(
                        preset,
                        _href=creator[preset],
                        _target='_blank',
                        _rel='noopener noreferrer'
                    )
                )
        return pre_links

    def route(self):
        """Return vars dict and view for route.

        Notes:
            the view_dict, view and optionally redirect properties are set.
        """
        # pylint: disable=too-many-return-statements
        request = self.request
        if not request.vars.creator:
            self.page_not_found()
            return

        if not self.get_creator():
            self.page_not_found()
            return

        if request.vars.book:
            if not self.get_book():
                self.page_not_found()
                return

        if request.vars.page:
            if not self.get_book_page():
                self.page_not_found()
                return

        self.embed = True if request.vars.embed else False
        self.zbr_origin = request.vars.zbr_origin

        # Handle redirects
        # If the creator is provided as an id, redirect to url with the creator
        # full name.
        if '{i:03d}'.format(i=self.creator.id) == \
                self.request.vars.creator:
            request_vars = request.vars
            if 'creator' in request_vars:
                del request_vars['creator']
            if self.book_page_record:
                self.redirect = page_url(
                    self.book_page_record,
                    reader=self.get_reader(),
                    embed=self.embed,
                )
                return
            if self.book:
                self.redirect = book_url(self.book)
                return
            if self.creator:
                c_url = creator_url(self.creator)
                if request.vars.monies:
                    self.redirect = '/'.join([c_url, 'monies'])
                else:
                    self.redirect = c_url
                return

        preparers = [
            'opengraph',    # Used by facebook sharer.php
            'twitter'       # Used by twitter Cards.
        ]

        self.set_response_meta(preparers)

        if self.book_page_record:
            if request.vars.page and os.path.splitext(request.vars.page)[1]:
                # if page has an extension, eg .jpg, use image view
                self.set_page_image_view()
            else:
                self.set_reader_view()
        elif self.book:
            self.set_book_view()
        elif self.creator:
            if request.vars.monies:
                self.set_creator_monies_view()
            else:
                self.set_creator_view()
        else:
            self.page_not_found()

    def set_book_view(self):
        """Set the view for the book page."""
        creator = self.get_creator()
        book = self.get_book()
        page_count = book.page_count()

        if page_count > 0:
            cover = read_link(
                book,
                [cover_image(
                    book,
                    size='web',
                    img_attributes={
                        '_alt': book.name,
                        '_class': 'img-responsive',
                    }
                )],
                _class='zco_book_reader',
            )
        else:
            cover = cover_image(
                book,
                size='web',
                img_attributes={
                    '_alt': book.name,
                    '_class': 'img-responsive',
                }
            )

        self.view_dict = dict(
            book=book,
            cover_image=cover,
            creator=creator,
            creator_article_link_set=CreatorArticleLinkSet(
                Creator(creator)
            ),
            creator_page_link_set=CreatorPageLinkSet(
                Creator(creator),
                pre_links=self.preset_links()
            ),
            book_review_link_set=BookReviewLinkSet(Book(book)),
            buy_book_link_set=BuyBookLinkSet(Book(book)),
            page_count=page_count,
        )

        self.view = 'books/book.html'

    def set_creator_monies_view(self):
        """Set the view for the creator monies page."""
        request = self.request
        creator = self.get_creator()

        if not request.vars.order:
            request.vars.order = 'book.name'

        grid = CreatorMoniesGrid(default_viewby='tile', creator=creator)
        self.view_dict = dict(
            creator=creator,
            grid=grid.render(),
        )

        self.view = 'creators/monies.html'

    def set_creator_view(self):
        """Set the view for the creator page."""
        db = self.db
        request = self.request
        creator = self.get_creator()

        if not request.vars.order:
            request.vars.order = 'book.name'

        queries = [(db.creator.id == creator.id)]
        completed_grid = CompletedGrid(queries=queries, default_viewby='list')
        ongoing_grid = OngoingGrid(queries=queries, default_viewby='list')

        self.view_dict = dict(
            creator=creator,
            grid=completed_grid,
            creator_article_link_set=CreatorArticleLinkSet(
                Creator(creator)
            ),
            creator_page_link_set=CreatorPageLinkSet(
                Creator(creator),
                pre_links=self.preset_links()
            ),
            ongoing_grid=ongoing_grid.render(),
            completed_grid=completed_grid.render()
        )

        self.view = 'creators/creator.html'

    def set_page_image_view(self):
        """Set the view for the book page image."""
        book_page_record = self.get_book_page()

        self.view_dict = dict(
            image=book_page_record.image,
            size='web',
        )

        self.view = 'books/page_image.html'

    def set_reader_view(self):
        """Set the view for the book reader."""
        request = self.request
        creator = self.get_creator()
        book = self.get_book()
        book_page_record = self.get_book_page()

        reader = self.get_reader()

        page_images = [
            Storage({'image': p.image, 'page_no': p.page_no})
            for p in book.pages()
        ]

        # Add indicia page
        indicia = BookIndiciaPage(book)
        try:
            content = indicia.render()
        except LookupError:
            content = ''

        if content:
            try:
                indicia_page_no = max([x.page_no for x in page_images]) + 1
            except (TypeError, ValueError):
                indicia_page_no = 999999            # Very high number

            page_images.append(Storage({
                'image': 'indicia',
                'page_no': indicia_page_no,
                'content': content,
            }))

        if not is_bot():
            ViewEvent(book, self.auth.user_id).log()

        try:
            first_page = get_page(book, page_no='first')
        except LookupError:
            first_page = None

        # The reader_link is the opposite of the current reader
        reader_link_text = 'scroll' if reader == 'slider' else 'slide'
        link_url_reader = 'scroller' if reader == 'slider' else 'slider'

        reader_link = A(
            SPAN(reader_link_text),
            _href=page_url(
                first_page,
                reader=link_url_reader,
                embed=self.embed,
                zbr_origin=self.zbr_origin,
            ),
            _class='btn btn-default scroller_slider_link',
            cid=request.cid
        )

        # Add css for RSS modal
        current.response.files.append(
            URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
        )

        use_scroller_if_short_view = False
        if 'reader' not in request.vars \
                and reader != 'scroller' \
                and indicia.get_orientation() != 'landscape':
            use_scroller_if_short_view = True

        book_marks = Zco().book_marks
        resume_page_no = book_marks[book.id] if book.id in book_marks else 1
        if resume_page_no < 1:
            resume_page_no = 1
        if resume_page_no > len(page_images):
            resume_page_no = len(page_images)

        self.view_dict = dict(
            book=book,
            creator=creator,
            pages=page_images,
            reader=reader,
            reader_link=reader_link,
            resume_page_no=resume_page_no,
            size='web',
            start_page_no=book_page_record.page_no,
            use_scroller_if_short_view=use_scroller_if_short_view,
        )

        self.view = 'books/{reader}.html'.format(reader=reader)

    def set_response_meta(self, preparer_codes):
        """Set the response.meta.

        Args:
            list of strings, preparer codes
        """
        html_metadata = html_metadata_from_records(
            self.creator, self.book)
        page_type = 'book' if self.book is not None else \
            'creator' if self.creator is not None else \
            'site'

        response = current.response
        response.meta = MetadataFactory(
            preparer_codes, html_metadata, page_type=page_type).metadata()
