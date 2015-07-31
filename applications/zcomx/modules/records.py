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
    def from_add(cls, data):
        """Add a db record from the given data and return the instance
        associateted with it.

        Args:
            data: dict, {field: value, ...}

        Returns:
            cls instance
        """
        db = current.app.db
        ret = db[cls.db_table].validate_and_insert(**data)
        db.commit()
        if ret.errors:
            msg = ', '.join([
                '{k}: {v}'.format(k=k, v=v)
                for k, v in ret.errors.items()
            ])
            raise SyntaxError(msg)
        return cls.from_id(ret.id)

    @classmethod
    def from_id(cls, record_id):
        """Create instance from record id.

        Args:
            record_id: integer, id of record

        Returns:
            cls instance
        """
        db = current.app.db
        query = (db[cls.db_table].id == record_id)
        record = db(query).select(limitby=(0, 1)).first()
        if not record:
            raise LookupError('Record not found, table {t}, id {i}'.format(
                t=cls.db_table, i=record_id))
        return cls(record.as_dict())

    @classmethod
    def from_key(cls, key):
        """Create instance from key

        Args:
            key: dict, {field: value, ...}

        Returns:
            cls instance
        """
        db = current.app.db
        queries = []
        for k, v in key.iteritems():
            queries.append((db[cls.db_table][k] == v))
        query = reduce(lambda x, y: x & y, queries) if queries else None
        return cls.from_query(query)

    @classmethod
    def from_query(cls, query):
        """Create instance from key

        Args:
            key: dict, {field: value, ...}

        Returns:
            cls instance
        """
        db = current.app.db
        record = db(query).select(limitby=(0, 1)).first()
        if not record:
            raise LookupError('Record not found, table {t}, query {q}'.format(
                t=cls.db_table, q=query))
        return cls(record.as_dict())

    @classmethod
    def from_updated(cls, record, data):
        """Update a db record and return a instance representing the
        updated record.

        Args:
            record: Record (or subclass) instance
            data: dict, {field: value, ...}

        Returns:
            cls instance
        """
        if not record.id:
            msg = 'Unable to update record with out id.'
            raise SyntaxError(msg)

        db = current.app.db
        query = (db[record.db_table].id == record.id)
        ret = db(query).validate_and_update(**data)
        db.commit()
        if ret.errors:
            msg = ', '.join([
                '{k}: {v}'.format(k=k, v=v)
                for k, v in ret.errors.items()
            ])
            raise SyntaxError(msg)
        return cls.from_id(record.id)

    def update_record(self, **data):
        """DEPRECATED do not use. Use from_updated()."""
        for line in traceback.format_stack():
            LOG.error(line)
        LOG.error('Record.update_record called')
        db = current.app.db
        db(db[self.db_table].id == self.id).update(**data)
        db.commit()
