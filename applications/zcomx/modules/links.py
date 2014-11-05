#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
from gluon import *
from applications.zcomx.modules.utils import \
    move_record, \
    reorder


class CustomLinks(object):
    """Class representing a set of custom links.

    For example, creators can have a set of custom links pointing to their
    services/memberships, etc.
    """
    def __init__(self, table, record_id):
        """Constructor

        Args:
            table: gluon.dal.Table instance, the table the links are associated
                    with. Eg db.creator or db.book
            record_id: integer, the id of the record in table the links are
                    associated with. Eg value of db.creator.id or db.book.id
        """
        self.table = table
        self.record_id = record_id

        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        db = self.table._db
        self.to_link_tablename = '{tbl}_to_link'.format(tbl=self.table)
        self.to_link_table = db[self.to_link_tablename]
        self.join_to_link_fieldname = '{tbl}_id'.format(tbl=self.table)
        self.join_to_link_field = \
            self.to_link_table[self.join_to_link_fieldname]

    def attach(self, form, attach_to_id, edit_url=None):
        """Attach the representation of the links to a form

        Args:
            form: gluon.slqhtml.SQLFORM instance.
            attach_to_id: string, id of element in form to which the links are
                attached. A table row (tr) is appended to the table after the
                row containing the element with this id.
            edit_url: string, URL for the edit button. If None, no edit button
                is added.
        """
        links_list = self.links()
        if edit_url:
            edit_button = A(
                'Edit', SPAN('', _class='glyphicon glyphicon-new-window'),
                _href=edit_url,
                _class='btn btn-default',
                _target='_blank',
            )
            links_list.append(edit_button)
        links_span = [SPAN(x, _class="custom_link") for x in links_list]
        for count, x in enumerate(form[0]):
            if x.attributes['_id'] == attach_to_id:
                form[0][count].append(
                    TR(
                        [
                            TD('Custom links:', _class='w2p_fl'),
                            TD(links_span, _class='w2p_fw'),
                            TD('', _class='w2p_fc'),
                        ],
                        _id='creator_custom_links__row',
                    ))

    def links(self):
        """Return a list of links."""
        # W0212: *Access to a protected member %%s of a client class*
        # pylint: disable=W0212
        db = self.table._db
        links = []
        query = (db.link.id > 0) & \
                (self.to_link_table.id != None) & \
                (self.table.id == self.record_id)
        left = [
            self.to_link_table.on(
                (self.to_link_table.link_id == db.link.id)
            ),
            self.table.on(self.join_to_link_field == self.table.id),
        ]
        orderby = [self.to_link_table.order_no, self.to_link_table.id]
        rows = db(query).select(db.link.ALL, left=left, orderby=orderby)
        for r in rows:
            links.append(
                A(r.name, _href=r.url, _title=r.title, _target='_blank'))
        return links

    def move_link(self, to_link_table_id, direction='up'):
        """Move a link in the order (as indicated by order_no) one spot in
        the specified direction.

        Args:
            to_link_table_id: integer, id of record in to_link_table
            direction: string, 'up' or 'down'
        """
        # W0212 (protected-access): *Access to a protected member
        # pylint: disable=W0212
        db = self.table._db
        record = db(self.to_link_table.id == to_link_table_id).select(
            self.to_link_table.ALL
        ).first()

        query = \
            (self.join_to_link_field == record[self.join_to_link_fieldname])
        move_record(
            self.to_link_table.order_no,
            record.id,
            direction=direction,
            query=query,
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
        filter_query = (self.join_to_link_field == self.record_id)
        return reorder(
            self.to_link_table.order_no,
            record_ids=link_ids,
            query=filter_query
        )

    def represent(self, pre_links=None, post_links=None):
        """Return HTML representing the links suitable for displaying on a
        public webpage.

        Args:
            pre_links: list of A() instances, links are added to the start of the links list.
            post_links: list of A() instances, links are added to the end of the links list.
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
            _class='custom_links breadcrumb pipe_delimiter',
        )
