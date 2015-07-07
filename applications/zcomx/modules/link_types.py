#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Classes and functions related to link types.
"""
from gluon import *
from applications.zcomx.modules.records import Record


class LinkType(Record):
    """Class representing a activity_log record"""
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
        db = current.app.db
        query = (db.link_type.code == code)
        link_type = db(query).select().first()
        if not link_type:
            raise LookupError('Link type not found, link: {c}'.format(
                c=code))
        return LinkType(link_type.as_dict())
