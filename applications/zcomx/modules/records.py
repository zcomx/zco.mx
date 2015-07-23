#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

Class and functions relatedo database records.
"""
import logging
import traceback
from gluon import *
from pydal.objects import Row

LOG = logging.getLogger('app')


class Record(Row):
    """Base class representing a database record."""

    db_table = None

    def __init__(self, *args, **kwargs):
        """Initializer"""
        Row.__init__(self, *args, **kwargs)

    def delete(self):
        """Delete the record from the db"""
        db = current.app.db
        db(db[self.db_table].id == self.id).delete()
        db.commit()

    def delete_record(self):
        """DEPRECATED use delete()."""
        for line in traceback.format_stack():
            LOG.error(line)
        LOG.error('Record.delete_record called')
        return self.delete()

    @classmethod
    def from_id(cls, record_id, db_table=None):
        """Create instance from record id.

        Args:
            record_id: integer, id of record
            db_table: str, name of database table
                Defaults to cls.db_table.

        Returns:
            cls instance
        """
        db = current.app.db
        table = db_table or cls.db_table
        query = (db[table].id == record_id)
        record = db(query).select().first()
        if not record:
            raise LookupError('Record not found, table {t}, id {i}'.format(
                t=table, i=record_id))
        return cls(record.as_dict())

    @classmethod
    def from_key(cls, key, db_table=None):
        """Create instance from key

        Args:
            key: dict, {field: value, ...}
            db_table: str, name of database table
                Defaults to cls.db_table.

        Returns:
            cls instance
        """
        db = current.app.db
        table = db_table or cls.db_table
        queries = []
        for k, v in key.iteritems():
            queries.append((db[table][k] == v))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        record = db(query).select().first()
        if not record:
            raise LookupError('Record not found, table {t}, key {k}'.format(
                t=table, k=key))
        return cls(record.as_dict())

    def save(self):
        """Save the record to the db."""
        db = current.app.db
        record_id = db[self.db_table].insert(**self.as_dict())
        db.commit()
        return record_id

    def update_record(self, **data):
        """DEPRECATED do not use."""
        for line in traceback.format_stack():
            LOG.error(line)
        LOG.error('Record.update_record called')
        db = current.app.db
        db(db[self.db_table].id == self.id).update(**data)
        db.commit()
