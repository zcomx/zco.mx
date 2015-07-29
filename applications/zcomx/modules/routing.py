#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Routing classes and functions.
"""
import logging
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
from applications.zcomx.modules.utils import entity_to_row
from applications.zcomx.modules.zco import \
    BOOK_STATUS_DISABLED, \
    BOOK_STATUS_DRAFT

LOG = logging.getLogger('app')


class Router(object):
    """Class representing a Router"""

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
        self.creator_record = None
        self.auth_user_record = None
        self.book_record = None
        self.book_page_record = None

    def get_book(self):
        """Get the record of the book based on request.vars.book.

        Returns:
            gluon.dal.Row representing book record
        """
        db = self.db
        request = self.request
        if not self.book_record:
            if request.vars.book:
                creator_record = self.get_creator()
                if creator_record:
                    match = request.vars.book.lower()
                    query = (db.book.creator_id == creator_record.id) & \
                        (db.book.name_for_url.lower() == match)
                    self.book_record = db(query).select(limitby=(0, 1)).first()
        return self.book_record

    def get_creator(self):
        """Get the record of the creator based on request.vars.creator.

        Returns:
            gluon.dal.Row representing creator record
        """
        db = self.db
        request = self.request
        if not self.creator_record:
            if request.vars.creator:
                # Test for request.vars.creator as creator.id
                try:
                    int(request.vars.creator)
                except (TypeError, ValueError):
                    pass
                else:
                    try:
                        self.creator_record = Creator.from_id(
                            request.vars.creator)
                    except LookupError:
                        pass

                # Test for request.vars.creator as creator.name_for_url
                if not self.creator_record:
                    name = request.vars.creator.replace('_', ' ')
                    query = (db.creator.name_for_url.lower() == name.lower())
                    creator = db(query).select(limitby=(0, 1)).first()
                    if creator:
                        self.creator_record = Creator(creator.as_dict())

                # Raise exception on 'SpareNN' records so 404 is returned.
                if self.creator_record:
                    re_spare = re.compile(r'Spare\d+')
                    if re_spare.match(self.creator_record.name_for_url):
                        fmt = 'Spare creator requested: {c}'
                        raise LookupError(fmt.format(
                            c=self.creator_record.name_for_url))

        return self.creator_record

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

        book_record = self.get_book()
        if not book_record:
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
            record = get_page(book_record, page_no=page_no)
        except LookupError:
            pass
        if record:
            return record

        # Check if indicia page is requested.
        last_page = None
        try:
            last_page = get_page(book_record, page_no='last')
        except LookupError:
            pass

        if not last_page or page_no != last_page.page_no + 1:
            return

        try:
            record = get_page(book_record, page_no='indicia')
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
        if self.book_record and self.book_record.status in unreadable_statuses:
            return 'draft'
        request = self.request
        if request.vars.reader \
                and request.vars.reader in ['scroller', 'slider']:
            return request.vars.reader
        if self.book_record:
            return self.book_record.reader

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
        #   elif book_record: use first page of that book
        #   elif creator_record: use first page of first book with pages from
        #       creator
        #   else: use first page of random released book
        creator_record = self.get_creator()
        book_record = self.get_book()
        page_record = self.get_book_page()

        query_wants = []
        if page_record and page_record.id:
            query_wants.append((db.book_page.id == page_record.id))
        if book_record and book_record.id:
            query_wants.append((db.book.id == book_record.id))
        if creator_record and creator_record.id:
            query_wants.append((db.creator.id == creator_record.id))
        if not query_wants:
            # random released book
            random_book = db(db.book.release_date != None).select(
                db.book.id,
                orderby='<random>',
                limitby=(0, 1),
            ).first()
            if random_book:
                query_wants.append((db.book.id == random_book.id))

        url_book_page = None
        url_book_record = None
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
                    url_book_record = entity_to_row(db.book, rows[0].book.id)
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
            'url': book_url(url_book_record, host=True),
        })
        urls.suggestions.append({
            'label': 'Read:',
            'url': page_url(url_book_page, host=True),
        })
        message = 'The requested page was not found on this server.'

        self.view_dict = dict(urls=urls, message=message)
        self.view = 'errors/page_not_found.html'

    def preset_links(self):
        """Return a list of preset links for the creator.

        Returns:
            list of A() instances representing links.
        """
        pre_links = []
        creator_record = self.get_creator()
        if not creator_record:
            return []
        for preset in ['shop', 'tumblr', 'facebook']:
            if creator_record[preset]:
                pre_links.append(
                    A(
                        preset,
                        _href=creator_record[preset],
                        _target='_blank'
                    )
                )
        return pre_links

    def route(self):
        """Return vars dict and view for route.

        Notes:
            the view_dict, view and optionally redirect properties are set.
        """
        # too-many-return-statements (R0911): *Too many return statements*
        # pylint: disable=R0911
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

        # Handle redirects
        # If the creator is provided as an id, redirect to url with the creator
        # full name.
        if '{i:03d}'.format(i=self.creator_record.id) == \
                self.request.vars.creator:
            request_vars = request.vars
            if 'creator' in request_vars:
                del request_vars['creator']
            if self.book_page_record:
                self.redirect = page_url(
                    self.book_page_record,
                    reader=self.get_reader()
                )
                return
            if self.book_record:
                self.redirect = book_url(self.book_record)
                return
            if self.creator_record:
                c_url = creator_url(self.creator_record)
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
                self.set_page_image_view()
            else:
                self.set_reader_view()
        elif self.book_record:
            self.set_book_view()
        elif self.creator_record:
            if request.vars.monies:
                self.set_creator_monies_view()
            else:
                self.set_creator_view()
        else:
            self.page_not_found()

    def set_book_view(self):
        """Set the view for the book page."""
        db = self.db
        creator_record = self.get_creator()
        book_record = self.get_book()
        page_count = db(db.book_page.book_id == book_record.id).count()

        if page_count > 0:
            cover = read_link(
                db,
                book_record,
                [cover_image(
                    db,
                    book_record,
                    size='web',
                    img_attributes={
                        '_alt': book_record.name,
                        '_class': 'img-responsive',
                    }
                )]
            )
        else:
            cover = cover_image(
                db,
                book_record,
                size='web',
                img_attributes={
                    '_alt': book_record.name,
                    '_class': 'img-responsive',
                }
            )

        self.view_dict = dict(
            book=book_record,
            cover_image=cover,
            creator=creator_record,
            creator_article_link_set=CreatorArticleLinkSet(
                Creator(creator_record)
            ),
            creator_page_link_set=CreatorPageLinkSet(
                Creator(creator_record),
                pre_links=self.preset_links()
            ),
            book_review_link_set=BookReviewLinkSet(Book(book_record)),
            buy_book_link_set=BuyBookLinkSet(Book(book_record)),
            page_count=page_count,
        )

        self.view = 'books/book.html'

    def set_creator_monies_view(self):
        """Set the view for the creator monies page."""
        request = self.request
        creator_record = self.get_creator()

        if not request.vars.order:
            request.vars.order = 'book.name'

        grid = CreatorMoniesGrid(default_viewby='tile', creator=creator_record)
        self.view_dict = dict(
            creator=creator_record,
            grid=grid.render(),
        )

        self.view = 'creators/monies.html'

    def set_creator_view(self):
        """Set the view for the creator page."""
        db = self.db
        request = self.request
        creator_record = self.get_creator()

        if not request.vars.order:
            request.vars.order = 'book.name'

        queries = [(db.creator.id == creator_record.id)]
        LOG.debug('queries: %s', queries)
        completed_grid = CompletedGrid(queries=queries, default_viewby='list')

        LOG.debug('queries: %s', queries)
        ongoing_grid = OngoingGrid(queries=queries, default_viewby='list')

        self.view_dict = dict(
            creator=creator_record,
            grid=completed_grid,
            creator_article_link_set=CreatorArticleLinkSet(
                Creator(creator_record)
            ),
            creator_page_link_set=CreatorPageLinkSet(
                Creator(creator_record),
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
        db = self.db
        request = self.request
        creator_record = self.get_creator()
        book_record = self.get_book()
        book_page_record = self.get_book_page()

        reader = self.get_reader()

        rows = db(db.book_page.book_id == book_record.id).select(
            db.book_page.image,
            db.book_page.page_no,
            orderby=[db.book_page.page_no, db.book_page.id]
        )

        page_images = [Storage(x) for x in rows.as_list()]
        # Add indicia page
        indicia = BookIndiciaPage(book_record)
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

        ViewEvent(book_record, self.auth.user_id).log()

        try:
            first_page = get_page(book_record, page_no='first')
        except LookupError:
            first_page = None

        scroll_link = A(
            SPAN('scroll'),
            _href=page_url(first_page, reader='scroller'),
            _class='btn btn-default {st}'.format(
                st='disabled' if reader == 'scroller' else 'active'),
            cid=request.cid
        )

        slider_data = dict(
            _href=page_url(first_page, reader='slider'),
            _class='btn btn-default active',
            cid=request.cid
        )

        if reader == 'slider':
            slider_data['_id'] = 'vertical_align_button'
            slider_data['_title'] = 'Center book page in window.'
            current.response.files.append(
                URL('static', 'css/slider.css')
            )

        slider_link = A(
            SPAN('slider'),
            **slider_data
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

        self.view_dict = dict(
            book=book_record,
            creator=creator_record,
            links=[scroll_link, slider_link],
            pages=page_images,
            reader=reader,
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
            self.creator_record, self.book_record)
        page_type = 'book' if self.book_record is not None else \
            'creator' if self.creator_record is not None else \
            'site'

        response = current.response
        response.meta = MetadataFactory(
            preparer_codes, html_metadata, page_type=page_type).metadata()
