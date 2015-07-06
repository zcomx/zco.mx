#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
from gluon import *
from applications.zcomx.modules.utils import \
    move_record, \
    reorder


class LinkSet(object):
    """Class representing a LinkSet"""

    def __init__(self, link_set_key):
        """Initializer

        Args:
            link_set_key: LinkSetKey instance
        """
        self.link_set_key = link_set_key

    def filter_query(self):
        """Return a query to filter records for the link set.

        Returns:
            gluon.packages.dal.pydal.objects Expression instance
        """
        db = current.app.db
        return (db.link.link_type_id == self.link_set_key.link_type_id) & \
            (db.link.record_table == self.link_set_key.record_table) & \
            (db.link.record_id == self.link_set_key.record_id)

    def links(self):
        """Return a list of links associated with the set."""
        links = []
        db = current.app.db
        query = self.filter_query()
        orderby = [db.link.order_no, db.link.id]
        rows = db(query).select(db.link.ALL, orderby=orderby)
        for r in rows:
            links.append(
                A(r.name, _href=r.url, _target='_blank'))
        return links

    def move_link(self, link_id, direction='up'):
        """Move a link in the order (as indicated by order_no) one spot in
        the specified direction.

        Args:
            link_id: integer, id of link record to move
            direction: string, 'up' or 'down'
        """
        db = current.app.db
        move_record(
            db.link.order_no,
            link_id,
            direction=direction,
            query=self.filter_query()
        )

    def reorder(self, link_ids=None):
        """Reorder the links setting the order_no according to the prescribed
            order in link_ids.

        Args:
            link_ids: list of integers, ids of link records (from self.table)
                Optional. If None, a list is created from the ids of all
                records from self.table ordered by order_no. If not None,
                the records in table are reordered in the order prescribed
                by link_ids.
        """
        db = current.app.db
        return reorder(
            db.link.order_no,
            record_ids=link_ids,
            query=self.filter_query()
        )

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
        links.extend(self.links())
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

    @classmethod
    def from_link(cls, link):
        """Create a LinkSetKey instance from a link.

        Args:
            link: Row representing a link record.

        Returns:
            LinkSetKey instance
        """
        return cls(link.link_type_id, link.record_table, link.record_id)
