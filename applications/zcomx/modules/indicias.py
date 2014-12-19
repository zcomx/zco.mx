#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Indicias classes and functions.
"""
from gluon import *

from applications.zcomx.modules.books import \
    get_page, \
    orientation as page_orientation
from applications.zcomx.modules.utils import \
    NotFoundError, \
    entity_to_row

DEFAULT_BOOK_TYPE = 'one-shot'


class IndiciaPage(object):
    """Class representing an indicia page.

    The indicia page is the web version of the indicia (as opposed to the
    indicia image)
    """
    default_indicia_image = URL(c='static', f='images/indicia_image.png')

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        self.entity = entity
        self.licence = 'FIXME This is the default licence FIXME'        # FIXME
        self.copyright = 'FIXME This is the default copyright FIXME'    # FIXME
        self.creator = None     # Row instance representing creator

    def render(self, orientation='portrait'):
        """Render the indicia page."""
        img_src = self.default_indicia_image
        if self.creator and self.creator.indicia_image:
            img_src = URL(
                c='images',
                f='download',
                args=self.creator.indicia_image,
                vars={'size': 'web'}
            )

        text_divs = []
        text_divs.append(DIV(
            """If you enjoyed this book... consider giving monies !!! Or share on twitter, tumblr and facebook!."""
        ))
        if self.creator:
            text_divs.append(DIV(
                DIV('contribute: http://{i:03d}.zco.mx/monies'.format(
                    i=self.creator.id)),
                DIV('contact info: http://{i:03d}.zco.mx'.format(
                    i=self.creator.id)),
            ))
        text_divs.append(DIV(
            """
            NAME OF BOOK copyright @ 2014 by CREATOR NAME
            All rights reserved. No copying without written
            consent from the author.
            """
        ))

        return DIV(
            DIV(
                IMG(
                    _src=img_src,
                ),
                _class='indicia_image_container',
            ),
            DIV(
                text_divs,
                _class='indicia_text_container',
            ),
            _class='indicia_preview_section {o}'.format(o=orientation)
        )


class BookIndiciaPage(IndiciaPage):
    """Class representing a book indicia page."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.table = db.book
        self.book = entity_to_row(db.book, self.entity)
        self.creator = entity_to_row(db.creator, self.book.creator_id)
        self.licence = 'FIXME insert book licence FIXME'      # FIXME
        self.copyright = 'FIXME insert book copyright FIXME'  # FIXME

    def render(self, orientation=None):
        """Render the indicia page."""
        if orientation is None:
            orientation = page_orientation(
                get_page(self.book, page_no='last'))
            if orientation != 'landscape':
                orientation = 'portrait'
        return IndiciaPage.render(self, orientation=orientation)


class CreatorIndiciaPage(IndiciaPage):
    """Class representing a book indicia page."""

    def __init__(self, entity):
        """Constructor

        Args:
            entity: Row instance or integer representing a record,
                if integer, this is the id of the record. The record is read.
            user_id: integer, id of user triggering event.
        """
        db = current.app.db
        IndiciaPage.__init__(self, entity)
        self.creator = entity_to_row(db.creator, self.entity)
        self.licence = 'FIXME insert creator licence FIXME'      # FIXME
        self.copyright = 'FIXME insert creator copyright FIXME'  # FIXME
