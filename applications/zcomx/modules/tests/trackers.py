#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit test tracker classes and functions.
"""
from gluon import *


class TableTracker(object):
    """Class representing a TableTracker used to track records in a table
    during tests when records can be created in the background and not
    easily controlled.

    Usage:
        tracker = TableTracker(db.job)
        job = tested_function()
        self.assertFalse(tracker.had(job)
        self.assertTrue(tracker.has(job)
    """
    def __init__(self, table, query=None):
        """Constructor

        Args:
            table: gluon.dal.base.Table instance
            query: Query instance
        """
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        self.table = table
        self.query = query if query is not None else self.table
        db = self.table._db
        self._ids = [x.id for x in db(self.query).select(self.table.id)]

    def diff(self):
        """Return the diff of table ids between had and has.

        Args:
            obj: DbObject instance.
        """
        # pylint: disable=protected-access
        db = self.table._db
        ids = [x.id for x in db(self.query).select()]
        diff_ids = list(set(ids).difference(set(self._ids)))
        return [
            db(self.table.id == x).select(limitby=(0, 1)).first()
            for x in diff_ids
        ]

    def had(self, row):
        """Return whether the record represented by row existed when the
        instance was initialized.

        Args:
            row: gluon.dal.objects.Row instance.
        """
        return True if row.id in self._ids else False

    def has(self, row):
        """Return whether the record represented by row exists.

        Args:
            row: gluon.dal.objects.Row instance.
        """
        # protected-access (W0212): *Access to a protected member
        # pylint: disable=W0212
        db = self.table._db
        ids = [x.id for x in db(self.query).select()]
        return True if row.id in ids else False
