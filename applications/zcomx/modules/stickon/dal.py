#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
modules/stickon/dal.py

Classes extending functionality of gluon/dal.py.
"""
from gluon import *

LOG = current.app.logger


class RecordGenerator():
    """Class representing a record generator"""

    def __init__(self, query, fields=None, orderby=None, limitby=None):
        """Initializer

        Args:
            query: gluon.dal.Expr
            fields: list of fields to include in output, db().select(*fields)
            orderby: select orderby
            limitby: select limitby
        """
        self.query = query
        self.fields = fields
        self.orderby = orderby
        self.limitby = limitby

    def generator(self):
        """Generator of records."""
        db = current.app.db
        fields = self.fields if self.fields is not None else []
        for r in db(self.query).select(
                *fields, orderby=self.orderby, limitby=self.limitby):
            yield r
