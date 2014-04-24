#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Creator classes and functions.
"""
from gluon import *
from applications.zcomix.modules.utils import \
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
        self.join_to_link_field = self.to_link_table[self.join_to_link_fieldname]

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
                    _type='button',
                    _target='_blank',
                    )
            links_list.append(edit_button)
        links_span = [SPAN(x, _class="custom_link") for x in links_list]
        for count, x in enumerate(form[0]):
            if x.attributes['_id'] == attach_to_id:
                form[0][count].append(
                        TR([
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
            links.append(A(r.name, _href=r.url, _title=r.title, _target='_blank'))
        return links

    def move_link(self, to_link_table_id, direction='up'):
        """Move a link in the order (as indicated by order_no) one spot in
        the specified direction.

        Args:
            to_link_table_id: integer, id of record in to_link_table
            direction: string, 'up' or 'down'
        """
        db = self.table._db
        record = db(self.to_link_table.id == to_link_table_id).select(
                self.to_link_table.ALL).first()

        query = (self.join_to_link_field == record[self.join_to_link_fieldname])
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
        return UL([LI(x) for x in links],
                _class='custom_links breadcrumb',
                )


class ReorderLink(object):
    """Class representing a ReorderLink, a up/down link in a grid that when
    clicked, changes the sequence the row is sorted.
    """

    def __init__(self, table, direction='up', next_url=None):
        """Constructor

        Args:
            table: gluon.dal.Table instance, the table the grid is displaying.
            direction='up': string, either 'down' or 'up', the direction of the link
        """
        self.table = table
        if direction not in ['down', 'up']:
            direction = 'up'
        self.direction = direction
        self.next_url = next_url
        self.label = '{first}{last}'.format(first=direction[0],
                last=direction[-1])
        self.header = self.label.title()
        self._max_order_no = None

    def get_max_order_no(self, row):
        """Determine and return the max order_no for all links of the
        given entity (creator or book)

        Args:
            row: dict of values of a row in a links grid.

        """
        if self._max_order_no is None:
            db = self.table._db
            if str(self.table) in row and 'id' in row[str(self.table)]:
                to_link_table_id = row[str(self.table)]['id']
                entity_tablename = str(self.table).replace('_to_link', '')
                entity_id_fieldname = '{tbl}_id'.format(tbl=entity_tablename)
                query = (self.table[entity_id_fieldname] == row[str(self.table)][entity_id_fieldname])
                try:
                    max_expr = self.table.order_no.max()
                    self._max_order_no = db(query).select(max_expr)[0][max_expr]
                except (KeyError, SyntaxError):
                    self._max_order_no = 0
        return self._max_order_no

    def grid_body_func(self, row):
        """Function suitable for the up and down arrow links in the links
        grid.

        Args:
            row: dict of values of a row in a links grid. Example:
             {'creator_to_link': {'id': 203L, 'order_no': 2L},
             'link': {'url': 'http://www.aaa.com', 'title': 'Aaa', 'id': 228L, 'name': 'aaa'}
             }
        """
        if str(self.table) not in row or 'order_no' not in row[str(self.table)]:
            return SPAN('-')

        order_no = row[str(self.table)]['order_no']

        if self.direction == 'up' and order_no == 1:
            return SPAN('-')

        max_order_no = self.get_max_order_no(row)
        if self.direction == 'down' and order_no >= max_order_no:
            return SPAN('-')

        return A(SPAN('',
                    _class='glyphicon glyphicon-arrow-{dir}'.format(dir=self.direction),
                    _title=self.direction
                    ),
                _href=URL(c='profile', f='order_no_handler',
                    args=[self.table, row[str(self.table)].id, self.direction],
                    vars={'next': self.next_url},
                    extension=False,
                    )
                )

    def links_dict(self):
        """Return a dict suitable for the grid links option."""
        return dict(header=self.header, body=self.grid_body_func)
