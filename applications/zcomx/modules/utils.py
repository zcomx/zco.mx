#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Utilty classes and functions.
"""
import os
import re
from gluon import *
from pydal.objects import Row
from gluon.html import XmlComponent
from gluon.languages import lazyT
from applications.zcomx.modules.zco import Zco


class ItemDescription(object):
    """Class representing an item description field.

    A description of an item is usually a blob of text. This class provides
    methods to format the description.
    """

    def __init__(self, description, more_text='more', truncate_length=200):
        """Constructor

        Args:
            description: string, the full-length item description
            more_text: string, the text used for the 'more' link.
            truncate_length: integer, if description is longer than this,
                the description is truncated with a '... more' link.
        """
        self.description = description
        self.more_text = more_text
        self.truncate_length = truncate_length

    def as_html(self, **attributes):
        """Return the HTML representation of the description.

        Args:
            attributes: dict of attributes of container DIV
        """
        short_description = self.description
        if self.description and len(self.description) > self.truncate_length:
            try:
                sections = \
                    self.description[:self.truncate_length].rsplit(None, 1)
                short_description = sections[0]
            except (KeyError, TypeError):
                short_description = ''

        divs = []

        if short_description and short_description != self.description:
            anchor = A(
                self.more_text,
                _href='#',
                _class='desc_more_link',
            )

            short_div = DIV(
                short_description,
                ' ... ',
                anchor,
                _class='short_description',
                _title=self.description,
            )

            full_div = DIV(
                self.description,
                _class='full_description hidden',
            )

            divs = [short_div, full_div]
        else:
            divs = [self.description or '']

        kwargs = {}
        kwargs.update(attributes)

        return DIV(*divs, **kwargs)


def abridged_list(items):
    """Return the list of items abridged.
    Example
        given:  [1, 2, 3, 4, 5]
        return: [1, 2, '...', 5]
    """
    if len(items) <= 4:
        return items

    snipped = items[0:2]
    snipped.append('...')
    snipped.append(items[-1])
    return snipped


def default_record(table, ignore_fields=None):
    """Return a dict represent a record from the table with all fields set to
    their default values.

    Args:
        table: gluon.dal.Table instance
        ignore_fields: list of strings, or string. Field names to exclude
            from the returned result.
            None: Return all field names of the table.
            list: List of field names
            string: 'common' => ['id', 'created_on', 'updated_on']

    Returns:
        dict
    """
    record = {}
    if ignore_fields is not None:
        if ignore_fields == 'common':
            ignore_fields = ['id', 'created_on', 'updated_on']
    for f in table.fields:
        if ignore_fields is None or f not in ignore_fields:
            record[f] = table[f].default
    return record


def entity_to_row(table, entity):
    """Return a Row instance for the entity.

    Args:
        table: gluon.dal.Table instance
        entity: Row instance or integer, if integer, this is the id of the
            record. The record is read from the table.
    """
    if not entity:
        return

    if isinstance(entity, Row):
        return entity

    # Assume entity is an id or a Reference instance
    # W0212 (protected-access): *Access to a protected member
    # pylint: disable=W0212
    db = table._db
    return db(table.id == int(entity)).select().first()


def faq_tabs(active='faq'):
    """Return a div of clickable tabs for cartoonists' faq page.

    Args:
        active: string, the tab with this controller is flagged as active.

    Returns:
        DIV instance.
    """

    lis = []
    tabs = [
        {
            'label': 'general',
            'controller': 'faq',
        },
        {
            'label': 'cartoonist',
            'controller': 'faqc',
        },
    ]

    if active not in [x['controller'] for x in tabs]:
        active = 'faq'

    for t in tabs:
        active_css = 'active' if t['controller'] == active else ''
        lis.append(LI(
            A(
                t['label'],
                _href=URL(c='z', f=t['controller'])
            ),
            _class='nav-tab {a}'.format(a=active_css),
        ))

    return DIV(
        UL(
            lis,
            _class='nav nav-tabs',
        ),
        _class='faq_options_container',
    )


def joined_list(items, element):
    """Return a list with element added between each item.

    Similar to str.join() except returns a list.

        >>>joined_list(['a', 'b', 'c'], '@')
        ['a', '@', 'b', '@', 'c']

    Args:
        items: list
        element: anything that can be an element of a list,
    """
    work_items = list(items)
    for x in sorted(range(0, len(work_items) - 1), reverse=True):
        work_items[x + 1:x + 1] = element
    return work_items


def markmin(controller, extra=None):
    """Return data for a controller displaying a markmin doc."""

    Zco().next_url = URL(
        c=current.request.controller,
        f=current.request.function,
        args=current.request.args,
        vars=current.request.vars
    )
    current.response.files.append(
        URL('static', 'bootstrap3-dialog/css/bootstrap-dialog.min.css')
    )

    contribute_link_func = lambda t: A(
        t,
        _href='/contributions/modal',
        _class='contribute_button no_rclick_menu'
    )

    data = dict(
        text=markmin_content('{ctrllr}.mkd'.format(ctrllr=controller)),
        markmin_extra=dict(contribute_link=contribute_link_func),
    )

    if extra:
        data.update(extra)
    return data


def markmin_content(filename):
    """Return markmin content."""
    content = ''
    fullname = os.path.join(current.request.folder, 'private', 'doc', filename)
    with open(fullname) as f:
        content = f.read()
    return content


def move_record(sequential_field, record_id, direction='up', query=None,
                start=1):
    """Move a record in the direction.

    Args:
        sequential_field: gluon.dal.Field instance
        record_id: integer, id of record to move.
        direction: string, 'up' or 'down'
        query: gluon.dal.Query, a query used to filter records updated.
            Only records returned by this query will be reordered.
                db(query).select()
            If None, all records of the table are reordered.
        start: integer, the sequential field value of the first record is set
            to this. Subsequent records have values incremented by 1.
    """
    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212

    db = sequential_field._db
    table = sequential_field.table

    record = db(table.id == record_id).select(table.ALL).first()
    if not record:
        # If the record doesn't exist, it can't be moved.
        return

    # Create a list of ids in order except for the one that is moved.
    filter_query = (table.id != record_id)
    if query:
        filter_query = filter_query & query
    rows = db(filter_query).select(table.id, orderby=sequential_field)
    record_ids = [x.id for x in rows]

    # Insert the moved record in it's new location.
    old_order_value = record[sequential_field.name]
    new_order_value = old_order_value + 1 if direction == 'down' \
        else old_order_value - 1
    if new_order_value < start:
        new_order_value = start
    record_ids.insert(new_order_value - 1, record.id)
    reorder(sequential_field, record_ids=record_ids, query=query, start=start)


def reorder(sequential_field, record_ids=None, query=None, start=1):
    """Reset a table's sequential field values.

    Args:
        sequential_field: gluon.dal.Field instance
        record_ids: list of integers, ids of records of the table in
            sequential order. If None, a list is created from the ids of the
            records of the table in order by sequential_field.
        query: gluon.dal.Query, a query used to filter records updated.
            Only records returned by this query will be reordered.
                db(query).select()
            If None, all records of the table are reordered.
            This is ignored if record_ids is provided.
        start: integer, the sequential field value of the first record is set
            to this. Subsequent records have values incremented by 1.
    """
    # W0212: *Access to a protected member %%s of a client class*
    # pylint: disable=W0212
    db = sequential_field._db
    table = sequential_field.table
    if not record_ids:
        if query is None:
            query = (table.id > 0)
        rows = db(query).select(
            table.id,
            orderby=[sequential_field, table.id]
        )
        record_ids = [x.id for x in rows]
    for count, record_id in enumerate(record_ids, start):
        update_query = (table.id == record_id) & \
            (sequential_field != count)       # Only update if value is changed
        db(update_query).update(**{sequential_field.name: count})
        db.commit()


def replace_in_elements(element, find, replace, callback=None):
    """Replace all occurrences of string in XmlComponent element and its
    children.

    Similar to XmlComponent.elements(find=<find>, replace=<replace>) but finds
    lazyT values.

    Args:
        element: XmlComponent instance.
        find: substring to search for
        replace: string to replace 'find' with.
        callback: function or lambda, called on every element where the
            replace was made. The element is passed as the first parameter,
            ie. callback(element)
    """
    if not hasattr(element, 'components'):
        return
    for i, c in enumerate(element.components):
        if isinstance(c, XmlComponent):
            replace_in_elements(c, find, replace, callback=callback)
        elif isinstance(c, (lazyT, str)) and str(c) == find:
            element.components[i] = replace
            if callback is not None and callable(callback):
                callback(element)


def vars_to_records(request_vars, table, multiple=False):
    """Convert request.vars to dicts representing records in table.

    Args:
        request_vars: Storage, eg request.vars
        table: str, name of table
        multiple: If True, expect multiple records per table.
            multiple        format
            False           tablename_fieldname
            True            tablename_fieldname__n where n is the index

    Returns:
        list of dicts

    Notes:
        Generally with multiple=True the index values are sequential starting
            at 0 but this is not required. Index values can start anywhere,
            have non-sequential values, and fields are expected to be in
            random order in request_vars.
    """
    records = {}
    for k, v in sorted(request_vars.items()):
        if k.find(table) == 0:
            if multiple:
                table_field, index = k.split('__')
            else:
                table_field, index = k, None
            field = re.sub(r'^{s}_'.format(s=table), '', table_field)
            if index not in records:
                records[index] = {}
            records[index][field] = v

    return [records[x] for x in sorted(records.keys())]
