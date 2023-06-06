#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions related to links.
"""
from gluon import *
from applications.zcomx.modules.records import Record


class Link(Record):
    """Class representing a link record"""
    db_table = 'link'


class Links():
    """Class representing a set of links"""

    def __init__(self, links):
        """Initializer

        Args:
            links: list of Link instances
        """
        self.links = links

    def __len__(self):
        """Return the number of links in the link set."""
        return len(self.links)

    def as_links(self):
        """Return the links as HTML links."""
        return [
            A(
                x.name,
                _href=x.url,
                _target='_blank',
                _rel='noopener noreferrer'
            ) for x in self.links
        ]

    @classmethod
    def from_links_key(cls, links_key):
        """Create a Links instance from the LinksKey instance."""
        db = current.app.db
        query = links_key.filter_query(db.link)
        orderby = [db.link.order_no, db.link.id]
        rows = db(query).select(orderby=orderby)
        return Links([Link(r.as_dict()) for r in rows])

    def represent(
            self,
            pre_links=None,
            post_links=None,
            ul_class='custom_links breadcrumb pipe_delimiter'):
        """Return HTML representing the links suitable for displaying on a
        public webpage.

        Args:
            pre_links: list of A() instances, links are added to the start of
                the links list.
            post_links: list of A() instances, links are added to the end of
                the links list.
            ul_class: string, used for UL class,  <ul class"...this...">
        """
        links = []
        if pre_links:
            links.extend(pre_links)
        links.extend(self.as_links())
        if post_links:
            links.extend(post_links)
        if not links:
            return None
        return UL(
            [LI(x) for x in links],
            _class=ul_class,
        )


class LinksKey():
    """Class representing a LinksKey"""

    def __init__(self, link_type_id, record_table, record_id):
        """Initializer

        Args:
            link_type_id: integer, id of link_type record.
            record_table: string, table name
            record_id: integer, if of record in table_name
        """
        self.link_type_id = link_type_id
        self.record_table = record_table
        self.record_id = record_id

    def filter_query(self, table):
        """Return a query suitable for filtering records in a table for the
        link set.

        Args:
            table: gluon.packages.dal.pydal.objects Table instance
                eg db.link
        Returns:
            gluon.packages.dal.pydal.objects Expression instance
        """
        return (table.link_type_id == self.link_type_id) & \
            (table.record_table == self.record_table) & \
            (table.record_id == self.record_id)

    @classmethod
    def from_link(cls, link):
        """Create a LinksKey instance from a link.

        Args:
            link: Row representing a link record.

        Returns:
            LinksKey instance
        """
        return cls(link.link_type_id, link.record_table, link.record_id)


class LinkType(Record):
    """Class representing a link_type record"""
    db_table = 'link_type'

    @classmethod
    def by_code(cls, code):
        """Factory to return LinkType instance representing link_type record
        with the given code.

        Args:
            code: string, code of liink_type

        Returns:
            LinkType instance
        """
        return cls.from_key({'code': code})


class BaseLinkSet():
    """Base class representing a link set."""

    link_type_code = ''

    def __init__(
            self,
            record,
            pre_links=None,
            post_links=None,
            ul_class='custom_links breadcrumb pipe_delimiter'):
        """Initializer

        Args:
            record: Record instance.
            pre_links: list of A() instances, links are added to the start of
                the links list.
            post_links: list of A() instances, links are added to the end of
                the links list.
            ul_class: string, used for UL class,  <ul class"...this...">
        """
        self.record = record
        self.pre_links = pre_links
        self.post_links = post_links
        self.ul_class = ul_class
        self._link_type = None
        self._links = None

    def __len__(self):
        """Return the number of links in the link set."""
        count = 0
        if self.pre_links:
            count += len(self.pre_links)
        count += len(self.links())
        if self.post_links:
            count += len(self.post_links)
        return count

    def label(self):
        """Return a label for the links set.

        Returns:
            str, the label
        """
        return self.link_type().label

    def link_type(self):
        """Return the LinkType associated with the link set."""
        if not self._link_type:
            self._link_type = LinkType.by_code(self.link_type_code)
        return self._link_type

    def links(self):
        """Return the Links associated with the links."""
        if not self._links:
            self._links = Links.from_links_key(
                LinksKey(
                    self.link_type().id,
                    self.record.db_table,
                    self.record.id
                )
            )
        return self._links

    def represent(self):
        """Return HTML representing the links suitable for displaying on a
        public webpage.
        """
        return self.links().represent(
            pre_links=self.pre_links,
            post_links=self.post_links,
            ul_class=self.ul_class,
        )


class BookReviewLinkSet(BaseLinkSet):
    """Class representing a 'book_review' link set."""

    link_type_code = 'book_review'


class BuyBookLinkSet(BaseLinkSet):
    """Class representing a 'buy_book' link set."""

    link_type_code = 'buy_book'


class CreatorArticleLinkSet(BaseLinkSet):
    """Class representing a 'creator_article' link set."""

    link_type_code = 'creator_article'


class CreatorPageLinkSet(BaseLinkSet):
    """Class representing a 'creator_page' link set."""

    link_type_code = 'creator_page'
