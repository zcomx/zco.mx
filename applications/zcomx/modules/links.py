#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
from gluon import *
from applications.zcomx.modules.records import Record


class Link(Record):
    """Class representing a link record"""
    db_table = 'link'


class LinkSet(object):
    """Class representing a LinkSet"""

    def __init__(self, links):
        """Initializer

        Args:
            links: list of Link instances
        """
        self.links = links

    def as_links(self):
        """Return the links as HTML links."""
        return [A(x.name, _href=x.url, _target='_blank') for x in self.links]

    @classmethod
    def from_link_set_key(cls, link_set_key):
        """Create a LinkSet instance from the LinkSetKey instance."""
        db = current.app.db
        query = link_set_key.filter_query(db.link)
        orderby = [db.link.order_no, db.link.id]
        rows = db(query).select(orderby=orderby)
        return LinkSet([Link(r.as_dict()) for r in rows])

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


class LinkSetKey(object):
    """Class representing a LinkSetKey"""

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
        """Create a LinkSetKey instance from a link.

        Args:
            link: Row representing a link record.

        Returns:
            LinkSetKey instance
        """
        return cls(link.link_type_id, link.record_table, link.record_id)
